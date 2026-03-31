# Python Public API Specification

| Field | Value |
|-------|-------|
| Version | 0.1.0 |
| Date | 2026-03-31 |
| Status | Active |
| Traceability | [Architecture](architecture.md) &#124; [Data Models](data-models.md) &#124; [Testing](testing.md) |

---

## Table of Contents

1. [CLI Interface](#1-cli-interface)
2. [src.xpm — XPM Program Builder](#2-srcxpm--xpm-program-builder)
3. [src.serum — Serum Preset Parsing & Conversion](#3-srcserum--serum-preset-parsing--conversion)
4. [src.impulse — IR Convolution & Saturation Engine](#4-srcimpulse--ir-convolution--saturation-engine)
5. [src.kikgen — LD_PRELOAD Code Generation](#5-srckikgen--ld_preload-code-generation)
6. [src.mockba — MockbaMod Addon Scaffolding](#6-srcmockba--mockbamod-addon-scaffolding)
7. [Error Reference](#7-error-reference)

---

## 1. CLI Interface

Entry point: `akai-convert` (installed via `pip install`), or `python -m src.cli`.

### Subcommands

#### `akai-convert info <preset_file>`

Print extracted filter parameters from a Serum preset.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `preset_file` | path | Yes | Path to `.fxp` or `.SerumPreset` file |

**Output**: Prints preset name, format, filter type (raw), cutoff, resonance, drive, fat, mix, pan, and envelope parameters (ADSR + amount) to stdout.

**Auto-detection**: `.fxp` extension routes to `parse_fxp()`, `.serumpreset` (case-insensitive) routes to `parse_serum_preset()`.

#### `akai-convert convert <preset_file> [--output-dir DIR]`

Convert Serum filter settings to Akai MPC equivalents.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `preset_file` | path | Yes | Path to `.fxp` or `.SerumPreset` file |
| `--output-dir`, `-o` | path | No | Save XPM drum program to this directory |

**Output**: Prints Akai filter type, cutoff/127, resonance/127, envelope values, IR fallback status, drive and fat mappings. If `--output-dir` is provided, saves an XPM program with the converted filter applied to pad A01.

**Errors**: `ValueError` for unknown file extensions. `FileNotFoundError` for missing preset files.

---

## 2. src.xpm — XPM Program Builder

### Classes

#### `DrumProgram(name: str = "DrumProgram")`

Builder for Akai MPC drum programs (.xpm). Maps instruments to pads (banks A-D, pads 1-16, up to 64 total).

| Method | Signature | Description |
|--------|-----------|-------------|
| `add_pad` | `(instrument: Instrument, bank: str = "A", pad: int = 1) -> None` | Assign instrument to pad. Bank must be A-D, pad must be 1-16. |
| `build_xml` | `() -> str` | Generate complete `.xpm` XML string. |
| `save` | `(output_dir: str \| Path) -> Path` | Save to `output_dir/Name/Name.xpm` with `Samples/` subdirectory. Returns path to `.xpm`. |
| `instruments` | property | Returns `list[Instrument]` (copy). |

**Raises**: `ValueError` if bank not in `ABCD` or pad not in 1-16.

#### `KeygroupProgram(name: str = "KeygroupProgram")`

Builder for keygroup programs (.xpm). Maps instruments across keyboard with key/velocity ranges.

| Method | Signature | Description |
|--------|-----------|-------------|
| `add_keygroup` | `(instrument: Instrument) -> None` | Add a keygroup instrument. |
| `build_xml` | `() -> str` | Generate complete `.xpm` XML string. |
| `save` | `(output_dir: str \| Path) -> Path` | Same as DrumProgram. |

#### `Instrument`

Dataclass representing a single instrument within a program.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | `""` | Instrument name |
| `layers` | `list[PadLayer]` | `[]` | Sample layers (max 4) |
| `filter_config` | `FilterConfig` | `FilterConfig()` | Filter settings |
| `mod_matrix` | `ModMatrix` | `ModMatrix()` | Modulation routing |
| `volume` | `int` | `100` | 0-127 |
| `pan` | `int` | `64` | 0-127 (64=center) |
| `mute_group` | `int` | `0` | 0=none, 1-32 |

| Method | Signature | Description |
|--------|-----------|-------------|
| `add_layer` | `(layer: PadLayer) -> None` | Add sample layer. **Raises** `ValueError` if already 4 layers. |
| `to_xml` | `(soup: BeautifulSoup) -> Tag` | Serialize to XML element. |

#### `PadLayer`

Dataclass for a single sample layer.

| Field | Type | Default | Range | Description |
|-------|------|---------|-------|-------------|
| `sample_path` | `str` | (required) | — | Relative path to sample |
| `volume` | `int` | `100` | 0-127 | Layer volume |
| `pan` | `int` | `64` | 0-127 | Pan (64=center) |
| `tune_coarse` | `int` | `0` | -36 to +36 | Semitones |
| `tune_fine` | `int` | `0` | -99 to +99 | Cents |
| `root_note` | `int` | `60` | 0-127 | MIDI note (60=C4) |
| `key_low` | `int` | `0` | 0-127 | Key range low |
| `key_high` | `int` | `127` | 0-127 | Key range high |
| `velocity_low` | `int` | `0` | 0-127 | Velocity range low |
| `velocity_high` | `int` | `127` | 0-127 | Velocity range high |

#### `FilterConfig`

Dataclass for MPC filter parameters. All integer fields are clamped to 0-127 in `__post_init__`.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `filter_type` | `FilterType` | `FilterType.OFF` | Filter mode |
| `cutoff` | `int` | `127` | Cutoff (0=20Hz, 127=20kHz, logarithmic) |
| `resonance` | `int` | `0` | Resonance |
| `env_amount` | `int` | `0` | Filter envelope depth |
| `attack` | `int` | `0` | Envelope attack |
| `decay` | `int` | `64` | Envelope decay |
| `sustain` | `int` | `127` | Envelope sustain |
| `release` | `int` | `64` | Envelope release |

| Method | Signature | Description |
|--------|-----------|-------------|
| `to_xml_dict` | `() -> dict[str, str]` | Returns dict of XML tag names to string values. |

### Enumerations

#### `FilterType(str, Enum)`

| Value | XML Name | Description |
|-------|----------|-------------|
| `OFF` | `"Off"` | Filter bypassed |
| `LP1` | `"LowPass1Pole"` | Low-pass 6dB/oct |
| `LP2` | `"LowPass2Pole"` | Low-pass 12dB/oct |
| `LP4` | `"LowPass4Pole"` | Low-pass 24dB/oct |
| `LP6` | `"LowPass6Pole"` | Low-pass 36dB/oct |
| `HP1` | `"HighPass1Pole"` | High-pass 6dB/oct |
| `HP2` | `"HighPass2Pole"` | High-pass 12dB/oct |
| `BP` | `"BandPass"` | Band-pass |
| `NOTCH` | `"BandReject"` | Notch / Band-reject |
| `LINK` | `"Link"` | Series HP+LP |

#### `ModSource(str, Enum)` — 10 values

`Velocity`, `Aftertouch`, `ModWheel`, `KeyTrack`, `LFO1`, `LFO2`, `FilterEnv`, `AmpEnv`, `PitchBend`, `Expression`

#### `ModDest(str, Enum)` — 10 values

`FilterCutoff`, `FilterResonance`, `Volume`, `Pan`, `Pitch`, `LFO1Rate`, `LFO2Rate`, `LFO1Depth`, `LFO2Depth`, `SampleStart`

#### `ModCurve(str, Enum)` — 4 values

`LINEAR`, `EXPONENTIAL`, `LOGARITHMIC`, `S_CURVE`

#### `ModMatrix`

| Method | Signature | Description |
|--------|-----------|-------------|
| `add` | `(source, dest, depth, curve=LINEAR) -> None` | Add route. Max 8. **Raises** `ValueError`. |
| `remove_route` | `(index: int) -> ModRoute` | Remove by index. |
| `clear` | `() -> None` | Remove all routes. |
| `get_routes_for_dest` | `(dest: ModDest) -> list[ModRoute]` | Filter by destination. |
| `get_routes_for_source` | `(source: ModSource) -> list[ModRoute]` | Filter by source. |
| `to_xml_list` | `() -> list[dict[str, str]]` | Serialize routes for XML. |
| `routes` | property | `list[ModRoute]` (copy). |

#### `ModRoute`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `source` | `ModSource` | (required) | Modulation source |
| `destination` | `ModDest` | (required) | Modulation target |
| `depth` | `int` | `0` | -127 to +127 (clamped in `__post_init__`) |
| `curve` | `ModCurve` | `LINEAR` | Response curve |

### Utility Functions

| Function | Signature | Description |
|----------|-----------|-------------|
| `hz_to_mpc` | `(freq_hz: float) -> int` | Convert Hz (20-20000) to MPC cutoff 0-127 (logarithmic). Clamps to range. |
| `mpc_to_hz` | `(mpc_val: int) -> float` | Reverse conversion: MPC 0-127 to Hz. Clamps to range. |
| `float_to_mpc` | `(value: float, min_val: float = 0.0, max_val: float = 1.0) -> int` | Normalize float to 0-127. Clamps to range. |

---

## 3. src.serum — Serum Preset Parsing & Conversion

### Parser Functions

#### `parse_fxp(file_path: str | Path) -> SerumV1Preset`

Parse a Serum v1 `.fxp` preset file (VST2 format).

**Raises**: `ValueError` if invalid FXP magic or unsupported format. `FileNotFoundError` if file missing.

#### `parse_serum_preset(file_path: str | Path) -> SerumV2Preset`

Parse a Serum 2 `.SerumPreset` file (XferJson + zstd/CBOR).

**Raises**: `ValueError` if missing XferJson magic. `ImportError` if `zstandard` or `cbor2` not installed.

### Conversion Functions

#### `serum_to_akai(serum: SerumFilterConfig) -> ConversionResult`

Core conversion engine. Maps Serum filter type to closest Akai equivalent, converts cutoff (log Hz → 0-127), resonance, envelope, drive, fat. Flags exotic filters for IR fallback.

#### `batch_convert(presets: list[SerumFilterConfig]) -> list[ConversionResult]`

Convert multiple configurations in batch.

### Dataclasses

#### `SerumFilterConfig`

| Field | Type | Default | Range | Description |
|-------|------|---------|-------|-------------|
| `filter_type` | `int` | `0` | SerumFilterSubtype values | Raw type index |
| `cutoff` | `float` | `0.5` | 0.0-1.0 | Normalized (log 20Hz-20kHz) |
| `resonance` | `float` | `0.0` | 0.0-1.0 | Resonance |
| `drive` | `float` | `0.0` | 0.0-1.0 | Drive |
| `fat` | `float` | `0.0` | 0.0-1.0 | Fat |
| `mix` | `float` | `1.0` | 0.0-1.0 | Dry/wet |
| `pan` | `float` | `0.5` | 0.0-1.0 | Pan (0.5=center) |
| `routing` | `int` | `0` | 0-1 | 0=serial, 1=parallel |
| `env_attack` | `float` | `0.0` | 0.0-1.0 | Envelope attack |
| `env_decay` | `float` | `0.5` | 0.0-1.0 | Envelope decay |
| `env_sustain` | `float` | `1.0` | 0.0-1.0 | Envelope sustain |
| `env_release` | `float` | `0.3` | 0.0-1.0 | Envelope release |
| `env_amount` | `float` | `0.0` | -1.0 to 1.0 | Envelope depth |

**Computed Properties**: `category` (SerumFilterCategory), `cutoff_hz` (float, 20-20000), `needs_ir_fallback` (bool).

#### `ConversionResult`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `filter_config` | `FilterConfig` | (required) | Converted Akai filter settings |
| `needs_ir_fallback` | `bool` | `False` | Whether IR baking is needed |
| `ir_description` | `str` | `""` | Human-readable IR rendering instruction |
| `drive_as_insert_gain` | `int` | `0` | 0-127 for insert effect |
| `fat_as_output_boost` | `int` | `0` | 0-127 for output level |
| `mix_blend` | `float` | `1.0` | Dry/wet for parallel layer |

#### `SerumV1Preset`

15 fields: `preset_name`, `plugin_id`, `version`, `num_params`, `params` (list[float]), plus 10 individual filter parameter fields extracted from known offsets. See [Data Models](data-models.md#serumv1preset).

#### `SerumV2Preset`

17 fields: `preset_name`, `metadata` (dict), `patch_data` (dict), plus 14 individual filter parameter fields (including dual filter support). See [Data Models](data-models.md#serumv2preset).

### Enumerations

#### `SerumFilterSubtype(IntEnum)` — 27 types

**Normal** (0-12): LP_12, LP_24, LP_48, HP_12, HP_24, HP_48, BP_12, BP_24, NOTCH_12, NOTCH_24, PEAK, LP_6, HP_6

**Multi** (20-23): MULTI_LP_HP, MULTI_LP_BP, MULTI_BP_HP, MULTI_LP_LP

**Flanges** (40-44): COMB_POS, COMB_NEG, PHASER_4, PHASER_8, FLANGER

**Misc** (60-66): REVERB, COMB_LP, COMB_HP, FORMANT_VOWEL, FORMANT_TALK, RING_MOD, SAMPLE_HOLD

#### `SerumFilterCategory(IntEnum)` — 4 values

`NORMAL=0`, `MULTI=1`, `FLANGES=2`, `MISC=3`

---

## 4. src.impulse — IR Convolution & Saturation Engine

### Functions

#### `load_ir(file_path: str | Path, target_sr: int = 44100) -> ImpulseResponse`

Load an impulse response from a `.wav` file. Resamples to `target_sr` if needed. Normalizes peak to 1.0.

**Raises**: `FileNotFoundError` if file missing.

#### `convolve_with_ir(source: np.ndarray, ir: ImpulseResponse, mix: float = 1.0) -> np.ndarray`

FFT convolution (`scipy.signal.fftconvolve`). Handles all mono/stereo combinations. Output length matches source. Mix 0.0=dry, 1.0=fully wet.

#### `apply_saturation(audio: np.ndarray, mode: SaturationMode, params: SaturationParams | None = None, sample_rate: int = 44100) -> np.ndarray`

Apply saturation algorithm. Processes each channel independently for stereo. Applies tone EQ, dry/wet mix, output gain, and final clip to [-1.0, 1.0].

### Classes

#### `ImpulseResponse`

| Field | Type | Description |
|-------|------|-------------|
| `data` | `np.ndarray` | Audio data (float64) |
| `sample_rate` | `int` | Sample rate |
| `channels` | `int` | Number of channels |
| `duration_seconds` | `float` | Duration |
| `source_path` | `str` | Original file path |

Properties: `is_stereo` (bool), `num_samples` (int).

#### `SaturationParams`

| Field | Type | Default | Range | Description |
|-------|------|---------|-------|-------------|
| `drive` | `float` | `0.5` | 0.0-1.0 | Input gain (maps to 1x-10x via `drive_linear`) |
| `mix` | `float` | `1.0` | 0.0-1.0 | Dry/wet blend |
| `tone` | `float` | `0.5` | 0.0-1.0 | Post-saturation tilt EQ (0=dark, 1=bright) |
| `output` | `float` | `0.8` | 0.0-1.0 | Makeup gain |

#### `FlavorPack(name: str = "FlavorPack", sample_rate: int = 44100)`

Orchestrator: processes source samples through recipes and generates Akai programs.

| Method | Signature | Description |
|--------|-----------|-------------|
| `add_source` | `(sample_path: str, recipe: FlavorRecipe) -> None` | Add source sample with processing recipe. |
| `build` | `(output_dir: str \| Path, program_type: str = "drum") -> Path` | Process all sources and build XPM program. Returns path to `.xpm`. |

#### `FlavorRecipe`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `ir_path` | `str \| None` | `None` | Path to impulse response |
| `ir_mix` | `float` | `1.0` | IR dry/wet |
| `saturation_chain` | `list[SaturationStep]` | `[]` | Ordered saturation steps |
| `output_filter` | `FilterConfig` | `FilterConfig(OFF)` | Post-processing filter |

| Method | Signature | Description |
|--------|-----------|-------------|
| `add_saturation` | `(mode, drive=0.5, mix=1.0, tone=0.5, output=0.8) -> None` | Append saturation step to chain. |

#### `SaturationStep`

| Field | Type | Description |
|-------|------|-------------|
| `mode` | `SaturationMode` | Algorithm to use |
| `params` | `SaturationParams` | Processing parameters |

### Enumerations

#### `SaturationMode(Enum)` — 10 algorithms

| Mode | Algorithm | Character |
|------|-----------|-----------|
| `SOFT_CLIP` | `tanh(gain * x)` | Warm, gentle compression |
| `HARD_CLIP` | `clip(gain * x, -1, 1)` | Aggressive digital edge |
| `TAPE` | Asymmetric soft clip + IIR hysteresis | Analog tape warmth |
| `TUBE` | `x / (1 + \|x\|)` + 2nd harmonic | Vacuum tube richness |
| `TRANSFORMER` | Asymmetric clip + bias + LF emphasis | Iron-core coloration |
| `DIODE` | `sign(x) * (1 - exp(-\|x\|))` | Germanium/silicon distortion |
| `FOLDBACK` | Signal folding at +/-1 boundaries | Complex harmonic textures |
| `BITCRUSH` | Bit depth (16→4bit) + SR reduction (1x-16x) | Lo-fi digital degradation |
| `VINYL` | Soft compress + noise + amplitude wobble | Record player character |
| `CONSOLE` | `log1p` compression + odd harmonics | Mixing desk glue |

---

## 5. src.kikgen — LD_PRELOAD Code Generation

### Functions

#### `generate_preload_script(libraries, mpc_binary, device_type, extra_env, output_path) -> str`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `libraries` | `list[str]` | (required) | `.so` library paths to preload (order matters) |
| `mpc_binary` | `str` | `"/usr/bin/MPC"` | Path to MPC binary |
| `device_type` | `str` | `"mpc_live"` | Target: `mpc_live`, `mpc_x`, `mpc_one`, `force` |
| `extra_env` | `dict[str, str] \| None` | `None` | Additional environment variables |
| `output_path` | `str \| Path \| None` | `None` | Write script to file (chmod 755) |

Returns bash script string. Unknown device types fall back to `mpc_live`.

#### `generate_midimapper_config(device_name, mappings, include_filter_defaults, output_path) -> str`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `device_name` | `str` | `"Custom Controller"` | MIDI controller name |
| `mappings` | `list[CCMapping] \| None` | `None` | Custom CC mappings |
| `include_filter_defaults` | `bool` | `True` | Include CC74/71/73/72 filter mappings |
| `output_path` | `str \| Path \| None` | `None` | Write JSON to file |

Returns JSON string. When `include_filter_defaults=True`, adds 4 mappings: cutoff (CC74), resonance (CC71), attack (CC73), release (CC72).

#### `generate_filter_inject_source(filter_cc_cutoff, filter_cc_resonance, initial_cutoff, initial_resonance, output_path) -> str`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `filter_cc_cutoff` | `int` | `74` | MIDI CC for cutoff |
| `filter_cc_resonance` | `int` | `71` | MIDI CC for resonance |
| `initial_cutoff` | `int` | `127` | Initial cutoff value |
| `initial_resonance` | `int` | `0` | Initial resonance value |
| `output_path` | `str \| Path \| None` | `None` | Write `.c` file |

Returns C source string for `snd_rawmidi_write()` interception library.

#### `generate_makefile(output_path: str | Path | None = None) -> str`

Returns ARM cross-compilation Makefile string. Compiler: `arm-linux-gnueabihf-gcc`, flags: `-shared -fPIC -Wall -O2`, links: `-ldl -lasound`.

### Classes

#### `CCMapping`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `source_cc` | `int` | (required) | Input CC number |
| `target_cc` | `int` | (required) | Output CC number |
| `channel_in` | `int` | `0` | Input channel (0=all) |
| `channel_out` | `int` | `0` | Output channel (0=same) |
| `min_value` | `int` | `0` | Output range min |
| `max_value` | `int` | `127` | Output range max |
| `description` | `str` | `""` | Human-readable label |

#### `MidiMapperConfig`

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `device_name` | `str` | `"Custom Controller"` | Controller name |
| `mappings` | `list[CCMapping]` | `[]` | CC mappings |
| `note_remaps` | `dict[int, int]` | `{}` | Note remapping |

Methods: `add_filter_controls(cutoff_cc, resonance_cc, attack_cc, release_cc)`, `to_dict()`, `to_json(indent=2)`.

---

## 6. src.mockba — MockbaMod Addon Scaffolding

### Functions

#### `scaffold_addon(addon_name, description, version, author, include_server, output_dir) -> Path`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `addon_name` | `str` | (required) | Addon folder name |
| `description` | `str` | `""` | Addon description |
| `version` | `str` | `"1.0.0"` | Semantic version |
| `author` | `str` | `""` | Author name |
| `include_server` | `bool` | `False` | Include Node.js server stub |
| `output_dir` | `str \| Path` | `"."` | Parent directory |

Creates: `addon_name/manifest.json`, `startup.sh` (chmod 755), `startup.lua`, `README.md`, optional `server/` with `package.json` + `index.js`. Returns path to addon directory.

#### `generate_sd_layout(output_dir, addons, include_bootstrap) -> Path`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `output_dir` | `str \| Path` | (required) | Root directory |
| `addons` | `list[str] \| None` | `None` | Addon placeholder names |
| `include_bootstrap` | `bool` | `True` | Include bootstrap.sh |

Creates: `MockbaMod_SD/` with `AddOns/`, `Scripts/`, `Logs/`, `Config/`. Bootstrap script runs fsck and loads addon startup scripts. Config includes SSH/VNC/auto-load settings with SD label `662522`. Returns path to `MockbaMod_SD/`.

#### `generate_preload_library_template(library_name, hook_functions, output_dir) -> dict[str, str]`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `library_name` | `str` | `"force_filter_hook"` | Library name (without `.so`) |
| `hook_functions` | `list[str] \| None` | `None` | Functions to intercept (default: snd_rawmidi_write, snd_pcm_writei, snd_seq_event_output) |
| `output_dir` | `str \| Path \| None` | `None` | Write files to directory |

Returns `dict` mapping filename to content: `{"library_name.c": ..., "Makefile": ...}`. Makefile includes `deploy` target copying to `/media/662522/AddOns/`.

---

## 7. Error Reference

| Exception | Module | Condition |
|-----------|--------|-----------|
| `ValueError("Invalid FXP magic")` | `serum.parser_v1` | File doesn't start with `CcnK` |
| `ValueError("File too small for FXP header")` | `serum.parser_v1` | File < 60 bytes |
| `ValueError("Unsupported FXP format")` | `serum.parser_v1` | Neither `FPCh` nor `FxCk` |
| `ValueError("Not a Serum 2 preset")` | `serum.parser_v2` | Missing `XferJson\0` magic |
| `ImportError("zstandard package required")` | `serum.parser_v2` | `zstandard` not installed |
| `ImportError("cbor2 package required")` | `serum.parser_v2` | `cbor2` not installed |
| `ValueError("Max 4 layers per instrument")` | `xpm.builder` | Adding 5th layer to Instrument |
| `ValueError("Bank must be one of ABCD")` | `xpm.builder` | Invalid bank letter |
| `ValueError("Pad must be 1-16")` | `xpm.builder` | Pad number out of range |
| `ValueError("max 8 routes")` | `xpm.mod_matrix` | Adding 9th modulation route |
| `ValueError("Unknown preset format")` | `cli` | File extension not `.fxp` or `.SerumPreset` |
| `FileNotFoundError` | `serum.parser_v1`, `impulse.ir_loader` | File does not exist |
