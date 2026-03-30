"""Impulse response loader and validator for Akai MPC program generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf


@dataclass
class ImpulseResponse:
    """A loaded and validated impulse response."""
    data: np.ndarray       # Audio samples (mono or stereo)
    sample_rate: int
    channels: int
    duration_seconds: float
    source_path: str

    @property
    def is_stereo(self) -> bool:
        return self.channels == 2

    @property
    def num_samples(self) -> int:
        return self.data.shape[0]


def load_ir(file_path: str | Path, target_sr: int = 44100) -> ImpulseResponse:
    """Load an impulse response .wav file.

    Args:
        file_path: Path to the IR .wav file.
        target_sr: Target sample rate. If the IR has a different rate,
                   it will be resampled.

    Returns:
        ImpulseResponse with loaded audio data.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        ValueError: If the file is not a valid audio file.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"IR file not found: {file_path}")

    data, sr = sf.read(str(file_path), dtype="float64")

    # Ensure 2D array (samples x channels)
    if data.ndim == 1:
        channels = 1
    else:
        channels = data.shape[1]

    # Resample if needed
    if sr != target_sr:
        from scipy.signal import resample

        num_target_samples = int(len(data) * target_sr / sr)
        if data.ndim == 1:
            data = resample(data, num_target_samples)
        else:
            data = np.column_stack([
                resample(data[:, ch], num_target_samples)
                for ch in range(channels)
            ])
        sr = target_sr

    # Normalize peak to 1.0
    peak = np.max(np.abs(data))
    if peak > 0:
        data = data / peak

    duration = len(data) / sr

    return ImpulseResponse(
        data=data,
        sample_rate=sr,
        channels=channels,
        duration_seconds=duration,
        source_path=str(file_path),
    )


def convolve_with_ir(source: np.ndarray, ir: ImpulseResponse, mix: float = 1.0) -> np.ndarray:
    """Convolve source audio with an impulse response.

    Args:
        source: Source audio samples (1D mono or 2D stereo).
        ir: The impulse response to convolve with.
        mix: Dry/wet mix (0.0 = fully dry, 1.0 = fully wet).

    Returns:
        Convolved audio, trimmed to source length.
    """
    from scipy.signal import fftconvolve

    mix = max(0.0, min(1.0, mix))

    if source.ndim == 1 and ir.data.ndim == 1:
        wet = fftconvolve(source, ir.data, mode="full")[:len(source)]
    elif source.ndim == 1 and ir.data.ndim == 2:
        # Mono source, stereo IR → stereo output
        wet = np.column_stack([
            fftconvolve(source, ir.data[:, ch], mode="full")[:len(source)]
            for ch in range(ir.channels)
        ])
    elif source.ndim == 2 and ir.data.ndim == 1:
        # Stereo source, mono IR
        wet = np.column_stack([
            fftconvolve(source[:, ch], ir.data, mode="full")[:len(source)]
            for ch in range(source.shape[1])
        ])
    else:
        # Stereo source, stereo IR
        channels = min(source.shape[1], ir.channels)
        wet = np.column_stack([
            fftconvolve(source[:, ch], ir.data[:, ch], mode="full")[:len(source)]
            for ch in range(channels)
        ])

    # Normalize wet signal
    peak = np.max(np.abs(wet))
    if peak > 0:
        wet = wet / peak

    # Dry/wet blend
    if source.ndim != wet.ndim:
        # Promote source to match wet dimensions
        if source.ndim == 1 and wet.ndim == 2:
            source = np.column_stack([source, source])

    return (1.0 - mix) * source + mix * wet
