# Data Models & File Format Specifications

| Field | Value |
|-------|-------|
| Version | 0.1.0 |
| Date | 2026-03-31 |
| Status | Active |
| Traceability | [API](api.md) &#124; [Architecture](architecture.md) &#124; [Testing](testing.md) |

---

## Table of Contents

1. [Dataclasses](#1-dataclasses)
2. [Enumerations](#2-enumerations)
3. [XPM File Format](#3-xpm-file-format)
4. [FXP File Format (Serum v1)](#4-fxp-file-format-serum-v1)
5. [SerumPreset Format (Serum v2)](#5-serumpreset-format-serum-v2)
6. [MIDI Mapper JSON](#6-midi-mapper-json)
7. [MockbaMod Manifest JSON](#7-mockbamod-manifest-json)
8. [Filter Mapping Tables](#8-filter-mapping-tables)
9. [Audio Conventions](#9-audio-conventions)

---

## 1. Dataclasses

### 1.1 FilterConfig (`src/xpm/filter_params.py`)

| Field | Type | Default | Range | XPM XML Tag |
|-------|------|---------|-------|-------------|
| `filter_type` | `FilterType` | `LP4` | enum | `FilterType` |
| `cutoff` | `int` | `127` | 0-127 | `FilterCutoff` |
| `resonance` | `int` | `0` | 0-127 | `FilterResonance` |
| `env_amount` | `int` | `0` | 0-127 | `FilterEnvAmount` |
| `attack` | `int` | `0` | 0-127 | `FilterAttack` |
| `decay` | `int` | `64` | 0-127 | `FilterDecay` |
| `sustain` | `int` | `127` | 0-127 | `FilterSustain` |
| `release` | `int` | `40` | 0-127 | `FilterRelease` |

**Validation:** `__post_init__()` clamps all integer fields to [0, 127] via `max(0, min(127, val))`.

**Methods:**
- `to_xml_dict() -> dict[str, str]` -- Returns XML tag names mapped to string values.

### 1.2 PadLayer (`src/xpm/builder.py`)

| Field | Type | Default | Range |
|-------|------|---------|-------|
| `sample_path` | `str` | (required) | relative path |
| `volume` | `int` | `100` | 0-127 |
| `pan` | `int` | `64` | 0-127 (64=center) |
| `tune_coarse` | `int` | `0` | -36 to +36 semitones |
| `tune_fine` | `int` | `0` | -99 to +99 cents |
| `root_note` | `int` | `60` | 0-127 MIDI (60=C4) |
| `key_low` | `int` | `0` | 0-127 MIDI |
| `key_high` | `int` | `127` | 0-127 MIDI |
| `velocity_low` | `int` | `0` | 0-127 |
| `velocity_high` | `int` | `127` | 0-127 |

### 1.3 Instrument (`src/xpm/builder.py`)

| Field | Type | Default | Constraint |
|-------|------|---------|-----------|
| `name` | `str` | `""` | -- |
| `layers` | `list[PadLayer]` | `[]` | max 4 (ValueError on 5th) |
| `filter_config` | `FilterConfig` | `FilterConfig()` | -- |
| `mod_matrix` | `ModMatrix` | `ModMatrix()` | -- |
| `volume` | `int` | `100` | 0-127 |
| `pan` | `int` | `64` | 0-127 |
| `mute_group` | `int` | `0` | 0=none, 1-32 |

### 1.4 ModRoute (`src/xpm/mod_matrix.py`)

| Field | Type | Default | Range |
|-------|------|---------|-------|
| `source` | `ModSource` | (required) | enum |
| `destination` | `ModDest` | (required) | enum |
| `depth` | `int` | `0` | -127 to +127 |
| `curve` | `ModCurve` | `LINEAR` | enum |

**Validation:** `__post_init__()` clamps `depth` to [-127, 127].

### 1.5 SerumFilterConfig (`src/serum/filter_map.py`)

| Field | Type | Default | Range |
|-------|------|---------|-------|
| `filter_type` | `int` | `0` | raw type index |
| `cutoff` | `float` | `0.5` | 0.0-1.0 |
| `resonance` | `float` | `0.0` | 0.0-1.0 |
| `drive` | `float` | `0.0` | 0.0-1.0 |
| `fat` | `float` | `0.0` | 0.0-1.0 |
| `mix` | `float` | `1.0` | 0.0-1.0 |
| `pan` | `float` | `0.5` | 0.0-1.0 (0.5=center) |
| `routing` | `int` | `0` | 0=serial, 1=parallel |
| `env_attack` | `float` | `0.0` | 0.0-1.0 |
| `env_decay` | `float` | `0.5` | 0.0-1.0 |
| `env_sustain` | `float` | `1.0` | 0.0-1.0 |
| `env_release` | `float` | `0.3` | 0.0-1.0 |
| `env_amount` | `float` | `0.0` | -1.0 to 1.0 |

**Properties:**
- `category -> SerumFilterCategory` -- Determined by `filter_type` range (0-19=NORMAL, 20-39=MULTI, 40-59=FLANGES, 60+=MISC)
- `cutoff_hz -> float` -- `20.0 * (20000.0/20.0)^cutoff`
- `needs_ir_fallback -> bool` -- True if category is FLANGES or MISC

### 1.6 ConversionResult (`src/serum/filter_map.py`)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `filter_config` | `FilterConfig` | (required) | Akai-compatible config |
| `needs_ir_fallback` | `bool` | `False` | IR baking required? |
| `ir_description` | `str` | `""` | Human-readable IR method |
| `drive_as_insert_gain` | `int` | `0` | 0-127 for MPC insert effect |
| `fat_as_output_boost` | `int` | `0` | 0-127 for MPC output level |
| `mix_blend` | `float` | `1.0` | dry/wet for parallel layer |

### 1.7 SerumV1Preset (`src/serum/parser_v1.py`)

Contains 15 fields: `preset_name` (str), `plugin_id` (int), `version` (int), `num_params` (int), `params` (list[float]), plus filter fields `filter_type_raw`, `filter_cutoff`, `filter_resonance`, `filter_drive`, `filter_fat`, `filter_mix`, `filter_pan`, `filter_routing`, `filter_env_attack`, `filter_env_decay`, `filter_env_sustain`, `filter_env_release`, `filter_env_amount` -- all float 0.0-1.0 (env_amount may be negative).

### 1.8 SerumV2Preset (`src/serum/parser_v2.py`)

Same filter fields as v1, plus: `metadata` (dict), `patch_data` (dict), `filter2_type_raw` (int), `filter2_cutoff` (float), `filter2_resonance` (float) for dual-filter mode.

### 1.9 ImpulseResponse (`src/impulse/ir_loader.py`)

| Field | Type | Description |
|-------|------|-------------|
| `data` | `np.ndarray` | Float64, shape (N,) mono or (N,2) stereo |
| `sample_rate` | `int` | Resampled to target_sr |
| `channels` | `int` | 1 or 2 |
| `duration_seconds` | `float` | `len(data) / sample_rate` |
| `source_path` | `str` | Original file path |

**Properties:**
- `is_stereo -> bool` -- `channels == 2`
- `num_samples -> int` -- `data.shape[0]`

### 1.10 SaturationParams (`src/impulse/saturation.py`)

| Field | Type | Default | Range |
|-------|------|---------|-------|
| `drive` | `float` | `0.5` | 0.0-1.0 (maps to 1x-10x gain) |
| `mix` | `float` | `1.0` | 0.0-1.0 dry/wet |
| `tone` | `float` | `0.5` | 0.0=dark, 1.0=bright |
| `output` | `float` | `0.8` | 0.0-1.0 makeup gain |

**Property:** `drive_linear -> float` = `1.0 + drive * 9.0`

### 1.11 SaturationStep (`src/impulse/flavor_pack.py`)

| Field | Type | Default |
|-------|------|---------|
| `mode` | `SaturationMode` | (required) |
| `params` | `SaturationParams` | `SaturationParams()` |

### 1.12 FlavorRecipe (`src/impulse/flavor_pack.py`)

| Field | Type | Default |
|-------|------|---------|
| `ir_path` | `str \| None` | `None` |
| `ir_mix` | `float` | `1.0` |
| `saturation_chain` | `list[SaturationStep]` | `[]` |
| `output_filter` | `FilterConfig` | `FilterConfig(filter_type=FilterType.OFF)` |

### 1.13 CCMapping (`src/kikgen/midimapper_config.py`)

| Field | Type | Default | Range |
|-------|------|---------|-------|
| `source_cc` | `int` | (required) | 0-127 |
| `target_cc` | `int` | (required) | 0-127 |
| `channel_in` | `int` | `0` | 0=all, 1-15 |
| `channel_out` | `int` | `0` | 0=same, 1-15 |
| `min_value` | `int` | `0` | 0-127 |
| `max_value` | `int` | `127` | 0-127 |
| `description` | `str` | `""` | -- |

### 1.14 MidiMapperConfig (`src/kikgen/midimapper_config.py`)

| Field | Type | Default |
|-------|------|---------|
| `device_name` | `str` | `"Custom Controller"` |
| `mappings` | `list[CCMapping]` | `[]` |
| `note_remaps` | `dict[int, int]` | `{}` |

---

## 2. Enumerations

### 2.1 FilterType (`src/xpm/filter_params.py`)

| Member | `.value` (XML) | Description |
|--------|---------------|-------------|
| `OFF` | `"Off"` | Filter disabled |
| `LP1` | `"LowPass1Pole"` | 6dB/oct low-pass |
| `LP2` | `"LowPass2Pole"` | 12dB/oct low-pass |
| `LP4` | `"LowPass4Pole"` | 24dB/oct low-pass |
| `LP6` | `"LowPass6Pole"` | 36dB/oct low-pass |
| `HP1` | `"HighPass1Pole"` | 6dB/oct high-pass |
| `HP2` | `"HighPass2Pole"` | 12dB/oct high-pass |
| `BP` | `"BandPass"` | Band-pass |
| `NOTCH` | `"BandReject"` | Band-reject (notch) |
| `LINK` | `"Link"` | Linked mode (series HP+LP) |

### 2.2 SaturationMode (`src/impulse/saturation.py`)

| Member | `.value` | Algorithm |
|--------|---------|-----------|
| `SOFT_CLIP` | `"soft_clip"` | `tanh(gain * x)` -- warm, gentle |
| `HARD_CLIP` | `"hard_clip"` | `clip(gain * x, -1, 1)` -- aggressive, digital |
| `TAPE` | `"tape"` | Asymmetric tanh + hysteresis -- analog tape |
| `TUBE` | `"tube"` | `x/(1+\|x\|)` + even harmonics -- vacuum tube |
| `TRANSFORMER` | `"transformer"` | Asymmetric clip + LF emphasis -- iron-core |
| `DIODE` | `"diode"` | `sign(x) * (1 - exp(-\|x\|))` -- germanium |
| `FOLDBACK` | `"foldback"` | Signal folding at +/-1 -- complex harmonics |
| `BITCRUSH` | `"bitcrush"` | Bit depth + SR reduction -- lo-fi |
| `VINYL` | `"vinyl"` | Soft clip + noise + wobble -- record player |
| `CONSOLE` | `"console"` | log compression + odd harmonics -- mixing desk |

### 2.3 SerumFilterSubtype (`src/serum/filter_map.py`)

**Normal Category (0-19):**

| Member | Value | Description |
|--------|-------|-------------|
| `LP_6` | 11 | Low-pass 6dB |
| `LP_12` | 0 | Low-pass 12dB |
| `LP_24` | 1 | Low-pass 24dB |
| `LP_48` | 2 | Low-pass 48dB (Serum 2) |
| `HP_6` | 12 | High-pass 6dB |
| `HP_12` | 3 | High-pass 12dB |
| `HP_24` | 4 | High-pass 24dB |
| `HP_48` | 5 | High-pass 48dB (Serum 2) |
| `BP_12` | 6 | Band-pass 12dB |
| `BP_24` | 7 | Band-pass 24dB |
| `NOTCH_12` | 8 | Notch 12dB |
| `NOTCH_24` | 9 | Notch 24dB |
| `PEAK` | 10 | Peak/bell filter |

**Multi Category (20-39):**

| Member | Value | Description |
|--------|-------|-------------|
| `MULTI_LP_HP` | 20 | Dual LP+HP |
| `MULTI_LP_BP` | 21 | Dual LP+BP |
| `MULTI_BP_HP` | 22 | Dual BP+HP |
| `MULTI_LP_LP` | 23 | Dual LP+LP |

**Flanges Category (40-59):**

| Member | Value | Description |
|--------|-------|-------------|
| `COMB_POS` | 40 | Positive comb filter |
| `COMB_NEG` | 41 | Negative comb filter |
| `PHASER_4` | 42 | 4-stage phaser |
| `PHASER_8` | 43 | 8-stage phaser |
| `FLANGER` | 44 | Flanger |

**Misc Category (60+):**

| Member | Value | Description |
|--------|-------|-------------|
| `REVERB` | 60 | Reverb filter |
| `COMB_LP` | 61 | Comb + LP |
| `COMB_HP` | 62 | Comb + HP |
| `FORMANT_VOWEL` | 63 | Formant vowel |
| `FORMANT_TALK` | 64 | Formant talk-box |
| `RING_MOD` | 65 | Ring modulator |
| `SAMPLE_HOLD` | 66 | Sample & hold |

### 2.4 SerumFilterCategory (`src/serum/filter_map.py`)

| Member | Value | Type Range |
|--------|-------|-----------|
| `NORMAL` | 0 | 0-19 |
| `MULTI` | 1 | 20-39 |
| `FLANGES` | 2 | 40-59 |
| `MISC` | 3 | 60+ |

### 2.5 ModSource (`src/xpm/mod_matrix.py`)

| Member | `.value` |
|--------|---------|
| `VELOCITY` | `"Velocity"` |
| `AFTERTOUCH` | `"Aftertouch"` |
| `MOD_WHEEL` | `"ModWheel"` |
| `KEY_TRACK` | `"KeyTrack"` |
| `LFO1` | `"LFO1"` |
| `LFO2` | `"LFO2"` |
| `FILTER_ENV` | `"FilterEnv"` |
| `AMP_ENV` | `"AmpEnv"` |
| `PITCH_BEND` | `"PitchBend"` |
| `EXPRESSION` | `"Expression"` |

### 2.6 ModDest (`src/xpm/mod_matrix.py`)

| Member | `.value` |
|--------|---------|
| `CUTOFF` | `"FilterCutoff"` |
| `RESONANCE` | `"FilterResonance"` |
| `VOLUME` | `"Volume"` |
| `PAN` | `"Pan"` |
| `PITCH` | `"Pitch"` |
| `LFO1_RATE` | `"LFO1Rate"` |
| `LFO1_DEPTH` | `"LFO1Depth"` |
| `LFO2_RATE` | `"LFO2Rate"` |
| `LFO2_DEPTH` | `"LFO2Depth"` |
| `SAMPLE_START` | `"SampleStart"` |

### 2.7 ModCurve (`src/xpm/mod_matrix.py`)

| Member | `.value` |
|--------|---------|
| `LINEAR` | `"Linear"` |
| `EXPONENTIAL` | `"Exponential"` |
| `LOGARITHMIC` | `"Logarithmic"` |
| `S_CURVE` | `"SCurve"` |

---

## 3. XPM File Format

XPM files are XML documents compatible with Akai MPC OS 3.7.1+.

### 3.1 Root Element

```xml
<?xml version="1.0" encoding="UTF-8"?>
<MPCVObject type="DrumProgram" version="3.7.1">
  <ProgramName>MyProgram</ProgramName>
  <ProgramType>Drum</ProgramType>
  ...
</MPCVObject>
```

`type` is either `"DrumProgram"` or `"KeygroupProgram"`.

### 3.2 Drum Program Structure

```xml
<Pads>
  <Pad id="0"><PadName>A01</PadName></Pad>
  <Pad id="1"><PadName>A02</PadName></Pad>
  <!-- up to 64 pads (banks A-D, pads 01-16) -->
</Pads>
<Instruments>
  <Instrument>
    <!-- see Instrument schema below -->
  </Instrument>
</Instruments>
```

### 3.3 Keygroup Program Structure

```xml
<Keygroups>
  <Keygroup id="0">
    <Instrument>
      <!-- see Instrument schema below -->
    </Instrument>
  </Keygroup>
</Keygroups>
```

### 3.4 Instrument Schema

```xml
<Instrument>
  <InstrumentName>A01</InstrumentName>
  <Volume>100</Volume>
  <Pan>64</Pan>
  <MuteGroup>0</MuteGroup>
  <Filter>
    <FilterType>LowPass4Pole</FilterType>
    <FilterCutoff>100</FilterCutoff>
    <FilterResonance>32</FilterResonance>
    <FilterEnvAmount>0</FilterEnvAmount>
    <FilterAttack>0</FilterAttack>
    <FilterDecay>64</FilterDecay>
    <FilterSustain>127</FilterSustain>
    <FilterRelease>40</FilterRelease>
  </Filter>
  <ModMatrix>
    <Route id="0">
      <Source>Velocity</Source>
      <Destination>FilterCutoff</Destination>
      <Depth>64</Depth>
      <Curve>Linear</Curve>
    </Route>
    <!-- up to 8 routes -->
  </ModMatrix>
  <Layers>
    <Layer>
      <SamplePath>Samples/kick.wav</SamplePath>
      <Volume>100</Volume>
      <Pan>64</Pan>
      <TuneCoarse>0</TuneCoarse>
      <TuneFine>0</TuneFine>
      <RootNote>60</RootNote>
      <KeyLow>0</KeyLow>
      <KeyHigh>127</KeyHigh>
      <VelocityLow>0</VelocityLow>
      <VelocityHigh>127</VelocityHigh>
    </Layer>
    <!-- up to 4 layers -->
  </Layers>
</Instrument>
```

### 3.5 Output Directory Structure

```
ProgramName/
+-- ProgramName.xpm
+-- Samples/
    +-- (referenced .wav files)
```

---

## 4. FXP File Format (Serum v1)

### 4.1 Header (60 bytes, big-endian)

| Offset | Size | Type | Description |
|--------|------|------|-------------|
| 0 | 4 | char[4] | Magic: `"CcnK"` |
| 4 | 4 | uint32 | Total chunk size |
| 8 | 4 | char[4] | fx_magic: `"FPCh"` (opaque) or `"FxCk"` (regular) |
| 12 | 4 | uint32 | Version |
| 16 | 4 | uint32 | Plugin ID (`0x5853524D` = "XSRM" for Serum) |
| 20 | 4 | uint32 | Plugin version |
| 24 | 4 | uint32 | Num programs/params |
| 28 | 4 | -- | Padding |
| 32 | 4 | uint32 | Chunk data size (FPCh only) |
| 36+ | -- | bytes | Chunk data |

### 4.2 FPCh Format (Opaque Chunk)

Data starting at offset 36 is zlib-compressed. Decompresses to a little-endian `float32` array.

### 4.3 FxCk Format (Regular Parameters)

Big-endian `float32` values starting at offset 28.

### 4.4 Filter Parameter Offsets

| Index | Parameter | Range |
|-------|----------|-------|
| 140 | `filter_type_raw` | 0.0-1.0 |
| 141 | `filter_cutoff` | 0.0-1.0 |
| 142 | `filter_resonance` | 0.0-1.0 |
| 143 | `filter_drive` | 0.0-1.0 |
| 144 | `filter_fat` | 0.0-1.0 |
| 145 | `filter_mix` | 0.0-1.0 |
| 146 | `filter_pan` | 0.0-1.0 |
| 147 | `filter_routing` | 0.0-1.0 |
| 148 | `filter_env_attack` | 0.0-1.0 |
| 149 | `filter_env_decay` | 0.0-1.0 |
| 150 | `filter_env_sustain` | 0.0-1.0 |
| 151 | `filter_env_release` | 0.0-1.0 |
| 152 | `filter_env_amount` | -1.0 to 1.0 |

### 4.5 Preset Name

Located at offset `0x4972`, 32 bytes, null-terminated ASCII. Fallback: bytes 36-68 of header.

---

## 5. SerumPreset Format (Serum v2)

### 5.1 Binary Layout

```
[9 bytes]     "XferJson\0" magic
[8 bytes LE]  JSON metadata length (uint64)
[N bytes]     JSON metadata (UTF-8)
[4 bytes LE]  CBOR payload length (uint32)
[4 bytes LE]  Format version (uint32, always 2)
[M bytes]     zstd-compressed CBOR data
```

### 5.2 JSON Metadata

Contains preset name as `"name"` or `"preset_name"` key.

### 5.3 CBOR Key Aliases

The parser searches the CBOR data recursively using multiple possible key names:

| Parameter | Key Aliases |
|----------|-------------|
| `filter_type_raw` | `filt_type`, `filter_type`, `FiltType`, `filt1_type` |
| `filter_cutoff` | `filt_cut`, `filter_cutoff`, `FiltCut`, `filt1_cut` |
| `filter_resonance` | `filt_res`, `filter_resonance`, `FiltRes`, `filt1_res` |
| `filter2_type_raw` | `filt2_type`, `filter2_type`, `Filt2Type` |

### 5.4 Dependencies

- **zstandard** >= 0.21 -- `ImportError` raised with installation hint if missing
- **cbor2** >= 5.5 -- `ImportError` raised with installation hint if missing

---

## 6. MIDI Mapper JSON

Generated by `generate_midimapper_config()`. Compatible with TheKikGen TKGL_MIDIMAPPER.

```json
{
  "device": "Custom Controller",
  "version": "1.0",
  "cc_mappings": [
    {
      "src_cc": 74,
      "dst_cc": 74,
      "ch_in": 0,
      "ch_out": 0,
      "min": 0,
      "max": 127,
      "description": "Filter Cutoff"
    }
  ],
  "note_remaps": {
    "36": 35
  }
}
```

### Standard CC Constants

| Constant | Value | Parameter |
|----------|-------|----------|
| `CC_CUTOFF` | 74 | Brightness / Filter Cutoff |
| `CC_RESONANCE` | 71 | Resonance / Timbre |
| `CC_ATTACK` | 73 | Attack Time |
| `CC_DECAY` | 75 | Decay Time |
| `CC_RELEASE` | 72 | Release Time |
| `CC_MOD_WHEEL` | 1 | Modulation Wheel |

---

## 7. MockbaMod Manifest JSON

Generated by `scaffold_addon()`.

```json
{
  "name": "addon_name",
  "description": "Addon description",
  "version": "1.0.0",
  "author": "Author Name",
  "type": "addon",
  "startup": "startup.sh",
  "compatible_firmware": ["4.0.0+"]
}
```

### MockbaMod Configuration (mockba.conf)

```ini
ssh_enabled=true
vnc_enabled=false
auto_load_addons=true
log_level=1
```

SD card must be ExFat formatted with volume label `"662522"`.

---

## 8. Filter Mapping Tables

### 8.1 Direct Map (_DIRECT_MAP) -- 13 entries

Exact Serum-to-Akai type equivalents. No IR fallback needed.

| Serum Subtype | Akai FilterType |
|---------------|----------------|
| `LP_6` (11) | `LP1` |
| `LP_12` (0) | `LP2` |
| `LP_24` (1) | `LP4` |
| `LP_48` (2) | `LP6` |
| `HP_6` (12) | `HP1` |
| `HP_12` (3) | `HP1` |
| `HP_24` (4) | `HP2` |
| `HP_48` (5) | `HP2` |
| `BP_12` (6) | `BP` |
| `BP_24` (7) | `BP` |
| `NOTCH_12` (8) | `NOTCH` |
| `NOTCH_24` (9) | `NOTCH` |
| `PEAK` (10) | `BP` |

### 8.2 Fallback Map (_FALLBACK_MAP) -- 16 entries

Closest Akai equivalent + IR fallback flag for exotic filter character.

| Serum Subtype | Akai FilterType | IR Description |
|---------------|----------------|----------------|
| `MULTI_LP_HP` (20) | `LP4` | Multi-mode filter |
| `MULTI_LP_BP` (21) | `LP4` | Multi-mode filter |
| `MULTI_BP_HP` (22) | `BP` | Multi-mode filter |
| `MULTI_LP_LP` (23) | `LP6` | Multi-mode filter |
| `COMB_POS` (40) | `LP2` | Positive comb: render IR at multiple cutoff positions |
| `COMB_NEG` (41) | `LP2` | Negative comb: render IR with inverted feedback |
| `PHASER_4` (42) | `LP2` | 4-stage phaser: render swept IR |
| `PHASER_8` (43) | `LP2` | 8-stage phaser: render swept IR |
| `FLANGER` (44) | `LP2` | Flanger: render short-delay IR with feedback |
| `REVERB` (60) | `LP4` | Reverb: convolve source with reverb IR |
| `COMB_LP` (61) | `LP2` | Comb + LP: render combined IR response |
| `COMB_HP` (62) | `HP2` | Comb + HP: render combined IR response |
| `FORMANT_VOWEL` (63) | `BP` | Formant: render formant shapes as processed samples |
| `FORMANT_TALK` (64) | `BP` | Formant: render talk-box shapes |
| `RING_MOD` (65) | `LP2` | Ring modulator: render AM-modulated source |
| `SAMPLE_HOLD` (66) | `LP2` | Sample & hold: render stepped random sweeps |

### 8.3 Unknown Types

Any `filter_type` not in either map defaults to `LP4` with `needs_ir_fallback=True`.

---

## 9. Audio Conventions

| Convention | Value |
|-----------|-------|
| Array type | `numpy.float64` (`np.ndarray`) |
| Sample range | -1.0 to 1.0 |
| Default sample rate | 44100 Hz |
| Mono shape | `(N,)` -- 1D array |
| Stereo shape | `(N, 2)` -- 2D array, samples x channels |
| Normalization | Peak-normalized to 1.0 (IR) or 0.95 (flavor pack output) |
| Convolution | FFT-based via `scipy.signal.fftconvolve` |
| Resampling | `scipy.signal.resample` (when source SR != target SR) |
| Final clipping | `np.clip(audio, -1.0, 1.0)` in `apply_saturation()` |
