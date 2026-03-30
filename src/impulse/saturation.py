"""Saturation mode engine with 10 distinct saturation algorithms.

Each mode shapes harmonic content differently, emulating various
analog hardware characteristics. Processed audio can be baked into
samples for Akai MPC programs.
"""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass

import numpy as np


class SaturationMode(Enum):
    """Available saturation modes for the flavor plugin."""
    SOFT_CLIP = "soft_clip"
    HARD_CLIP = "hard_clip"
    TAPE = "tape"
    TUBE = "tube"
    TRANSFORMER = "transformer"
    DIODE = "diode"
    FOLDBACK = "foldback"
    BITCRUSH = "bitcrush"
    VINYL = "vinyl"
    CONSOLE = "console"


@dataclass
class SaturationParams:
    """Parameters shared across all saturation modes."""
    drive: float = 0.5      # Input gain (0.0-1.0, mapped to 1x-10x)
    mix: float = 1.0        # Dry/wet blend (0.0-1.0)
    tone: float = 0.5       # Post-saturation tilt EQ (0.0=dark, 1.0=bright)
    output: float = 0.8     # Makeup gain (0.0-1.0)

    @property
    def drive_linear(self) -> float:
        """Convert drive 0-1 to linear gain (1x to 10x)."""
        return 1.0 + self.drive * 9.0


def _apply_tone(signal: np.ndarray, tone: float, sr: int = 44100) -> np.ndarray:
    """Apply a simple tilt EQ: tone < 0.5 darkens, > 0.5 brightens."""
    if abs(tone - 0.5) < 0.01:
        return signal

    from scipy.signal import butter, sosfilt

    if tone < 0.5:
        # Darken: low-pass
        cutoff = 2000 + tone * 16000  # 2kHz to 10kHz
        sos = butter(1, cutoff, btype="low", fs=sr, output="sos")
    else:
        # Brighten: high shelf approximated as gentle HP boost
        blend = (tone - 0.5) * 2.0
        cutoff = 3000
        sos = butter(1, cutoff, btype="high", fs=sr, output="sos")
        hp = sosfilt(sos, signal)
        return signal + blend * 0.5 * hp

    return sosfilt(sos, signal)


def _soft_clip(x: np.ndarray, gain: float) -> np.ndarray:
    """Warm, gentle compression via tanh."""
    return np.tanh(gain * x)


def _hard_clip(x: np.ndarray, gain: float) -> np.ndarray:
    """Aggressive digital clipping."""
    return np.clip(gain * x, -1.0, 1.0)


def _tape(x: np.ndarray, gain: float) -> np.ndarray:
    """Analog tape emulation: asymmetric soft clip + hysteresis approximation."""
    driven = gain * x
    # Asymmetric saturation (positive side clips harder)
    positive = np.tanh(driven * 1.2)
    negative = np.tanh(driven * 0.8)
    saturated = np.where(driven >= 0, positive, negative)
    # Simple hysteresis approximation via IIR smoothing
    result = np.zeros_like(saturated)
    result[0] = saturated[0]
    alpha = 0.05
    for i in range(1, len(saturated)):
        result[i] = alpha * saturated[i] + (1 - alpha) * result[i - 1]
    return result


def _tube(x: np.ndarray, gain: float) -> np.ndarray:
    """Vacuum tube warmth: waveshaper with even harmonic boost."""
    driven = gain * x
    # Core waveshaper: x / (1 + |x|)
    shaped = driven / (1.0 + np.abs(driven))
    # Add subtle 2nd harmonic (even-order distortion)
    second_harmonic = 0.15 * np.square(shaped)
    return shaped + second_harmonic


def _transformer(x: np.ndarray, gain: float) -> np.ndarray:
    """Iron-core transformer coloration: asymmetric clipping + LF emphasis."""
    driven = gain * x
    # Asymmetric clipping with LF bias
    bias = 0.1
    saturated = np.tanh((driven + bias) * 1.5) - np.tanh(bias * 1.5)
    # LF emphasis: simple single-pole LP blend
    lf = np.zeros_like(saturated)
    lf[0] = saturated[0]
    for i in range(1, len(saturated)):
        lf[i] = 0.15 * saturated[i] + 0.85 * lf[i - 1]
    return 0.7 * saturated + 0.3 * lf


def _diode(x: np.ndarray, gain: float) -> np.ndarray:
    """Germanium/silicon diode distortion."""
    driven = gain * x
    return np.sign(driven) * (1.0 - np.exp(-np.abs(driven)))


def _foldback(x: np.ndarray, gain: float) -> np.ndarray:
    """Wavefolder: generates complex harmonics via signal folding."""
    driven = gain * x
    # Foldback formula: folds signal back at +-1 boundaries
    return np.abs(np.abs(np.fmod(driven - 1.0, 4.0)) - 2.0) - 1.0


def _bitcrush(x: np.ndarray, gain: float) -> np.ndarray:
    """Lo-fi digital degradation: bit depth and sample rate reduction."""
    # Map drive to bit depth: high drive = fewer bits (more crushed)
    bit_depth = max(2, int(16 - gain * 12))  # 16-bit down to 4-bit
    # Map drive to sample rate reduction factor
    sr_factor = max(1, int(1 + gain * 15))  # 1x to 16x reduction

    # Bit depth reduction
    levels = 2 ** bit_depth
    crushed = np.round(x * levels) / levels

    # Sample rate reduction (sample & hold)
    if sr_factor > 1:
        held = np.copy(crushed)
        for i in range(len(held)):
            if i % sr_factor != 0:
                held[i] = held[i - (i % sr_factor)]
        return held

    return crushed


def _vinyl(x: np.ndarray, gain: float) -> np.ndarray:
    """Record player character: gentle compression + noise + HF wobble."""
    # Gentle compression via soft clip at lower gain
    compressed = np.tanh(x * (1.0 + gain * 2.0))
    # Add subtle noise floor
    noise = np.random.normal(0, 0.003 * gain, len(x))
    # HF wobble (very slow amplitude modulation)
    t = np.arange(len(x)) / 44100.0
    wobble = 1.0 + 0.02 * gain * np.sin(2 * np.pi * 0.5 * t)
    return compressed * wobble + noise


def _console(x: np.ndarray, gain: float) -> np.ndarray:
    """Mixing desk coloration: subtle compression + harmonic saturation."""
    driven = x * (1.0 + gain * 3.0)
    # Gentle compression curve
    compressed = np.sign(driven) * np.log1p(np.abs(driven)) / np.log1p(1.0 + gain * 3.0)
    # Add subtle odd harmonics
    harmonics = 0.05 * gain * np.power(compressed, 3)
    return compressed + harmonics


# Dispatch table
_PROCESSORS: dict[SaturationMode, callable] = {
    SaturationMode.SOFT_CLIP: _soft_clip,
    SaturationMode.HARD_CLIP: _hard_clip,
    SaturationMode.TAPE: _tape,
    SaturationMode.TUBE: _tube,
    SaturationMode.TRANSFORMER: _transformer,
    SaturationMode.DIODE: _diode,
    SaturationMode.FOLDBACK: _foldback,
    SaturationMode.BITCRUSH: _bitcrush,
    SaturationMode.VINYL: _vinyl,
    SaturationMode.CONSOLE: _console,
}


def apply_saturation(
    audio: np.ndarray,
    mode: SaturationMode,
    params: SaturationParams | None = None,
    sample_rate: int = 44100,
) -> np.ndarray:
    """Apply a saturation mode to audio data.

    Args:
        audio: Input audio (1D mono or 2D stereo, float64, range -1..1).
        mode: Which saturation algorithm to use.
        params: Saturation parameters (drive, mix, tone, output).
                Defaults to SaturationParams() if not provided.
        sample_rate: Sample rate for tone EQ processing.

    Returns:
        Processed audio with saturation applied.
    """
    if params is None:
        params = SaturationParams()

    processor = _PROCESSORS[mode]
    gain = params.drive_linear

    # Process each channel independently for stereo
    if audio.ndim == 2:
        processed = np.column_stack([
            processor(audio[:, ch], gain)
            for ch in range(audio.shape[1])
        ])
    else:
        processed = processor(audio, gain)

    # Apply tone EQ
    if audio.ndim == 2:
        for ch in range(processed.shape[1]):
            processed[:, ch] = _apply_tone(processed[:, ch], params.tone, sample_rate)
    else:
        processed = _apply_tone(processed, params.tone, sample_rate)

    # Dry/wet mix
    mixed = (1.0 - params.mix) * audio + params.mix * processed

    # Output gain
    mixed = mixed * params.output

    # Final clip to prevent overs
    return np.clip(mixed, -1.0, 1.0)
