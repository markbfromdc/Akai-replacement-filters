"""Integration tests: end-to-end pipeline validation.

Tests that verify the full Serum → Akai conversion pipeline works
when importing from top-level packages.
"""

import numpy as np
import pytest
import soundfile as sf

# All imports use top-level package paths to validate __init__.py exports
from src.serum import (
    SerumFilterConfig,
    SerumFilterSubtype,
    serum_to_akai,
    batch_convert,
    ConversionResult,
)
from src.xpm import (
    DrumProgram,
    KeygroupProgram,
    Instrument,
    PadLayer,
    FilterConfig,
    FilterType,
    ModSource,
    ModDest,
    ModMatrix,
)
from src.impulse import (
    FlavorPack,
    FlavorRecipe,
    SaturationMode,
    SaturationParams,
    SaturationStep,
    load_ir,
    ImpulseResponse,
)
from src.kikgen import (
    generate_preload_script,
    generate_midimapper_config,
    generate_filter_inject_source,
    generate_makefile,
    CCMapping,
    MidiMapperConfig,
)
from src.mockba import (
    scaffold_addon,
    generate_sd_layout,
    generate_preload_library_template,
)


class TestSerumToXpmPipeline:
    """End-to-end: Serum filter config → conversion → XPM drum program."""

    def test_lp24_to_drum_program(self, tmp_dir):
        # Step 1: Define Serum filter
        serum_config = SerumFilterConfig(
            filter_type=SerumFilterSubtype.LP_24,
            cutoff=0.6,
            resonance=0.4,
            drive=0.3,
            env_amount=0.5,
        )

        # Step 2: Convert
        result = serum_to_akai(serum_config)
        assert isinstance(result, ConversionResult)
        assert result.filter_config.filter_type == FilterType.LP4
        assert not result.needs_ir_fallback
        assert 0 <= result.filter_config.cutoff <= 127
        assert 0 <= result.filter_config.resonance <= 127

        # Step 3: Build drum program
        program = DrumProgram("Integration_Kit")
        inst = Instrument(name="TestPad", filter_config=result.filter_config)
        inst.mod_matrix.add(ModSource.VELOCITY, ModDest.CUTOFF, depth=64)
        inst.add_layer(PadLayer(sample_path="Samples/test.wav"))
        program.add_pad(inst, bank="A", pad=1)

        # Step 4: Generate and verify XML
        xml = program.build_xml()
        assert "LowPass4Pole" in xml
        assert "TestPad" in xml
        assert "Integration_Kit" in xml
        assert "Velocity" in xml
        assert "FilterCutoff" in xml

        # Step 5: Save to disk
        xpm_path = program.save(tmp_dir)
        assert xpm_path.exists()
        assert xpm_path.suffix == ".xpm"
        assert (tmp_dir / "Integration_Kit" / "Samples").is_dir()

    def test_exotic_filter_flags_ir_fallback(self):
        serum_config = SerumFilterConfig(
            filter_type=SerumFilterSubtype.COMB_POS,
            cutoff=0.5,
            resonance=0.3,
        )
        result = serum_to_akai(serum_config)
        assert result.needs_ir_fallback
        assert result.ir_description != ""

    def test_batch_convert_pipeline(self):
        configs = [
            SerumFilterConfig(filter_type=SerumFilterSubtype.LP_24, cutoff=0.3),
            SerumFilterConfig(filter_type=SerumFilterSubtype.HP_12, cutoff=0.7),
            SerumFilterConfig(filter_type=SerumFilterSubtype.FORMANT_VOWEL, cutoff=0.5),
        ]
        results = batch_convert(configs)
        assert len(results) == 3
        assert results[0].filter_config.filter_type == FilterType.LP4
        assert results[1].filter_config.filter_type == FilterType.HP1
        assert results[2].needs_ir_fallback


class TestFlavorPackPipeline:
    """End-to-end: FlavorRecipe → FlavorPack → processed audio + XPM."""

    def test_saturation_chain_to_drum_program(self, tmp_dir):
        # Create test audio
        wav_path = tmp_dir / "kick.wav"
        t = np.arange(4410) / 44100.0
        audio = 0.7 * np.sin(2 * np.pi * 100.0 * t) * np.exp(-t * 20)
        sf.write(str(wav_path), audio, 44100)

        # Build recipe with saturation chain
        recipe = FlavorRecipe(
            output_filter=FilterConfig(filter_type=FilterType.LP4, cutoff=90),
        )
        recipe.add_saturation(SaturationMode.TAPE, drive=0.5)
        recipe.add_saturation(SaturationMode.TUBE, drive=0.3)

        # Process and build
        pack = FlavorPack("FlavorKit")
        pack.add_source(str(wav_path), recipe)
        xpm_path = pack.build(tmp_dir, program_type="drum")

        assert xpm_path.exists()
        samples_dir = tmp_dir / "FlavorKit" / "Samples"
        wav_files = list(samples_dir.glob("*.wav"))
        assert len(wav_files) == 1
        assert "flavored" in wav_files[0].name

        # Verify processed audio is valid
        processed, sr = sf.read(str(wav_files[0]))
        assert sr == 44100
        assert np.all(np.isfinite(processed))
        assert np.max(np.abs(processed)) <= 1.0

    def test_flavor_to_keygroup(self, tmp_dir):
        wav_path = tmp_dir / "piano.wav"
        t = np.arange(4410) / 44100.0
        audio = 0.5 * np.sin(2 * np.pi * 440.0 * t)
        sf.write(str(wav_path), audio, 44100)

        recipe = FlavorRecipe()
        recipe.add_saturation(SaturationMode.CONSOLE, drive=0.2)

        pack = FlavorPack("KeygroupKit")
        pack.add_source(str(wav_path), recipe)
        xpm_path = pack.build(tmp_dir, program_type="keygroup")
        assert xpm_path.exists()


class TestCLIImports:
    """Verify CLI module can be imported without errors."""

    def test_cli_module_imports(self):
        from src.cli import main, cmd_info, cmd_convert, _preset_to_filter_config
        assert callable(main)
        assert callable(cmd_info)
        assert callable(cmd_convert)
        assert callable(_preset_to_filter_config)

    def test_preset_to_filter_config(self):
        from src.cli import _preset_to_filter_config
        from src.serum import SerumV1Preset

        preset = SerumV1Preset(
            preset_name="Test",
            plugin_id=0,
            version=1,
            num_params=0,
            params=[],
            filter_type_raw=1.0,
            filter_cutoff=0.6,
            filter_resonance=0.4,
        )
        config = _preset_to_filter_config(preset)
        assert isinstance(config, SerumFilterConfig)
        assert config.filter_type == 1
        assert config.cutoff == 0.6
        assert config.resonance == 0.4


class TestFullExportCoverage:
    """Verify all top-level exports are importable and usable."""

    def test_xpm_exports(self):
        from src.xpm import (
            DrumProgram, KeygroupProgram, Instrument, PadLayer,
            FilterConfig, FilterType, ModMatrix, ModRoute,
            ModSource, ModDest, ModCurve,
        )
        # Verify they're the real classes
        inst = Instrument(name="test")
        assert inst.name == "test"

    def test_serum_exports(self):
        from src.serum import (
            parse_fxp, parse_serum_preset, serum_to_akai,
            batch_convert, SerumFilterConfig, SerumFilterSubtype,
            ConversionResult, SerumV1Preset, SerumV2Preset,
        )
        assert callable(parse_fxp)
        assert callable(serum_to_akai)

    def test_impulse_exports(self):
        from src.impulse import (
            load_ir, ImpulseResponse, convolve_with_ir,
            apply_saturation, SaturationMode, SaturationParams,
            FlavorPack, FlavorRecipe, SaturationStep,
        )
        assert len(SaturationMode) == 10

    def test_kikgen_exports(self):
        from src.kikgen import (
            generate_preload_script, generate_midimapper_config,
            generate_filter_inject_source, generate_makefile,
            CCMapping, MidiMapperConfig,
        )
        assert callable(generate_preload_script)

    def test_mockba_exports(self):
        from src.mockba import (
            scaffold_addon, generate_sd_layout,
            generate_preload_library_template,
        )
        assert callable(scaffold_addon)
