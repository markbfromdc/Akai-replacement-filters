# Deployment Specifications

| Field | Value |
|-------|-------|
| Version | 0.1.0 |
| Date | 2026-03-31 |
| Status | Active |
| Traceability | [Architecture](architecture.md) &#124; [Testing](testing.md) &#124; [API](api.md) |

---

## Table of Contents

1. [Installation](#1-installation)
2. [CLI Usage](#2-cli-usage)
3. [CI/CD Pipeline](#3-cicd-pipeline)
4. [Device Deployment -- MPC (via KikGen)](#4-device-deployment--mpc-via-kikgen)
5. [Device Deployment -- Force (via MockbaMod)](#5-device-deployment--force-via-mockbamod)
6. [Cross-Compilation](#6-cross-compilation)
7. [Environment Variables](#7-environment-variables)
8. [Rollback Procedures](#8-rollback-procedures)
9. [Compatibility Matrix](#9-compatibility-matrix)

---

## 1. Installation

### 1.1 From Source (Development)

```bash
git clone https://github.com/markbfromdc/akai-replacement-filters
cd akai-replacement-filters
pip install -e ".[dev]"
```

### 1.2 Production Install

```bash
pip install .
```

### 1.3 System Requirements

- **Python:** >= 3.10
- **libsndfile:** Required by `soundfile` package (system library)
- **C compiler:** Not required for Python library usage; only needed for compiling generated C source files targeting MPC/Force

### 1.4 Dependencies

| Package | Min Version | Purpose | Required |
|---------|------------|---------|----------|
| beautifulsoup4 | 4.12 | XPM XML generation | Yes |
| lxml | 5.0 | XML parsing backend | Yes |
| numpy | 1.24 | Float64 audio arrays, DSP math | Yes |
| scipy | 1.11 | FFT convolution, resampling, Butterworth filters | Yes |
| soundfile | 0.12 | WAV file I/O | Yes |
| zstandard | 0.21 | Serum v2 preset decompression | Yes (runtime) |
| cbor2 | 5.5 | Serum v2 CBOR decoding | Yes (runtime) |
| pytest | 7.4 | Test framework | Dev only |
| pytest-cov | 4.1 | Coverage reporting | Dev only |

### 1.5 Build System

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"
```

---

## 2. CLI Usage

Entry point defined in `pyproject.toml`:

```toml
[project.scripts]
akai-convert = "src.cli:main"
```

### 2.1 Info Command

```bash
akai-convert info <preset_file>
```

Prints filter parameters from a Serum preset. Auto-detects format by extension (`.fxp` for v1, `.serumpreset` for v2).

**Output example:**
```
Preset: MyBass
Format: Serum v1 (.fxp)
Filter Type (raw): 1
Cutoff:     0.600
Resonance:  0.400
Drive:      0.200
...
```

### 2.2 Convert Command

```bash
akai-convert convert <preset_file> [--output-dir DIR]
```

Converts Serum filter settings to Akai MPC equivalents. With `--output-dir`, generates a `.xpm` drum program.

**Output example:**
```
Preset: MyBass
Akai Filter Type: LowPass4Pole
Cutoff:     76/127
Resonance:  51/127
...
IR Fallback: No
Saved XPM program to: output/MyBass_converted/MyBass_converted.xpm
```

### 2.3 Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Invalid arguments or unknown preset format |
| 2 | File not found or parse error |

---

## 3. CI/CD Pipeline

### 3.1 GitHub Actions Configuration

File: `.github/workflows/ci.yml`

```yaml
name: CI
on:
  push:
    branches: [main, "claude/*"]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pip install -e ".[dev]"
      - run: pytest --cov=src --cov-report=term-missing -v
```

### 3.2 Quality Gates

| Gate | Criterion |
|------|----------|
| Tests | All 227 tests pass |
| Coverage | >= 90% line coverage |
| Python versions | 3.10, 3.11, 3.12 all green |

### 3.3 Publishing

No PyPI publish step configured yet (v0.1.0 alpha). Future: trusted-publishers or `twine` upload.

---

## 4. Device Deployment -- MPC (via KikGen)

For MPC Live, MPC X, and MPC One standalone devices.

### 4.1 XPM Program Deployment

1. Generate `.xpm` program using `DrumProgram` or `KeygroupProgram` API
2. Copy the `ProgramName/` folder (containing `.xpm` + `Samples/`) to the MPC
3. Place in the device's internal storage under `Projects/` or `Programs/`
4. Compatible with MPC OS 3.7.1+

### 4.2 LD_PRELOAD Library Deployment

**Prerequisites:**
- SSH access to the MPC device
- ARM cross-compilation toolchain installed on development machine

**Steps:**

1. **Generate C source:**
   ```python
   from src.kikgen import generate_filter_inject_source, generate_makefile
   generate_filter_inject_source(output_path="filter_inject.c")
   generate_makefile(output_path="Makefile")
   ```

2. **Cross-compile:**
   ```bash
   make  # Uses arm-linux-gnueabihf-gcc
   ```

3. **Generate launch script:**
   ```python
   from src.kikgen import generate_preload_script
   generate_preload_script(
       libraries=["/home/user/filter_inject.so"],
       device_type="mpc_live",
       output_path="launch.sh",
   )
   ```

4. **Deploy via SSH:**
   ```bash
   scp filter_inject.so launch.sh root@mpc-device:/home/user/
   ssh root@mpc-device ./launch.sh
   ```

### 4.3 MIDI Mapper Deployment

1. Generate JSON config:
   ```python
   from src.kikgen import generate_midimapper_config
   generate_midimapper_config(
       device_name="My Controller",
       output_path="mapper.json",
   )
   ```
2. Copy `mapper.json` to device
3. Load via TKGL_MIDIMAPPER library

---

## 5. Device Deployment -- Force (via MockbaMod)

For Akai Force with MockbaMod firmware.

### 5.1 Prerequisites

- MockbaMod firmware installed on the Force
- ExFat-formatted SD card with volume label **`662522`**

### 5.2 SD Card Setup

```python
from src.mockba import generate_sd_layout

sd_root = generate_sd_layout(
    output_dir="media/",
    addons=["filter_hook"],
    include_bootstrap=True,
)
```

Creates:
```
media/MockbaMod_SD/
+-- AddOns/
|   +-- filter_hook/
+-- Scripts/
|   +-- bootstrap.sh
+-- Logs/
+-- Config/
    +-- mockba.conf
```

### 5.3 Addon Deployment

```python
from src.mockba import scaffold_addon

addon_dir = scaffold_addon(
    addon_name="filter_hook",
    description="Custom filter injection for Force",
    version="1.0.0",
    output_dir="media/MockbaMod_SD/AddOns",
)
```

### 5.4 Force LD_PRELOAD Libraries

```python
from src.mockba import generate_preload_library_template

files = generate_preload_library_template(
    library_name="force_filter",
    output_dir="media/MockbaMod_SD/AddOns/filter_hook/libs",
)
```

Then cross-compile and place `.so` in the addon directory. Reference from `startup.sh`:

```bash
export LD_PRELOAD="$ADDON_DIR/libs/force_filter.so:$LD_PRELOAD"
```

### 5.5 Boot Sequence

1. Insert SD card (label `662522`) into Force
2. Reboot Force
3. MockbaMod detects SD card by label
4. `Scripts/bootstrap.sh` runs automatically
5. Bootstrap iterates `AddOns/*/startup.sh` and launches each
6. Logs written to `Logs/boot_YYYYMMDD_HHMMSS.log`

---

## 6. Cross-Compilation

### 6.1 Toolchain

| Setting | Value |
|---------|-------|
| Compiler | `arm-linux-gnueabihf-gcc` |
| Architecture | ARM Cortex-A (32-bit hard-float) |
| Target OS | Linux (MPC/Force embedded) |

### 6.2 Compiler Flags

```makefile
CC = arm-linux-gnueabihf-gcc
CFLAGS = -shared -fPIC -Wall -O2
LDFLAGS = -ldl -lasound
```

### 6.3 Build Targets

| Target | Source | Output | Purpose |
|--------|--------|--------|---------|
| `filter_inject.so` | `filter_inject.c` | ARM shared library | MIDI CC interception for MPC |
| `{name}.so` | `{name}.c` | ARM shared library | Custom Force hooks via MockbaMod |

### 6.4 Installing the Toolchain

```bash
# Debian/Ubuntu
sudo apt install gcc-arm-linux-gnueabihf

# macOS (via Homebrew)
brew install arm-linux-gnueabihf-binutils
# (Full GCC cross-compiler requires additional setup)
```

---

## 7. Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TKGL_VERBOSE` | (unset) | Enable verbose logging in KikGen scripts |
| Custom via `extra_env` | -- | Passed to `generate_preload_script()`, exported in launch script |

Example:
```python
generate_preload_script(
    libraries=["filter_inject.so"],
    extra_env={"TKGL_VERBOSE": "1", "MY_CUSTOM_VAR": "value"},
)
```

Generates:
```bash
export TKGL_VERBOSE="1"
export MY_CUSTOM_VAR="value"
```

---

## 8. Rollback Procedures

### 8.1 XPM Programs

XPM programs are self-contained folders. To rollback:
- Delete the `ProgramName/` directory from the device
- No system state is modified

### 8.2 LD_PRELOAD Libraries (MPC)

To remove LD_PRELOAD injection:
- Delete the `.so` file and launch script from the device
- Restart the MPC normally (without the launch script)
- The standard `/usr/bin/MPC` binary runs unmodified

### 8.3 MockbaMod Addons (Force)

To remove an addon:
- Delete the addon folder from `AddOns/` on the SD card
- Or remove the SD card entirely -- Force boots normally without MockbaMod

### 8.4 Full Rollback

- Remove SD card (Force)
- Delete all custom files via SSH (MPC)
- Restart device -- all factory behavior restored

---

## 9. Compatibility Matrix

| Device | XPM Programs | KikGen LD_PRELOAD | MockbaMod Addons | MIDI Mapper |
|--------|:----------:|:----------------:|:---------------:|:----------:|
| MPC Live | Yes | Yes | No | Yes |
| MPC X | Yes | Yes | No | Yes |
| MPC One | Yes | Yes | No | Yes |
| Akai Force | Yes | Via MockbaMod | Yes | Yes |

### OS Requirements

| Feature | Minimum OS |
|---------|-----------|
| XPM programs | MPC OS 3.7.1+ |
| LD_PRELOAD injection | Linux-based firmware (all standalone MPC/Force) |
| MockbaMod | Force firmware with MockbaMod patch |
| MIDI Mapper | Requires TKGL_MIDIMAPPER library loaded via LD_PRELOAD |

---

## 10. Version History

| Version | Date | Status | Notes |
|---------|------|--------|-------|
| 0.1.0 | 2026-03-31 | Alpha | Initial release. 5 packages, 15 modules, CLI, 227 tests, 91% coverage. |
