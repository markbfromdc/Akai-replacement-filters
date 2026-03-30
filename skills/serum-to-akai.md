# Serum to Akai Filter Conversion

Convert 3rd party Xfer Serum filter presets to Akai MPC filter modes.

## When to Use
Use this skill when the user wants to:
- Convert Serum .fxp or .SerumPreset files to Akai MPC programs
- Map Serum filter types to Akai filter modes
- Upload custom Serum filter modules to key groups or drum programs

## Conversion Process

### 1. Parse the Serum Preset
```python
from src.serum import parse_fxp, parse_serum_preset

# Serum v1 (.fxp)
preset = parse_fxp("path/to/preset.fxp")

# Serum 2 (.SerumPreset)
preset = parse_serum_preset("path/to/preset.SerumPreset")
```

### 2. Create a SerumFilterConfig
```python
from src.serum.filter_map import SerumFilterConfig, serum_to_akai

config = SerumFilterConfig(
    filter_type=preset.filter_type_raw,
    cutoff=preset.filter_cutoff,
    resonance=preset.filter_resonance,
    drive=preset.filter_drive,
    fat=preset.filter_fat,
    mix=preset.filter_mix,
    env_attack=preset.filter_env_attack,
    env_decay=preset.filter_env_decay,
    env_sustain=preset.filter_env_sustain,
    env_release=preset.filter_env_release,
    env_amount=preset.filter_env_amount,
)
```

### 3. Convert to Akai Filter Mode
```python
result = serum_to_akai(config)

# result.filter_config — Akai FilterConfig ready for XPM
# result.needs_ir_fallback — True if exotic filter needs IR baking
# result.ir_description — What IR processing is needed
# result.drive_as_insert_gain — Mapped drive value for Akai insert FX
```

### 4. Build an XPM Program
```python
from src.xpm import DrumProgram, KeygroupProgram, Instrument, PadLayer

program = KeygroupProgram("Serum_Converted")
instrument = Instrument(
    name="Lead",
    filter_config=result.filter_config,
)
instrument.add_layer(PadLayer(sample_path="Samples/source.wav"))
program.add_keygroup(instrument)
program.save("output/")
```

## Filter Type Mapping Reference

| Serum Filter | Akai Mode | Direct? |
|---|---|---|
| Normal LP 6/12/24/48dB | LP1/LP2/LP4/LP6 | Yes |
| Normal HP 6/12/24dB | HP1/HP2 | Yes |
| Normal BP | BP | Yes |
| Normal Notch | BandReject | Yes |
| Multi types | Closest LP/BP + layers | Approximate |
| Comb/Phaser/Flanger | LP2 + IR bake | IR fallback |
| Formant/Vowel | BP + IR bake | IR fallback |
| Reverb | LP4 + IR bake | IR fallback |

## Key Source Files
- `src/serum/parser_v1.py` — .fxp parser
- `src/serum/parser_v2.py` — .SerumPreset parser
- `src/serum/filter_map.py` — Core conversion engine
- `src/xpm/builder.py` — XPM program builder
- `src/xpm/filter_params.py` — Akai filter parameter model
