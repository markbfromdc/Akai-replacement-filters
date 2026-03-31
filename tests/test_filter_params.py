"""Tests for filter parameter definitions and normalization."""

import math

import pytest

from src.xpm.filter_params import (
    FilterConfig,
    FilterType,
    hz_to_mpc,
    mpc_to_hz,
    float_to_mpc,
)


class TestHzToMpc:
    """Tests for Hz → MPC cutoff conversion."""

    def test_20hz_maps_to_0(self):
        assert hz_to_mpc(20.0) == 0

    def test_20khz_maps_to_127(self):
        assert hz_to_mpc(20000.0) == 127

    def test_clamps_below_20hz(self):
        assert hz_to_mpc(1.0) == 0
        assert hz_to_mpc(0.0) == 0

    def test_clamps_above_20khz(self):
        assert hz_to_mpc(50000.0) == 127

    def test_1khz_midrange(self):
        result = hz_to_mpc(1000.0)
        assert 50 < result < 80  # Should be roughly in the middle-ish

    def test_logarithmic_not_linear(self):
        # 200Hz and 2kHz should NOT be linearly spaced
        low = hz_to_mpc(200.0)
        mid = hz_to_mpc(2000.0)
        high = hz_to_mpc(20000.0)
        # The distance from low→mid should be similar to mid→high (log spacing)
        assert abs((mid - low) - (high - mid)) < 5

    def test_monotonically_increasing(self):
        freqs = [20, 100, 500, 1000, 5000, 10000, 20000]
        values = [hz_to_mpc(f) for f in freqs]
        for i in range(len(values) - 1):
            assert values[i] <= values[i + 1]


class TestMpcToHz:
    """Tests for MPC cutoff → Hz reverse conversion."""

    def test_0_maps_to_20hz(self):
        assert mpc_to_hz(0) == pytest.approx(20.0, rel=0.01)

    def test_127_maps_to_20khz(self):
        assert mpc_to_hz(127) == pytest.approx(20000.0, rel=0.01)

    def test_clamps_below_0(self):
        assert mpc_to_hz(-10) == pytest.approx(20.0, rel=0.01)

    def test_clamps_above_127(self):
        assert mpc_to_hz(200) == pytest.approx(20000.0, rel=0.01)

    def test_round_trip_consistency(self):
        """hz_to_mpc → mpc_to_hz should approximate the original frequency."""
        for freq in [50, 200, 1000, 5000, 15000]:
            mpc_val = hz_to_mpc(float(freq))
            recovered = mpc_to_hz(mpc_val)
            # Allow some tolerance due to integer quantization
            assert abs(math.log(recovered / freq)) < 0.1  # Within ~10% log scale

    def test_monotonically_increasing(self):
        values = [mpc_to_hz(v) for v in range(0, 128)]
        for i in range(len(values) - 1):
            assert values[i] <= values[i + 1]


class TestFloatToMpc:
    """Tests for float → MPC 0-127 conversion."""

    def test_zero_maps_to_0(self):
        assert float_to_mpc(0.0) == 0

    def test_one_maps_to_127(self):
        assert float_to_mpc(1.0) == 127

    def test_half_maps_to_64(self):
        assert float_to_mpc(0.5) in (63, 64)

    def test_clamps_below_min(self):
        assert float_to_mpc(-0.5) == 0

    def test_clamps_above_max(self):
        assert float_to_mpc(1.5) == 127

    def test_custom_range(self):
        assert float_to_mpc(5.0, min_val=0.0, max_val=10.0) in (63, 64)
        assert float_to_mpc(0.0, min_val=0.0, max_val=10.0) == 0
        assert float_to_mpc(10.0, min_val=0.0, max_val=10.0) == 127

    def test_quarter_and_three_quarter(self):
        q = float_to_mpc(0.25)
        tq = float_to_mpc(0.75)
        assert 28 <= q <= 35
        assert 92 <= tq <= 99


class TestFilterType:
    """Tests for FilterType enum."""

    def test_all_filter_types_have_values(self):
        types = list(FilterType)
        assert len(types) == 10  # OFF, LP1-6, HP1-2, BP, NOTCH, LINK

    def test_lp4_value(self):
        assert FilterType.LP4.value == "LowPass4Pole"

    def test_off_value(self):
        assert FilterType.OFF.value == "Off"


class TestFilterConfig:
    """Tests for FilterConfig dataclass."""

    def test_default_values(self):
        fc = FilterConfig()
        assert fc.filter_type == FilterType.LP4
        assert fc.cutoff == 127
        assert fc.resonance == 0

    def test_clamping_above_127(self):
        fc = FilterConfig(cutoff=200, resonance=300, env_amount=999)
        assert fc.cutoff == 127
        assert fc.resonance == 127
        assert fc.env_amount == 127

    def test_clamping_below_0(self):
        fc = FilterConfig(cutoff=-10, resonance=-50, attack=-1)
        assert fc.cutoff == 0
        assert fc.resonance == 0
        assert fc.attack == 0

    def test_to_xml_dict_keys(self):
        fc = FilterConfig(filter_type=FilterType.HP2, cutoff=64, resonance=32)
        d = fc.to_xml_dict()
        assert d["FilterType"] == "HighPass2Pole"
        assert d["FilterCutoff"] == "64"
        assert d["FilterResonance"] == "32"
        assert "FilterAttack" in d
        assert "FilterDecay" in d
        assert "FilterSustain" in d
        assert "FilterRelease" in d
        assert "FilterEnvAmount" in d

    def test_to_xml_dict_all_strings(self):
        fc = FilterConfig()
        d = fc.to_xml_dict()
        for key, val in d.items():
            assert isinstance(val, str), f"{key} should be str, got {type(val)}"

    def test_boundary_values(self):
        fc = FilterConfig(cutoff=0, resonance=0, env_amount=0, attack=0, decay=0, sustain=0, release=0)
        assert all(getattr(fc, a) == 0 for a in ("cutoff", "resonance", "env_amount", "attack", "decay", "sustain", "release"))

        fc = FilterConfig(cutoff=127, resonance=127, env_amount=127, attack=127, decay=127, sustain=127, release=127)
        assert all(getattr(fc, a) == 127 for a in ("cutoff", "resonance", "env_amount", "attack", "decay", "sustain", "release"))
