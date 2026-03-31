"""Tests for KikGen LD_PRELOAD modules: preload_gen, midimapper_config, filter_inject."""

import json
import tempfile
from pathlib import Path

import pytest

from src.kikgen.preload_gen import generate_preload_script
from src.kikgen.midimapper_config import (
    CCMapping,
    MidiMapperConfig,
    generate_midimapper_config,
    CC_CUTOFF,
    CC_RESONANCE,
    CC_ATTACK,
    CC_RELEASE,
)
from src.kikgen.filter_inject import (
    generate_filter_inject_source,
    generate_makefile,
)


class TestGeneratePreloadScript:
    """Tests for generate_preload_script()."""

    def test_basic_script(self):
        script = generate_preload_script(["/opt/libs/filter.so"])
        assert "#!/bin/bash" in script
        assert "LD_PRELOAD" in script
        assert "/opt/libs/filter.so" in script

    def test_multiple_libraries(self):
        libs = ["/opt/a.so", "/opt/b.so", "/opt/c.so"]
        script = generate_preload_script(libs)
        assert "/opt/a.so:/opt/b.so:/opt/c.so" in script

    def test_device_type_mpc_live(self):
        script = generate_preload_script(["/lib.so"], device_type="mpc_live")
        assert "MPC Live" in script

    def test_device_type_mpc_x(self):
        script = generate_preload_script(["/lib.so"], device_type="mpc_x")
        assert "MPC X" in script

    def test_device_type_mpc_one(self):
        script = generate_preload_script(["/lib.so"], device_type="mpc_one")
        assert "MPC One" in script

    def test_device_type_force(self):
        script = generate_preload_script(["/lib.so"], device_type="force")
        assert "Akai Force" in script

    def test_unknown_device_defaults(self):
        script = generate_preload_script(["/lib.so"], device_type="unknown_device")
        assert "MPC Live" in script  # Falls back to mpc_live

    def test_custom_binary(self):
        script = generate_preload_script(["/lib.so"], mpc_binary="/custom/MPC")
        assert "exec /custom/MPC" in script

    def test_extra_env(self):
        script = generate_preload_script(
            ["/lib.so"],
            extra_env={"MY_VAR": "hello", "DEBUG": "1"},
        )
        assert 'export MY_VAR="hello"' in script
        assert 'export DEBUG="1"' in script

    def test_library_verification(self):
        script = generate_preload_script(["/lib.so"])
        assert "Library not found" in script

    def test_process_management(self):
        script = generate_preload_script(["/lib.so"])
        assert "pidof" in script or "killall" in script

    def test_output_to_file(self, tmp_dir):
        out = tmp_dir / "launch.sh"
        generate_preload_script(["/lib.so"], output_path=out)
        assert out.exists()
        assert out.stat().st_mode & 0o755
        content = out.read_text()
        assert "#!/bin/bash" in content

    def test_set_euo_pipefail(self):
        script = generate_preload_script(["/lib.so"])
        assert "set -euo pipefail" in script


class TestCCMapping:
    """Tests for CCMapping dataclass."""

    def test_defaults(self):
        m = CCMapping(source_cc=10, target_cc=74)
        assert m.channel_in == 0
        assert m.channel_out == 0
        assert m.min_value == 0
        assert m.max_value == 127

    def test_to_dict(self):
        m = CCMapping(source_cc=10, target_cc=74, description="Cutoff")
        d = m.to_dict()
        assert d["src_cc"] == 10
        assert d["dst_cc"] == 74
        assert d["description"] == "Cutoff"

    def test_to_dict_no_description(self):
        m = CCMapping(source_cc=10, target_cc=74)
        d = m.to_dict()
        assert "description" not in d

    def test_custom_range(self):
        m = CCMapping(source_cc=1, target_cc=74, min_value=20, max_value=100)
        d = m.to_dict()
        assert d["min"] == 20
        assert d["max"] == 100


class TestMidiMapperConfig:
    """Tests for MidiMapperConfig."""

    def test_defaults(self):
        config = MidiMapperConfig()
        assert config.device_name == "Custom Controller"
        assert config.mappings == []
        assert config.note_remaps == {}

    def test_add_filter_controls(self):
        config = MidiMapperConfig()
        config.add_filter_controls()
        assert len(config.mappings) == 4
        target_ccs = [m.target_cc for m in config.mappings]
        assert CC_CUTOFF in target_ccs
        assert CC_RESONANCE in target_ccs
        assert CC_ATTACK in target_ccs
        assert CC_RELEASE in target_ccs

    def test_add_filter_controls_custom_ccs(self):
        config = MidiMapperConfig()
        config.add_filter_controls(cutoff_cc=20, resonance_cc=21)
        assert config.mappings[0].source_cc == 20
        assert config.mappings[1].source_cc == 21

    def test_to_dict(self):
        config = MidiMapperConfig(device_name="My Controller")
        config.add_filter_controls()
        d = config.to_dict()
        assert d["device"] == "My Controller"
        assert d["version"] == "1.0"
        assert len(d["cc_mappings"]) == 4

    def test_to_dict_with_note_remaps(self):
        config = MidiMapperConfig()
        config.note_remaps = {36: 60, 37: 61}
        d = config.to_dict()
        assert d["note_remaps"] == {"36": 60, "37": 61}

    def test_to_json(self):
        config = MidiMapperConfig()
        config.add_filter_controls()
        j = config.to_json()
        parsed = json.loads(j)
        assert parsed["device"] == "Custom Controller"
        assert len(parsed["cc_mappings"]) == 4


class TestGenerateMidimapperConfig:
    """Tests for generate_midimapper_config() convenience function."""

    def test_default_with_filter_controls(self):
        result = generate_midimapper_config()
        parsed = json.loads(result)
        assert len(parsed["cc_mappings"]) == 4

    def test_no_filter_defaults(self):
        result = generate_midimapper_config(include_filter_defaults=False)
        parsed = json.loads(result)
        assert len(parsed["cc_mappings"]) == 0

    def test_custom_device_name(self):
        result = generate_midimapper_config(device_name="Launchpad")
        parsed = json.loads(result)
        assert parsed["device"] == "Launchpad"

    def test_custom_mappings_appended(self):
        custom = [CCMapping(source_cc=50, target_cc=60, description="Custom")]
        result = generate_midimapper_config(mappings=custom)
        parsed = json.loads(result)
        # 4 filter defaults + 1 custom
        assert len(parsed["cc_mappings"]) == 5

    def test_output_to_file(self, tmp_dir):
        out = tmp_dir / "midimapper.json"
        generate_midimapper_config(output_path=out)
        assert out.exists()
        parsed = json.loads(out.read_text())
        assert "cc_mappings" in parsed


class TestGenerateFilterInjectSource:
    """Tests for generate_filter_inject_source()."""

    def test_default_source(self):
        source = generate_filter_inject_source()
        assert "#define FILTER_CC_CUTOFF    74" in source
        assert "#define FILTER_CC_RESONANCE 71" in source
        assert "static unsigned char g_cutoff = 127" in source
        assert "static unsigned char g_resonance = 0" in source

    def test_custom_cc_numbers(self):
        source = generate_filter_inject_source(
            filter_cc_cutoff=20,
            filter_cc_resonance=21,
        )
        assert "#define FILTER_CC_CUTOFF    20" in source
        assert "#define FILTER_CC_RESONANCE 21" in source

    def test_custom_initial_values(self):
        source = generate_filter_inject_source(
            initial_cutoff=64,
            initial_resonance=32,
        )
        assert "g_cutoff = 64" in source
        assert "g_resonance = 32" in source

    def test_contains_required_includes(self):
        source = generate_filter_inject_source()
        assert "#include <dlfcn.h>" in source
        assert "#include <alsa/asoundlib.h>" in source
        assert "#define _GNU_SOURCE" in source

    def test_contains_snd_rawmidi_write(self):
        source = generate_filter_inject_source()
        assert "snd_rawmidi_write" in source

    def test_contains_constructor(self):
        source = generate_filter_inject_source()
        assert "__attribute__((constructor))" in source

    def test_output_to_file(self, tmp_dir):
        out = tmp_dir / "filter_inject.c"
        generate_filter_inject_source(output_path=out)
        assert out.exists()
        assert "#define _GNU_SOURCE" in out.read_text()


class TestGenerateMakefile:
    """Tests for generate_makefile()."""

    def test_default_makefile(self):
        mk = generate_makefile()
        assert "arm-linux-gnueabihf-gcc" in mk
        assert "-shared -fPIC" in mk
        assert "-ldl -lasound" in mk
        assert "filter_inject.so" in mk
        assert "filter_inject.c" in mk

    def test_has_targets(self):
        mk = generate_makefile()
        assert "all:" in mk
        assert "clean:" in mk

    def test_output_to_file(self, tmp_dir):
        out = tmp_dir / "Makefile"
        generate_makefile(output_path=out)
        assert out.exists()
        assert "arm-linux-gnueabihf-gcc" in out.read_text()
