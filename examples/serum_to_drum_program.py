"""Example: Convert a Serum preset's filter settings to an Akai MPC drum program."""

from src.serum.filter_map import SerumFilterConfig, SerumFilterSubtype, serum_to_akai
from src.xpm import DrumProgram, Instrument, PadLayer
from src.xpm.mod_matrix import ModSource, ModDest


def main():
    # Define a Serum filter configuration (as if parsed from a preset)
    serum_filter = SerumFilterConfig(
        filter_type=SerumFilterSubtype.LP_24,  # 24dB/oct Low Pass
        cutoff=0.6,        # ~1.2kHz
        resonance=0.4,     # Moderate resonance
        drive=0.3,         # Light drive
        fat=0.2,           # Subtle boost
        mix=1.0,           # Fully wet
        env_attack=0.01,
        env_decay=0.5,
        env_sustain=0.6,
        env_release=0.3,
        env_amount=0.5,
    )

    # Convert to Akai filter settings
    result = serum_to_akai(serum_filter)
    print(f"Akai Filter Type: {result.filter_config.filter_type.value}")
    print(f"Cutoff: {result.filter_config.cutoff}/127")
    print(f"Resonance: {result.filter_config.resonance}/127")
    print(f"Needs IR fallback: {result.needs_ir_fallback}")

    # Build a drum program with the converted filter
    program = DrumProgram("Serum_Converted_Kit")

    kick = Instrument(
        name="Kick",
        filter_config=result.filter_config,
    )
    kick.add_layer(PadLayer(sample_path="Samples/kick.wav"))
    kick.mod_matrix.add(ModSource.VELOCITY, ModDest.CUTOFF, depth=64)
    kick.mod_matrix.add(ModSource.VELOCITY, ModDest.VOLUME, depth=100)

    program.add_pad(kick, bank="A", pad=1)
    xpm_path = program.save("output")
    print(f"Saved program to: {xpm_path}")


if __name__ == "__main__":
    main()
