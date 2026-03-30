"""Parser for Serum 2 .SerumPreset files.

Serum 2 presets use a two-part format:
  1. Header: b"XferJson\\x00" + uint64_le(json_length) + JSON metadata
  2. Payload: uint32_le(cbor_length) + uint32_le(2) + zstd_compressed(CBOR data)

The CBOR payload contains the full patch data including filter configuration.
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass, field
from pathlib import Path

try:
    import zstandard as zstd
except ImportError:
    zstd = None

try:
    import cbor2
except ImportError:
    cbor2 = None

XFER_JSON_MAGIC = b"XferJson\x00"


@dataclass
class SerumV2Preset:
    """Parsed data from a Serum 2 .SerumPreset file."""
    preset_name: str
    metadata: dict = field(default_factory=dict)
    patch_data: dict = field(default_factory=dict)

    # Extracted filter parameters
    filter_type_raw: int = 0
    filter_cutoff: float = 0.5
    filter_resonance: float = 0.0
    filter_drive: float = 0.0
    filter_fat: float = 0.0
    filter_mix: float = 1.0
    filter_pan: float = 0.5
    filter_routing: int = 0

    # Filter 2 (Serum 2 dual filter)
    filter2_type_raw: int = 0
    filter2_cutoff: float = 0.5
    filter2_resonance: float = 0.0

    # Filter envelope
    filter_env_attack: float = 0.0
    filter_env_decay: float = 0.5
    filter_env_sustain: float = 1.0
    filter_env_release: float = 0.3
    filter_env_amount: float = 0.0


def _read_header(data: bytes) -> tuple[dict, int]:
    """Read the XferJson header and return (metadata_dict, payload_offset)."""
    if not data.startswith(XFER_JSON_MAGIC):
        raise ValueError("Not a Serum 2 preset: missing XferJson magic")

    magic_len = len(XFER_JSON_MAGIC)
    json_length = struct.unpack_from("<Q", data, magic_len)[0]
    json_start = magic_len + 8
    json_end = json_start + json_length
    json_bytes = data[json_start:json_end]

    metadata = json.loads(json_bytes.decode("utf-8"))
    return metadata, json_end


def _read_payload(data: bytes, offset: int) -> dict:
    """Decompress and decode the CBOR payload."""
    if zstd is None:
        raise ImportError("zstandard package required for Serum 2 presets: pip install zstandard")
    if cbor2 is None:
        raise ImportError("cbor2 package required for Serum 2 presets: pip install cbor2")

    cbor_length = struct.unpack_from("<I", data, offset)[0]
    format_ver = struct.unpack_from("<I", data, offset + 4)[0]
    compressed_data = data[offset + 8:]

    dctx = zstd.ZstdDecompressor()
    decompressed = dctx.decompress(compressed_data, max_output_size=cbor_length)
    patch_data = cbor2.loads(decompressed)

    return patch_data


def _extract_filter_params(patch: dict) -> dict:
    """Extract filter parameters from the CBOR patch data.

    The exact keys depend on Serum's internal CBOR schema, which is
    partially documented by community reverse-engineering efforts.
    Common keys: 'filt_type', 'filt_cut', 'filt_res', 'filt_drv', etc.
    """
    result = {}

    # Try various known key patterns
    filter_keys = {
        "filter_type_raw": ["filt_type", "filter_type", "FiltType", "filt1_type"],
        "filter_cutoff": ["filt_cut", "filter_cutoff", "FiltCut", "filt1_cut"],
        "filter_resonance": ["filt_res", "filter_resonance", "FiltRes", "filt1_res"],
        "filter_drive": ["filt_drv", "filter_drive", "FiltDrv", "filt1_drv"],
        "filter_fat": ["filt_fat", "filter_fat", "FiltFat", "filt1_fat"],
        "filter_mix": ["filt_mix", "filter_mix", "FiltMix", "filt1_mix"],
        "filter_pan": ["filt_pan", "filter_pan", "FiltPan", "filt1_pan"],
        "filter_routing": ["filt_route", "filter_routing", "FiltRoute"],
        "filter2_type_raw": ["filt2_type", "filter2_type", "Filt2Type"],
        "filter2_cutoff": ["filt2_cut", "filter2_cutoff", "Filt2Cut"],
        "filter2_resonance": ["filt2_res", "filter2_resonance", "Filt2Res"],
        "filter_env_attack": ["fenv_atk", "filt_env_attack", "FEnvAtk"],
        "filter_env_decay": ["fenv_dec", "filt_env_decay", "FEnvDec"],
        "filter_env_sustain": ["fenv_sus", "filt_env_sustain", "FEnvSus"],
        "filter_env_release": ["fenv_rel", "filt_env_release", "FEnvRel"],
        "filter_env_amount": ["fenv_amt", "filt_env_amount", "FEnvAmt"],
    }

    def _deep_get(d: dict, key: str):
        """Recursively search for a key in nested dicts."""
        if key in d:
            return d[key]
        for v in d.values():
            if isinstance(v, dict):
                found = _deep_get(v, key)
                if found is not None:
                    return found
        return None

    for param_name, possible_keys in filter_keys.items():
        for key in possible_keys:
            val = _deep_get(patch, key)
            if val is not None:
                result[param_name] = val
                break

    return result


def parse_serum_preset(file_path: str | Path) -> SerumV2Preset:
    """Parse a Serum 2 .SerumPreset file.

    Args:
        file_path: Path to the .SerumPreset file.

    Returns:
        SerumV2Preset with all extracted parameters.

    Raises:
        ValueError: If the file is not a valid Serum 2 preset.
        ImportError: If zstandard or cbor2 packages are not installed.
    """
    data = Path(file_path).read_bytes()
    metadata, payload_offset = _read_header(data)
    patch_data = _read_payload(data, payload_offset)

    preset_name = metadata.get("name", metadata.get("preset_name", Path(file_path).stem))
    filter_params = _extract_filter_params(patch_data)

    preset = SerumV2Preset(
        preset_name=preset_name,
        metadata=metadata,
        patch_data=patch_data,
        **filter_params,
    )

    return preset
