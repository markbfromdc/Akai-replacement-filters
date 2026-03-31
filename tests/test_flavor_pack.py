"""Tests for flavor pack orchestration: IR + saturation → Akai programs."""

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import numpy as np
import pytest
import soundfile as sf

from src.impulse.flavor_pack import (
    FlavorPack,
    FlavorRecipe,
    SaturationStep,
)
from src.impulse.saturation import SaturationMode, SaturationParams
from src.xpm.filter_params import FilterConfig, FilterType


@pytest.fixture
def sample_wav(tmp_dir):
    """Create a simple test .wav file."""
    path = tmp_dir / "kick.wav"
    t = np.arange(4410) / 44100.0
    audio = 0.7 * np.sin(2 * np.pi * 100.0 * t) * np.exp(-t * 20)
    sf.write(str(path), audio, 44100)
    return path


@pytest.fixture
def sample_wav_48k(tmp_dir):
    """Create a test .wav file at 48kHz."""
    path = tmp_dir / "snare_48k.wav"
    t = np.arange(4800) / 48000.0
    audio = 0.6 * np.sin(2 * np.pi * 200.0 * t) * np.exp(-t * 30)
    sf.write(str(path), audio, 48000)
    return path


@pytest.fixture
def ir_wav(tmp_dir):
    """Create a simple impulse response .wav."""
    path = tmp_dir / "room_ir.wav"
    ir = np.zeros(500)
    ir[0] = 1.0
    ir[10:] = np.exp(-np.arange(490) / 50.0) * 0.3
    sf.write(str(path), ir, 44100)
    return path


class TestFlavorRecipe:
    """Tests for FlavorRecipe configuration."""

    def test_default_recipe(self):
        recipe = FlavorRecipe()
        assert recipe.ir_path is None
        assert recipe.ir_mix == 1.0
        assert recipe.saturation_chain == []
        assert recipe.output_filter.filter_type == FilterType.OFF

    def test_recipe_with_ir(self):
        recipe = FlavorRecipe(ir_path="/some/ir.wav", ir_mix=0.7)
        assert recipe.ir_path == "/some/ir.wav"
        assert recipe.ir_mix == 0.7

    def test_add_saturation(self):
        recipe = FlavorRecipe()
        recipe.add_saturation(SaturationMode.TAPE, drive=0.6, mix=0.8)
        assert len(recipe.saturation_chain) == 1
        assert recipe.saturation_chain[0].mode == SaturationMode.TAPE
        assert recipe.saturation_chain[0].params.drive == 0.6
        assert recipe.saturation_chain[0].params.mix == 0.8

    def test_multiple_saturation_steps(self):
        recipe = FlavorRecipe()
        recipe.add_saturation(SaturationMode.TAPE, drive=0.6)
        recipe.add_saturation(SaturationMode.TUBE, drive=0.3)
        recipe.add_saturation(SaturationMode.CONSOLE, drive=0.2)
        assert len(recipe.saturation_chain) == 3
        assert recipe.saturation_chain[0].mode == SaturationMode.TAPE
        assert recipe.saturation_chain[1].mode == SaturationMode.TUBE
        assert recipe.saturation_chain[2].mode == SaturationMode.CONSOLE

    def test_recipe_with_output_filter(self):
        filt = FilterConfig(filter_type=FilterType.LP4, cutoff=80, resonance=30)
        recipe = FlavorRecipe(output_filter=filt)
        assert recipe.output_filter.filter_type == FilterType.LP4
        assert recipe.output_filter.cutoff == 80


class TestSaturationStep:
    """Tests for SaturationStep dataclass."""

    def test_defaults(self):
        step = SaturationStep(mode=SaturationMode.SOFT_CLIP)
        assert step.mode == SaturationMode.SOFT_CLIP
        assert step.params.drive == 0.5

    def test_custom_params(self):
        params = SaturationParams(drive=0.9, mix=0.5, tone=0.7, output=0.6)
        step = SaturationStep(mode=SaturationMode.DIODE, params=params)
        assert step.params.drive == 0.9


class TestFlavorPack:
    """Tests for FlavorPack processing and build pipeline."""

    def test_init(self):
        pack = FlavorPack("Test Kit", sample_rate=48000)
        assert pack.name == "Test Kit"
        assert pack.sample_rate == 48000

    def test_add_source(self, sample_wav):
        pack = FlavorPack()
        recipe = FlavorRecipe()
        pack.add_source(str(sample_wav), recipe)
        assert len(pack._sources) == 1

    def test_process_single_no_effects(self, sample_wav):
        pack = FlavorPack()
        recipe = FlavorRecipe()
        result = pack._process_single(str(sample_wav), recipe)
        assert isinstance(result, np.ndarray)
        assert np.all(np.isfinite(result))
        # Should be normalized to ~0.95 peak
        assert np.max(np.abs(result)) == pytest.approx(0.95, abs=0.01)

    def test_process_single_with_saturation(self, sample_wav):
        pack = FlavorPack()
        recipe = FlavorRecipe()
        recipe.add_saturation(SaturationMode.SOFT_CLIP, drive=0.5)
        result = pack._process_single(str(sample_wav), recipe)
        assert isinstance(result, np.ndarray)
        assert np.all(np.isfinite(result))

    def test_process_single_with_ir(self, sample_wav, ir_wav):
        pack = FlavorPack()
        recipe = FlavorRecipe(ir_path=str(ir_wav), ir_mix=0.5)
        result = pack._process_single(str(sample_wav), recipe)
        assert isinstance(result, np.ndarray)
        assert np.all(np.isfinite(result))

    def test_process_with_resampling(self, sample_wav_48k):
        pack = FlavorPack(sample_rate=44100)
        recipe = FlavorRecipe()
        result = pack._process_single(str(sample_wav_48k), recipe)
        assert isinstance(result, np.ndarray)
        # Resampled length should be approximately 4800 * 44100/48000 = 4410
        assert abs(len(result) - 4410) < 10

    def test_build_drum_program(self, sample_wav, tmp_dir):
        pack = FlavorPack("TestDrum")
        recipe = FlavorRecipe()
        pack.add_source(str(sample_wav), recipe)
        xpm_path = pack.build(tmp_dir, program_type="drum")
        assert xpm_path.exists()
        assert xpm_path.suffix == ".xpm"
        # Check samples directory was created
        samples_dir = tmp_dir / "TestDrum" / "Samples"
        assert samples_dir.exists()
        # Check processed wav exists
        wav_files = list(samples_dir.glob("*.wav"))
        assert len(wav_files) == 1
        assert "flavored" in wav_files[0].name

    def test_build_keygroup_program(self, sample_wav, tmp_dir):
        pack = FlavorPack("TestKeygroup")
        recipe = FlavorRecipe()
        pack.add_source(str(sample_wav), recipe)
        xpm_path = pack.build(tmp_dir, program_type="keygroup")
        assert xpm_path.exists()

    def test_build_multiple_sources(self, sample_wav, tmp_dir):
        # Create a second source with a different name
        snare_path = tmp_dir / "snare.wav"
        t = np.arange(4410) / 44100.0
        audio = 0.5 * np.sin(2 * np.pi * 200.0 * t) * np.exp(-t * 30)
        sf.write(str(snare_path), audio, 44100)

        pack = FlavorPack("MultiKit")
        recipe1 = FlavorRecipe()
        recipe2 = FlavorRecipe()
        recipe2.add_saturation(SaturationMode.TAPE, drive=0.4)
        pack.add_source(str(sample_wav), recipe1)
        pack.add_source(str(snare_path), recipe2)
        xpm_path = pack.build(tmp_dir, program_type="drum")
        assert xpm_path.exists()
        samples_dir = tmp_dir / "MultiKit" / "Samples"
        wav_files = list(samples_dir.glob("*.wav"))
        assert len(wav_files) == 2

    def test_full_chain(self, sample_wav, ir_wav, tmp_dir):
        """End-to-end: IR + saturation chain + output filter → drum program."""
        pack = FlavorPack("FullChain")
        recipe = FlavorRecipe(
            ir_path=str(ir_wav),
            ir_mix=0.6,
            output_filter=FilterConfig(filter_type=FilterType.LP4, cutoff=90),
        )
        recipe.add_saturation(SaturationMode.TAPE, drive=0.5)
        recipe.add_saturation(SaturationMode.TUBE, drive=0.3)
        pack.add_source(str(sample_wav), recipe)
        xpm_path = pack.build(tmp_dir, program_type="drum")
        assert xpm_path.exists()
