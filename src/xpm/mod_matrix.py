"""Modulation matrix for Akai MPC keygroup/drum programs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ModSource(Enum):
    """Available modulation sources in MPC programs."""
    VELOCITY = "Velocity"
    AFTERTOUCH = "Aftertouch"
    MOD_WHEEL = "ModWheel"
    KEY_TRACK = "KeyTrack"
    LFO1 = "LFO1"
    LFO2 = "LFO2"
    FILTER_ENV = "FilterEnv"
    AMP_ENV = "AmpEnv"
    PITCH_BEND = "PitchBend"
    EXPRESSION = "Expression"


class ModDest(Enum):
    """Available modulation destinations in MPC programs."""
    CUTOFF = "FilterCutoff"
    RESONANCE = "FilterResonance"
    VOLUME = "Volume"
    PAN = "Pan"
    PITCH = "Pitch"
    LFO1_RATE = "LFO1Rate"
    LFO1_DEPTH = "LFO1Depth"
    LFO2_RATE = "LFO2Rate"
    LFO2_DEPTH = "LFO2Depth"
    SAMPLE_START = "SampleStart"


class ModCurve(Enum):
    """Modulation curve shapes."""
    LINEAR = "Linear"
    EXPONENTIAL = "Exponential"
    LOGARITHMIC = "Logarithmic"
    S_CURVE = "SCurve"


@dataclass
class ModRoute:
    """A single modulation routing: source -> destination with depth and curve."""
    source: ModSource
    destination: ModDest
    depth: int = 0          # -127 to +127
    curve: ModCurve = ModCurve.LINEAR

    def __post_init__(self):
        self.depth = max(-127, min(127, self.depth))

    def to_xml_dict(self) -> dict[str, str]:
        return {
            "Source": self.source.value,
            "Destination": self.destination.value,
            "Depth": str(self.depth),
            "Curve": self.curve.value,
        }


class ModMatrix:
    """Manages a collection of modulation routings for an MPC program.

    Supports up to 8 simultaneous routes (typical MPC limit).
    """
    MAX_ROUTES = 8

    def __init__(self):
        self._routes: list[ModRoute] = []

    @property
    def routes(self) -> list[ModRoute]:
        return list(self._routes)

    def add_route(self, route: ModRoute) -> None:
        if len(self._routes) >= self.MAX_ROUTES:
            raise ValueError(f"Mod matrix full: max {self.MAX_ROUTES} routes")
        self._routes.append(route)

    def add(self, source: ModSource, destination: ModDest, depth: int,
            curve: ModCurve = ModCurve.LINEAR) -> None:
        self.add_route(ModRoute(source, destination, depth, curve))

    def remove_route(self, index: int) -> ModRoute:
        return self._routes.pop(index)

    def clear(self) -> None:
        self._routes.clear()

    def to_xml_list(self) -> list[dict[str, str]]:
        return [r.to_xml_dict() for r in self._routes]

    def get_routes_for_dest(self, dest: ModDest) -> list[ModRoute]:
        return [r for r in self._routes if r.destination == dest]

    def get_routes_for_source(self, source: ModSource) -> list[ModRoute]:
        return [r for r in self._routes if r.source == source]
