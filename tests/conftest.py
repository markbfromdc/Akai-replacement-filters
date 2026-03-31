"""Shared test fixtures and helpers."""

import tempfile
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf


@pytest.fixture
def tmp_dir():
    """Provide a temporary directory that is cleaned up after the test."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def mono_wav(tmp_dir):
    """Create a mono .wav test file and return its path."""
    path = tmp_dir / "test_mono.wav"
    t = np.arange(4410) / 44100.0
    audio = 0.5 * np.sin(2 * np.pi * 440.0 * t)
    sf.write(str(path), audio, 44100)
    return path


@pytest.fixture
def stereo_wav(tmp_dir):
    """Create a stereo .wav test file and return its path."""
    path = tmp_dir / "test_stereo.wav"
    t = np.arange(4410) / 44100.0
    left = 0.5 * np.sin(2 * np.pi * 440.0 * t)
    right = 0.5 * np.sin(2 * np.pi * 880.0 * t)
    audio = np.column_stack([left, right])
    sf.write(str(path), audio, 44100)
    return path


@pytest.fixture
def mono_wav_48k(tmp_dir):
    """Create a mono .wav at 48kHz for resampling tests."""
    path = tmp_dir / "test_48k.wav"
    t = np.arange(4800) / 48000.0
    audio = 0.5 * np.sin(2 * np.pi * 440.0 * t)
    sf.write(str(path), audio, 48000)
    return path


@pytest.fixture
def short_ir_wav(tmp_dir):
    """Create a short impulse response .wav file."""
    path = tmp_dir / "short_ir.wav"
    # Simple decaying impulse
    ir = np.zeros(1000)
    ir[0] = 1.0
    ir[1:] = np.exp(-np.arange(999) / 100.0) * 0.5
    sf.write(str(path), ir, 44100)
    return path


@pytest.fixture
def test_signal():
    """Generate a mono test sine wave (0.1s at 440Hz)."""
    t = np.arange(4410) / 44100.0
    return 0.8 * np.sin(2 * np.pi * 440.0 * t)


@pytest.fixture
def stereo_signal():
    """Generate a stereo test signal."""
    t = np.arange(4410) / 44100.0
    left = 0.8 * np.sin(2 * np.pi * 440.0 * t)
    right = 0.6 * np.sin(2 * np.pi * 880.0 * t)
    return np.column_stack([left, right])
