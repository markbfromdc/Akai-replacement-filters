"""Generate TKGL_MIDIMAPPER configuration files for custom controller mappings.

Creates JSON configs compatible with TheKikGen's TKGL_MIDIMAPPER library,
with focus on filter-related CC assignments.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


# Standard MIDI CC numbers for common filter controls
CC_CUTOFF = 74         # Brightness / Filter Cutoff (standard)
CC_RESONANCE = 71      # Resonance / Timbre
CC_ATTACK = 73         # Attack Time
CC_DECAY = 75          # Decay Time
CC_RELEASE = 72        # Release Time
CC_MOD_WHEEL = 1       # Modulation Wheel


@dataclass
class CCMapping:
    """A single MIDI CC mapping entry."""
    source_cc: int          # CC number from external controller
    target_cc: int          # CC number mapped to MPC parameter
    channel_in: int = 0     # Input MIDI channel (0 = all)
    channel_out: int = 0    # Output MIDI channel (0 = same)
    min_value: int = 0      # Output range minimum
    max_value: int = 127    # Output range maximum
    description: str = ""

    def to_dict(self) -> dict:
        entry = {
            "src_cc": self.source_cc,
            "dst_cc": self.target_cc,
            "ch_in": self.channel_in,
            "ch_out": self.channel_out,
            "min": self.min_value,
            "max": self.max_value,
        }
        if self.description:
            entry["description"] = self.description
        return entry


@dataclass
class MidiMapperConfig:
    """Complete TKGL_MIDIMAPPER configuration."""
    device_name: str = "Custom Controller"
    mappings: list[CCMapping] = field(default_factory=list)
    note_remaps: dict[int, int] = field(default_factory=dict)

    def add_filter_controls(
        self,
        cutoff_cc: int = CC_CUTOFF,
        resonance_cc: int = CC_RESONANCE,
        attack_cc: int = CC_ATTACK,
        release_cc: int = CC_RELEASE,
    ) -> None:
        """Add standard filter CC mappings."""
        self.mappings.extend([
            CCMapping(cutoff_cc, CC_CUTOFF, description="Filter Cutoff"),
            CCMapping(resonance_cc, CC_RESONANCE, description="Filter Resonance"),
            CCMapping(attack_cc, CC_ATTACK, description="Filter Env Attack"),
            CCMapping(release_cc, CC_RELEASE, description="Filter Env Release"),
        ])

    def to_dict(self) -> dict:
        config = {
            "device": self.device_name,
            "version": "1.0",
            "cc_mappings": [m.to_dict() for m in self.mappings],
        }
        if self.note_remaps:
            config["note_remaps"] = {str(k): v for k, v in self.note_remaps.items()}
        return config

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)


def generate_midimapper_config(
    device_name: str = "Custom Controller",
    mappings: list[CCMapping] | None = None,
    include_filter_defaults: bool = True,
    output_path: str | Path | None = None,
) -> str:
    """Generate a TKGL_MIDIMAPPER JSON configuration.

    Args:
        device_name: Name of the external MIDI controller.
        mappings: Custom CC mappings. If None, uses filter defaults.
        include_filter_defaults: Include standard filter CC mappings.
        output_path: If provided, write the JSON to this path.

    Returns:
        JSON string of the configuration.
    """
    config = MidiMapperConfig(device_name=device_name)

    if include_filter_defaults:
        config.add_filter_controls()

    if mappings:
        config.mappings.extend(mappings)

    json_str = config.to_json()

    if output_path:
        Path(output_path).write_text(json_str)

    return json_str
