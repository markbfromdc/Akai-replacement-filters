# User Story Specifications

| Field | Value |
|-------|-------|
| Version | 0.1.0 |
| Date | 2026-03-31 |
| Status | Active |
| Traceability | [API](api.md) &#124; [Data Models](data-models.md) &#124; [Testing](testing.md) |

---

## Table of Contents

1. [Personas](#1-personas)
2. [Serum to Akai Conversion](#2-serum-to-akai-conversion)
3. [XPM Program Creation](#3-xpm-program-creation)
4. [Impulse Response & Saturation](#4-impulse-response--saturation)
5. [KikGen LD_PRELOAD Optimization](#5-kikgen-ld_preload-optimization)
6. [MockbaMod Addon Scaffolding](#6-mockbamod-addon-scaffolding)
7. [CLI Operations](#7-cli-operations)
8. [Traceability Matrix](#8-traceability-matrix)

---

## 1. Personas

| ID | Persona | Description |
|----|---------|-------------|
| P1 | Music Producer | Electronic music producer using MPC Live/X/One/Force for live performance and production |
| P2 | Sound Designer | Creates sample-based instruments with custom filter and saturation processing |
| P3 | Firmware Hacker | Deploys custom mods to MPC/Force hardware via LD_PRELOAD or MockbaMod |
| P4 | Developer | Integrates the library into a larger audio processing pipeline |

---

## 2. Serum to Akai Conversion

*Derived from skill: `serum-to-akai.md`*

### US-2.1: Parse Serum v1 Preset

**As** P1, **I want to** parse a `.fxp` file **so that** I can inspect its filter parameters before conversion.

**Acceptance Criteria:**
- `parse_fxp(path)` returns `SerumV1Preset` with all 13 filter fields populated
- Preset name extracted from FXP binary (offset 0x4972)
- Raises `ValueError("Invalid FXP magic")` for non-FXP files
- Raises `ValueError("File too small for FXP header")` for files < 60 bytes

**Edge Cases:**
- File with fewer than 140 parameters: filter fields default to 0.0
- Corrupted zlib data in FPCh format: falls back to raw float interpretation

### US-2.2: Parse Serum v2 Preset

**As** P1, **I want to** parse a `.SerumPreset` file **so that** I can access Serum 2 filter configurations.

**Acceptance Criteria:**
- `parse_serum_preset(path)` returns `SerumV2Preset` with filter fields + dual-filter fields
- Raises `ImportError` with installation hint if `zstandard` or `cbor2` not installed
- Raises `ValueError("Not a Serum 2 preset: missing XferJson magic")` for invalid files
- Deep-searches CBOR data using multiple key aliases (e.g., `filt_type`, `filter_type`, `FiltType`)

**Edge Cases:**
- Missing CBOR keys: filter values default to 0.0 (cutoff defaults to 0.5, mix to 1.0)
- Dual-filter mode: `filter2_type_raw`, `filter2_cutoff`, `filter2_resonance` populated

### US-2.3: Convert Serum Filter to Akai Equivalent

**As** P1, **I want to** convert a Serum filter configuration to Akai MPC filter settings **so that** I can recreate the sound on my MPC.

**Acceptance Criteria:**
- Direct mapping for standard LP/HP/BP/Notch types (13 entries in `_DIRECT_MAP`)
- Cutoff converted logarithmically: Serum 0.0 -> MPC 0, Serum 1.0 -> MPC 127
- Resonance, ADSR, drive, fat all converted via `float_to_mpc()` to 0-127
- Exotic types (comb, phaser, formant, etc.) flagged with `needs_ir_fallback=True`
- Human-readable `ir_description` provided for all 12 IR-requiring types

**Edge Cases:**
- Unknown filter type (not in either map): defaults to `LP4` + IR fallback
- `env_amount` negative: absolute value taken for MPC mapping

### US-2.4: Batch Convert Multiple Presets

**As** P4, **I want to** convert multiple Serum configs at once **so that** I can process preset banks efficiently.

**Acceptance Criteria:**
- `batch_convert(list)` returns `list[ConversionResult]` in same order
- Empty list input returns empty list

---

## 3. XPM Program Creation

*Derived from skill: `xpm-creator.md`*

### US-3.1: Build Drum Program

**As** P2, **I want to** create an MPC drum program with custom filter settings per pad **so that** I can build sample-based drum kits.

**Acceptance Criteria:**
- `DrumProgram` generates valid `.xpm` XML with `<Pads>` and `<Instruments>` sections
- Pads assigned to banks A-D, pads 1-16 (up to 64 total)
- Auto-assigns pad name (e.g., "A01") if instrument has no name
- Raises `ValueError` for invalid bank letter or pad number

**Edge Cases:**
- Bank letter must be in "ABCD" (case-insensitive)
- Pad number must be 1-16

### US-3.2: Build Keygroup Program

**As** P2, **I want to** create an MPC keygroup program with keyboard-mapped samples **so that** I can build pitched instruments.

**Acceptance Criteria:**
- `KeygroupProgram` generates valid `.xpm` XML with `<Keygroups>` section
- Each keygroup wraps an instrument with key range configured via `PadLayer` fields

### US-3.3: Configure Filter Per Instrument

**As** P2, **I want to** set filter type, cutoff, and resonance per instrument **so that** each sound has its own tonal character.

**Acceptance Criteria:**
- All 10 `FilterType` values serialize to correct XML strings
- All integer parameters clamped to 0-127 automatically
- `to_xml_dict()` produces correct XML tag names

### US-3.4: Configure Modulation Matrix

**As** P2, **I want to** route modulation sources to destinations **so that** my programs respond expressively to velocity, aftertouch, and LFOs.

**Acceptance Criteria:**
- Up to 8 routes per instrument (raises `ValueError` on 9th)
- Depth clamped to [-127, +127]
- 10 sources x 10 destinations x 4 curves available
- `get_routes_for_dest()` and `get_routes_for_source()` filter correctly

### US-3.5: Multi-Layer Instruments

**As** P2, **I want to** add up to 4 velocity or key-split layers per instrument **so that** I can create realistic instruments.

**Acceptance Criteria:**
- Max 4 layers per instrument (raises `ValueError` on 5th)
- Each layer has independent sample path, volume, pan, tuning, key/velocity ranges

### US-3.6: Save Program to Disk

**As** P2, **I want to** save the program as a `.xpm` file with a `Samples/` folder **so that** I can copy it to my MPC.

**Acceptance Criteria:**
- `save(output_dir)` creates `ProgramName/ProgramName.xpm` + `ProgramName/Samples/`
- Returns `Path` to the `.xpm` file
- Directories created with `parents=True, exist_ok=True`

---

## 4. Impulse Response & Saturation

*Derived from skill: `impulse-saturation.md`*

### US-4.1: Load Impulse Response

**As** P2, **I want to** load an IR `.wav` file **so that** I can convolve it with my samples.

**Acceptance Criteria:**
- `load_ir(path, target_sr)` returns `ImpulseResponse` with correct fields
- Resamples to `target_sr` if source sample rate differs
- Normalizes peak to 1.0
- Raises `FileNotFoundError` for missing files

**Edge Cases:**
- Stereo IR: `channels=2`, `is_stereo=True`
- 48kHz IR with `target_sr=44100`: resampled automatically

### US-4.2: Convolve Source with IR

**As** P2, **I want to** apply an impulse response to my source audio **so that** I can bake reverb/cabinet character into samples.

**Acceptance Criteria:**
- Handles all 4 channel combinations: mono+mono, mono+stereo, stereo+mono, stereo+stereo
- Output trimmed to source length
- `mix` parameter: 0.0=fully dry, 1.0=fully wet
- Wet signal peak-normalized to 1.0 before mixing

### US-4.3: Apply Saturation

**As** P2, **I want to** apply saturation effects to my audio **so that** I can add harmonic warmth or distortion.

**Acceptance Criteria:**
- All 10 modes produce finite output in [-1.0, 1.0] range
- `drive` 0.0 -> 1x gain, `drive` 1.0 -> 10x gain
- `mix` 0.0 -> fully dry, `mix` 1.0 -> fully wet
- `tone` < 0.5 -> darker, `tone` > 0.5 -> brighter
- Stereo signals processed per-channel independently
- Final output clipped to [-1.0, 1.0]

**Edge Cases:**
- Silence input: output remains silence (no DC offset)
- Extreme drive (1.0) with hard_clip: fully clipped square wave

### US-4.4: Build Flavor Pack

**As** P2, **I want to** process multiple sources through IR + saturation chains and build an MPC program **so that** I can create "flavored" sample kits.

**Acceptance Criteria:**
- `FlavorPack` processes N sources through their recipes
- Output `.wav` files normalized to 0.95 peak (0.5dB headroom)
- Builds `DrumProgram` (bank A-D assignment) or `KeygroupProgram`
- Output directory: `FlavorPackName/FlavorPackName.xpm` + `Samples/`

**Edge Cases:**
- Recipe with no IR and no saturation: source passes through with normalization only
- Multiple sources with same stem name: `{stem}_flavored.wav` naming

---

## 5. KikGen LD_PRELOAD Optimization

*Derived from skill: `kikgen-optimize.md`*

### US-5.1: Generate Preload Launch Script

**As** P3, **I want to** generate a launch script for LD_PRELOAD injection **so that** I can run custom .so libraries on my MPC.

**Acceptance Criteria:**
- Script includes `#!/bin/bash`, `set -euo pipefail`
- Library existence verification loop
- Stops existing MPC process (`killall MPC`)
- Sets `LD_PRELOAD` and executes binary
- Supports 4 device types: `mpc_live`, `mpc_x`, `mpc_one`, `force`
- Optional `extra_env` variables exported
- Output file gets `chmod 0o755`

**Edge Cases:**
- Unknown device type: defaults to `mpc_live` config

### US-5.2: Generate MIDI Mapper Config

**As** P3, **I want to** generate a TKGL_MIDIMAPPER JSON config **so that** I can remap CC messages from my controller.

**Acceptance Criteria:**
- Valid JSON with `device`, `version`, `cc_mappings` fields
- Default filter controls: CC 74 (cutoff), 71 (resonance), 73 (attack), 72 (release)
- Custom mappings appended after defaults
- `note_remaps` included when provided

**Edge Cases:**
- `include_filter_defaults=False`: no default CCs added
- Empty mappings list: valid JSON with empty `cc_mappings` array

### US-5.3: Generate Filter Injection C Source

**As** P3, **I want to** generate a C source file for filter injection **so that** I can compile custom MIDI interception logic.

**Acceptance Criteria:**
- Valid C source with `#define _GNU_SOURCE`, ALSA includes
- Intercepts `snd_rawmidi_write()` via `dlsym(RTLD_NEXT, ...)`
- Configurable CC numbers for cutoff and resonance
- Constructor logs initialization with `__attribute__((constructor))`
- Compile command: `arm-linux-gnueabihf-gcc -shared -fPIC -o filter_inject.so filter_inject.c -ldl -lasound`

### US-5.4: Generate Makefile

**As** P3, **I want to** generate a Makefile for cross-compiling **so that** I can build ARM .so libraries.

**Acceptance Criteria:**
- `CC = arm-linux-gnueabihf-gcc`
- `CFLAGS = -shared -fPIC -Wall -O2`
- `LDFLAGS = -ldl -lasound`
- `all` and `clean` targets

---

## 6. MockbaMod Addon Scaffolding

*Derived from skill: `mockba-mod.md`*

### US-6.1: Scaffold MockbaMod Addon

**As** P3, **I want to** generate a MockbaMod addon folder structure **so that** I can deploy custom logic to my Akai Force.

**Acceptance Criteria:**
- Creates `addon_name/` with `manifest.json`, `startup.sh`, `startup.lua`, `README.md`
- `startup.sh` has executable permission (0o755)
- `manifest.json` has correct schema with `compatible_firmware: ["4.0.0+"]`
- Optional Node.js server: `server/package.json` + `server/index.js`

**Edge Cases:**
- Empty description: defaults to `"{addon_name} MockbaMod addon"`
- `include_server=False`: no `server/` directory created

### US-6.2: Generate SD Card Layout

**As** P3, **I want to** generate the MockbaMod SD card directory structure **so that** I can prepare a bootable SD card for my Force.

**Acceptance Criteria:**
- Creates `MockbaMod_SD/` with `AddOns/`, `Scripts/`, `Logs/`, `Config/`
- `bootstrap.sh` executable, runs fsck and loads addon startup scripts
- `mockba.conf` with default settings (ssh_enabled=true, log_level=1)
- Addon placeholder directories created when `addons` list provided

**Edge Cases:**
- `include_bootstrap=False`: no `bootstrap.sh` created
- Empty addons list: `AddOns/` directory exists but empty

### US-6.3: Generate Force Preload Library Template

**As** P3, **I want to** generate C source templates for Force-specific LD_PRELOAD libraries **so that** I can intercept system calls.

**Acceptance Criteria:**
- Returns `dict[str, str]` with `{library_name}.c` and `Makefile`
- Default hooks: `snd_rawmidi_write`, `snd_pcm_writei`, `snd_seq_event_output`
- Constructor and destructor with `__attribute__` annotations
- Force-specific paths: `/usr/bin/MPC`, `/dev/snd/midiC0D0`
- Makefile includes `deploy` target copying to `/media/662522/AddOns/`

---

## 7. CLI Operations

*Derived from `src/cli.py`*

### US-7.1: Inspect Preset Filter Parameters

**As** P1, **I want to** run `akai-convert info preset.fxp` **so that** I can see the filter settings before converting.

**Acceptance Criteria:**
- Auto-detects format by extension: `.fxp` -> v1, `.serumpreset` -> v2
- Prints: preset name, format, filter type, cutoff, resonance, drive, fat, mix, pan, ADSR
- All float values printed to 3 decimal places

**Edge Cases:**
- Unknown extension: raises `ValueError` with supported formats listed

### US-7.2: Convert Preset to Akai Program

**As** P1, **I want to** run `akai-convert convert preset.fxp -o output/` **so that** I can generate an MPC program file.

**Acceptance Criteria:**
- Prints Akai filter type, all parameter values as `N/127`, IR fallback status
- With `--output-dir`: creates drum program with converted filter settings, saves `.xpm`
- Without `--output-dir`: prints conversion results only (no file output)

---

## 8. Traceability Matrix

| Story | API Functions | Test Files | Data Models |
|-------|-------------|-----------|-------------|
| US-2.1 | `parse_fxp()` | `test_serum_parser.py`, `test_parser_v1_extended.py` | `SerumV1Preset` |
| US-2.2 | `parse_serum_preset()` | `test_serum_parser_v2.py` | `SerumV2Preset` |
| US-2.3 | `serum_to_akai()` | `test_filter_map.py` | `SerumFilterConfig`, `ConversionResult`, `FilterConfig` |
| US-2.4 | `batch_convert()` | `test_filter_map.py` | `SerumFilterConfig`, `ConversionResult` |
| US-3.1 | `DrumProgram`, `add_pad()` | `test_xpm_builder.py` | `Instrument`, `PadLayer` |
| US-3.2 | `KeygroupProgram`, `add_keygroup()` | `test_xpm_builder.py` | `Instrument`, `PadLayer` |
| US-3.3 | `FilterConfig`, `FilterType` | `test_filter_params.py` | `FilterConfig` |
| US-3.4 | `ModMatrix`, `ModRoute` | `test_mod_matrix.py` | `ModRoute`, `ModSource`, `ModDest` |
| US-3.5 | `Instrument.add_layer()` | `test_xpm_builder.py` | `PadLayer` |
| US-3.6 | `save()` | `test_xpm_builder.py` | -- |
| US-4.1 | `load_ir()` | `test_ir_loader.py` | `ImpulseResponse` |
| US-4.2 | `convolve_with_ir()` | `test_ir_loader.py` | `ImpulseResponse` |
| US-4.3 | `apply_saturation()` | `test_impulse.py` | `SaturationMode`, `SaturationParams` |
| US-4.4 | `FlavorPack.build()` | `test_flavor_pack.py` | `FlavorRecipe`, `SaturationStep` |
| US-5.1 | `generate_preload_script()` | `test_kikgen.py` | -- |
| US-5.2 | `generate_midimapper_config()` | `test_kikgen.py` | `CCMapping`, `MidiMapperConfig` |
| US-5.3 | `generate_filter_inject_source()` | `test_kikgen.py` | -- |
| US-5.4 | `generate_makefile()` | `test_kikgen.py` | -- |
| US-6.1 | `scaffold_addon()` | `test_mockba.py` | -- |
| US-6.2 | `generate_sd_layout()` | `test_mockba.py` | -- |
| US-6.3 | `generate_preload_library_template()` | `test_mockba.py` | -- |
| US-7.1 | `cmd_info()` | `test_integration.py` | `SerumV1Preset`, `SerumV2Preset` |
| US-7.2 | `cmd_convert()` | `test_integration.py` | `ConversionResult` |
