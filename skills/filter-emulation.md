# DSP Filter Emulation Creation

Create DSP filter emulations (SVF, ladder, comb, formant) targeting Akai MPC architecture.

## When to Use
Use this skill when the user wants to:
- Implement a custom DSP filter algorithm
- Prototype filter behavior in Python/numpy before baking into samples
- Create filter emulations that approximate analog hardware

## Filter Architectures

### State Variable Filter (SVF) — Andy Simper's TPT Equations
The most portable and widely-used filter topology. Provides simultaneous LP, HP, BP, and Notch outputs.

```python
import numpy as np

def svf_process(audio, cutoff_hz, resonance, sample_rate=44100, filter_type="lp"):
    """Topology-Preserving Transform State Variable Filter."""
    g = np.tan(np.pi * cutoff_hz / sample_rate)
    k = 2.0 - 2.0 * resonance  # resonance 0-1
    a1 = 1.0 / (1.0 + g * (g + k))
    a2 = g * a1
    a3 = g * a2

    ic1eq = 0.0
    ic2eq = 0.0
    output = np.zeros_like(audio)

    for i in range(len(audio)):
        v0 = audio[i]
        v3 = v0 - ic2eq
        v1 = a1 * ic1eq + a2 * v3
        v2 = ic2eq + a2 * ic1eq + a3 * v3
        ic1eq = 2.0 * v1 - ic1eq
        ic2eq = 2.0 * v2 - ic2eq

        if filter_type == "lp":
            output[i] = v2
        elif filter_type == "hp":
            output[i] = v0 - k * v1 - v2
        elif filter_type == "bp":
            output[i] = v1
        elif filter_type == "notch":
            output[i] = v0 - k * v1

    return output
```

### Moog Ladder Filter (4-pole LP)
Classic 24dB/oct resonant low-pass. Maps directly to Akai LP4 mode.

```python
def moog_ladder(audio, cutoff_hz, resonance, sample_rate=44100):
    """Simplified Moog ladder filter (Huovilainen model)."""
    fc = cutoff_hz / sample_rate
    f = fc * 1.16
    fb = resonance * (1.0 - 0.15 * f * f)
    stages = [0.0, 0.0, 0.0, 0.0]
    output = np.zeros_like(audio)

    for i in range(len(audio)):
        x = audio[i] - fb * stages[3]
        for s in range(4):
            stages[s] = stages[s] + f * (np.tanh(x) - np.tanh(stages[s]))
            x = stages[s]
        output[i] = stages[3]

    return output
```

### Comb Filter
For Serum comb/flanger filter fallbacks. Bake the output as an IR.

```python
def comb_filter(audio, delay_ms=5.0, feedback=0.7, sample_rate=44100):
    """Feedforward + feedback comb filter."""
    delay_samples = int(delay_ms * sample_rate / 1000.0)
    output = np.zeros_like(audio)
    buffer = np.zeros(delay_samples)
    buf_idx = 0

    for i in range(len(audio)):
        delayed = buffer[buf_idx]
        output[i] = audio[i] + feedback * delayed
        buffer[buf_idx] = audio[i] + feedback * delayed
        buf_idx = (buf_idx + 1) % delay_samples

    return output
```

### Formant Filter
For Serum vowel/formant filter fallbacks.

```python
def formant_filter(audio, vowel="a", sample_rate=44100):
    """Simple formant filter using parallel bandpass filters."""
    from scipy.signal import butter, sosfilt

    # Formant frequencies for vowels (F1, F2, F3)
    formants = {
        "a": [800, 1150, 2900],
        "e": [350, 2000, 2800],
        "i": [270, 2140, 3200],
        "o": [450, 800, 2830],
        "u": [325, 700, 2530],
    }
    freqs = formants.get(vowel, formants["a"])
    output = np.zeros_like(audio)
    for f in freqs:
        bw = f * 0.1  # 10% bandwidth
        low = max(20, f - bw)
        high = min(sample_rate / 2 - 1, f + bw)
        sos = butter(2, [low, high], btype="band", fs=sample_rate, output="sos")
        output += sosfilt(sos, audio) / len(freqs)
    return output
```

## Integration with Akai MPC

After prototyping a filter, use it to process source samples offline:

```python
from src.impulse.saturation import apply_saturation, SaturationMode
from src.xpm import KeygroupProgram, Instrument, PadLayer
from src.xpm.filter_params import FilterConfig, FilterType

# Process audio through custom filter
processed = svf_process(audio, cutoff_hz=2000, resonance=0.7)

# Save as .wav and reference in XPM program
import soundfile as sf
sf.write("processed.wav", processed, 44100)
```

## Key Source Files
- `src/xpm/filter_params.py` — FilterConfig, hz_to_mpc, FilterType
- `src/impulse/ir_loader.py` — convolve_with_ir for IR-based approaches
- `src/impulse/saturation.py` — Saturation modes to chain after filtering
