"""Flavor pack: orchestrate IR convolution and saturation into Akai MPC programs.

Takes source samples, applies impulse responses and saturation chains,
exports processed .wav files, and builds XPM programs referencing them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import soundfile as sf

from .ir_loader import ImpulseResponse, load_ir, convolve_with_ir
from .saturation import SaturationMode, SaturationParams, apply_saturation
from src.xpm.builder import DrumProgram, KeygroupProgram, Instrument, PadLayer
from src.xpm.filter_params import FilterConfig, FilterType


@dataclass
class SaturationStep:
    """A single step in a saturation processing chain."""
    mode: SaturationMode
    params: SaturationParams = field(default_factory=SaturationParams)


@dataclass
class FlavorRecipe:
    """Defines how to process a source sample: IR + saturation chain."""
    ir_path: str | None = None          # Optional impulse response
    ir_mix: float = 1.0                 # IR dry/wet
    saturation_chain: list[SaturationStep] = field(default_factory=list)
    output_filter: FilterConfig = field(default_factory=lambda: FilterConfig(filter_type=FilterType.OFF))

    def add_saturation(self, mode: SaturationMode, drive: float = 0.5,
                       mix: float = 1.0, tone: float = 0.5, output: float = 0.8) -> None:
        self.saturation_chain.append(SaturationStep(
            mode=mode,
            params=SaturationParams(drive=drive, mix=mix, tone=tone, output=output),
        ))


class FlavorPack:
    """Process source samples through flavor recipes and generate Akai programs.

    Usage:
        pack = FlavorPack("My Flavor Kit")
        recipe = FlavorRecipe(ir_path="reverb.wav")
        recipe.add_saturation(SaturationMode.TAPE, drive=0.6)
        recipe.add_saturation(SaturationMode.TUBE, drive=0.3)
        pack.add_source("kick.wav", recipe)
        pack.add_source("snare.wav", recipe)
        pack.build("output/")
    """

    def __init__(self, name: str = "FlavorPack", sample_rate: int = 44100):
        self.name = name
        self.sample_rate = sample_rate
        self._sources: list[tuple[str, FlavorRecipe]] = []

    def add_source(self, sample_path: str, recipe: FlavorRecipe) -> None:
        """Add a source sample with its processing recipe."""
        self._sources.append((sample_path, recipe))

    def _process_single(self, source_path: str, recipe: FlavorRecipe) -> np.ndarray:
        """Process a single source through its recipe chain."""
        audio, sr = sf.read(source_path, dtype="float64")

        # Resample if needed
        if sr != self.sample_rate:
            from scipy.signal import resample
            num_samples = int(len(audio) * self.sample_rate / sr)
            if audio.ndim == 1:
                audio = resample(audio, num_samples)
            else:
                audio = np.column_stack([
                    resample(audio[:, ch], num_samples)
                    for ch in range(audio.shape[1])
                ])

        # Apply IR convolution
        if recipe.ir_path:
            ir = load_ir(recipe.ir_path, target_sr=self.sample_rate)
            audio = convolve_with_ir(audio, ir, mix=recipe.ir_mix)

        # Apply saturation chain
        for step in recipe.saturation_chain:
            audio = apply_saturation(audio, step.mode, step.params, self.sample_rate)

        # Normalize
        peak = np.max(np.abs(audio))
        if peak > 0:
            audio = audio / peak * 0.95  # Leave 0.5dB headroom

        return audio

    def build(self, output_dir: str | Path, program_type: str = "drum") -> Path:
        """Process all sources and build an Akai MPC program.

        Args:
            output_dir: Directory to write the program and processed samples.
            program_type: "drum" for drum program, "keygroup" for keygroup.

        Returns:
            Path to the generated .xpm file.
        """
        output_dir = Path(output_dir)
        program_dir = output_dir / self.name
        samples_dir = program_dir / "Samples"
        samples_dir.mkdir(parents=True, exist_ok=True)

        if program_type == "drum":
            program = DrumProgram(self.name)
        else:
            program = KeygroupProgram(self.name)

        for i, (source_path, recipe) in enumerate(self._sources):
            # Process audio
            processed = self._process_single(source_path, recipe)

            # Write processed sample
            source_name = Path(source_path).stem
            out_filename = f"{source_name}_flavored.wav"
            out_path = samples_dir / out_filename
            sf.write(str(out_path), processed, self.sample_rate)

            # Create instrument
            layer = PadLayer(
                sample_path=f"Samples/{out_filename}",
                volume=100,
            )
            instrument = Instrument(
                name=source_name,
                filter_config=recipe.output_filter,
            )
            instrument.add_layer(layer)

            if program_type == "drum":
                bank = "ABCD"[i // 16]
                pad = (i % 16) + 1
                program.add_pad(instrument, bank=bank, pad=pad)
            else:
                program.add_keygroup(instrument)

        # Save program
        xpm_path = program.save(output_dir)
        return xpm_path
