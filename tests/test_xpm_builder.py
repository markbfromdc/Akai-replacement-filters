"""Tests for XPM program builder."""

import tempfile
from pathlib import Path

from src.xpm.builder import DrumProgram, KeygroupProgram, Instrument, PadLayer
from src.xpm.filter_params import FilterConfig, FilterType
from src.xpm.mod_matrix import ModMatrix, ModSource, ModDest, ModCurve


def test_drum_program_creation():
    program = DrumProgram("TestKit")
    kick = Instrument(name="Kick")
    kick.add_layer(PadLayer(sample_path="Samples/kick.wav"))
    program.add_pad(kick, bank="A", pad=1)

    xml = program.build_xml()
    assert "TestKit" in xml
    assert "Kick" in xml
    assert "kick.wav" in xml


def test_keygroup_program_creation():
    program = KeygroupProgram("TestKeys")
    inst = Instrument(name="Piano")
    inst.add_layer(PadLayer(sample_path="Samples/piano.wav", root_note=60))
    program.add_keygroup(inst)

    xml = program.build_xml()
    assert "TestKeys" in xml
    assert "Piano" in xml
    assert "piano.wav" in xml


def test_filter_config_in_xml():
    program = DrumProgram("FilterTest")
    inst = Instrument(
        name="Filtered",
        filter_config=FilterConfig(
            filter_type=FilterType.LP4,
            cutoff=80,
            resonance=40,
            env_amount=64,
        ),
    )
    inst.add_layer(PadLayer(sample_path="Samples/test.wav"))
    program.add_pad(inst, bank="A", pad=1)

    xml = program.build_xml()
    assert "LowPass4Pole" in xml
    assert "80" in xml  # FilterCutoff value
    assert "40" in xml  # FilterResonance value
    assert "FilterCutoff" in xml
    assert "FilterResonance" in xml


def test_mod_matrix_in_xml():
    program = DrumProgram("ModTest")
    inst = Instrument(name="Modulated")
    inst.mod_matrix.add(ModSource.VELOCITY, ModDest.CUTOFF, depth=80)
    inst.mod_matrix.add(ModSource.LFO1, ModDest.RESONANCE, depth=30, curve=ModCurve.EXPONENTIAL)
    inst.add_layer(PadLayer(sample_path="Samples/test.wav"))
    program.add_pad(inst, bank="A", pad=1)

    xml = program.build_xml()
    assert "Velocity" in xml
    assert "FilterCutoff" in xml
    assert "80" in xml
    assert "Exponential" in xml


def test_save_creates_files():
    program = DrumProgram("SaveTest")
    inst = Instrument(name="Pad")
    inst.add_layer(PadLayer(sample_path="Samples/test.wav"))
    program.add_pad(inst, bank="A", pad=1)

    with tempfile.TemporaryDirectory() as tmpdir:
        xpm_path = program.save(tmpdir)
        assert xpm_path.exists()
        assert xpm_path.suffix == ".xpm"
        assert (Path(tmpdir) / "SaveTest" / "Samples").is_dir()


def test_max_layers_per_instrument():
    inst = Instrument(name="Full")
    for i in range(4):
        inst.add_layer(PadLayer(sample_path=f"Samples/layer{i}.wav"))

    try:
        inst.add_layer(PadLayer(sample_path="Samples/extra.wav"))
        assert False, "Should have raised ValueError"
    except ValueError:
        pass


def test_velocity_layers():
    inst = Instrument(name="VelSwitch")
    inst.add_layer(PadLayer(sample_path="Samples/soft.wav", velocity_low=0, velocity_high=63))
    inst.add_layer(PadLayer(sample_path="Samples/hard.wav", velocity_low=64, velocity_high=127))
    assert len(inst.layers) == 2
