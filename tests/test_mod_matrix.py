"""Tests for mod matrix."""

import pytest

from src.xpm.mod_matrix import ModMatrix, ModRoute, ModSource, ModDest, ModCurve


def test_add_route():
    mm = ModMatrix()
    mm.add(ModSource.VELOCITY, ModDest.CUTOFF, depth=80)
    assert len(mm.routes) == 1
    assert mm.routes[0].source == ModSource.VELOCITY
    assert mm.routes[0].destination == ModDest.CUTOFF
    assert mm.routes[0].depth == 80


def test_max_routes():
    mm = ModMatrix()
    for i in range(8):
        mm.add(ModSource.VELOCITY, ModDest.CUTOFF, depth=i * 10)

    with pytest.raises(ValueError, match="max 8"):
        mm.add(ModSource.LFO1, ModDest.PAN, depth=50)


def test_depth_clamping():
    route = ModRoute(ModSource.VELOCITY, ModDest.CUTOFF, depth=200)
    assert route.depth == 127

    route = ModRoute(ModSource.VELOCITY, ModDest.CUTOFF, depth=-200)
    assert route.depth == -127


def test_get_routes_for_dest():
    mm = ModMatrix()
    mm.add(ModSource.VELOCITY, ModDest.CUTOFF, depth=80)
    mm.add(ModSource.LFO1, ModDest.CUTOFF, depth=30)
    mm.add(ModSource.MOD_WHEEL, ModDest.RESONANCE, depth=60)

    cutoff_routes = mm.get_routes_for_dest(ModDest.CUTOFF)
    assert len(cutoff_routes) == 2

    reso_routes = mm.get_routes_for_dest(ModDest.RESONANCE)
    assert len(reso_routes) == 1


def test_get_routes_for_source():
    mm = ModMatrix()
    mm.add(ModSource.VELOCITY, ModDest.CUTOFF, depth=80)
    mm.add(ModSource.VELOCITY, ModDest.VOLUME, depth=100)
    mm.add(ModSource.LFO1, ModDest.PAN, depth=40)

    vel_routes = mm.get_routes_for_source(ModSource.VELOCITY)
    assert len(vel_routes) == 2


def test_remove_route():
    mm = ModMatrix()
    mm.add(ModSource.VELOCITY, ModDest.CUTOFF, depth=80)
    mm.add(ModSource.LFO1, ModDest.PAN, depth=40)

    removed = mm.remove_route(0)
    assert removed.source == ModSource.VELOCITY
    assert len(mm.routes) == 1


def test_clear():
    mm = ModMatrix()
    mm.add(ModSource.VELOCITY, ModDest.CUTOFF, depth=80)
    mm.add(ModSource.LFO1, ModDest.PAN, depth=40)

    mm.clear()
    assert len(mm.routes) == 0


def test_to_xml_list():
    mm = ModMatrix()
    mm.add(ModSource.VELOCITY, ModDest.CUTOFF, depth=80, curve=ModCurve.EXPONENTIAL)

    xml_list = mm.to_xml_list()
    assert len(xml_list) == 1
    assert xml_list[0]["Source"] == "Velocity"
    assert xml_list[0]["Destination"] == "FilterCutoff"
    assert xml_list[0]["Depth"] == "80"
    assert xml_list[0]["Curve"] == "Exponential"
