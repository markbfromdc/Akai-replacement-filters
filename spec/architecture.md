# System Architecture

| Field | Value |
|-------|-------|
| Version | 0.1.0 |
| Date | 2026-03-31 |
| Status | Active |
| Traceability | [API](api.md) &#124; [Data Models](data-models.md) &#124; [Deployment](deployment.md) |

---

## Table of Contents

1. [Technology Stack](#1-technology-stack)
2. [Component Diagram](#2-component-diagram)
3. [Package Dependency Map](#3-package-dependency-map)
4. [Data Flow — Serum to XPM Pipeline](#4-data-flow--serum-to-xpm-pipeline)
5. [Data Flow — Flavor Pack Pipeline](#5-data-flow--flavor-pack-pipeline)
6. [Data Flow — Device Deployment](#6-data-flow--device-deployment)
7. [Design Decisions](#7-design-decisions)

---

## 1. Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Language | Python 3.10+ | Type hints, `X \| Y` union syntax |
| XML Generation | BeautifulSoup 4.12+ / lxml 5.0+ | .xpm program XML DOM manipulation |
| DSP | NumPy 1.24+ | Float64 audio arrays, signal math |
| Signal Processing | SciPy 1.11+ | FFT convolution, resampling, Butterworth filters |
| Audio I/O | soundfile 0.12+ | WAV read/write, format auto-detection |
| Serum v2 Decompression | zstandard 0.21+ | Zstd-compressed CBOR payloads |
| Serum v2 Serialization | cbor2 5.5+ | CBOR binary object representation |
| Cross-compilation | arm-linux-gnueabihf-gcc | ARM shared libraries for MPC/Force |
| Testing | pytest 7.4+ / pytest-cov 4.1+ | Unit/integration tests, coverage |
| CI/CD | GitHub Actions | Python 3.10/3.11/3.12 matrix |

---

## 2. Component Diagram

```
+---------------------------------------------------------------------+
|                        akai-replacement-filters                      |
+---------------------------------------------------------------------+
|                                                                      |
|  +--------------+     +--------------+     +------------------+     |
|  |  src/serum   |     |  src/xpm     |     |  src/impulse     |     |
|  |              |     |              |     |                  |     |
|  |  parser_v1   |     |  builder     |     |  ir_loader       |     |
|  |  parser_v2   |---->|  filter_params|<----|  saturation      |     |
|  |  filter_map  |     |  mod_matrix  |     |  flavor_pack     |     |
|  +--------------+     |  templates/  |     +------------------+     |
|         |             +--------------+              |               |
|         |                    ^                      |               |
|         |                    |                      |               |
|         +--------------------+----------------------+               |
|                              |                                      |
|  +--------------+     +------+-------+                             |
|  |  src/kikgen  |     |  src/cli     |                             |
|  |              |     |              |                             |
|  |  preload_gen |     |  info cmd    |                             |
|  |  midimapper  |     |  convert cmd |                             |
|  |  filter_inject|    +--------------+                             |
|  +--------------+                                                   |
|                                                                      |
|  +--------------+                                                   |
|  |  src/mockba  |                                                   |
|  |              |                                                   |
|  | addon_scaffold|                                                  |
|  |  sd_card     |                                                   |
|  |  preload_hack|                                                   |
|  +--------------+                                                   |
+---------------------------------------------------------------------+
```

### Dependency Arrows

| From | To | Relationship |
|------|----|-------------|
| `serum.filter_map` | `xpm.filter_params` | Imports `FilterConfig`, `FilterType`, `hz_to_mpc`, `float_to_mpc` |
| `impulse.flavor_pack` | `xpm.builder` | Imports `DrumProgram`, `KeygroupProgram`, `Instrument`, `PadLayer` |
| `impulse.flavor_pack` | `xpm.filter_params` | Imports `FilterConfig`, `FilterType` |
| `impulse.flavor_pack` | `impulse.ir_loader` | Imports `load_ir`, `convolve_with_ir` |
| `impulse.flavor_pack` | `impulse.saturation` | Imports `apply_saturation`, `SaturationMode`, `SaturationParams` |
| `cli` | `serum` | Imports parsers and conversion engine |
| `cli` | `xpm` | Imports program builders |

### Standalone Packages

- **`src/kikgen`** -- No internal dependencies; generates shell scripts, JSON configs, and C source code
- **`src/mockba`** -- No internal dependencies; generates directory structures and templates

---

## 3. Package Dependency Map

```
src/xpm (standalone -- no internal deps)
  +-- filter_params.py  <- Foundation: FilterConfig, FilterType, hz_to_mpc
  +-- mod_matrix.py     <- Foundation: ModMatrix, ModRoute, enums
  +-- builder.py        <- Uses filter_params, mod_matrix
  +-- templates/        <- XML templates for DrumProgram, KeygroupProgram

src/serum (depends on xpm)
  +-- parser_v1.py      <- Standalone FXP binary parser
  +-- parser_v2.py      <- Standalone SerumPreset parser (zstd + CBOR)
  +-- filter_map.py     <- Imports from xpm.filter_params

src/impulse (depends on xpm)
  +-- ir_loader.py      <- Standalone IR loader + convolver
  +-- saturation.py     <- Standalone 10-mode saturation engine
  +-- flavor_pack.py    <- Imports from xpm.builder, xpm.filter_params,
                           ir_loader, saturation

src/kikgen (standalone -- generates text/code files)
  +-- preload_gen.py
  +-- midimapper_config.py
  +-- filter_inject.py

src/mockba (standalone -- generates directory structures)
  +-- addon_scaffold.py
  +-- sd_card.py
  +-- preload_hack.py

src/cli.py (depends on serum, xpm)
```

---

## 4. Data Flow -- Serum to XPM Pipeline

This is the primary conversion pipeline, mapping Serum filter presets to Akai MPC programs.

```
 +-------------------+
 |  .fxp file        |  Serum v1 (VST2 binary)
 |  .SerumPreset     |  Serum v2 (XferJson + zstd/CBOR)
 +--------+----------+
          |
          v
 +-------------------+  Auto-detect by file extension:
 |  Parser           |  .fxp -> parse_fxp() -> SerumV1Preset
 |  (v1 or v2)      |  .serumpreset -> parse_serum_preset() -> SerumV2Preset
 +--------+----------+
          |  Extracts: filter_type_raw, cutoff (0-1), resonance (0-1),
          |  drive, fat, mix, pan, ADSR envelope
          v
 +-------------------+
 | SerumFilterConfig  |  Intermediate representation
 +--------+----------+
          |
          v
 +-------------------+  Two-tier mapping:
 |  serum_to_akai()  |  1. _DIRECT_MAP: 13 types -> exact Akai equivalent
 |                   |  2. _FALLBACK_MAP: 16 types -> closest + IR flag
 |                   |  3. Unknown -> LP4 + IR fallback
 +--------+----------+
          |  Returns ConversionResult:
          |  - FilterConfig (type, cutoff 0-127, resonance 0-127, ADSR)
          |  - needs_ir_fallback (bool)
          |  - ir_description (str)
          |  - drive_as_insert_gain, fat_as_output_boost (0-127)
          v
 +-------------------+
 |  FilterConfig     |  Akai-native parameters, all 0-127
 +--------+----------+
          |
          v
 +-------------------+
 |  Instrument       |  Wraps FilterConfig + ModMatrix + up to 4 PadLayers
 +--------+----------+
          |
     +----+-----+
     v          v
 DrumProgram  KeygroupProgram
     |          |
     v          v
 +-------------------+
 |  .xpm XML file    |  + Samples/ directory
 +-------------------+
```

### Parameter Conversion Details

| Serum Parameter | Transformation | Akai Parameter |
|----------------|---------------|----------------|
| cutoff (0.0-1.0) | `20 * (20000/20)^cutoff` then `hz_to_mpc()` | cutoff (0-127) |
| resonance (0.0-1.0) | `float_to_mpc()` | resonance (0-127) |
| env_attack (0.0-1.0) | `float_to_mpc()` | attack (0-127) |
| env_decay (0.0-1.0) | `float_to_mpc()` | decay (0-127) |
| env_sustain (0.0-1.0) | `float_to_mpc()` | sustain (0-127) |
| env_release (0.0-1.0) | `float_to_mpc()` | release (0-127) |
| env_amount (-1.0-1.0) | `float_to_mpc(abs(val))` | env_amount (0-127) |
| drive (0.0-1.0) | `float_to_mpc()` | drive_as_insert_gain (0-127) |
| fat (0.0-1.0) | `float_to_mpc()` | fat_as_output_boost (0-127) |

---

## 5. Data Flow -- Flavor Pack Pipeline

Processes source audio through IR convolution and saturation chains, then exports as Akai programs.

```
 +-----------------+   +-----------------+
 |  source.wav     |   |  FlavorRecipe   |
 |  (kick, snare,  |   |  - ir_path      |
 |   piano, etc.)  |   |  - ir_mix       |
 +--------+--------+   |  - saturation[] |
          |             |  - output_filter|
          |             +--------+--------+
          |                      |
          v                      v
 +------------------------------------------+
 |  FlavorPack._process_single()            |
 |                                          |
 |  1. sf.read(source) -> float64           |
 |  2. Resample to target SR               |
 |  3. convolve_with_ir() if IR set        |
 |  4. For each SaturationStep:            |
 |     apply_saturation(audio,             |
 |       step.mode, step.params)           |
 |  5. Normalize (peak -> 0.95)            |
 +-------------------+--------------------+
                     |
                     v
 +-------------------+
 | {name}_flavored   |  Processed .wav in Samples/ dir
 | .wav              |
 +--------+----------+
          |
          v
 +-------------------+
 |  Instrument       |  PadLayer -> sample_path = "Samples/{name}_flavored.wav"
 |  + output_filter  |  FilterConfig from recipe
 +--------+----------+
          |
          v
 +-------------------+
 |  DrumProgram /    |  Bank A-D, Pads 1-16 (drum)
 |  KeygroupProgram  |  or Keygroups with key ranges
 +--------+----------+
          |
          v
 +-------------------+
 |  output_dir/      |
 |  FlavorPackName/  |
 |  +-- *.xpm       |
 |  +-- Samples/    |
 |      +-- *.wav   |
 +-------------------+
```

### Saturation Chain Processing

Each `SaturationStep` in the chain is applied sequentially. The output of one step feeds the next:

```
source -> [TAPE drive=0.6] -> [TUBE drive=0.3] -> [VINYL drive=0.2] -> processed
```

All intermediate audio remains float64 in [-1.0, 1.0] range. Final `apply_saturation()` clips to [-1.0, 1.0].

---

## 6. Data Flow -- Device Deployment

Two deployment paths exist for injecting custom filter logic onto Akai hardware.

### 6.1 MPC Devices (via KikGen LD_PRELOAD)

```
 +----------------------------+
 |  generate_filter_inject    |  -> filter_inject.c
 |  _source()                 |
 +-------------+--------------+
               |
               v
 +----------------------------+
 |  generate_makefile()       |  -> Makefile
 +-------------+--------------+
               |
               v
 +----------------------------+
 |  arm-linux-gnueabihf-gcc  |  Cross-compile to ARM .so
 |  -shared -fPIC -Wall -O2  |
 |  -ldl -lasound            |
 +-------------+--------------+
               |
               v
 +----------------------------+
 | generate_preload_script()  |  -> launch.sh
 +-------------+--------------+
               |
               v
 +----------------------------+
 |  Deploy to MPC via SSH:    |
 |  - filter_inject.so        |
 |  - launch.sh               |
 |                            |
 |  Run: ./launch.sh          |
 |  LD_PRELOAD=...so          |
 |  /usr/bin/MPC              |
 +----------------------------+
```

Target devices: `mpc_live`, `mpc_x`, `mpc_one`, `force`

### 6.2 Akai Force (via MockbaMod)

```
 +----------------------------+
 |  scaffold_addon()          |  -> addon_name/
 |                            |     +-- manifest.json
 |                            |     +-- startup.sh
 |                            |     +-- startup.lua
 |                            |     +-- README.md
 +-------------+--------------+
               |
               v
 +----------------------------+
 | generate_preload_library   |  -> {name}.c + Makefile
 | _template()                |
 +-------------+--------------+
               |  Cross-compile with ARM toolchain
               v
 +----------------------------+
 |  generate_sd_layout()      |  -> MockbaMod_SD/
 |                            |     +-- AddOns/{addon}/
 |                            |     +-- Scripts/bootstrap.sh
 |                            |     +-- Logs/
 |                            |     +-- Config/mockba.conf
 +-------------+--------------+
               |
               v
 +----------------------------+
 |  Copy MockbaMod_SD/ to     |
 |  ExFat SD card             |
 |  (label: "662522")         |
 |                            |
 |  Insert SD -> reboot Force |
 |  bootstrap.sh runs auto    |
 +----------------------------+
```

---

## 7. Design Decisions

### 7.1 Two-Tier Filter Mapping Strategy

**Decision:** Use direct type mapping for standard filters, IR fallback for exotic types.

**Rationale:** Akai MPC has 9 filter modes (LP1-LP6, HP1-HP2, BP, NOTCH, LINK). Serum has 27+ filter subtypes across 4 categories. Standard LP/HP/BP/Notch filters map directly. Exotic types (comb, phaser, flanger, formant, ring mod) have no Akai equivalent -- the closest approximation is to render the filter's character as an impulse response baked into the sample.

**Trade-off:** IR-baked samples are static (no real-time cutoff modulation), but accurately preserve the filter's tonal character.

### 7.2 Universal 0-127 Parameter Convention

**Decision:** All MPC parameters use integer 0-127 range with automatic clamping in `__post_init__()`.

**Rationale:** Matches Akai's native MIDI-derived parameter scheme. Simplifies validation -- every numeric parameter has the same range and clamping behavior. Eliminates entire classes of out-of-range bugs.

### 7.3 Offline DSP Processing (Baked into Samples)

**Decision:** Apply saturation and IR convolution offline, writing processed `.wav` files rather than real-time processing.

**Rationale:** MPC standalone devices have limited CPU for real-time effects. Baking effects into samples guarantees consistent playback on all MPC/Force hardware regardless of CPU load. Programs are fully self-contained.

### 7.4 XML Templates for XPM Generation

**Decision:** Use BeautifulSoup with XML templates (`drum_program.xml`, `keygroup_program.xml`) rather than string formatting.

**Rationale:** Templates ensure structural validity of the .xpm format. BeautifulSoup handles escaping, encoding, and pretty-printing. Templates can be validated against the actual MPC firmware parser.

### 7.5 Standalone Generator Packages (kikgen, mockba)

**Decision:** `kikgen` and `mockba` have no internal package dependencies.

**Rationale:** These packages generate platform-specific artifacts (shell scripts, C source, directory layouts) that are independent of the audio processing pipeline. Users can use them standalone without importing the DSP stack.

### 7.6 Lazy Imports for Optional Dependencies

**Decision:** `zstandard` and `cbor2` are imported at call time in `parser_v2.py`, raising `ImportError` with installation hints if missing.

**Rationale:** Serum v2 parsing is optional functionality. Users who only work with v1 presets or only build XPM programs should not need these dependencies installed.

### 7.7 Float64 Audio Convention

**Decision:** All internal audio processing uses `numpy.float64` arrays in [-1.0, 1.0] range at 44100 Hz default sample rate.

**Rationale:** Float64 provides sufficient headroom for multi-stage saturation chains without accumulating quantization artifacts. 44100 Hz is the standard MPC sample rate. Resampling is handled transparently by `ir_loader` and `flavor_pack`.
