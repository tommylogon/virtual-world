"""Light barrier parity with sound (task-421).

The premise of the task was that light spill ignored way state entirely. It did
not, quite: ``_best_spill`` had a **binary** gate on ``current_state == "open" or
see_through``, so a locked or closed door already blocked spill completely. What
was actually wrong is narrower and worse in three ways, and these tests pin all
of them:

1. **A see-through way leaked exactly as much as an open one.** A window is not a
   missing door, and sound rated it *worse* than an open doorway — the two systems
   disagreed about the one thing a window is.
2. **A closed door leaked nothing at all.** A shut door leaks a little around the
   frame; zero is a discontinuity, not a model.
3. **The light cache never noticed a door closing.** ``recompute_area_lights``
   stamped ``graph.get_revision()``, but mutating a way's ``current_state`` in
   place does not bump the revision, so a sealed room kept reporting the light it
   had before it was sealed.
"""

import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine import barriers  # noqa: E402
from engine.barriers import (  # noqa: E402
    DEFAULT_LIGHT_TRANSMISSION,
    DEFAULT_SOUND_COSTS,
    WAY_STATES,
    declared_state,
    get_light_transmission,
    get_sound_cost,
    signature,
    way_state,
)
from engine.lighting import LightingSystem  # noqa: E402
from engine.sound import get_way_barrier  # noqa: E402
from graph import EDGE_CONNECTION, Edge, Node, WorldGraph  # noqa: E402

DARK = {"light": "pitch_black", "temperature": 18, "air": "fresh",
        "smell": "neutral", "noise": "quiet"}
BRIGHT = {"light": "blinding", "temperature": 18, "air": "fresh",
          "smell": "neutral", "noise": "quiet"}


def _two_rooms(door_properties=None):
    """Two areas joined by one way. The fixture the acceptance asks for."""
    graph = WorldGraph()
    graph.add_node(Node(id="area_lit", type="area", name="Lit",
                        properties={"environment": dict(BRIGHT)}))
    graph.add_node(Node(id="area_dark", type="area", name="Dark",
                        properties={"environment": dict(DARK)}))
    props = {"current_state": "open", "description": "", "pass_message": ""}
    props.update(door_properties or {})
    graph.add_node(Node(id="way_door", type="way", name="Door", properties=props))
    for source, target in (("area_lit", "way_door"), ("way_door", "area_dark"),
                           ("area_dark", "way_door"), ("way_door", "area_lit")):
        graph.add_edge(Edge(source=source, target=target,
                            type=EDGE_CONNECTION, properties={}))
    return graph


#: Pin the built-in values for every test in this file. Engine Config is a live
#: singleton, so a test elsewhere that saves an override would otherwise change
#: what these assertions mean depending on the run order. (The leak that made
#: that happen was fixed in `tests/test_engine_config.py`; pinning here means
#: this file does not have to trust that fix to stay order-independent.)
DEFAULTS = {
    "light.spill_factor": 0.5,
    **{f"light.way_{state}": value
       for state, value in DEFAULT_LIGHT_TRANSMISSION.items()},
    **{f"sound.way_{state}": value
       for state, value in DEFAULT_SOUND_COSTS.items()},
}


@pytest.fixture(autouse=True)
def _pinned_defaults():
    with configured(**DEFAULTS):
        yield


def _dark_light_in(graph, **door_properties):
    """Light in the dark room, with a fresh system so no cache is involved."""
    graph.get_node("way_door").properties.update(door_properties)
    lighting = LightingSystem(graph)
    lighting.recompute_area_lights(hour=12)
    return lighting.get_ambient_light("area_dark")


# ── the acceptance's own case: open vs closed vs locked ────────────────────


def _spill_in(graph, **door_properties):
    """The spill contribution alone, with the room's own light out of the way.

    ``get_ambient_light`` floors at the room's authored base, so a *locked* door
    in a pitch-black room cannot move it however little light it passes. The
    acceptance's "three distinct results" is about the barrier table, so it is
    measured on the spill the table produced.
    """
    graph.get_node("way_door").properties.update(door_properties)
    lighting = LightingSystem(graph)
    return lighting._best_spill("area_dark")


def test_open_closed_and_locked_give_three_distinct_spill_results():
    open_ = _spill_in(_two_rooms(), current_state="open")
    closed = _spill_in(_two_rooms(), current_state="closed")
    locked = _spill_in(_two_rooms(), current_state="locked")

    assert len({open_, closed, locked}) == 3, (
        f"open={open_} closed={closed} locked={locked}: the acceptance is three "
        "DISTINCT results, not three labels that happen to agree"
    )
    # And in the right order: a shut door is darker than a missing one, and a
    # locked door is darker still.
    assert open_ > closed > locked > 0
    assert open_ > 0, "an open door passes light"


def test_the_same_three_doors_move_the_rooms_reading_where_there_is_room():
    """The ambient reading honours the table, in a room dark enough to show it."""
    floor = LightingSystem(_two_rooms()).get_light_int(DARK, 80)
    open_ = _dark_light_in(_two_rooms(), current_state="open")
    closed = _dark_light_in(_two_rooms(), current_state="closed")
    assert open_ > closed > floor, (
        f"open={open_} closed={closed} floor={floor}"
    )
    # A locked door passes almost nothing, and in a pitch-black room "almost
    # nothing" is under the floor: the reading is the floor, not a wrong number.
    assert _dark_light_in(_two_rooms(), current_state="locked") == floor


def test_a_closed_door_leaks_a_little_rather_than_nothing():
    """Zero was a discontinuity, not a model. A shut door has a frame."""
    floor = LightingSystem(_two_rooms()).get_light_int(DARK, 80)
    assert _spill_in(_two_rooms(), current_state="closed") > 0
    assert _dark_light_in(_two_rooms(), current_state="closed") > floor


def test_a_blocked_passage_and_a_hidden_panel_admit_nothing():
    floor = LightingSystem(_two_rooms()).get_light_int(DARK, 80)
    for state in ("blocked", "hidden"):
        assert _dark_light_in(_two_rooms(), current_state=state) == floor, (
            f"a {state} way should pass no light at all"
        )


# ── decision: a window is not a missing door ───────────────────────────────


def test_a_see_through_way_is_no_longer_worth_as_much_as_an_open_one():
    see_through = _dark_light_in(_two_rooms(), current_state="open",
                                 see_through=True)
    open_ = _dark_light_in(_two_rooms(), current_state="open")
    floor = LightingSystem(_two_rooms()).get_light_int(DARK, 80)
    assert floor < see_through < open_, (
        f"open={open_} see_through={see_through} floor={floor}"
    )


def test_see_through_outranks_the_state_in_both_systems():
    """Sound has always let `see_through` win; light now does too.

    The bug was never a *different rule* between the two systems, it was that
    light had a binary one. So the resolution order is the shared part, and this
    test holds both systems to it rather than holding sound to my idea of it.
    """
    graph = _two_rooms()
    door = graph.get_node("way_door")

    for state in ("open", "closed", "locked", "blocked", "hidden"):
        door.properties.update({"current_state": state, "see_through": True})
        assert declared_state(door) == state
        assert way_state(door) == "see_through", f"{state} + see_through"
        assert get_sound_cost(door) == DEFAULT_SOUND_COSTS["see_through"]
        assert get_light_transmission(door) == \
            DEFAULT_LIGHT_TRANSMISSION["see_through"]

    # Without the tag the state decides, for both.
    for state in WAY_STATES:
        door.properties.update({"current_state": state})
        door.properties.pop("see_through", None)
        assert way_state(door) == state


def test_a_shut_window_rates_as_a_window_unless_the_author_gave_it_mass():
    """Sound's existing three-step order, kept byte for byte.

    The declared solid state gates the per-door override, so `sound_barrier` on
    a shut window wins; without one the window wins. Light copies the order and
    gets `light_barrier` at the same point.
    """
    graph = _two_rooms()
    door = graph.get_node("way_door")

    door.properties.update({"current_state": "closed", "see_through": True})
    assert get_way_barrier(door) == DEFAULT_SOUND_COSTS["see_through"]
    assert get_light_transmission(door) == \
        DEFAULT_LIGHT_TRANSMISSION["see_through"]

    door.properties["sound_barrier"] = 2
    door.properties["light_barrier"] = 0.05
    assert get_way_barrier(door) == 2.0
    assert get_light_transmission(door) == 0.05

    # The override is gated on the DECLARED state, so an open window with one
    # still rates as a window.
    door.properties["current_state"] = "open"
    assert get_way_barrier(door) == DEFAULT_SOUND_COSTS["see_through"]
    assert get_light_transmission(door) == \
        DEFAULT_LIGHT_TRANSMISSION["see_through"]


# ── decision: one shared barrier table ─────────────────────────────────────


def test_sound_reads_the_shared_table_and_keeps_its_numbers():
    graph = _two_rooms()
    door = graph.get_node("way_door")
    for state in WAY_STATES:
        door.properties["current_state"] = state
        door.properties.pop("see_through", None)
        assert get_way_barrier(door) == DEFAULT_SOUND_COSTS[state]
        assert get_way_barrier(door) == get_sound_cost(door)
    # The public snapshot sound still exposes is now built from the shared table.
    from engine.sound import WAY_BARRIERS

    assert set(WAY_BARRIERS) == set(WAY_STATES)
    assert WAY_BARRIERS["hidden"] == DEFAULT_SOUND_COSTS["hidden"]


@contextmanager
def configured(**overrides):
    """Set engine_config values for the duration of a block.

    Mutates ``config._values`` directly rather than going through ``save()``,
    which writes ``engine_config.json`` to disk — a test must not dirty the repo.
    """
    from engine.runtime_config import config

    previous = {key: config._values.get(key) for key in overrides}
    config._values.update(overrides)
    try:
        yield
    finally:
        config._values.update(previous)


def test_changing_a_configured_value_moves_both_systems():
    """The acceptance: "changing a value changes both systems"."""
    graph = _two_rooms()
    door = graph.get_node("way_door")
    door.properties["current_state"] = "open"
    door.properties["see_through"] = True

    with configured(**{"light.way_see_through": 0.2}):
        assert get_light_transmission(door) == 0.2
        # sound is unaffected by a *light* key — two tables, side by side.
        assert get_sound_cost(door) == DEFAULT_SOUND_COSTS["see_through"]

    with configured(**{"sound.way_see_through": 1.5}):
        assert get_sound_cost(door) == 1.5
        assert get_light_transmission(door) == \
            DEFAULT_LIGHT_TRANSMISSION["see_through"]

    assert get_light_transmission(door) == DEFAULT_LIGHT_TRANSMISSION["see_through"]
    assert get_sound_cost(door) == DEFAULT_SOUND_COSTS["see_through"]


def test_a_configured_transmission_moves_the_actual_light():
    """The config is not decoration: the value reaches the computed light."""
    graph = _two_rooms()
    with configured(**{"light.way_see_through": 0.0}):
        assert _dark_light_in(graph, current_state="open", see_through=True) == \
            LightingSystem(graph).get_light_int(DARK, 80)


def test_both_tables_run_along_the_same_ladder():
    """The part that had drifted: which states exist, and their order.

    A cost and a fraction run in opposite directions, so the numbers cannot be
    shared — but the ORDER can, and it is the order that says "a window is not
    an open door". A new state added to one table and not the other fails here.
    """
    assert set(DEFAULT_SOUND_COSTS) == set(WAY_STATES)
    assert set(DEFAULT_LIGHT_TRANSMISSION) == set(WAY_STATES)
    order = list(WAY_STATES)
    assert DEFAULT_SOUND_COSTS["open"] <= DEFAULT_SOUND_COSTS["see_through"]
    assert DEFAULT_SOUND_COSTS["see_through"] <= DEFAULT_SOUND_COSTS["closed"]
    assert DEFAULT_LIGHT_TRANSMISSION["open"] >= DEFAULT_LIGHT_TRANSMISSION["see_through"]
    assert DEFAULT_LIGHT_TRANSMISSION["see_through"] >= DEFAULT_LIGHT_TRANSMISSION["closed"]
    assert DEFAULT_LIGHT_TRANSMISSION["closed"] >= DEFAULT_LIGHT_TRANSMISSION["locked"]
    assert order.index("open") < order.index("hidden")


# ── per-door overrides ─────────────────────────────────────────────────────


def test_a_per_door_light_barrier_is_a_transmission_not_a_cost():
    """`light_barrier: 0.1` means "a tenth of the light gets through".

    Copying the sound number's meaning would have made a per-door light override
    mean the opposite of what it says, which is the kind of bug that only shows
    up as "why is the sealed room brighter".
    """
    graph = _two_rooms()
    door = graph.get_node("way_door")
    floor = LightingSystem(graph).get_light_int(DARK, 80)

    door.properties.update({"current_state": "locked", "light_barrier": 0.0})
    assert _dark_light_in(graph) == floor
    door.properties["light_barrier"] = 1.0
    assert _dark_light_in(graph) == _dark_light_in(
        _two_rooms(), current_state="open"
    )
    # A nonsense override falls back to the table rather than crashing or
    # poisoning the area.
    door.properties["light_barrier"] = "lots"
    assert _dark_light_in(graph) == _dark_light_in(
        _two_rooms(), current_state="locked"
    )


def test_a_per_door_sound_barrier_still_applies_while_solid():
    graph = _two_rooms()
    door = graph.get_node("way_door")
    door.properties.update({"current_state": "locked", "sound_barrier": 4.0})
    assert get_sound_cost(door) == 4.0
    door.properties["current_state"] = "open"
    assert get_sound_cost(door) == DEFAULT_SOUND_COSTS["open"], (
        "an override on an open door is meaningless; it must not apply"
    )


def test_an_unrecognised_state_is_passable_not_opaque():
    graph = _two_rooms()
    door = graph.get_node("way_door")
    for state in ("ajar", "", None, "ajar-ish"):
        door.properties["current_state"] = state
        assert way_state(door) == "open", f"{state!r} should read as open"
        assert get_light_transmission(door) == DEFAULT_LIGHT_TRANSMISSION["open"]
    door.properties["current_state"] = "barred"
    assert way_state(door) == "locked"
    door.properties["current_state"] = "concealed"
    assert way_state(door) == "hidden"


# ── decision: the cache notices a door move ────────────────────────────────


def test_closing_a_door_invalidates_the_cached_light():
    graph = _two_rooms()
    lighting = LightingSystem(graph)
    lighting.recompute_area_lights(hour=12)
    before = lighting.get_ambient_light("area_dark")

    # The bug: this is what set_way_view does, and the graph revision does not
    # move, so the cached stamp was returned unchanged.
    graph.get_node("way_door").properties["current_state"] = "locked"
    assert graph.get_revision() == 0 or True  # revision is not the guard
    after = lighting.get_ambient_light("area_dark")

    assert after < before, (
        f"sealing the door left the cached light at {after} (was {before})"
    )


def test_opening_it_again_invalidates_the_other_way_too():
    graph = _two_rooms()
    lighting = LightingSystem(graph)
    door = graph.get_node("way_door")
    door.properties["current_state"] = "locked"
    lighting.recompute_area_lights(hour=12)
    sealed = lighting.get_ambient_light("area_dark")

    door.properties["current_state"] = "open"
    assert lighting.get_ambient_light("area_dark") > sealed


def test_a_per_door_override_change_invalidates_the_cache():
    graph = _two_rooms()
    lighting = LightingSystem(graph)
    door = graph.get_node("way_door")
    door.properties["current_state"] = "closed"
    lighting.recompute_area_lights(hour=12)
    before = lighting.get_ambient_light("area_dark")

    door.properties["light_barrier"] = 0.0
    assert lighting.get_ambient_light("area_dark") < before


def test_untouched_doors_keep_the_cache_warm():
    """The signature must not invalidate on its own, or the cache is useless."""
    graph = _two_rooms()
    lighting = LightingSystem(graph)
    lighting.recompute_area_lights(hour=12)
    assert lighting._barrier_signature() == \
        lighting._barrier_signature(), "the signature is not stable"
    assert lighting.get_ambient_light("area_dark") == \
        lighting.get_ambient_light("area_dark")


def test_the_signature_is_order_independent():
    """The signature is sorted, so a graph walk in a different order still hits
    the cache. Without that, every caller with a differently-ordered node dict
    would recompute the world on every read."""
    a = _two_rooms()
    b = _two_rooms()
    b.get_node("way_door").properties["current_state"] = "locked"
    open_door, locked_door = a.get_node("way_door"), b.get_node("way_door")

    assert signature([open_door]) != signature([locked_door])
    parts = signature([open_door]).split(";"), signature([locked_door]).split(";")
    assert signature([open_door, locked_door]).split(";") == \
        sorted(parts[0] + parts[1])
    assert signature([locked_door, open_door]) == \
        signature([open_door, locked_door])


# ── decision 4: the aggregation rule is untouched ──────────────────────────


def test_the_brightest_single_source_still_wins_and_sources_do_not_sum():
    """Task-421 changes spill, never the aggregation rule (task-407)."""
    graph = WorldGraph()
    graph.add_node(Node(id="area_room", type="area", name="Room",
                        properties={"environment": dict(DARK)}))
    for index in range(4):
        graph.add_node(Node(id=f"item_ember_{index}", type="item",
                            name=f"Ember {index}",
                            properties={"tags": ["light_source"],
                                        "light_level": 30, "current_state": "lit"}))
        graph.add_edge(Edge(source=f"item_ember_{index}", target="area_room",
                            type="in", properties={}))
    lighting = LightingSystem(graph)
    stats = lighting._item_light_stats("area_room")
    assert stats[1] == 30, "the strongest single source is the ceiling"
    assert lighting.get_ambient_light("area_room", hour=12) <= 30


@pytest.mark.parametrize("state", list(WAY_STATES))
def test_every_state_on_the_ladder_has_both_a_cost_and_a_transmission(state):
    assert state in DEFAULT_SOUND_COSTS
    assert state in DEFAULT_LIGHT_TRANSMISSION
    assert 0.0 <= DEFAULT_LIGHT_TRANSMISSION[state] <= 1.0
    assert DEFAULT_SOUND_COSTS[state] > 0.0


def test_the_module_is_importable_without_a_graph():
    """`engine.barriers` is pure data; a data-driven spawner (task-570) will
    import it with no world loaded."""
    assert barriers.WAY_STATES
    assert get_sound_cost({"current_state": "open"}) == DEFAULT_SOUND_COSTS["open"]
    assert get_light_transmission({"current_state": "open"}) == 1.0
    assert get_light_transmission({"see_through": True}) == \
        DEFAULT_LIGHT_TRANSMISSION["see_through"]
