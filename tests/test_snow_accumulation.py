"""Snow reaches the world (task-556).

Snowy weather used to be a label with three readers and no consequence: it dimmed
the light and raised a Perception DC. It now settles a **depth** on an exterior
area, and that depth - not the word "snowy" - is what movement and forage read.
These tests pin the mechanism (how depth advances and decays, and where it is
written) and the wiring (the forecast tick writes it; a world that never snows is
unchanged).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.weather_forecast import (  # noqa: E402
    SNOW_ACCUM_CM_PER_HOUR, SNOW_DEEP_CM, SNOW_LIGHT_CM, SNOW_MAX_CM,
    SNOW_MELT_CM_PER_HOUR, advance_snow_depth, snow_depth_prose,
    snow_forage_dc_penalty, snow_movement_energy,
)


# --- the mechanism ---------------------------------------------------------

def test_snowy_accumulates_and_anything_else_melts():
    assert advance_snow_depth(0, "snowy", 60) == SNOW_ACCUM_CM_PER_HOUR
    # Round-trip: one hour of snow, one hour of clear is a partial thaw.
    depth = advance_snow_depth(0, "snowy", 60)
    depth = advance_snow_depth(depth, "clear", 60)
    assert depth == SNOW_ACCUM_CM_PER_HOUR - SNOW_MELT_CM_PER_HOUR
    # rain melts too: it is not the snow state, so it is decay.
    assert advance_snow_depth(10, "rainy", 60) == 10 - SNOW_MELT_CM_PER_HOUR


def test_melt_never_goes_negative_and_accumulation_is_capped():
    assert advance_snow_depth(0.5, "clear", 600) == 0.0
    assert advance_snow_depth(0, "snowy", 10 ** 6) == SNOW_MAX_CM


def test_unknown_weather_words_melt_rather_than_snow():
    # normalize_weather maps aliases; an unrecognised word is not snow.
    assert advance_snow_depth(5, "blizzard", 60) > 5          # snow-tagged extreme
    assert advance_snow_depth(5, "wat", 60) < 5


def test_movement_energy_scales_with_depth():
    assert snow_movement_energy(0) == 0
    assert snow_movement_energy(SNOW_LIGHT_CM - 0.1) == 0
    assert snow_movement_energy(SNOW_LIGHT_CM) == 1
    assert snow_movement_energy(SNOW_DEEP_CM) == 3
    assert snow_movement_energy(SNOW_MAX_CM) == 6
    assert snow_movement_energy(None) == 0


def test_forage_penalty_scales_with_depth():
    assert snow_forage_dc_penalty(0) == 0
    assert snow_forage_dc_penalty(SNOW_LIGHT_CM) == 2
    assert snow_forage_dc_penalty(SNOW_DEEP_CM) == 4
    assert snow_forage_dc_penalty(SNOW_MAX_CM) == 6
    assert snow_forage_dc_penalty("junk") == 0


def test_depth_prose_only_speaks_when_there_is_snow():
    assert snow_depth_prose(0) == ""
    assert snow_depth_prose(0.5) == ""
    assert "crust" in snow_depth_prose(SNOW_LIGHT_CM)
    assert "inches" in snow_depth_prose(SNOW_DEEP_CM)
    assert "knee-high" in snow_depth_prose(SNOW_MAX_CM)


# --- the wiring: the forecast tick writes depth on open-sky areas ----------

def _world(weather, tags, minutes=60):
    """A bare VirtualWorld with one area, and the forecast applied once."""
    from graph import Node, WorldGraph
    from virtual_world_engine import VirtualWorld

    world = VirtualWorld.__new__(VirtualWorld)
    graph = WorldGraph()
    area = Node(id="area_glade", type="area", name="Glade")
    area.properties["tags"] = tags
    graph.add_node(area)
    world.graph = graph
    world.time_per_tick_minutes = minutes
    world.world_state = {}
    world.current_season = lambda: "winter"
    world._apply_forecast_env({"weather": weather})
    return area


def _apply(area, weather, minutes):
    """Re-apply the forecast to an existing area node at a given cadence."""
    from graph import WorldGraph
    from virtual_world_engine import VirtualWorld

    world = VirtualWorld.__new__(VirtualWorld)
    graph = WorldGraph()
    graph.add_node(area)
    world.graph = graph
    world.time_per_tick_minutes = minutes
    world.world_state = {}
    world.current_season = lambda: "winter"
    world._apply_forecast_env({"weather": weather})
    return area


def test_snowy_weather_settles_depth_on_an_exterior_area():
    area = _world("snowy", ["outdoor"])
    env = area.properties["environment"]
    assert env["snow_depth"] == SNOW_ACCUM_CM_PER_HOUR


def test_snow_does_not_settle_indoors():
    area = _world("snowy", ["interior"])
    assert "snow_depth" not in area.properties.get("environment", {})


def test_clearing_weather_decays_snow_before_it_clears():
    # Two hours of settled snow, then one clear hour: lower, not gone.
    area = _world("snowy", ["exterior"], minutes=120)
    depth = area.properties["environment"]["snow_depth"]
    _apply(area, "clear", 60)
    assert area.properties["environment"]["snow_depth"] == depth - SNOW_MELT_CM_PER_HOUR
    assert area.properties["environment"]["snow_depth"] > 0


def test_a_thaw_removes_the_key_when_depth_hits_zero():
    area = _world("snowy", ["exterior"], minutes=60)   # 3.0 cm
    assert area.properties["environment"]["snow_depth"] > 0
    _apply(area, "clear", 600)                          # long clear -> melted
    assert "snow_depth" not in area.properties["environment"]


def test_a_clear_world_gains_no_snow_key_at_all():
    area = _world("clear", ["exterior"])
    assert "snow_depth" not in area.properties["environment"]


def test_snow_depth_round_trips_through_node_serialization():
    area = _world("snowy", ["outdoor"])
    dumped = area.to_dict()
    assert dumped["properties"]["environment"]["snow_depth"] == SNOW_ACCUM_CM_PER_HOUR


# --- the readers actually consult the depth --------------------------------

def test_snow_deepens_the_forage_check(monkeypatch):
    """The depth, not the weather word, raises the search DC (task-556)."""
    import engine.foraging as foraging
    from area import Area
    from virtual_world_engine import VirtualWorld

    world = VirtualWorld()
    world.movement.add_area(Area("Snowfield", "A field.", ["field", "exterior"]))
    world.name_matcher._set_player_area(world.active_player, "Snowfield")
    node = world.graph.get_node(world.area_node_id("Snowfield"))
    # add_area does not copy Area.tags onto the node; a foragable area needs them.
    node.properties["tags"] = ["field", "exterior"]
    env = node.properties.setdefault("environment", {})

    seen = {}

    def fake_check(gs, player, skill_key, dc):
        seen["dc"] = dc
        return False, 0            # fail: no spawn, but the DC is captured

    monkeypatch.setattr(foraging, "_search_check", fake_check)

    env["snow_depth"] = 20.0       # >= SNOW_DEEP_CM -> +4
    foraging.find_or_spawn(world, world.player, "Snowfield", skill="survival")
    snowy_dc = seen["dc"]

    env["snow_depth"] = 0.0
    foraging.find_or_spawn(world, world.player, "Snowfield", skill="survival")
    assert seen["dc"] == snowy_dc - 4


def test_deep_snow_costs_extra_move_energy():
    """Crossing into deep snow spends more energy than clear ground (task-556)."""
    from area import Area
    from virtual_world_engine import VirtualWorld

    def move_energy(snow):
        world = VirtualWorld()
        world.movement.add_area(Area("Room A", "First.", ["exterior"]))
        world.movement.add_area(Area("Room B", "Cold.", ["exterior"]))
        world.movement.connect_areas("Room A", "Room B", "north", "south", state="open")
        world.name_matcher._set_player_area(world.active_player, "Room A")
        world.player.vitals["Energy"] = 100
        if snow is not None:
            node = world.graph.get_node(world.area_node_id("Room B"))
            node.properties.setdefault("environment", {})["snow_depth"] = snow
        world.move_to_area("north")
        return world.player.vitals["Energy"]

    clear = move_energy(None)
    deep = move_energy(40)         # >= SNOW_BURIED_CM -> 6 energy
    assert clear - deep >= 6
