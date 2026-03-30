# XPM Creator with Full Mod Matrix

Create Akai MPC .xpm programs (drum and keygroup) with full modulation matrix manipulation.

## When to Use
Use this skill when the user wants to:
- Create XPM drum programs or keygroup programs
- Set up modulation routings (velocity→cutoff, LFO→resonance, etc.)
- Configure multi-layer instruments with velocity splits
- Build programs with custom filter settings

## Quick Start

### Drum Program
```python
from src.xpm import DrumProgram, Instrument, PadLayer, FilterConfig, FilterType, ModMatrix
from src.xpm.mod_matrix import ModSource, ModDest, ModCurve

# Create program
program = DrumProgram("My Kit")

# Create instrument with filter
kick = Instrument(
    name="Kick",
    filter_config=FilterConfig(
        filter_type=FilterType.LP4,
        cutoff=80,
        resonance=20,
        env_amount=64,
        decay=40,
    ),
)
kick.add_layer(PadLayer(sample_path="Samples/kick.wav"))

# Add mod matrix routing
kick.mod_matrix.add(ModSource.VELOCITY, ModDest.CUTOFF, depth=80)
kick.mod_matrix.add(ModSource.VELOCITY, ModDest.VOLUME, depth=100)

program.add_pad(kick, bank="A", pad=1)
program.save("output/")
```

### Keygroup Program with Velocity Layers
```python
from src.xpm import KeygroupProgram, Instrument, PadLayer, FilterConfig, FilterType

program = KeygroupProgram("Velocity Piano")

piano = Instrument(
    name="Piano",
    filter_config=FilterConfig(filter_type=FilterType.LP4, cutoff=100, resonance=10),
)

# 4 velocity layers
piano.add_layer(PadLayer(sample_path="Samples/piano_pp.wav", velocity_low=0, velocity_high=31))
piano.add_layer(PadLayer(sample_path="Samples/piano_mp.wav", velocity_low=32, velocity_high=63))
piano.add_layer(PadLayer(sample_path="Samples/piano_mf.wav", velocity_low=64, velocity_high=95))
piano.add_layer(PadLayer(sample_path="Samples/piano_ff.wav", velocity_low=96, velocity_high=127))

program.add_keygroup(piano)
program.save("output/")
```

## Mod Matrix Deep Dive

### Available Sources
| Source | Use For |
|---|---|
| `Velocity` | Dynamic filter response to playing intensity |
| `Aftertouch` | Pressure-sensitive filter sweeps |
| `ModWheel` | Manual filter control via CC1 |
| `KeyTrack` | Cutoff follows keyboard position |
| `LFO1` / `LFO2` | Rhythmic filter modulation |
| `FilterEnv` | ADSR-driven filter sweeps |
| `AmpEnv` | Volume envelope as mod source |
| `PitchBend` | Pitch wheel filter control |
| `Expression` | CC11 expression pedal |

### Available Destinations
| Destination | Effect |
|---|---|
| `FilterCutoff` | Open/close the filter |
| `FilterResonance` | Boost resonant peak |
| `Volume` | Dynamic volume control |
| `Pan` | Stereo movement |
| `Pitch` | Pitch modulation |
| `LFO1Rate` / `LFO2Rate` | LFO speed modulation |
| `SampleStart` | Change playback start point |

### Complex Routing Example
```python
from src.xpm.mod_matrix import ModMatrix, ModSource, ModDest, ModCurve

mm = ModMatrix()
mm.add(ModSource.VELOCITY, ModDest.CUTOFF, depth=80, curve=ModCurve.EXPONENTIAL)
mm.add(ModSource.MOD_WHEEL, ModDest.CUTOFF, depth=127)
mm.add(ModSource.LFO1, ModDest.CUTOFF, depth=30)
mm.add(ModSource.KEY_TRACK, ModDest.CUTOFF, depth=64)
mm.add(ModSource.AFTERTOUCH, ModDest.RESONANCE, depth=50)
mm.add(ModSource.VELOCITY, ModDest.VOLUME, depth=100)
mm.add(ModSource.LFO2, ModDest.PAN, depth=40)
mm.add(ModSource.PITCH_BEND, ModDest.PITCH, depth=127)
# Max 8 routes per instrument
```

## Key Source Files
- `src/xpm/builder.py` — DrumProgram, KeygroupProgram, Instrument, PadLayer
- `src/xpm/filter_params.py` — FilterConfig, FilterType, hz_to_mpc
- `src/xpm/mod_matrix.py` — ModMatrix, ModRoute, ModSource, ModDest, ModCurve
