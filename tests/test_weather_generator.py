"""Seeded, terrain-aware weather generation (task-763).

The forecast was authored, or a single global state machine. This adds a seeded
per-area field: the same Markov chain, but its weights are conditioned on season
and terrain, its tail (the extreme kinds) is never truncated, and neighbours are
coupled so a front spreads. These tests pin the mechanism (reachability, the
cap, the coupling maths) and the wiring (a reproducible per-area field, applied
to the right areas).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine import weather_forecast as wf  # noqa: E402


# --- reachability: season and terrain may ADD an edge ----------------------

def test_season_adds_the_snow_edge_the_table_lacks():
    # No row of the default table transitions into `snowy`, so only an additive
    # season/terrain edge can make it reachable (the preview's finding a).
    base = wf.conditioned_weights("clear")
    assert base.get("snowy", 0) == 0
    winter = wf.conditioned_weights("clear", season="winter")
    assert winter["snowy"] > 0, "winter cannot produce snow"
    summer = wf.conditioned_weights("clear", season="summer")
    assert summer.get("snowy", 0) == 0, "summer should suppress snow"


def test_painted_climate_biases_the_weather():
    # task-557's compiled `climate` is a generator input alongside biome tags.
    def weighted(climate, state, season=None):
        return wf.conditioned_weights(
            "clear", season=season,
            terrain=wf.terrain_weather_bias([], climate)).get(state, 0)

    assert weighted("arctic", "snowy", "winter") > weighted("temperate", "snowy", "winter")
    assert weighted("arid", "snowy") == 0                 # arid cannot snow
    assert weighted("arid", "heatwave") > wf.EXTREME_BASE_WEIGHT
    assert weighted("tropical", "rainy") > weighted("temperate", "rainy")
    assert wf.terrain_weather_bias([], None) == {}        # unpainted is no bias


def test_terrain_bias_reads_and_sums_tags():
    assert wf.terrain_weather_bias(["alpine"])["snowy"] > 0
    assert wf.terrain_weather_bias(["desert"])["clear"] > 0
    coastline = wf.terrain_weather_bias(["coast", "forest"])
    assert coastline["foggy"] >= 3 and coastline["rainy"] >= 2
    assert wf.terrain_weather_bias(["nothing_here"]) == {}


def test_negative_bias_suppresses_but_never_inverts():
    # A summer desert should not be *more* likely to rain than the base table.
    base = wf.conditioned_weights("cloudy", season="summer")
    desert = wf.conditioned_weights("cloudy", season="summer",
                                    terrain=wf.terrain_weather_bias(["desert"]))
    assert desert["rainy"] <= base["rainy"]
    assert all(weight >= 0 for weight in desert.values())


# --- the extreme tail: defined by the registry kind, never truncated -------

def test_extreme_kind_is_reachable_and_capped():
    # `blizzard` is real library content (task-763), kind: extreme.
    weights = wf.conditioned_weights("clear")
    assert 0 < weights["blizzard"] <= wf.EXTREME_CAP
    # Season and terrain may raise it, but never past the cap.
    raised = wf.conditioned_weights("clear", season="winter", terrain={"blizzard": 99})
    assert raised["blizzard"] == wf.EXTREME_CAP


def test_season_and_terrain_gate_the_extremes():
    # The tail keeps extremes *reachable*, not nonsensical: a summer blizzard and
    # a desert blizzard are suppressed to zero, while the fitting extremes rise.
    assert wf.conditioned_weights("clear", season="summer").get("blizzard", 0) == 0
    assert wf.conditioned_weights(
        "clear", season="summer",
        terrain=wf.terrain_weather_bias(["desert"])).get("blizzard", 0) == 0
    desert_summer = wf.conditioned_weights(
        "clear", season="summer", terrain=wf.terrain_weather_bias(["desert"]))
    assert desert_summer["heatwave"] > wf.EXTREME_BASE_WEIGHT
    alpine_winter = wf.conditioned_weights(
        "clear", season="winter", terrain=wf.terrain_weather_bias(["alpine"]))
    assert alpine_winter["blizzard"] > wf.EXTREME_BASE_WEIGHT
    assert alpine_winter.get("heatwave", 0) == 0


def test_a_snow_tagged_extreme_accumulates_snow():
    assert wf.weather_produces_snow("snowy") is True
    assert wf.weather_produces_snow("blizzard") is True   # tag-driven, not hardcoded
    assert wf.weather_produces_snow("thunderstorm") is False
    assert wf.weather_produces_snow("clear") is False
    assert wf.advance_snow_depth(0, "blizzard", 60) > 0


def test_precipitation_scales_snow_accumulation():
    light = wf.advance_snow_depth(0, "snowy", 60, precipitation=1.0)
    heavy = wf.advance_snow_depth(0, "snowy", 60, precipitation=10.0)
    assert 0 < light < heavy
    # Without a precipitation argument the flat default rate applies (task-556).
    assert wf.advance_snow_depth(0, "snowy", 60) == wf.SNOW_ACCUM_CM_PER_HOUR


def test_the_extreme_records_are_registered():
    for rid in ("blizzard", "thunderstorm", "heatwave", "cold_snap"):
        assert wf.weather_types().get(rid), f"{rid} missing from the weather library"
        assert wf.weather_state_kind(rid) == "extreme"
    assert wf.weather_tuning("blizzard")["precipitation"] > 0


def test_roll_never_truncates_the_tail():
    weights = {"clear": 100.0, "blizzard": 1.0}
    rng = wf.random.Random(0)
    seen = {wf.roll_from_weights(rng, weights, "clear") for _ in range(500)}
    assert "blizzard" in seen, "a rare tail state never rolls"


# --- the field: seeded, per-area, neighbour-coupled ------------------------

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


def test_a_generated_field_is_per_area_and_reproducible():
    world = _world()
    a = world._weather_field_for_day("winter")
    ids = {world.area_node_id(n) for n in ("Glade", "Peak", "Dune")}
    assert set(a) == ids                       # one state per open-sky area
    assert all(state in wf.WEATHER_STATES for state in a.values())

    world._weather_field = {}
    world._weather_field_day = None
    b = world._weather_field_for_day("winter")
    assert a == b, "same seed and day must reproduce the field"


def test_neighbour_coupling_biases_toward_a_neighbour_state():
    # The coupling math: a state a neighbour is in gets a bonus, so a front can
    # spread. This is the mechanism the field rollout uses for `neighbours`.
    plain = wf.conditioned_weights("clear", season="winter")
    coupled = wf.conditioned_weights("clear", season="winter",
                                     coupling={"snowy": 20})
    assert coupled["snowy"] > plain["snowy"]

    # And it changes the roll: a neighbour of an all-snowy map snows more often.
    def snowy_at_glade(bonus):
        world = _world()
        areas, neighbours, _climates = world._area_terrain_index()
        glade = world.area_node_id("Glade")
        prev = {area_id: "snowy" for area_id in areas}
        prev[glade] = "clear"          # Glade is the one we watch, neighbours snowy
        count = 0
        for seed in range(40):
            field = wf.generate_weather_field(
                prev, areas, neighbours, season="winter", seed=seed, day=1,
                coupling_bonus=bonus)
            count += field[glade] == "snowy"
        return count

    assert snowy_at_glade(6.0) > snowy_at_glade(0.0)


def test_snowy_is_reachable_over_a_winter_month():
    world = _world()
    areas, neighbours, _climates = world._area_terrain_index()
    states = set()
    prev = {}
    for day in range(1, 31):
        prev = wf.generate_weather_field(prev, areas, neighbours,
                                         season="winter", seed=7, day=day)
        states |= set(prev.values())
    assert "snowy" in states, "a winter month never produced snow"


# --- ordered overrides: area > date > heuristic ---------------------------

def test_field_overrides_precedence():
    field = {"a": "clear", "b": "clear", "c": "cloudy"}
    # A date override sweeps every area for that day...
    dated = wf.apply_field_overrides(field, date_overrides={"5": "stormy"}, day=5)
    assert set(dated.values()) == {"stormy"}
    # ...and an area override pins one area over it.
    both = wf.apply_field_overrides(
        field, area_overrides={"b": "clear"}, date_overrides={"5": "stormy"}, day=5)
    assert both["a"] == "stormy" and both["b"] == "clear" and both["c"] == "stormy"


# --- wiring: the field reaches the areas' environment ----------------------

def test_generated_field_weather_lands_on_each_area():
    world = _world()
    eff = {"weather": "clear"}          # the global fallback the field overrides
    field = {world.area_node_id("Peak"): "snowy",
             world.area_node_id("Dune"): "clear",
             world.area_node_id("Glade"): "rainy"}
    world._apply_forecast_env(eff, field=field)
    envs = {n: world.graph.get_node(world.area_node_id(n)).properties["environment"]
            for n in ("Glade", "Peak", "Dune")}
    assert envs["Peak"]["weather"] == "snowy"
    assert envs["Glade"]["weather"] == "rainy"
    assert envs["Dune"]["weather"] == "clear"
    # The state's tuning landed with it: snow is breezy and dry, and nudges the
    # temperature below a clear area at the same hour.
    assert envs["Peak"]["wind"] == "breeze"
    assert envs["Peak"]["humidity"] == "dry"
    assert envs["Peak"]["temperature"] < envs["Dune"]["temperature"]
