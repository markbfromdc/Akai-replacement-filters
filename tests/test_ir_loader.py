"""Tests for impulse response loading and convolution."""

import numpy as np
import pytest
import soundfile as sf

from src.impulse.ir_loader import (
    ImpulseResponse,
    load_ir,
    convolve_with_ir,
)


class TestLoadIR:
    """Tests for load_ir() function."""

    def test_load_mono_wav(self, mono_wav):
        ir = load_ir(mono_wav)
        assert ir.channels == 1
        assert ir.sample_rate == 44100
        assert not ir.is_stereo
        assert ir.num_samples > 0
        assert ir.duration_seconds > 0
        assert np.max(np.abs(ir.data)) <= 1.0  # Normalized

    def test_load_stereo_wav(self, stereo_wav):
        ir = load_ir(stereo_wav)
        assert ir.channels == 2
        assert ir.is_stereo
        assert ir.data.ndim == 2

    def test_resampling(self, mono_wav_48k):
        ir = load_ir(mono_wav_48k, target_sr=44100)
        assert ir.sample_rate == 44100
        # 4800 samples at 48k → ~4410 at 44.1k
        assert abs(ir.num_samples - 4410) < 10

    def test_normalization(self, short_ir_wav):
        ir = load_ir(short_ir_wav)
        assert np.max(np.abs(ir.data)) == pytest.approx(1.0, abs=1e-6)

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_ir("/nonexistent/path/ir.wav")

    def test_source_path_stored(self, mono_wav):
        ir = load_ir(mono_wav)
        assert str(mono_wav) in ir.source_path

    def test_duration_accuracy(self, mono_wav):
        ir = load_ir(mono_wav)
        expected = 4410 / 44100.0  # 0.1 seconds
        assert ir.duration_seconds == pytest.approx(expected, abs=0.001)


class TestImpulseResponseProperties:
    """Tests for ImpulseResponse dataclass properties."""

    def test_is_stereo_false(self):
        ir = ImpulseResponse(data=np.zeros(100), sample_rate=44100, channels=1, duration_seconds=0.01, source_path="")
        assert not ir.is_stereo

    def test_is_stereo_true(self):
        ir = ImpulseResponse(data=np.zeros((100, 2)), sample_rate=44100, channels=2, duration_seconds=0.01, source_path="")
        assert ir.is_stereo

    def test_num_samples(self):
        ir = ImpulseResponse(data=np.zeros(500), sample_rate=44100, channels=1, duration_seconds=0.01, source_path="")
        assert ir.num_samples == 500


class TestConvolveWithIR:
    """Tests for convolve_with_ir() function."""

    def _make_ir(self, data, channels=1):
        return ImpulseResponse(
            data=data, sample_rate=44100, channels=channels,
            duration_seconds=len(data) / 44100.0, source_path="test",
        )

    def test_mono_source_mono_ir(self, test_signal):
        ir_data = np.zeros(100)
        ir_data[0] = 1.0  # Delta function → output ≈ input
        ir = self._make_ir(ir_data)
        result = convolve_with_ir(test_signal, ir, mix=1.0)
        assert result.shape == test_signal.shape
        assert np.all(np.isfinite(result))

    def test_stereo_source_mono_ir(self, stereo_signal):
        ir_data = np.zeros(100)
        ir_data[0] = 1.0
        ir = self._make_ir(ir_data)
        result = convolve_with_ir(stereo_signal, ir, mix=1.0)
        assert result.ndim == 2
        assert result.shape[1] == 2

    def test_mono_source_stereo_ir(self, test_signal):
        ir_data = np.zeros((100, 2))
        ir_data[0, :] = 1.0
        ir = self._make_ir(ir_data, channels=2)
        result = convolve_with_ir(test_signal, ir, mix=1.0)
        assert result.ndim == 2  # Mono promoted to stereo

    def test_stereo_source_stereo_ir(self, stereo_signal):
        ir_data = np.zeros((100, 2))
        ir_data[0, :] = 1.0
        ir = self._make_ir(ir_data, channels=2)
        result = convolve_with_ir(stereo_signal, ir, mix=1.0)
        assert result.ndim == 2
        assert result.shape[1] == 2

    def test_mix_zero_returns_dry(self, test_signal):
        ir_data = np.ones(100) * 0.5  # Non-trivial IR
        ir = self._make_ir(ir_data)
        result = convolve_with_ir(test_signal, ir, mix=0.0)
        np.testing.assert_allclose(result, test_signal, atol=1e-10)

    def test_mix_one_differs_from_dry(self, test_signal):
        ir_data = np.zeros(100)
        ir_data[0] = 0.5
        ir_data[10] = 0.5  # Delay = produces echo
        ir = self._make_ir(ir_data)
        result = convolve_with_ir(test_signal, ir, mix=1.0)
        assert not np.allclose(result, test_signal, atol=0.01)

    def test_mix_clamping(self, test_signal):
        ir_data = np.zeros(100)
        ir_data[0] = 1.0
        ir = self._make_ir(ir_data)
        # Should not crash with out-of-range mix values
        result_low = convolve_with_ir(test_signal, ir, mix=-0.5)
        result_high = convolve_with_ir(test_signal, ir, mix=1.5)
        assert np.all(np.isfinite(result_low))
        assert np.all(np.isfinite(result_high))

    def test_output_length_matches_source(self, test_signal):
        ir_data = np.random.randn(500)
        ir = self._make_ir(ir_data)
        result = convolve_with_ir(test_signal, ir, mix=1.0)
        assert len(result) == len(test_signal)
