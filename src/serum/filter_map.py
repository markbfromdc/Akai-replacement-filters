"""Core conversion engine: Serum filter types and parameters → Akai MPC filter modes.

Maps all 75+ Serum filter types to the closest Akai MPC filter equivalent,
with parameter normalization between the two architectures.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import IntEnum

from src.xpm.filter_params import FilterConfig, FilterType, hz_to_mpc, float_to_mpc


class SerumFilterCategory(IntEnum):
    """Serum filter categories (encoded in filter_type_raw upper bits)."""
    NORMAL = 0
    MULTI = 1
    FLANGES = 2
    MISC = 3


class SerumFilterSubtype(IntEnum):
    """Serum Normal category subtypes."""
    LP_12 = 0
    LP_24 = 1
    LP_48 = 2    # Serum 2
    HP_12 = 3
    HP_24 = 4
    HP_48 = 5    # Serum 2
    BP_12 = 6
    BP_24 = 7
    NOTCH_12 = 8
    NOTCH_24 = 9
    PEAK = 10
    LP_6 = 11
    HP_6 = 12
    # Multi category
    MULTI_LP_HP = 20
    MULTI_LP_BP = 21
    MULTI_BP_HP = 22
    MULTI_LP_LP = 23
    # Flanges category
    COMB_POS = 40
    COMB_NEG = 41
    PHASER_4 = 42
    PHASER_8 = 43
    FLANGER = 44
    # Misc category
    REVERB = 60
    COMB_LP = 61
    COMB_HP = 62
    FORMANT_VOWEL = 63
    FORMANT_TALK = 64
    RING_MOD = 65
    SAMPLE_HOLD = 66


@dataclass
class SerumFilterConfig:
    """Represents a Serum filter configuration before conversion."""
    filter_type: int = 0        # Raw type index
    cutoff: float = 0.5         # 0.0-1.0 normalized (maps to 20Hz-20kHz log)
    resonance: float = 0.0      # 0.0-1.0
    drive: float = 0.0          # 0.0-1.0
    fat: float = 0.0            # 0.0-1.0
    mix: float = 1.0            # 0.0-1.0 (dry/wet)
    pan: float = 0.5            # 0.0-1.0 (0.5 = center)
    routing: int = 0            # 0=serial, 1=parallel (Serum 2)

    # Envelope
    env_attack: float = 0.0     # 0.0-1.0
    env_decay: float = 0.5      # 0.0-1.0
    env_sustain: float = 1.0    # 0.0-1.0
    env_release: float = 0.3    # 0.0-1.0
    env_amount: float = 0.0     # -1.0 to 1.0

    @property
    def category(self) -> SerumFilterCategory:
        if self.filter_type < 20:
            return SerumFilterCategory.NORMAL
        elif self.filter_type < 40:
            return SerumFilterCategory.MULTI
        elif self.filter_type < 60:
            return SerumFilterCategory.FLANGES
        else:
            return SerumFilterCategory.MISC

    @property
    def cutoff_hz(self) -> float:
        """Convert normalized cutoff to Hz (20Hz-20kHz logarithmic)."""
        return 20.0 * math.pow(20000.0 / 20.0, self.cutoff)

    @property
    def needs_ir_fallback(self) -> bool:
        """Whether this filter type requires IR baking (no direct Akai equivalent)."""
        return self.category in (SerumFilterCategory.FLANGES, SerumFilterCategory.MISC)


# Direct mapping table: Serum filter type → Akai FilterType
_DIRECT_MAP: dict[int, FilterType] = {
    # Normal LP
    SerumFilterSubtype.LP_6: FilterType.LP1,
    SerumFilterSubtype.LP_12: FilterType.LP2,
    SerumFilterSubtype.LP_24: FilterType.LP4,
    SerumFilterSubtype.LP_48: FilterType.LP6,
    # Normal HP
    SerumFilterSubtype.HP_6: FilterType.HP1,
    SerumFilterSubtype.HP_12: FilterType.HP1,
    SerumFilterSubtype.HP_24: FilterType.HP2,
    SerumFilterSubtype.HP_48: FilterType.HP2,
    # Normal BP
    SerumFilterSubtype.BP_12: FilterType.BP,
    SerumFilterSubtype.BP_24: FilterType.BP,
    # Normal Notch
    SerumFilterSubtype.NOTCH_12: FilterType.NOTCH,
    SerumFilterSubtype.NOTCH_24: FilterType.NOTCH,
    # Peak
    SerumFilterSubtype.PEAK: FilterType.BP,
}

# Fallback mapping for exotic types → closest Akai type + IR flag
_FALLBACK_MAP: dict[int, FilterType] = {
    # Multi → closest single filter
    SerumFilterSubtype.MULTI_LP_HP: FilterType.LP4,
    SerumFilterSubtype.MULTI_LP_BP: FilterType.LP4,
    SerumFilterSubtype.MULTI_BP_HP: FilterType.BP,
    SerumFilterSubtype.MULTI_LP_LP: FilterType.LP6,
    # Flanges → LP2 as base (IR handles the character)
    SerumFilterSubtype.COMB_POS: FilterType.LP2,
    SerumFilterSubtype.COMB_NEG: FilterType.LP2,
    SerumFilterSubtype.PHASER_4: FilterType.LP2,
    SerumFilterSubtype.PHASER_8: FilterType.LP2,
    SerumFilterSubtype.FLANGER: FilterType.LP2,
    # Misc → various
    SerumFilterSubtype.REVERB: FilterType.LP4,
    SerumFilterSubtype.COMB_LP: FilterType.LP2,
    SerumFilterSubtype.COMB_HP: FilterType.HP2,
    SerumFilterSubtype.FORMANT_VOWEL: FilterType.BP,
    SerumFilterSubtype.FORMANT_TALK: FilterType.BP,
    SerumFilterSubtype.RING_MOD: FilterType.LP2,
    SerumFilterSubtype.SAMPLE_HOLD: FilterType.LP2,
}


@dataclass
class ConversionResult:
    """Result of a Serum→Akai filter conversion."""
    filter_config: FilterConfig
    needs_ir_fallback: bool = False
    ir_description: str = ""
    drive_as_insert_gain: int = 0   # 0-127 for insert effect
    fat_as_output_boost: int = 0    # 0-127 for output level
    mix_blend: float = 1.0          # dry/wet for parallel layer


def _convert_envelope(serum: SerumFilterConfig) -> tuple[int, int, int, int, int]:
    """Convert Serum filter envelope to MPC ADSR + env amount."""
    attack = float_to_mpc(serum.env_attack)
    decay = float_to_mpc(serum.env_decay)
    sustain = float_to_mpc(serum.env_sustain)
    release = float_to_mpc(serum.env_release)
    # Env amount: Serum uses -1..+1, MPC uses 0-127 (with center = no mod)
    env_amount = float_to_mpc(abs(serum.env_amount))
    return attack, decay, sustain, release, env_amount


def serum_to_akai(serum: SerumFilterConfig) -> ConversionResult:
    """Convert a Serum filter configuration to Akai MPC filter settings.

    This is the core conversion engine. It:
    1. Maps the Serum filter type to the closest Akai filter mode
    2. Converts cutoff from log Hz to MPC 0-127
    3. Converts resonance, drive, fat, mix, and envelope
    4. Flags exotic filter types that need IR fallback processing

    Args:
        serum: Serum filter configuration to convert.

    Returns:
        ConversionResult with the Akai FilterConfig and metadata.
    """
    # Determine Akai filter type
    ftype = serum.filter_type
    if ftype in _DIRECT_MAP:
        akai_type = _DIRECT_MAP[ftype]
        needs_ir = False
        ir_desc = ""
    elif ftype in _FALLBACK_MAP:
        akai_type = _FALLBACK_MAP[ftype]
        needs_ir = serum.needs_ir_fallback
        ir_desc = _IR_DESCRIPTIONS.get(ftype, "Exotic filter: render as IR")
    else:
        akai_type = FilterType.LP4
        needs_ir = True
        ir_desc = f"Unknown Serum filter type {ftype}: defaulting to LP4 + IR"

    # Convert cutoff: Serum normalized 0-1 → Hz → MPC 0-127
    cutoff = hz_to_mpc(serum.cutoff_hz)

    # Convert resonance: Serum 0-1 → MPC 0-127
    resonance = float_to_mpc(serum.resonance)

    # Convert envelope
    attack, decay, sustain, release, env_amount = _convert_envelope(serum)

    # Map drive and fat to Akai-compatible values
    drive_gain = float_to_mpc(serum.drive)
    fat_boost = float_to_mpc(serum.fat)

    filter_config = FilterConfig(
        filter_type=akai_type,
        cutoff=cutoff,
        resonance=resonance,
        env_amount=env_amount,
        attack=attack,
        decay=decay,
        sustain=sustain,
        release=release,
    )

    return ConversionResult(
        filter_config=filter_config,
        needs_ir_fallback=needs_ir,
        ir_description=ir_desc,
        drive_as_insert_gain=drive_gain,
        fat_as_output_boost=fat_boost,
        mix_blend=serum.mix,
    )


_IR_DESCRIPTIONS: dict[int, str] = {
    SerumFilterSubtype.COMB_POS: "Positive comb filter: render IR at multiple cutoff positions for velocity layers",
    SerumFilterSubtype.COMB_NEG: "Negative comb filter: render IR with inverted feedback",
    SerumFilterSubtype.PHASER_4: "4-stage phaser: render swept IR across cutoff range",
    SerumFilterSubtype.PHASER_8: "8-stage phaser: render swept IR across cutoff range",
    SerumFilterSubtype.FLANGER: "Flanger: render short-delay IR with feedback",
    SerumFilterSubtype.REVERB: "Reverb filter: convolve source with reverb IR",
    SerumFilterSubtype.COMB_LP: "Comb + LP filter: render combined IR response",
    SerumFilterSubtype.COMB_HP: "Comb + HP filter: render combined IR response",
    SerumFilterSubtype.FORMANT_VOWEL: "Formant/vowel filter: render formant shapes as processed samples",
    SerumFilterSubtype.FORMANT_TALK: "Formant/talk filter: render talk-box shapes as processed samples",
    SerumFilterSubtype.RING_MOD: "Ring modulator: render AM-modulated source samples",
    SerumFilterSubtype.SAMPLE_HOLD: "Sample & hold: render stepped random filter sweeps",
}


def batch_convert(presets: list[SerumFilterConfig]) -> list[ConversionResult]:
    """Convert multiple Serum filter configs at once."""
    return [serum_to_akai(p) for p in presets]
