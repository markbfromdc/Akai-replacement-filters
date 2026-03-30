# Flavor Plugin — Impulse Response & Saturation

Upload custom impulse responses and apply saturation modes to create flavor-processed Akai MPC programs.

## When to Use
Use this skill when the user wants to:
- Apply impulse responses to samples for MPC programs
- Use saturation/distortion modes to color audio
- Create flavor packs combining IR + saturation chains
- Process Serum exotic filter types via IR fallback

## Saturation Modes

| Mode | Character | Best For |
|---|---|---|
| `SOFT_CLIP` | Warm, gentle compression | Subtle warmth on any source |
| `HARD_CLIP` | Aggressive, digital edge | Harsh leads, distorted drums |
| `TAPE` | Analog tape warmth | Vintage drum machines, lo-fi |
| `TUBE` | Vacuum tube richness | Bass, synth leads, warmth |
| `TRANSFORMER` | Iron-core LF thickening | Bass, kick drums |
| `DIODE` | Germanium/silicon grit | Guitars, aggressive synths |
| `FOLDBACK` | Complex harmonics | Sound design, metallic textures |
| `BITCRUSH` | Lo-fi digital degradation | Retro, chiptune, industrial |
| `VINYL` | Record player character | Lo-fi hip-hop, ambient |
| `CONSOLE` | Mixing desk coloration | Subtle glue, mix bus warmth |

## Quick Start

### Apply Saturation to Audio
```python
import numpy as np
import soundfile as sf
from src.impulse import apply_saturation, SaturationMode
from src.impulse.saturation import SaturationParams

audio, sr = sf.read("source.wav", dtype="float64")

# Tape saturation with moderate drive
processed = apply_saturation(
    audio,
    SaturationMode.TAPE,
    SaturationParams(drive=0.6, mix=0.8, tone=0.45, output=0.85),
    sample_rate=sr,
)

sf.write("output.wav", processed, sr)
```

### Chain Multiple Saturation Modes
```python
# Tube → Tape → Console (classic mastering chain)
audio = apply_saturation(audio, SaturationMode.TUBE, SaturationParams(drive=0.3))
audio = apply_saturation(audio, SaturationMode.TAPE, SaturationParams(drive=0.4))
audio = apply_saturation(audio, SaturationMode.CONSOLE, SaturationParams(drive=0.2))
```

### Load and Apply Impulse Response
```python
from src.impulse import load_ir
from src.impulse.ir_loader import convolve_with_ir

ir = load_ir("cabinet.wav", target_sr=44100)
processed = convolve_with_ir(audio, ir, mix=0.7)
```

### Build a Flavor Pack (Full Pipeline)
```python
from src.impulse import FlavorPack, SaturationMode
from src.impulse.flavor_pack import FlavorRecipe
from src.xpm.filter_params import FilterConfig, FilterType

# Create a recipe: reverb IR + tape + tube saturation
recipe = FlavorRecipe(
    ir_path="plate_reverb.wav",
    ir_mix=0.4,
    output_filter=FilterConfig(filter_type=FilterType.LP4, cutoff=90),
)
recipe.add_saturation(SaturationMode.TAPE, drive=0.5, tone=0.4)
recipe.add_saturation(SaturationMode.TUBE, drive=0.3, mix=0.6)

# Build MPC drum program from multiple flavored samples
pack = FlavorPack("Vintage Kit")
pack.add_source("kick.wav", recipe)
pack.add_source("snare.wav", recipe)
pack.add_source("hat.wav", recipe)
xpm_path = pack.build("output/", program_type="drum")
```

## Saturation Parameters

All modes share 4 parameters:

| Parameter | Range | Effect |
|---|---|---|
| `drive` | 0.0-1.0 | Input gain (1x-10x). Higher = more saturation |
| `mix` | 0.0-1.0 | Dry/wet blend. 0=clean, 1=fully saturated |
| `tone` | 0.0-1.0 | Post-saturation tilt EQ. <0.5=dark, >0.5=bright |
| `output` | 0.0-1.0 | Makeup gain. Compensate for level changes |

## Key Source Files
- `src/impulse/saturation.py` — 10 saturation modes with SaturationParams
- `src/impulse/ir_loader.py` — IR loading, resampling, convolution
- `src/impulse/flavor_pack.py` — FlavorPack orchestrator
- `src/xpm/builder.py` — XPM program generation
