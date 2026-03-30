"""Tests for Serum preset parsers.

Note: Full parsing tests require actual .fxp/.SerumPreset files.
These tests verify the parser structure and error handling.
"""

import struct
import tempfile
from pathlib import Path

import pytest

from src.serum.parser_v1 import parse_fxp, FXP_MAGIC, SerumV1Preset


def _make_minimal_fxp(num_params: int = 300) -> bytes:
    """Create a minimal valid-ish FXP file for testing."""
    # FXP header (FxCk format — regular float params)
    header = bytearray(28)
    header[0:4] = FXP_MAGIC
    struct.pack_into(">I", header, 4, 24 + num_params * 4)  # byte size
    header[8:12] = b"FxCk"  # regular preset
    struct.pack_into(">I", header, 12, 1)  # version
    struct.pack_into(">I", header, 16, 0x5853524D)  # plugin ID
    struct.pack_into(">I", header, 20, 1)  # plugin version
    struct.pack_into(">I", header, 24, num_params)  # num params

    # Parameters as big-endian floats
    params = bytearray()
    for i in range(num_params):
        params += struct.pack(">f", i / num_params)

    return bytes(header + params)


def test_parse_fxp_structure():
    data = _make_minimal_fxp(300)
    with tempfile.NamedTemporaryFile(suffix=".fxp", delete=False) as f:
        f.write(data)
        f.flush()

        preset = parse_fxp(f.name)
        assert isinstance(preset, SerumV1Preset)
        assert preset.num_params == 300
        assert len(preset.params) == 300


def test_parse_fxp_invalid_magic():
    data = b"XXXX" + b"\x00" * 100
    with tempfile.NamedTemporaryFile(suffix=".fxp", delete=False) as f:
        f.write(data)
        f.flush()

        with pytest.raises(ValueError, match="Invalid FXP magic"):
            parse_fxp(f.name)


def test_parse_fxp_too_small():
    data = b"CcnK" + b"\x00" * 10
    with tempfile.NamedTemporaryFile(suffix=".fxp", delete=False) as f:
        f.write(data)
        f.flush()

        with pytest.raises(ValueError, match="too small"):
            parse_fxp(f.name)
