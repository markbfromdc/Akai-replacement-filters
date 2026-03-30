"""Tests for impulse response and saturation modules."""

import numpy as np
import pytest

from src.impulse.saturation import (
    SaturationMode,
    SaturationParams,
    apply_saturation,
)


def _test_signal(duration_s: float = 0.1, freq_hz: float = 440.0, sr: int = 44100) -> np.ndarray:
    """Generate a test sine wave."""
    t = np.arange(int(duration_s * sr)) / sr
    return 0.8 * np.sin(2 * np.pi * freq_hz * t)


class TestSaturationModes:
    """Test each saturation mode produces valid output."""

    @pytest.mark.parametrize("mode", list(SaturationMode))
    def test_mode_produces_output(self, mode):
        audio = _test_signal()
        result = apply_saturation(audio, mode)
        assert result.shape == audio.shape
        assert np.all(np.isfinite(result))
        assert np.max(np.abs(result)) <= 1.0

    @pytest.mark.parametrize("mode", list(SaturationMode))
    def test_mode_with_custom_params(self, mode):
        audio = _test_signal()
        params = SaturationParams(drive=0.8, mix=0.7, tone=0.6, output=0.9)
        result = apply_saturation(audio, mode, params)
        assert result.shape == audio.shape
        assert np.all(np.isfinite(result))

    def test_dry_wet_mix(self):
        audio = _test_signal()
        # Fully dry
        dry = apply_saturation(audio, SaturationMode.SOFT_CLIP, SaturationParams(mix=0.0))
        np.testing.assert_allclose(dry, audio * 0.8, atol=1e-6)  # output=0.8 default

        # Fully wet should differ from dry
        wet = apply_saturation(audio, SaturationMode.SOFT_CLIP, SaturationParams(mix=1.0, drive=0.8))
        assert not np.allclose(wet, audio * 0.8, atol=0.01)

    def test_drive_increases_distortion(self):
        audio = _test_signal()
        low_drive = apply_saturation(audio, SaturationMode.HARD_CLIP, SaturationParams(drive=0.1))
        high_drive = apply_saturation(audio, SaturationMode.HARD_CLIP, SaturationParams(drive=1.0))
        # Higher drive should produce more harmonic content (higher RMS after normalization)
        assert not np.allclose(low_drive, high_drive, atol=0.01)

    def test_stereo_input(self):
        mono = _test_signal()
        stereo = np.column_stack([mono, mono * 0.8])
        result = apply_saturation(stereo, SaturationMode.TUBE)
        assert result.shape == stereo.shape
        assert result.ndim == 2

    def test_silence_input(self):
        silence = np.zeros(4410)
        result = apply_saturation(silence, SaturationMode.TAPE)
        # Should remain near-silent (tape mode has hysteresis but no self-oscillation)
        assert np.max(np.abs(result)) < 0.01


class TestSaturationParams:
    def test_drive_linear_conversion(self):
        params = SaturationParams(drive=0.0)
        assert params.drive_linear == 1.0

        params = SaturationParams(drive=1.0)
        assert params.drive_linear == 10.0

        params = SaturationParams(drive=0.5)
        assert params.drive_linear == 5.5
