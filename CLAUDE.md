# Akai Replacement Filters

## Project Overview
Convert 3rd party Xfer Serum filter presets to Akai MPC filter modes. Includes DSP saturation/impulse response baking, XPM program generation with full mod matrix, MockbaMod addon scaffolding, and KikGen LD_PRELOAD optimization.

## Setup
```bash
pip install -e ".[dev]"
```

Dependencies: beautifulsoup4, lxml, numpy, scipy, soundfile, zstandard, cbor2

## Common Commands
```bash
pytest                          # Run all tests
pytest tests/test_filter_map.py # Run specific test file
pytest -v                       # Verbose test output
```

## Project Structure
```
src/
├── xpm/            # XPM program builder (drum & keygroup), filter params, mod matrix
├── serum/          # Serum v1/v2 preset parsers and Serum→Akai filter conversion
├── impulse/        # Flavor plugin: IR loading, 10 saturation modes, flavor packs
├── kikgen/         # KikGen LD_PRELOAD optimization (launch scripts, MIDI mapper, filter injection)
└── mockba/         # MockbaMod addon scaffolding, SD card layout, Force preload templates
skills/             # 7 Claude Code skills (.md files)
tests/              # pytest test suite
examples/           # Usage examples
```

## Conventions
- Python 3.10+ with type hints
- All MPC parameter values use 0-127 integer range
- Filter cutoff maps logarithmically: 0 ≈ 20Hz, 127 ≈ 20kHz
- XPM files are XML-based, generated with BeautifulSoup/lxml
- Audio processing uses float64 numpy arrays in -1.0 to 1.0 range
- Serum filter types that have no Akai equivalent use IR fallback (baked into samples)
