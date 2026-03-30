"""Tests for Serum → Akai filter conversion engine."""

from src.serum.filter_map import (
    SerumFilterConfig,
    SerumFilterSubtype,
    serum_to_akai,
    batch_convert,
    ConversionResult,
)
from src.xpm.filter_params import FilterType


def test_lp24_direct_map():
    config = SerumFilterConfig(filter_type=SerumFilterSubtype.LP_24, cutoff=0.5, resonance=0.5)
    result = serum_to_akai(config)
    assert result.filter_config.filter_type == FilterType.LP4
    assert not result.needs_ir_fallback
    assert 0 <= result.filter_config.cutoff <= 127
    assert 0 <= result.filter_config.resonance <= 127


def test_hp12_direct_map():
    config = SerumFilterConfig(filter_type=SerumFilterSubtype.HP_12, cutoff=0.7, resonance=0.3)
    result = serum_to_akai(config)
    assert result.filter_config.filter_type == FilterType.HP1
    assert not result.needs_ir_fallback


def test_bp_direct_map():
    config = SerumFilterConfig(filter_type=SerumFilterSubtype.BP_12, cutoff=0.6, resonance=0.4)
    result = serum_to_akai(config)
    assert result.filter_config.filter_type == FilterType.BP
    assert not result.needs_ir_fallback


def test_notch_direct_map():
    config = SerumFilterConfig(filter_type=SerumFilterSubtype.NOTCH_12, cutoff=0.5, resonance=0.5)
    result = serum_to_akai(config)
    assert result.filter_config.filter_type == FilterType.NOTCH


def test_comb_needs_ir_fallback():
    config = SerumFilterConfig(filter_type=SerumFilterSubtype.COMB_POS, cutoff=0.5)
    result = serum_to_akai(config)
    assert result.needs_ir_fallback
    assert result.ir_description != ""


def test_formant_needs_ir_fallback():
    config = SerumFilterConfig(filter_type=SerumFilterSubtype.FORMANT_VOWEL, cutoff=0.5)
    result = serum_to_akai(config)
    assert result.needs_ir_fallback
    assert result.filter_config.filter_type == FilterType.BP


def test_cutoff_conversion_range():
    # Low cutoff (near 20Hz)
    low = SerumFilterConfig(filter_type=SerumFilterSubtype.LP_24, cutoff=0.0)
    result_low = serum_to_akai(low)
    assert result_low.filter_config.cutoff == 0

    # High cutoff (near 20kHz)
    high = SerumFilterConfig(filter_type=SerumFilterSubtype.LP_24, cutoff=1.0)
    result_high = serum_to_akai(high)
    assert result_high.filter_config.cutoff == 127


def test_resonance_conversion():
    config = SerumFilterConfig(filter_type=SerumFilterSubtype.LP_24, resonance=0.0)
    result = serum_to_akai(config)
    assert result.filter_config.resonance == 0

    config = SerumFilterConfig(filter_type=SerumFilterSubtype.LP_24, resonance=1.0)
    result = serum_to_akai(config)
    assert result.filter_config.resonance == 127


def test_drive_and_fat_mapping():
    config = SerumFilterConfig(
        filter_type=SerumFilterSubtype.LP_24,
        drive=0.8,
        fat=0.6,
    )
    result = serum_to_akai(config)
    assert result.drive_as_insert_gain > 0
    assert result.fat_as_output_boost > 0


def test_envelope_conversion():
    config = SerumFilterConfig(
        filter_type=SerumFilterSubtype.LP_24,
        env_attack=0.2,
        env_decay=0.6,
        env_sustain=0.8,
        env_release=0.4,
        env_amount=0.7,
    )
    result = serum_to_akai(config)
    assert 0 <= result.filter_config.attack <= 127
    assert 0 <= result.filter_config.decay <= 127
    assert 0 <= result.filter_config.sustain <= 127
    assert 0 <= result.filter_config.release <= 127
    assert result.filter_config.env_amount > 0


def test_batch_convert():
    configs = [
        SerumFilterConfig(filter_type=SerumFilterSubtype.LP_24, cutoff=0.5),
        SerumFilterConfig(filter_type=SerumFilterSubtype.HP_24, cutoff=0.3),
        SerumFilterConfig(filter_type=SerumFilterSubtype.COMB_POS, cutoff=0.7),
    ]
    results = batch_convert(configs)
    assert len(results) == 3
    assert results[0].filter_config.filter_type == FilterType.LP4
    assert results[1].filter_config.filter_type == FilterType.HP2
    assert results[2].needs_ir_fallback


def test_unknown_filter_type_defaults():
    config = SerumFilterConfig(filter_type=99, cutoff=0.5)
    result = serum_to_akai(config)
    assert result.filter_config.filter_type == FilterType.LP4
    assert result.needs_ir_fallback
