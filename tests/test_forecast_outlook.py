"""The 7-day per-area forecast outlook (task-762).

`weather_outlook` rolls the same seeded `generate_weather_field` the live sim
uses forward from the current day, one day at a time, and must do so without
advancing the world. These tests pin the projection (one state per open-sky area
per day, reproducible, dates advancing) and, above all, that it is a pure read:
the live `_weather_field` is never written and the clock does not move.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine import weather_forecast as wf  # noqa: E402


def _world():
    from area import Area
    from virtual_world_engine import VirtualWorld
    world = VirtualWorld()
    world.time_per_tick_minutes = 60
    for name, tags in (("Glade", ["exterior", "forest"]),
                       ("Peak", ["exterior", "alpine"]),
                       ("Dune", ["exterior", "desert"])):
        world.movement.add_area(Area(name, "", tags))
        node = world.graph.get_node(world.area_node_id(name))
        node.properties["tags"] = tags
    world.movement.connect_areas("Glade", "Peak", "north", "south", state="open")
    world.movement.connect_areas("Peak", "Dune", "east", "west", state="open")
    world.forecast_schedule = {
        "mode": "generated", "seed": 3, "granularity": "hourly",
        "current_state": "clear", "transition_interval": 1,
        "transition_table": {}, "entries": [],
    }
    world._forecast_sched_obj = None
    return world


def _ids(world):
    return {world.area_node_id(n) for n in ("Glade", "Peak", "Dune")}


def test_outlook_yields_one_state_per_area_for_each_day():
    world = _world()
    out = world.weather_outlook(7)
    assert out["generated"] is True
    assert len(out["days"]) == 7
    assert [d["offset"] for d in out["days"]] == list(range(7))
    for day in out["days"]:
        assert set(day["states"]) == _ids(world)
        assert all(s in wf.WEATHER_STATES for s in day["states"].values())
        assert set(day["temps"]) == _ids(world)


def test_outlook_is_seeded_and_reproducible():
    world = _world()
    a = world.weather_outlook(7)
    b = world.weather_outlook(7)
    assert [d["states"] for d in a["days"]] == [d["states"] for d in b["days"]]


def test_outlook_never_writes_the_live_field_or_the_clock():
    world = _world()
    world._weather_field = {"sentinel": "rainy"}   # a stand-in for the live day
    world._weather_field_day = 1
    tick_before = world.time_ticks
    world.weather_outlook(7)
    # The live field is the seed, not an output: it and the cache key are intact,
    # and the clock never moved.
    assert world._weather_field == {"sentinel": "rainy"}
    assert world._weather_field_day == 1
    assert world.time_ticks == tick_before


def test_outlook_honours_the_ordered_overrides():
    world = _world()
    world.forecast_schedule["date_overrides"] = {"2": "snowy"}
    world.forecast_schedule["area_overrides"] = {world.area_node_id("Glade"): "clear"}
    out = world.weather_outlook(3)
    day2 = out["days"][1]
    # Date override sweeps every area for day 2, then the area override pins Glade.
    assert day2["states"][world.area_node_id("Peak")] == "snowy"
    assert day2["states"][world.area_node_id("Dune")] == "snowy"
    assert day2["states"][world.area_node_id("Glade")] == "clear"


def test_outlook_temperature_follows_the_state_tuning():
    world = _world()
    world.forecast_schedule["date_overrides"] = {"1": "clear", "2": "snowy"}
    out = world.weather_outlook(2)
    glade = world.area_node_id("Glade")
    # Same area, same base: a snowy day is colder than a clear one by the
    # difference in the states' temperature_mod (-3 vs +1).
    assert out["days"][1]["temps"][glade] < out["days"][0]["temps"][glade]


def test_outlook_dates_advance_from_today():
    world = _world()
    world.calendar_config = {"days_per_month": 3, "months_per_year": 12}
    out = world.weather_outlook(4)
    assert [d["day"] for d in out["days"]] == [1, 2, 3, 4]
    assert [d["day_of_month"] for d in out["days"]] == [1, 2, 3, 1]
    assert [d["month"] for d in out["days"]] == [1, 1, 1, 2]
    assert out["days"][0]["moon"]["name"]          # a moon phase for each day
    assert out["start_day"] == 1


def test_outlook_areas_are_named_and_limited_to_open_sky():
    world = _world()
    out = world.weather_outlook(1)
    names = {a["name"] for a in out["areas"]}
    assert names == {"Glade", "Peak", "Dune"}
    assert set(a["id"] for a in out["areas"]) == _ids(world)


def test_outlook_reports_a_non_generated_mode_as_a_preview():
    world = _world()
    world.forecast_schedule["mode"] = "authored"
    out = world.weather_outlook(2)
    assert out["generated"] is False
    assert out["mode"] == "authored"
