# Testing Specifications

| Field | Value |
|-------|-------|
| Version | 0.1.0 |
| Date | 2026-03-31 |
| Status | Active |
| Traceability | [API](api.md) &#124; [User Stories](user-stories.md) &#124; [Deployment](deployment.md) |

---

## Table of Contents

1. [Test Strategy Overview](#1-test-strategy-overview)
2. [Test Categories](#2-test-categories)
3. [Coverage by Module](#3-coverage-by-module)
4. [Fixture Inventory](#4-fixture-inventory)
5. [Test Patterns](#5-test-patterns)
6. [Test Execution](#6-test-execution)
7. [Coverage Requirements](#7-coverage-requirements)
8. [Recommended Additions](#8-recommended-additions)

---

## 1. Test Strategy Overview

| Metric | Value |
|--------|-------|
| Framework | pytest >= 7.4 with pytest-cov >= 4.1 |
| Total tests | 227 |
| Test files | 13 |
| Line coverage | 91% (1014 statements, 96 missed) |
| Execution time | ~2.1 seconds |
| CI matrix | Python 3.10, 3.11, 3.12 on ubuntu-latest |

---

## 2. Test Categories

### 2.1 Unit Tests (12 files)

Per-module tests validating individual functions, classes, and edge cases.

| File | Tests | Module Under Test |
|------|-------|-------------------|
| `test_filter_params.py` | 29 | `src/xpm/filter_params` |
| `test_mod_matrix.py` | 8 | `src/xpm/mod_matrix` |
| `test_xpm_builder.py` | 7 | `src/xpm/builder` |
| `test_serum_parser.py` | 3 | `src/serum/parser_v1` |
| `test_parser_v1_extended.py` | 19 | `src/serum/parser_v1` (extended) |
| `test_serum_parser_v2.py` | 15 | `src/serum/parser_v2` |
| `test_filter_map.py` | 12 | `src/serum/filter_map` |
| `test_ir_loader.py` | 18 | `src/impulse/ir_loader` |
| `test_impulse.py` | 25 | `src/impulse/saturation` |
| `test_flavor_pack.py` | 17 | `src/impulse/flavor_pack` |
| `test_kikgen.py` | 38 | `src/kikgen/*` |
| `test_mockba.py` | 24 | `src/mockba/*` |

### 2.2 Integration Tests (1 file)

| File | Tests | Description |
|------|-------|-------------|
| `test_integration.py` | 12 | End-to-end pipeline validation |

**Test classes in `test_integration.py`:**
- `TestSerumToXpmPipeline` -- Full Serum parse -> convert -> XPM build -> save
- `TestFlavorPackPipeline` -- Saturation chain -> drum/keygroup program
- `TestCLIImports` -- Module imports, `_preset_to_filter_config()` helper
- `TestFullExportCoverage` -- All 5 package `__init__.py` exports verified

---

## 3. Coverage by Module

| Module | Statements | Missed | Coverage | Missing Lines |
|--------|-----------|--------|----------|---------------|
| `src/__init__.py` | 0 | 0 | 100% | -- |
| `src/cli.py` | 73 | 60 | 18% | 45-51, 56-72, 77-103, 107-127, 131 |
| `src/impulse/__init__.py` | 4 | 0 | 100% | -- |
| `src/impulse/flavor_pack.py` | 69 | 1 | 99% | 77 |
| `src/impulse/ir_loader.py` | 56 | 1 | 98% | 65 |
| `src/impulse/saturation.py` | 111 | 4 | 96% | 53-54, 63, 148 |
| `src/kikgen/__init__.py` | 4 | 0 | 100% | -- |
| `src/kikgen/filter_inject.py` | 14 | 0 | 100% | -- |
| `src/kikgen/midimapper_config.py` | 48 | 0 | 100% | -- |
| `src/kikgen/preload_gen.py` | 18 | 0 | 100% | -- |
| `src/mockba/__init__.py` | 4 | 0 | 100% | -- |
| `src/mockba/addon_scaffold.py` | 25 | 0 | 100% | -- |
| `src/mockba/preload_hack.py` | 19 | 0 | 100% | -- |
| `src/mockba/sd_card.py` | 20 | 0 | 100% | -- |
| `src/serum/__init__.py` | 4 | 0 | 100% | -- |
| `src/serum/filter_map.py` | 110 | 2 | 98% | 82, 84 |
| `src/serum/parser_v1.py` | 98 | 2 | 98% | 128-129 |
| `src/serum/parser_v2.py` | 84 | 22 | 74% | 19-20, 24-25, 77-90, 156-170 |
| `src/xpm/__init__.py` | 4 | 0 | 100% | -- |
| `src/xpm/builder.py` | 144 | 4 | 97% | 136, 192, 194, 196 |
| `src/xpm/filter_params.py` | 42 | 0 | 100% | -- |
| `src/xpm/mod_matrix.py` | 63 | 0 | 100% | -- |
| **TOTAL** | **1014** | **96** | **91%** | -- |

### Coverage Gaps

| Module | Gap | Reason |
|--------|-----|--------|
| `cli.py` (18%) | `cmd_info()`, `cmd_convert()`, `main()` | No CLI integration tests with mock argv |
| `parser_v2.py` (74%) | `zstandard`/`cbor2` import paths, deep key search | Requires real or synthetic Serum v2 binary data |
| `saturation.py` (96%) | Tone EQ dark path, vinyl sample-hold loop guard | Edge conditions in Butterworth filter paths |

---

## 4. Fixture Inventory

### 4.1 Shared Fixtures (`tests/conftest.py`)

| Fixture | Scope | Returns | Description |
|---------|-------|---------|-------------|
| `tmp_dir` | function | `Path` | Temporary directory, cleaned up after test |
| `mono_wav` | function | `Path` | 440Hz sine, 0.1s, 44100Hz mono .wav file |
| `stereo_wav` | function | `Path` | L=440Hz R=880Hz, 0.1s, 44100Hz stereo .wav |
| `mono_wav_48k` | function | `Path` | 440Hz sine, 0.1s, 48000Hz mono .wav (resampling tests) |
| `short_ir_wav` | function | `Path` | Decaying exponential impulse, 1000 samples at 44100Hz |
| `test_signal` | function | `np.ndarray` | 0.8 amplitude 440Hz mono (no file, array only) |
| `stereo_signal` | function | `np.ndarray` | L=0.8*440Hz R=0.6*880Hz stereo array |

### 4.2 Local Fixtures (`tests/test_flavor_pack.py`)

| Fixture | Returns | Description |
|---------|---------|-------------|
| `sample_wav` | `Path` | 440Hz mono .wav for flavor pack input |
| `ir_wav` | `Path` | Short IR .wav for convolution tests |
| `second_sample_wav` | `Path` | 880Hz mono .wav (avoids filename collision) |

---

## 5. Test Patterns

### 5.1 Parametrized Tests

Used for exhaustive coverage of enum values and mode variants:

```python
@pytest.mark.parametrize("mode", list(SaturationMode))
def test_all_saturation_modes(mode, test_signal):
    result = apply_saturation(test_signal, mode)
    assert np.all(np.isfinite(result))
    assert np.max(np.abs(result)) <= 1.0
```

Applied to:
- All 10 `SaturationMode` values
- All 27 `SerumFilterSubtype` values for conversion
- All 10 `FilterType` values for XML serialization

### 5.2 Class-Based Grouping

Tests organized by functional area:

```python
class TestGeneratePreloadScript:
    def test_default_device(self): ...
    def test_mpc_x_device(self): ...
    def test_force_device(self): ...
    def test_extra_env(self): ...
    def test_output_to_file(self): ...
```

### 5.3 Binary Format Synthesis

Tests construct binary data from scratch rather than relying on fixture files:

```python
def _make_fpch_fxp(self, params=None):
    header = struct.pack(">4sI4sIIIII", b"CcnK", 0, b"FPCh", ...)
    data = zlib.compress(struct.pack(f"<{len(params)}f", *params))
    return header + data
```

### 5.4 Error Testing

```python
with pytest.raises(ValueError, match="Max 4 layers"):
    for _ in range(5):
        instrument.add_layer(PadLayer("sample.wav"))
```

### 5.5 Audio Signal Generation

Tests create synthetic audio signals directly in numpy:

```python
t = np.arange(4410) / 44100.0
audio = 0.5 * np.sin(2 * np.pi * 440.0 * t)
```

---

## 6. Test Execution

### 6.1 Local Commands

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_filter_map.py

# Verbose output
pytest -v

# With coverage report
pytest --cov=src --cov-report=term-missing

# Run single test
pytest tests/test_impulse.py::test_soft_clip_mode -v
```

### 6.2 CI Pipeline

Defined in `.github/workflows/ci.yml`:

```yaml
strategy:
  matrix:
    python-version: ["3.10", "3.11", "3.12"]
steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-python@v5
  - run: pip install -e ".[dev]"
  - run: pytest --cov=src --cov-report=term-missing -v
```

Triggers: push to `main` or `claude/*` branches, PRs to `main`.

---

## 7. Coverage Requirements

### 7.1 Current Targets

| Scope | Target | Current |
|-------|--------|---------|
| Overall | >= 90% | 91% |
| Core modules (xpm, serum, impulse) | >= 95% | 96-100% |
| Generator modules (kikgen, mockba) | >= 95% | 100% |
| CLI | >= 70% | 18% |

### 7.2 Quality Gates

- All 227 tests pass on Python 3.10, 3.11, 3.12
- No uncovered public API function (except CLI)
- No test imports from `_`-prefixed internal functions (except boundary testing)
- Test execution completes in < 5 seconds

---

## 8. Recommended Additions

### 8.1 CLI Tests (Priority: High)

Add `test_cli.py` with mock `sys.argv` and captured stdout to cover:
- `cmd_info()` with synthetic `.fxp` file
- `cmd_convert()` with `--output-dir`
- `_parse_preset()` unknown extension error
- `main()` argument parsing

Expected coverage improvement: `cli.py` from 18% to ~85%.

### 8.2 Security Tests (Priority: Medium)

- Path traversal in sample paths (e.g., `../../etc/passwd` in PadLayer.sample_path)
- XML injection in instrument/program names
- Malformed binary presets (fuzzing-style: truncated, random bytes)
- Oversized parameter arrays in FXP files

### 8.3 Performance Benchmarks (Priority: Low)

- Batch conversion throughput (1000 presets)
- FFT convolution with large IRs (> 5 second IR at 44100Hz)
- Saturation chain with 8+ sequential steps
- FlavorPack build with 64 sources

### 8.4 Property-Based Testing (Priority: Low)

Using `hypothesis` for:
- FilterConfig clamping: any int always results in 0-127
- ModRoute depth clamping: any int always results in -127 to 127
- `hz_to_mpc` / `mpc_to_hz` roundtrip within tolerance
- `float_to_mpc` monotonicity
