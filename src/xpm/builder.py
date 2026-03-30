"""XPM program builder for Akai MPC drum and keygroup programs.

Generates valid .xpm XML files compatible with MPC Live/X/One/Force (OS 3.7.1+).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from bs4 import BeautifulSoup

from .filter_params import FilterConfig, FilterType
from .mod_matrix import ModMatrix

_TEMPLATES_DIR = Path(__file__).parent / "templates"


@dataclass
class PadLayer:
    """A single sample layer within a pad/keygroup."""
    sample_path: str
    volume: int = 100          # 0-127
    pan: int = 64              # 0-127 (64 = center)
    tune_coarse: int = 0       # -36 to +36 semitones
    tune_fine: int = 0         # -99 to +99 cents
    root_note: int = 60        # MIDI note (C4 = 60)
    key_low: int = 0           # MIDI note range low
    key_high: int = 127        # MIDI note range high
    velocity_low: int = 0      # Velocity range low
    velocity_high: int = 127   # Velocity range high

    def to_xml(self, soup: BeautifulSoup) -> BeautifulSoup:
        layer = soup.new_tag("Layer")
        fields = {
            "SamplePath": self.sample_path,
            "Volume": str(self.volume),
            "Pan": str(self.pan),
            "TuneCoarse": str(self.tune_coarse),
            "TuneFine": str(self.tune_fine),
            "RootNote": str(self.root_note),
            "KeyLow": str(self.key_low),
            "KeyHigh": str(self.key_high),
            "VelocityLow": str(self.velocity_low),
            "VelocityHigh": str(self.velocity_high),
        }
        for tag_name, value in fields.items():
            tag = soup.new_tag(tag_name)
            tag.string = value
            layer.append(tag)
        return layer


@dataclass
class Instrument:
    """An instrument within a program (one per pad in drum, one per keygroup)."""
    name: str = ""
    layers: list[PadLayer] = field(default_factory=list)
    filter_config: FilterConfig = field(default_factory=FilterConfig)
    mod_matrix: ModMatrix = field(default_factory=ModMatrix)
    volume: int = 100          # 0-127
    pan: int = 64              # 0-127
    mute_group: int = 0        # 0 = none, 1-32

    def add_layer(self, layer: PadLayer) -> None:
        if len(self.layers) >= 4:
            raise ValueError("Max 4 layers per instrument")
        self.layers.append(layer)

    def to_xml(self, soup: BeautifulSoup) -> BeautifulSoup:
        inst = soup.new_tag("Instrument")

        name_tag = soup.new_tag("InstrumentName")
        name_tag.string = self.name
        inst.append(name_tag)

        vol_tag = soup.new_tag("Volume")
        vol_tag.string = str(self.volume)
        inst.append(vol_tag)

        pan_tag = soup.new_tag("Pan")
        pan_tag.string = str(self.pan)
        inst.append(pan_tag)

        mute_tag = soup.new_tag("MuteGroup")
        mute_tag.string = str(self.mute_group)
        inst.append(mute_tag)

        # Filter section
        filter_section = soup.new_tag("Filter")
        for tag_name, value in self.filter_config.to_xml_dict().items():
            tag = soup.new_tag(tag_name)
            tag.string = value
            filter_section.append(tag)
        inst.append(filter_section)

        # Mod matrix section
        mod_section = soup.new_tag("ModMatrix")
        for i, route_dict in enumerate(self.mod_matrix.to_xml_list()):
            route_tag = soup.new_tag("Route", id=str(i))
            for tag_name, value in route_dict.items():
                tag = soup.new_tag(tag_name)
                tag.string = value
                route_tag.append(tag)
            mod_section.append(route_tag)
        inst.append(mod_section)

        # Layers
        layers_tag = soup.new_tag("Layers")
        for layer in self.layers:
            layers_tag.append(layer.to_xml(soup))
        inst.append(layers_tag)

        return inst


class _BaseProgramBuilder:
    """Base class for XPM program builders."""

    def __init__(self, name: str, program_type: str, template_file: str):
        self.name = name
        self.program_type = program_type
        self._instruments: list[Instrument] = []

        template_path = _TEMPLATES_DIR / template_file
        with open(template_path, "r") as f:
            self._soup = BeautifulSoup(f.read(), "xml")

        # Set program name
        prog_name = self._soup.find("ProgramName")
        if prog_name:
            prog_name.string = name

    @property
    def instruments(self) -> list[Instrument]:
        return list(self._instruments)

    def build_xml(self) -> str:
        """Generate the complete .xpm XML string."""
        root = self._soup.find("MPCVObject")

        # Populate instruments
        instruments_tag = self._soup.find("Instruments")
        if instruments_tag:
            instruments_tag.clear()
            for inst in self._instruments:
                instruments_tag.append(inst.to_xml(self._soup))

        return self._soup.prettify()

    def save(self, output_dir: str | Path) -> Path:
        """Save the .xpm program to a directory.

        Creates a folder structure:
          output_dir/
            ProgramName.xpm
            Samples/
              (referenced sample files should be copied here)
        """
        output_dir = Path(output_dir)
        program_dir = output_dir / self.name
        program_dir.mkdir(parents=True, exist_ok=True)
        (program_dir / "Samples").mkdir(exist_ok=True)

        xpm_path = program_dir / f"{self.name}.xpm"
        xpm_path.write_text(self.build_xml(), encoding="utf-8")
        return xpm_path


class DrumProgram(_BaseProgramBuilder):
    """Builder for Akai MPC drum programs (.xpm).

    Drum programs map instruments to pads (A01-D16, up to 64 pads).
    """

    # Pad naming: banks A-D, pads 01-16
    PAD_BANKS = "ABCD"
    PADS_PER_BANK = 16

    def __init__(self, name: str = "DrumProgram"):
        super().__init__(name, "Drum", "drum_program.xml")

    def add_pad(self, instrument: Instrument, bank: str = "A", pad: int = 1) -> None:
        """Add an instrument to a specific pad.

        Args:
            instrument: The instrument to assign.
            bank: Pad bank letter (A-D).
            pad: Pad number (1-16).
        """
        if bank.upper() not in self.PAD_BANKS:
            raise ValueError(f"Bank must be one of {self.PAD_BANKS}")
        if not 1 <= pad <= self.PADS_PER_BANK:
            raise ValueError(f"Pad must be 1-{self.PADS_PER_BANK}")
        if not instrument.name:
            instrument.name = f"{bank.upper()}{pad:02d}"
        self._instruments.append(instrument)

    def build_xml(self) -> str:
        root = self._soup.find("MPCVObject")

        # Build pads section
        pads_tag = self._soup.find("Pads")
        if pads_tag:
            pads_tag.clear()
            for i, inst in enumerate(self._instruments):
                pad_tag = self._soup.new_tag("Pad", id=str(i))
                name_tag = self._soup.new_tag("PadName")
                name_tag.string = inst.name
                pad_tag.append(name_tag)
                pads_tag.append(pad_tag)

        return super().build_xml()


class KeygroupProgram(_BaseProgramBuilder):
    """Builder for Akai MPC keygroup programs (.xpm).

    Keygroup programs map instruments across the keyboard with
    configurable key ranges and up to 4 velocity layers per keygroup.
    """

    def __init__(self, name: str = "KeygroupProgram"):
        super().__init__(name, "Keygroup", "keygroup_program.xml")

    def add_keygroup(self, instrument: Instrument) -> None:
        """Add a keygroup instrument.

        Args:
            instrument: The instrument with layers configured for
                       key range and velocity splits.
        """
        self._instruments.append(instrument)

    def build_xml(self) -> str:
        root = self._soup.find("MPCVObject")

        # Build keygroups section
        keygroups_tag = self._soup.find("Keygroups")
        if keygroups_tag:
            keygroups_tag.clear()
            for i, inst in enumerate(self._instruments):
                kg_tag = self._soup.new_tag("Keygroup", id=str(i))
                kg_tag.append(inst.to_xml(self._soup))
                keygroups_tag.append(kg_tag)

        return super().build_xml()
