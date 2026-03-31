"""Extended tests for Serum v1 .fxp parser — FPCh format, edge cases, param extraction."""

import struct
import tempfile
import zlib
from pathlib import Path

import pytest

from src.serum.parser_v1 import (
    parse_fxp,
    _read_fxp_header,
    _extract_params_from_chunk,
    _extract_preset_name,
    _safe_param,
    FXP_MAGIC,
    FXP_HEADER_SIZE,
    SERUM_PLUGIN_ID,
    PARAM_FILTER_TYPE,
    PARAM_FILTER_CUTOFF,
    PARAM_FILTER_RESONANCE,
    SerumV1Preset,
)


def _make_fpch_fxp(params: list[float], preset_name: str = "Test") -> bytes:
    """Create a minimal FPCh format FXP file with zlib-compressed params."""
    # Build parameter block as LE float32
    param_block = b""
    for p in params:
        param_block += struct.pack("<f", p)

    # Compress
    compressed = zlib.compress(param_block)

    # FXP header for FPCh (opaque chunk)
    # Layout: 0-3 magic, 4-7 byte size, 8-11 fxMagic, 12-15 version,
    #         16-19 pluginID, 20-23 pluginVersion, 24-27 numPrograms,
    #         28-31 padding, 32-35 chunk size, 36+ chunk data
    # The parser reads chunk data from offset 36, and _read_fxp_header
    # requires at least FXP_HEADER_SIZE (60) total bytes.
    header = bytearray(36)
    header[0:4] = FXP_MAGIC
    struct.pack_into(">I", header, 4, 32 + len(compressed))
    header[8:12] = b"FPCh"
    struct.pack_into(">I", header, 12, 1)  # version
    struct.pack_into(">I", header, 16, SERUM_PLUGIN_ID)  # plugin ID
    struct.pack_into(">I", header, 20, 1)  # plugin version
    struct.pack_into(">I", header, 24, 1)  # num programs
    struct.pack_into(">I", header, 32, len(compressed))  # chunk size

    # Chunk data starts at offset 36; total must be >= FXP_HEADER_SIZE (60)
    data = bytes(header) + compressed
    if len(data) < FXP_HEADER_SIZE:
        data = data + b"\x00" * (FXP_HEADER_SIZE - len(data))
    return data


def _make_fxck_fxp(num_params: int = 300) -> bytes:
    """Create a minimal FxCk format FXP file."""
    header = bytearray(28)
    header[0:4] = FXP_MAGIC
    struct.pack_into(">I", header, 4, 24 + num_params * 4)
    header[8:12] = b"FxCk"
    struct.pack_into(">I", header, 12, 1)
    struct.pack_into(">I", header, 16, SERUM_PLUGIN_ID)
    struct.pack_into(">I", header, 20, 1)
    struct.pack_into(">I", header, 24, num_params)

    params = bytearray()
    for i in range(num_params):
        params += struct.pack(">f", i / num_params)

    return bytes(header + params)


class TestReadFxpHeader:
    """Tests for _read_fxp_header()."""

    def test_valid_fpch(self):
        data = _make_fpch_fxp([0.5] * 200)
        plugin_id, version, num_programs, chunk_size = _read_fxp_header(data)
        assert plugin_id == SERUM_PLUGIN_ID
        assert chunk_size > 0

    def test_valid_fxck(self):
        data = _make_fxck_fxp(100)
        plugin_id, version, num_params, chunk_size = _read_fxp_header(data)
        assert plugin_id == SERUM_PLUGIN_ID
        assert num_params == 100
        assert chunk_size == 0  # FxCk has no opaque chunk

    def test_invalid_magic(self):
        data = b"XXXX" + b"\x00" * 100
        with pytest.raises(ValueError, match="Invalid FXP magic"):
            _read_fxp_header(data)

    def test_too_small(self):
        data = FXP_MAGIC + b"\x00" * 10
        with pytest.raises(ValueError, match="too small"):
            _read_fxp_header(data)

    def test_unsupported_format(self):
        data = bytearray(100)
        data[0:4] = FXP_MAGIC
        data[8:12] = b"ZZZZ"
        with pytest.raises(ValueError, match="Unsupported FXP format"):
            _read_fxp_header(bytes(data))


class TestExtractParamsFromChunk:
    """Tests for _extract_params_from_chunk()."""

    def test_zlib_compressed(self):
        params = [0.1, 0.2, 0.3, 0.4]
        raw = b"".join(struct.pack("<f", p) for p in params)
        compressed = zlib.compress(raw)
        result = _extract_params_from_chunk(compressed)
        assert len(result) == 4
        assert abs(result[0] - 0.1) < 1e-6
        assert abs(result[3] - 0.4) < 1e-6

    def test_uncompressed_fallback(self):
        params = [1.0, 2.0, 3.0]
        raw = b"".join(struct.pack("<f", p) for p in params)
        result = _extract_params_from_chunk(raw)
        assert len(result) == 3
        assert abs(result[0] - 1.0) < 1e-6

    def test_empty_chunk(self):
        result = _extract_params_from_chunk(b"")
        assert result == []


class TestExtractPresetName:
    """Tests for _extract_preset_name()."""

    def test_fallback_from_header(self):
        data = b"\x00" * 36 + b"MyPreset\x00" + b"\x00" * 50
        name = _extract_preset_name(data)
        assert name == "MyPreset"

    def test_empty_name(self):
        data = b"\x00" * 200
        name = _extract_preset_name(data)
        assert name == ""


class TestSafeParam:
    """Tests for _safe_param()."""

    def test_valid_index(self):
        params = [0.1, 0.2, 0.3]
        assert _safe_param(params, 1) == 0.2

    def test_out_of_range(self):
        params = [0.1]
        assert _safe_param(params, 5) == 0.0

    def test_negative_index(self):
        params = [0.1, 0.2]
        assert _safe_param(params, -1) == 0.0

    def test_custom_default(self):
        params = []
        assert _safe_param(params, 0, default=0.5) == 0.5


class TestParseFxpFPCh:
    """Tests for parse_fxp() with FPCh (opaque chunk) format."""

    def test_fpch_basic(self, tmp_path):
        # Create params with known filter values at expected offsets
        params = [0.0] * 200
        params[PARAM_FILTER_TYPE] = 3.0
        params[PARAM_FILTER_CUTOFF] = 0.75
        params[PARAM_FILTER_RESONANCE] = 0.3
        data = _make_fpch_fxp(params)

        fxp = tmp_path / "test.fxp"
        fxp.write_bytes(data)

        preset = parse_fxp(fxp)
        assert isinstance(preset, SerumV1Preset)
        assert abs(preset.filter_type_raw - 3.0) < 1e-4
        assert abs(preset.filter_cutoff - 0.75) < 1e-4
        assert abs(preset.filter_resonance - 0.3) < 1e-4

    def test_fpch_all_filter_params(self, tmp_path):
        params = [0.0] * 200
        params[PARAM_FILTER_TYPE] = 5.0
        params[PARAM_FILTER_CUTOFF] = 0.6
        params[PARAM_FILTER_RESONANCE] = 0.4
        from src.serum.parser_v1 import (
            PARAM_FILTER_DRIVE, PARAM_FILTER_FAT,
            PARAM_FILTER_MIX, PARAM_FILTER_PAN,
            PARAM_FILTER_ENV_ATTACK, PARAM_FILTER_ENV_DECAY,
            PARAM_FILTER_ENV_SUSTAIN, PARAM_FILTER_ENV_RELEASE,
            PARAM_FILTER_ENV_AMOUNT,
        )
        params[PARAM_FILTER_DRIVE] = 0.7
        params[PARAM_FILTER_FAT] = 0.2
        params[PARAM_FILTER_MIX] = 0.9
        params[PARAM_FILTER_PAN] = 0.3
        params[PARAM_FILTER_ENV_ATTACK] = 0.1
        params[PARAM_FILTER_ENV_DECAY] = 0.5
        params[PARAM_FILTER_ENV_SUSTAIN] = 0.8
        params[PARAM_FILTER_ENV_RELEASE] = 0.4
        params[PARAM_FILTER_ENV_AMOUNT] = 0.6

        data = _make_fpch_fxp(params)
        fxp = tmp_path / "full.fxp"
        fxp.write_bytes(data)

        preset = parse_fxp(fxp)
        assert abs(preset.filter_drive - 0.7) < 1e-4
        assert abs(preset.filter_fat - 0.2) < 1e-4
        assert abs(preset.filter_mix - 0.9) < 1e-4
        assert abs(preset.filter_env_attack - 0.1) < 1e-4
        assert abs(preset.filter_env_amount - 0.6) < 1e-4


class TestParseFxpEdgeCases:
    """Edge cases for parse_fxp()."""

    def test_fxck_with_few_params(self, tmp_path):
        """FxCk with fewer params than filter offsets — should use defaults."""
        data = _make_fxck_fxp(10)  # Only 10 params, filter offsets are 140+
        fxp = tmp_path / "small.fxp"
        fxp.write_bytes(data)
        preset = parse_fxp(fxp)
        assert preset.filter_type_raw == 0.0  # default
        assert preset.filter_cutoff == 0.0

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            parse_fxp("/nonexistent/file.fxp")

    def test_preset_dataclass_defaults(self):
        preset = SerumV1Preset(
            preset_name="X", plugin_id=0, version=1, num_params=0, params=[],
        )
        assert preset.filter_pan == 0.5
        assert preset.filter_env_sustain == 1.0
        assert preset.filter_env_release == 0.3
