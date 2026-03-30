# MockbaMod Addon & Preload Workflow

Work with MockbaMod (Akai Force modded firmware) — generate addons, LD_PRELOAD libraries, and SD card configurations.

## When to Use
Use this skill when the user wants to:
- Create a MockbaMod addon for Akai Force
- Set up an SD card for MockbaMod
- Generate LD_PRELOAD library templates for Force firmware
- Deploy custom filter modules via MockbaMod

## MockbaMod Architecture
- **Firmware component**: Modified firmware image (installed via USB update)
- **SD card component**: ExFat formatted, label `662522`, contains AddOns and Scripts
- **Addon manager**: Loads addons from `AddOns/` folder on boot
- **Languages**: Lua (79.7%) and Shell (20.3%)

## Scaffold an Addon

```python
from src.mockba import scaffold_addon

# Basic addon
addon_dir = scaffold_addon(
    addon_name="FilterModule",
    description="Custom filter processing for Akai Force",
    version="1.0.0",
    author="Your Name",
    output_dir="./addons",
)

# Addon with Node.js web server (like FORCE-APPS-SERVER-MOCKBA)
addon_dir = scaffold_addon(
    addon_name="FilterServer",
    description="Web-based filter configuration interface",
    include_server=True,
    output_dir="./addons",
)
```

## Generate SD Card Layout

```python
from src.mockba import generate_sd_layout

sd_root = generate_sd_layout(
    output_dir="./sd_card",
    addons=["FilterModule", "MidiMapper"],
    include_bootstrap=True,
)
# Creates: MockbaMod_SD/AddOns/, Scripts/, Logs/, Config/
```

## Generate LD_PRELOAD Library Template

```python
from src.mockba import generate_preload_library_template

files = generate_preload_library_template(
    library_name="force_filter_hook",
    hook_functions=["snd_rawmidi_write", "snd_pcm_writei"],
    output_dir="./libs",
)
# Creates: force_filter_hook.c and Makefile
# Compile with: arm-linux-gnueabihf-gcc -shared -fPIC -o force_filter_hook.so ...
```

## Deployment Workflow

1. Create addon: `scaffold_addon("MyFilter", ...)`
2. Generate LD_PRELOAD library: `generate_preload_library_template(...)`
3. Cross-compile the .so with ARM toolchain
4. Generate SD card layout: `generate_sd_layout(...)`
5. Copy addon + .so to `AddOns/` on the SD card
6. Insert SD card and reboot Force

## Key Source Files
- `src/mockba/addon_scaffold.py` — Addon folder generator
- `src/mockba/sd_card.py` — SD card layout builder
- `src/mockba/preload_hack.py` — Force-specific LD_PRELOAD templates
- GitHub reference: MockbaTheBorg/MockbaMod
