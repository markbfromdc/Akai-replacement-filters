"""Example: Create a keygroup program with impulse response and saturation processing."""

from src.impulse.flavor_pack import FlavorPack, FlavorRecipe
from src.impulse.saturation import SaturationMode
from src.xpm.filter_params import FilterConfig, FilterType


def main():
    # Create a flavor recipe: reverb IR + tape + tube saturation
    recipe = FlavorRecipe(
        ir_path="impulse_responses/plate_reverb.wav",
        ir_mix=0.35,
        output_filter=FilterConfig(
            filter_type=FilterType.LP4,
            cutoff=90,
            resonance=15,
        ),
    )
    recipe.add_saturation(SaturationMode.TAPE, drive=0.4, tone=0.45)
    recipe.add_saturation(SaturationMode.TUBE, drive=0.25, mix=0.6)

    # Build a keygroup program from flavored samples
    pack = FlavorPack("Vintage Keys", sample_rate=44100)
    pack.add_source("samples/piano_C3.wav", recipe)
    pack.add_source("samples/piano_C4.wav", recipe)
    pack.add_source("samples/piano_C5.wav", recipe)

    xpm_path = pack.build("output/", program_type="keygroup")
    print(f"Saved keygroup program to: {xpm_path}")


if __name__ == "__main__":
    main()
