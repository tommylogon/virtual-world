"""Wind direction (task-555): the magnitude gets a compass alongside it.

``wind`` stays "how hard"; ``wind_direction`` is "from where" (the
meteorological convention). Purely additive — nothing reads it for an effect
yet, so a world that authors nothing behaves exactly as before.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.weather_forecast import (  # noqa: E402
    WIND_DIRECTIONS, ForecastSchedule, normalize_wind_direction,
)


def test_wind_directions_use_the_compiler_compass_vocabulary():
    # One compass vocabulary, not two: the same 8 words the compiler's
    # world_compile._COMPASS_BY_SIGN uses. If either side changes, this fails.
    from engine.world_compile import _COMPASS_BY_SIGN
    assert set(WIND_DIRECTIONS) == set(_COMPASS_BY_SIGN.values())
    assert WIND_DIRECTIONS == ["north", "northeast", "east", "southeast",
                               "south", "southwest", "west", "northwest"]


def test_normalize_wind_direction():
    assert normalize_wind_direction("N") == "north"
    assert normalize_wind_direction("ne") == "northeast"
    assert normalize_wind_direction("  NorthWesterly ") == "northwest"
    assert normalize_wind_direction("north") == "north"
    # Unknown stays unknown, so a reader falls through to its own default.
    assert normalize_wind_direction("up") == ""
    assert normalize_wind_direction(None) == ""


def test_resolve_merges_wind_direction_over_the_schedule():
    sched = ForecastSchedule({"mode": "authored"})
    merged = sched.resolve(
        {"wind": "gale", "wind_direction": "north"},
        {"wind_direction": "southwest"})
    assert merged["wind_direction"] == "southwest"
    assert merged["wind"] == "gale"          # untouched
    # A schedule value survives when the override says nothing about it.
    assert sched.resolve({"wind_direction": "east"}, {})["wind_direction"] == "east"


def test_override_accepts_wind_direction():
    from virtual_world_engine import VirtualWorld
    world = VirtualWorld.__new__(VirtualWorld)   # set_forecast_override touches only this
    world.forecast_override = None
    ov = world.set_forecast_override({"wind": "gale", "wind_direction": "northeast"})
    assert ov == {"wind": "gale", "wind_direction": "northeast"}


def test_wind_direction_round_trips_through_node_serialization():
    # The value lives in area.properties.environment, which the scenario
    # serialises — so it survives save/load the same way weather/wind do.
    from graph import Node
    node = Node(id="area_test", type="area", name="Test")
    node.properties["environment"] = {"wind": "gale", "wind_direction": "north"}
    dumped = node.to_dict()
    assert dumped["properties"]["environment"]["wind_direction"] == "north"
