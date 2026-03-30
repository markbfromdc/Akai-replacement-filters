# KikGen LD_PRELOAD Optimization

Optimize the TheKikGen/MPC-LiveXplore LD_PRELOAD technique for custom filter injection on Akai MPC devices.

## When to Use
Use this skill when the user wants to:
- Generate optimized LD_PRELOAD launch scripts for MPC Live/X/One
- Create TKGL_MIDIMAPPER configurations for filter CC mapping
- Build custom .so libraries for runtime filter parameter injection
- Optimize library loading order or intercepted function calls

## Generate Optimized Launch Script

```python
from src.kikgen import generate_preload_script

script = generate_preload_script(
    libraries=[
        "./tkgl_midimapper.so",
        "./filter_inject.so",
    ],
    device_type="mpc_live",  # or "mpc_x", "mpc_one", "force"
    extra_env={"TKGL_VERBOSE": "1"},
    output_path="launch_mpc.sh",
)
```

## Generate MIDI Mapper Config

```python
from src.kikgen import generate_midimapper_config
from src.kikgen.midimapper_config import CCMapping

# With default filter controls (CC74=cutoff, CC71=resonance, etc.)
config_json = generate_midimapper_config(
    device_name="Arturia KeyStep",
    include_filter_defaults=True,
    output_path="midimapper.json",
)

# Custom mappings
custom = [
    CCMapping(source_cc=16, target_cc=74, description="Knob 1 → Cutoff"),
    CCMapping(source_cc=17, target_cc=71, description="Knob 2 → Resonance"),
    CCMapping(source_cc=18, target_cc=73, min_value=0, max_value=100, description="Knob 3 → Attack"),
]
config_json = generate_midimapper_config(
    device_name="Generic MIDI Controller",
    mappings=custom,
    output_path="custom_mapper.json",
)
```

## Generate Filter Injection Library

```python
from src.kikgen import generate_filter_inject_source
from src.kikgen.filter_inject import generate_makefile

# Generate C source
source = generate_filter_inject_source(
    filter_cc_cutoff=74,
    filter_cc_resonance=71,
    initial_cutoff=100,
    initial_resonance=30,
    output_path="filter_inject.c",
)

# Generate Makefile
makefile = generate_makefile(output_path="Makefile")

# Compile (requires ARM toolchain):
# make
```

## Optimization Tips

### Library Loading Order
Load libraries in dependency order. The filter injection library should load after TKGL_MIDIMAPPER:
```
LD_PRELOAD=./tkgl_midimapper.so:./filter_inject.so /usr/bin/MPC
```

### Intercepted Functions
- `snd_rawmidi_write` — MIDI output (filter CC injection)
- `snd_pcm_writei` — Audio output (for monitoring)
- `snd_seq_event_output` — ALSA sequencer events

### Filter CC Standard Assignments
| CC | Parameter | Range |
|---|---|---|
| 74 | Filter Cutoff (Brightness) | 0-127 |
| 71 | Filter Resonance (Timbre) | 0-127 |
| 73 | Attack Time | 0-127 |
| 75 | Decay Time | 0-127 |
| 72 | Release Time | 0-127 |
| 1 | Mod Wheel | 0-127 |

## Key Source Files
- `src/kikgen/preload_gen.py` — Launch script generator
- `src/kikgen/midimapper_config.py` — TKGL_MIDIMAPPER config generator
- `src/kikgen/filter_inject.py` — C source code generator
- GitHub reference: TheKikGen/MPC-LiveXplore, TheKikGen/MPCLiveXplore-libs
