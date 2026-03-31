"""Tests for MockbaMod modules: addon_scaffold, sd_card, preload_hack."""

import json
import os
from pathlib import Path

import pytest

from src.mockba.addon_scaffold import scaffold_addon
from src.mockba.sd_card import generate_sd_layout
from src.mockba.preload_hack import generate_preload_library_template


class TestScaffoldAddon:
    """Tests for scaffold_addon() directory generation."""

    def test_basic_scaffold(self, tmp_dir):
        result = scaffold_addon("MyAddon", output_dir=tmp_dir)
        assert result == tmp_dir / "MyAddon"
        assert result.is_dir()

    def test_manifest_json(self, tmp_dir):
        scaffold_addon("TestAddon", description="A test", version="2.0.0",
                       author="Tester", output_dir=tmp_dir)
        manifest = json.loads((tmp_dir / "TestAddon" / "manifest.json").read_text())
        assert manifest["name"] == "TestAddon"
        assert manifest["description"] == "A test"
        assert manifest["version"] == "2.0.0"
        assert manifest["author"] == "Tester"
        assert manifest["type"] == "addon"
        assert manifest["startup"] == "startup.sh"
        assert "compatible_firmware" in manifest

    def test_startup_sh_executable(self, tmp_dir):
        scaffold_addon("ExecTest", output_dir=tmp_dir)
        sh = tmp_dir / "ExecTest" / "startup.sh"
        assert sh.exists()
        assert sh.stat().st_mode & 0o755
        content = sh.read_text()
        assert "#!/bin/bash" in content
        assert "ExecTest" in content

    def test_startup_lua(self, tmp_dir):
        scaffold_addon("LuaTest", output_dir=tmp_dir)
        lua = tmp_dir / "LuaTest" / "startup.lua"
        assert lua.exists()
        assert "LuaTest" in lua.read_text()

    def test_readme(self, tmp_dir):
        scaffold_addon("ReadmeTest", description="My addon", output_dir=tmp_dir)
        readme = tmp_dir / "ReadmeTest" / "README.md"
        assert readme.exists()
        assert "ReadmeTest" in readme.read_text()

    def test_no_server_by_default(self, tmp_dir):
        scaffold_addon("NoServer", output_dir=tmp_dir)
        assert not (tmp_dir / "NoServer" / "server").exists()

    def test_with_server(self, tmp_dir):
        scaffold_addon("WithServer", include_server=True, output_dir=tmp_dir)
        server_dir = tmp_dir / "WithServer" / "server"
        assert server_dir.is_dir()
        # package.json
        pkg = json.loads((server_dir / "package.json").read_text())
        assert pkg["name"] == "WithServer-server"
        assert "start" in pkg["scripts"]
        # index.js
        index = (server_dir / "index.js").read_text()
        assert "WithServer" in index
        assert "http" in index

    def test_default_description(self, tmp_dir):
        scaffold_addon("DefaultDesc", output_dir=tmp_dir)
        manifest = json.loads((tmp_dir / "DefaultDesc" / "manifest.json").read_text())
        assert "MockbaMod addon" in manifest["description"]

    def test_returns_addon_path(self, tmp_dir):
        result = scaffold_addon("PathTest", output_dir=tmp_dir)
        assert isinstance(result, Path)
        assert result.name == "PathTest"


class TestGenerateSdLayout:
    """Tests for generate_sd_layout() directory structure."""

    def test_basic_layout(self, tmp_dir):
        root = generate_sd_layout(tmp_dir)
        assert root == tmp_dir / "MockbaMod_SD"
        assert (root / "AddOns").is_dir()
        assert (root / "Scripts").is_dir()
        assert (root / "Logs").is_dir()
        assert (root / "Config").is_dir()

    def test_bootstrap_script(self, tmp_dir):
        root = generate_sd_layout(tmp_dir)
        bootstrap = root / "Scripts" / "bootstrap.sh"
        assert bootstrap.exists()
        assert bootstrap.stat().st_mode & 0o755
        content = bootstrap.read_text()
        assert "#!/bin/bash" in content
        assert "MockbaMod Bootstrap" in content
        assert "AddOns" in content

    def test_no_bootstrap(self, tmp_dir):
        root = generate_sd_layout(tmp_dir, include_bootstrap=False)
        assert not (root / "Scripts" / "bootstrap.sh").exists()

    def test_config_file(self, tmp_dir):
        root = generate_sd_layout(tmp_dir)
        conf = root / "Config" / "mockba.conf"
        assert conf.exists()
        content = conf.read_text()
        assert "662522" in content
        assert "ssh_enabled" in content

    def test_addon_placeholders(self, tmp_dir):
        root = generate_sd_layout(tmp_dir, addons=["FilterMod", "MidiMapper"])
        assert (root / "AddOns" / "FilterMod").is_dir()
        assert (root / "AddOns" / "MidiMapper").is_dir()

    def test_no_addon_placeholders(self, tmp_dir):
        root = generate_sd_layout(tmp_dir, addons=None)
        # AddOns dir exists but is empty
        assert (root / "AddOns").is_dir()
        children = list((root / "AddOns").iterdir())
        assert len(children) == 0

    def test_returns_root_path(self, tmp_dir):
        root = generate_sd_layout(tmp_dir)
        assert isinstance(root, Path)
        assert root.name == "MockbaMod_SD"


class TestGeneratePreloadLibraryTemplate:
    """Tests for generate_preload_library_template()."""

    def test_default_output(self):
        files = generate_preload_library_template()
        assert "force_filter_hook.c" in files
        assert "Makefile" in files

    def test_custom_library_name(self):
        files = generate_preload_library_template(library_name="my_hook")
        assert "my_hook.c" in files
        assert "my_hook" in files["my_hook.c"]
        assert "my_hook.so" in files["Makefile"]

    def test_c_source_content(self):
        files = generate_preload_library_template()
        src = files["force_filter_hook.c"]
        assert "#define _GNU_SOURCE" in src
        assert "__attribute__((constructor))" in src
        assert "__attribute__((destructor))" in src
        assert "Akai Force" in src

    def test_default_hook_functions(self):
        files = generate_preload_library_template()
        src = files["force_filter_hook.c"]
        assert "snd_rawmidi_write" in src
        assert "snd_pcm_writei" in src
        assert "snd_seq_event_output" in src

    def test_custom_hook_functions(self):
        hooks = ["open", "read", "write"]
        files = generate_preload_library_template(hook_functions=hooks)
        src = files[list(files.keys())[0]]
        for hook in hooks:
            assert hook in src

    def test_makefile_content(self):
        files = generate_preload_library_template()
        mk = files["Makefile"]
        assert "arm-linux-gnueabihf-gcc" in mk
        assert "-shared -fPIC" in mk
        assert "deploy:" in mk
        assert "662522" in mk  # MockbaMod SD card label

    def test_output_to_dir(self, tmp_dir):
        files = generate_preload_library_template(
            library_name="test_lib",
            output_dir=tmp_dir,
        )
        assert (tmp_dir / "test_lib.c").exists()
        assert (tmp_dir / "Makefile").exists()
        assert "test_lib" in (tmp_dir / "test_lib.c").read_text()

    def test_returns_dict(self):
        result = generate_preload_library_template()
        assert isinstance(result, dict)
        assert len(result) == 2
