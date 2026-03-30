# Akai MPC OS 3.7.1 Reference

Reference guide for Akai MPC OS 3.7.1 features, .xpm format, and filter capabilities.

## When to Use
Use this skill when the user asks about:
- Akai MPC OS 3.7.1 features or compatibility
- XPM file format specifics for OS 3.7.1
- Filter types and mod matrix capabilities
- Known quirks or workarounds for this OS version

## OS 3.7.1 Filter Modes

| Filter Mode | XML Value | Slope | Description |
|---|---|---|---|
| Off | `Off` | — | No filtering |
| Low Pass 1-pole | `LowPass1Pole` | 6dB/oct | Gentle roll-off |
| Low Pass 2-pole | `LowPass2Pole` | 12dB/oct | Standard LP |
| Low Pass 4-pole | `LowPass4Pole` | 24dB/oct | Classic synth LP |
| Low Pass 6-pole | `LowPass6Pole` | 36dB/oct | Steep LP |
| High Pass 1-pole | `HighPass1Pole` | 6dB/oct | Gentle HP |
| High Pass 2-pole | `HighPass2Pole` | 12dB/oct | Standard HP |
| Band Pass | `BandPass` | — | Resonant BP |
| Band Reject | `BandReject` | — | Notch filter |
| Link | `Link` | — | Serial HP+LP chain |

## XPM File Format (OS 3.7.1)

XPM files are XML-based program definitions stored in folder structures:

```
ProgramName/
├── ProgramName.xpm    (XML program definition)
└── Samples/
    ├── sample1.wav
    └── sample2.wav
```

### XML Structure
```xml
<?xml version="1.0" encoding="UTF-8"?>
<MPCVObject type="KeygroupProgram" version="3.7.1">
  <ProgramName>MyProgram</ProgramName>
  <ProgramType>Keygroup</ProgramType>
  <Keygroups>
    <Keygroup id="0">
      <Instrument>
        <Filter>
          <FilterType>LowPass4Pole</FilterType>
          <FilterCutoff>100</FilterCutoff>
          <FilterResonance>40</FilterResonance>
          <FilterEnvAmount>64</FilterEnvAmount>
          <FilterAttack>0</FilterAttack>
          <FilterDecay>60</FilterDecay>
          <FilterSustain>80</FilterSustain>
          <FilterRelease>40</FilterRelease>
        </Filter>
        <ModMatrix>
          <Route id="0">
            <Source>Velocity</Source>
            <Destination>FilterCutoff</Destination>
            <Depth>64</Depth>
            <Curve>Linear</Curve>
          </Route>
        </ModMatrix>
        <Layers>
          <Layer>
            <SamplePath>Samples/sound.wav</SamplePath>
            <Volume>100</Volume>
            <RootNote>60</RootNote>
          </Layer>
        </Layers>
      </Instrument>
    </Keygroup>
  </Keygroups>
</MPCVObject>
```

## Mod Matrix Sources & Destinations (OS 3.7.1)

### Sources
Velocity, Aftertouch, ModWheel, KeyTrack, LFO1, LFO2, FilterEnv, AmpEnv, PitchBend, Expression

### Destinations
FilterCutoff, FilterResonance, Volume, Pan, Pitch, LFO1Rate, LFO1Depth, LFO2Rate, LFO2Depth, SampleStart

### Limits
- Max 8 simultaneous mod routes per instrument
- Depth range: -127 to +127
- Max 4 layers per keygroup
- Max 128 keygroups per program

## Parameter Ranges

| Parameter | Range | Notes |
|---|---|---|
| Cutoff | 0-127 | Logarithmic: 0≈20Hz, 127≈20kHz |
| Resonance | 0-127 | Values >100 may self-oscillate |
| Env Amount | 0-127 | Filter envelope modulation depth |
| Attack | 0-127 | Filter envelope attack time |
| Decay | 0-127 | Filter envelope decay time |
| Sustain | 0-127 | Filter envelope sustain level |
| Release | 0-127 | Filter envelope release time |
| Volume | 0-127 | Layer/instrument volume |
| Pan | 0-127 | 0=hard left, 64=center, 127=hard right |

## Known Quirks (OS 3.7.1)
- Band Reject (Notch) filter resonance above 100 can cause audio artifacts
- Link mode requires both HP and LP cutoff settings; use mod matrix to control independently
- Keygroup programs with >64 keygroups may cause UI lag on MPC One
- Sample paths in XPM are relative to the program folder

## Key Source Files
- `src/xpm/filter_params.py` — FilterType enum matches OS 3.7.1 values
- `src/xpm/builder.py` — Generates OS 3.7.1 compatible XPM files
- `src/xpm/mod_matrix.py` — ModSource/ModDest enums match OS 3.7.1
