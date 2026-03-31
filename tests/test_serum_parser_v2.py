"""Tests for Serum 2 .SerumPreset parser."""

import json
import struct
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.serum.parser_v2 import (
    SerumV2Preset,
    XFER_JSON_MAGIC,
    _read_header,
    _extract_filter_params,
)


def _make_serum2_header(metadata: dict) -> bytes:
    """Build a valid XferJson header from metadata dict."""
    json_bytes = json.dumps(metadata).encode("utf-8")
    header = XFER_JSON_MAGIC
    header += struct.pack("<Q", len(json_bytes))
    header += json_bytes
    return header


class TestReadHeader:
    """Tests for _read_header()."""

    def test_valid_header(self):
        meta = {"name": "TestPreset", "version": 2}
        data = _make_serum2_header(meta)
        metadata, offset = _read_header(data)
        assert metadata["name"] == "TestPreset"
        assert metadata["version"] == 2
        assert offset == len(data)

    def test_invalid_magic(self):
        data = b"NotXferJson" + b"\x00" * 100
        with pytest.raises(ValueError, match="missing XferJson magic"):
            _read_header(data)

    def test_empty_metadata(self):
        meta = {}
        data = _make_serum2_header(meta)
        metadata, offset = _read_header(data)
        assert metadata == {}

    def test_complex_metadata(self):
        meta = {
            "name": "Deep Bass",
            "author": "Producer",
            "tags": ["bass", "deep", "sub"],
            "preset_name": "Deep Bass Lead",
        }
        data = _make_serum2_header(meta)
        metadata, offset = _read_header(data)
        assert metadata["author"] == "Producer"
        assert "bass" in metadata["tags"]


class TestExtractFilterParams:
    """Tests for _extract_filter_params() nested dict search."""

    def test_flat_dict_with_primary_keys(self):
        patch_data = {
            "filt_type": 3,
            "filt_cut": 0.75,
            "filt_res": 0.3,
            "filt_drv": 0.5,
        }
        result = _extract_filter_params(patch_data)
        assert result["filter_type_raw"] == 3
        assert result["filter_cutoff"] == 0.75
        assert result["filter_resonance"] == 0.3
        assert result["filter_drive"] == 0.5

    def test_alternate_key_names(self):
        patch_data = {
            "FiltType": 5,
            "FiltCut": 0.6,
            "FiltRes": 0.2,
        }
        result = _extract_filter_params(patch_data)
        assert result["filter_type_raw"] == 5
        assert result["filter_cutoff"] == 0.6

    def test_nested_dict_search(self):
        patch_data = {
            "oscillators": {"osc1": {"type": "wavetable"}},
            "filter_section": {
                "filt_type": 7,
                "filt_cut": 0.9,
                "filt_res": 0.4,
            },
        }
        result = _extract_filter_params(patch_data)
        assert result["filter_type_raw"] == 7
        assert result["filter_cutoff"] == 0.9

    def test_deeply_nested(self):
        patch_data = {
            "level1": {
                "level2": {
                    "level3": {
                        "filt_type": 10,
                    }
                }
            }
        }
        result = _extract_filter_params(patch_data)
        assert result["filter_type_raw"] == 10

    def test_empty_dict(self):
        result = _extract_filter_params({})
        assert result == {}

    def test_no_matching_keys(self):
        patch_data = {"unrelated_key": 42, "another": {"nested": True}}
        result = _extract_filter_params(patch_data)
        assert result == {}

    def test_filter2_dual_filter(self):
        patch_data = {
            "filt_type": 1,
            "filt_cut": 0.5,
            "filt2_type": 3,
            "filt2_cut": 0.7,
            "filt2_res": 0.2,
        }
        result = _extract_filter_params(patch_data)
        assert result["filter_type_raw"] == 1
        assert result["filter2_type_raw"] == 3
        assert result["filter2_cutoff"] == 0.7

    def test_envelope_params(self):
        patch_data = {
            "fenv_atk": 0.1,
            "fenv_dec": 0.4,
            "fenv_sus": 0.8,
            "fenv_rel": 0.3,
            "fenv_amt": 0.6,
        }
        result = _extract_filter_params(patch_data)
        assert result["filter_env_attack"] == 0.1
        assert result["filter_env_decay"] == 0.4
        assert result["filter_env_sustain"] == 0.8
        assert result["filter_env_release"] == 0.3
        assert result["filter_env_amount"] == 0.6

    def test_first_key_variant_wins(self):
        """When multiple key variants exist, the first match should win."""
        patch_data = {
            "filt_type": 1,
            "FiltType": 99,  # Should NOT override the first match
        }
        result = _extract_filter_params(patch_data)
        assert result["filter_type_raw"] == 1


class TestSerumV2Preset:
    """Tests for the SerumV2Preset dataclass."""

    def test_defaults(self):
        p = SerumV2Preset(preset_name="Test")
        assert p.filter_cutoff == 0.5
        assert p.filter_resonance == 0.0
        assert p.filter_mix == 1.0
        assert p.filter_pan == 0.5
        assert p.filter_env_sustain == 1.0

    def test_with_overrides(self):
        p = SerumV2Preset(
            preset_name="Lead",
            filter_type_raw=5,
            filter_cutoff=0.8,
            filter2_type_raw=3,
        )
        assert p.filter_type_raw == 5
        assert p.filter_cutoff == 0.8
        assert p.filter2_type_raw == 3
