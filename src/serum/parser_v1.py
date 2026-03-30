"""Parser for Serum v1 .fxp preset files.

Serum v1 presets use the VST2 .fxp format with an opaque chunk containing
zlib-compressed parameter data. Filter parameters are extracted from known
offsets within the decompressed parameter block.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from pathlib import Path

# FXP header constants
FXP_MAGIC = b"CcnK"
FXP_HEADER_SIZE = 60
SERUM_PLUGIN_ID = 0x5853524D  # 'XSRM' — Xfer Serum

# Known parameter offsets (float32 index positions within the param block)
# These are approximate; exact offsets may vary by Serum version.
PARAM_FILTER_TYPE = 140
PARAM_FILTER_CUTOFF = 141
PARAM_FILTER_RESONANCE = 142
PARAM_FILTER_DRIVE = 143
PARAM_FILTER_FAT = 144
PARAM_FILTER_MIX = 145
PARAM_FILTER_PAN = 146
PARAM_FILTER_ROUTING = 147

# Filter envelope offsets
PARAM_FILTER_ENV_ATTACK = 148
PARAM_FILTER_ENV_DECAY = 149
PARAM_FILTER_ENV_SUSTAIN = 150
PARAM_FILTER_ENV_RELEASE = 151
PARAM_FILTER_ENV_AMOUNT = 152

# Preset name offset (within raw chunk, not param block)
PRESET_NAME_OFFSET = 0x4972
PRESET_NAME_LENGTH = 32


@dataclass
class SerumV1Preset:
    """Parsed data from a Serum v1 .fxp file."""
    preset_name: str
    plugin_id: int
    version: int
    num_params: int
    params: list[float]

    # Extracted filter parameters (convenience)
    filter_type_raw: float = 0.0
    filter_cutoff: float = 0.0
    filter_resonance: float = 0.0
    filter_drive: float = 0.0
    filter_fat: float = 0.0
    filter_mix: float = 0.0
    filter_pan: float = 0.5
    filter_routing: float = 0.0
    filter_env_attack: float = 0.0
    filter_env_decay: float = 0.5
    filter_env_sustain: float = 1.0
    filter_env_release: float = 0.3
    filter_env_amount: float = 0.0


def _read_fxp_header(data: bytes) -> tuple[int, int, int, int]:
    """Read FXP header and return (plugin_id, version, num_programs, chunk_size)."""
    if len(data) < FXP_HEADER_SIZE:
        raise ValueError(f"File too small for FXP header: {len(data)} bytes")

    magic = data[0:4]
    if magic != FXP_MAGIC:
        raise ValueError(f"Invalid FXP magic: {magic!r}, expected {FXP_MAGIC!r}")

    # Byte layout (big-endian):
    # 0-3:   magic "CcnK"
    # 4-7:   byte size (rest of chunk)
    # 8-11:  fxMagic (FPCh for preset, FBCh for bank)
    # 12-15: version
    # 16-19: plugin unique ID
    # 20-23: plugin version
    # 24-27: numPrograms
    # 28-31: padding
    # 32-35: chunk size
    # 36+:   chunk data

    fx_magic = data[8:12]
    version = struct.unpack(">I", data[12:16])[0]
    plugin_id = struct.unpack(">I", data[16:20])[0]
    plugin_version = struct.unpack(">I", data[20:24])[0]
    num_programs = struct.unpack(">I", data[24:28])[0]

    if fx_magic == b"FPCh":
        # Opaque chunk preset
        chunk_size = struct.unpack(">I", data[32:36])[0]
        return plugin_id, plugin_version, num_programs, chunk_size
    elif fx_magic == b"FxCk":
        # Regular preset (parameters as float array)
        num_params = struct.unpack(">I", data[24:28])[0]
        return plugin_id, plugin_version, num_params, 0
    else:
        raise ValueError(f"Unsupported FXP format: {fx_magic!r}")


def _extract_params_from_chunk(chunk_data: bytes) -> list[float]:
    """Attempt to decompress and extract float parameters from the chunk."""
    # Try zlib decompression first (common in Serum v1)
    try:
        decompressed = zlib.decompress(chunk_data)
    except zlib.error:
        decompressed = chunk_data

    # Extract as array of little-endian float32 values
    num_floats = len(decompressed) // 4
    params = []
    for i in range(num_floats):
        val = struct.unpack("<f", decompressed[i * 4:(i + 1) * 4])[0]
        params.append(val)

    return params


def _extract_preset_name(data: bytes) -> str:
    """Extract the preset name from the raw FXP data."""
    if len(data) > PRESET_NAME_OFFSET + PRESET_NAME_LENGTH:
        raw = data[PRESET_NAME_OFFSET:PRESET_NAME_OFFSET + PRESET_NAME_LENGTH]
        return raw.split(b"\x00")[0].decode("ascii", errors="replace").strip()
    # Fallback: read from header area (bytes 36-63 in some FXP versions)
    raw = data[36:68]
    return raw.split(b"\x00")[0].decode("ascii", errors="replace").strip()


def _safe_param(params: list[float], index: int, default: float = 0.0) -> float:
    """Safely get a parameter value by index."""
    if 0 <= index < len(params):
        return params[index]
    return default


def parse_fxp(file_path: str | Path) -> SerumV1Preset:
    """Parse a Serum v1 .fxp preset file.

    Args:
        file_path: Path to the .fxp file.

    Returns:
        SerumV1Preset with all extracted parameters.

    Raises:
        ValueError: If the file is not a valid FXP preset.
    """
    data = Path(file_path).read_bytes()
    plugin_id, version, num_params, chunk_size = _read_fxp_header(data)

    preset_name = _extract_preset_name(data)

    # Extract parameter block
    if chunk_size > 0:
        # Opaque chunk format — data starts at offset 36
        chunk_start = 36
        chunk_data = data[chunk_start:chunk_start + chunk_size]
        params = _extract_params_from_chunk(chunk_data)
    else:
        # Regular float array format
        params = []
        offset = 28
        for _ in range(num_params):
            val = struct.unpack(">f", data[offset:offset + 4])[0]
            params.append(val)
            offset += 4

    preset = SerumV1Preset(
        preset_name=preset_name,
        plugin_id=plugin_id,
        version=version,
        num_params=len(params),
        params=params,
        filter_type_raw=_safe_param(params, PARAM_FILTER_TYPE),
        filter_cutoff=_safe_param(params, PARAM_FILTER_CUTOFF),
        filter_resonance=_safe_param(params, PARAM_FILTER_RESONANCE),
        filter_drive=_safe_param(params, PARAM_FILTER_DRIVE),
        filter_fat=_safe_param(params, PARAM_FILTER_FAT),
        filter_mix=_safe_param(params, PARAM_FILTER_MIX, 1.0),
        filter_pan=_safe_param(params, PARAM_FILTER_PAN, 0.5),
        filter_routing=_safe_param(params, PARAM_FILTER_ROUTING),
        filter_env_attack=_safe_param(params, PARAM_FILTER_ENV_ATTACK),
        filter_env_decay=_safe_param(params, PARAM_FILTER_ENV_DECAY, 0.5),
        filter_env_sustain=_safe_param(params, PARAM_FILTER_ENV_SUSTAIN, 1.0),
        filter_env_release=_safe_param(params, PARAM_FILTER_ENV_RELEASE, 0.3),
        filter_env_amount=_safe_param(params, PARAM_FILTER_ENV_AMOUNT),
    )

    return preset
