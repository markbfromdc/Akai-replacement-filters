"""Canonical filter parameter definitions and normalization for Akai MPC programs."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum


class FilterType(Enum):
    """Akai MPC filter types available in keygroup/drum programs."""
    OFF = "Off"
    LP1 = "LowPass1Pole"    # 6dB/oct
    LP2 = "LowPass2Pole"    # 12dB/oct
    LP4 = "LowPass4Pole"    # 24dB/oct
    LP6 = "LowPass6Pole"    # 36dB/oct
    HP1 = "HighPass1Pole"   # 6dB/oct
    HP2 = "HighPass2Pole"   # 12dB/oct
    BP = "BandPass"
    NOTCH = "BandReject"
    LINK = "Link"           # Linked mode (series HP+LP)


def hz_to_mpc(freq_hz: float) -> int:
    """Convert frequency in Hz to MPC cutoff value (0-127).

    MPC cutoff maps logarithmically: 0 = ~20Hz, 127 = ~20kHz.
    """
    freq_hz = max(20.0, min(20000.0, freq_hz))
    normalized = math.log(freq_hz / 20.0) / math.log(20000.0 / 20.0)
    return round(normalized * 127)


def mpc_to_hz(mpc_val: int) -> float:
    """Convert MPC cutoff value (0-127) back to frequency in Hz."""
    mpc_val = max(0, min(127, mpc_val))
    normalized = mpc_val / 127.0
    return 20.0 * math.pow(20000.0 / 20.0, normalized)


def float_to_mpc(value: float, min_val: float = 0.0, max_val: float = 1.0) -> int:
    """Convert a normalized float to MPC 0-127 range."""
    normalized = (value - min_val) / (max_val - min_val)
    return round(max(0.0, min(1.0, normalized)) * 127)


@dataclass
class FilterConfig:
    """Complete filter configuration for an Akai MPC program layer."""
    filter_type: FilterType = FilterType.LP4
    cutoff: int = 127       # 0-127
    resonance: int = 0      # 0-127
    env_amount: int = 0     # 0-127 (filter envelope depth)
    attack: int = 0         # 0-127
    decay: int = 64         # 0-127
    sustain: int = 127      # 0-127
    release: int = 40       # 0-127

    def __post_init__(self):
        for attr in ("cutoff", "resonance", "env_amount", "attack", "decay", "sustain", "release"):
            val = max(0, min(127, getattr(self, attr)))
            object.__setattr__(self, attr, val)

    def to_xml_dict(self) -> dict[str, str]:
        """Return dict of XML element names to values for .xpm serialization."""
        return {
            "FilterType": self.filter_type.value,
            "FilterCutoff": str(self.cutoff),
            "FilterResonance": str(self.resonance),
            "FilterEnvAmount": str(self.env_amount),
            "FilterAttack": str(self.attack),
            "FilterDecay": str(self.decay),
            "FilterSustain": str(self.sustain),
            "FilterRelease": str(self.release),
        }
