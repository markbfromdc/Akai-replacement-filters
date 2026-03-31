"""Command-line interface for akai-replacement-filters.

Usage:
    akai-convert info <preset_file>
    akai-convert convert <preset_file> [--output-dir DIR]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.serum import (
    parse_fxp,
    parse_serum_preset,
    serum_to_akai,
    SerumFilterConfig,
    SerumV1Preset,
    SerumV2Preset,
)
from src.xpm import DrumProgram, Instrument, PadLayer


def _preset_to_filter_config(preset: SerumV1Preset | SerumV2Preset) -> SerumFilterConfig:
    """Convert a parsed preset's filter fields into a SerumFilterConfig."""
    return SerumFilterConfig(
        filter_type=int(preset.filter_type_raw),
        cutoff=preset.filter_cutoff,
        resonance=preset.filter_resonance,
        drive=preset.filter_drive,
        fat=preset.filter_fat,
        mix=preset.filter_mix,
        pan=preset.filter_pan,
        env_attack=preset.filter_env_attack,
        env_decay=preset.filter_env_decay,
        env_sustain=preset.filter_env_sustain,
        env_release=preset.filter_env_release,
        env_amount=preset.filter_env_amount,
    )


def _parse_preset(file_path: Path) -> SerumV1Preset | SerumV2Preset:
    """Auto-detect preset format and parse."""
    suffix = file_path.suffix.lower()
    if suffix == ".fxp":
        return parse_fxp(file_path)
    elif suffix == ".serumpreset":
        return parse_serum_preset(file_path)
    else:
        raise ValueError(f"Unknown preset format: {suffix} (expected .fxp or .SerumPreset)")


def cmd_info(args: argparse.Namespace) -> None:
    """Print filter parameters from a Serum preset."""
    preset_path = Path(args.preset_file)
    preset = _parse_preset(preset_path)

    print(f"Preset: {preset.preset_name}")
    print(f"Format: {'Serum v1 (.fxp)' if isinstance(preset, SerumV1Preset) else 'Serum 2 (.SerumPreset)'}")
    print(f"Filter Type (raw): {preset.filter_type_raw}")
    print(f"Cutoff:     {preset.filter_cutoff:.3f}")
    print(f"Resonance:  {preset.filter_resonance:.3f}")
    print(f"Drive:      {preset.filter_drive:.3f}")
    print(f"Fat:        {preset.filter_fat:.3f}")
    print(f"Mix:        {preset.filter_mix:.3f}")
    print(f"Pan:        {preset.filter_pan:.3f}")
    print(f"Env Attack: {preset.filter_env_attack:.3f}")
    print(f"Env Decay:  {preset.filter_env_decay:.3f}")
    print(f"Env Sustain:{preset.filter_env_sustain:.3f}")
    print(f"Env Release:{preset.filter_env_release:.3f}")
    print(f"Env Amount: {preset.filter_env_amount:.3f}")


def cmd_convert(args: argparse.Namespace) -> None:
    """Convert a Serum preset to Akai MPC filter settings."""
    preset_path = Path(args.preset_file)
    preset = _parse_preset(preset_path)
    serum_config = _preset_to_filter_config(preset)
    result = serum_to_akai(serum_config)

    print(f"Preset: {preset.preset_name}")
    print(f"Akai Filter Type: {result.filter_config.filter_type.value}")
    print(f"Cutoff:     {result.filter_config.cutoff}/127")
    print(f"Resonance:  {result.filter_config.resonance}/127")
    print(f"Env Amount: {result.filter_config.env_amount}/127")
    print(f"Attack:     {result.filter_config.attack}/127")
    print(f"Decay:      {result.filter_config.decay}/127")
    print(f"Sustain:    {result.filter_config.sustain}/127")
    print(f"Release:    {result.filter_config.release}/127")
    print(f"IR Fallback: {'Yes — ' + result.ir_description if result.needs_ir_fallback else 'No'}")
    print(f"Drive (insert gain): {result.drive_as_insert_gain}/127")
    print(f"Fat (output boost):  {result.fat_as_output_boost}/127")

    if args.output_dir:
        output_dir = Path(args.output_dir)
        program_name = f"{preset.preset_name}_converted"
        program = DrumProgram(program_name)
        inst = Instrument(name=preset.preset_name, filter_config=result.filter_config)
        inst.add_layer(PadLayer(sample_path="Samples/placeholder.wav"))
        program.add_pad(inst, bank="A", pad=1)
        xpm_path = program.save(output_dir)
        print(f"\nSaved XPM program to: {xpm_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="akai-convert",
        description="Convert Serum filter presets to Akai MPC filter modes.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # info subcommand
    info_parser = subparsers.add_parser("info", help="Print preset filter parameters")
    info_parser.add_argument("preset_file", help="Path to .fxp or .SerumPreset file")

    # convert subcommand
    convert_parser = subparsers.add_parser("convert", help="Convert preset to Akai filter settings")
    convert_parser.add_argument("preset_file", help="Path to .fxp or .SerumPreset file")
    convert_parser.add_argument("--output-dir", "-o", help="Save XPM program to this directory")

    args = parser.parse_args()

    if args.command == "info":
        cmd_info(args)
    elif args.command == "convert":
        cmd_convert(args)


if __name__ == "__main__":
    main()
