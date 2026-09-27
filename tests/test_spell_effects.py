"""Lyrie's spellbook (task-391): the five new spell effects and their durations.

Covers ``polymorph_target``, ``create_illusory_companion``, ``broadcast_emotion``,
``bind_companion`` and ``reveal_hidden`` from ``engine/effect_handlers/spells.py``,
plus the turn sweep in ``engine/companions.py`` that makes their durations real.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph import Node, Edge, EDGE_IN, EDGE_CONNECTION
from engine.node_ids import NodeIDHelper
from virtual_world_engine import VirtualWorld

AREA = "Spell Clearing"
NEXT = "Spell Grove"


def _world():
    w = VirtualWorld()
    _add_area(w, AREA)
    _add_area(w, NEXT)
    w.set_player_area(next(iter(w.player_manager.players)), AREA)
    return w


def _add_area(world, name, env=None):
    node = Node(id=NodeIDHelper.area_node_id(name), type="area", name=name,
                properties={"description": "", "environment": env or {}})
    world.graph.add_node(node)
    return node


def _exec(world, etype, params, context=None, item_node=None):
    return world.triggers._effects.execute(etype, params, context or {},
                                           item_node=item_node, game_state=world)


def _add_way(world, area_a, area_b, way_id="way_spell_link", state="open"):
    """Connect two areas through a way node, exactly as the graph really stores it.

    Both directions for both areas — four ``EDGE_CONNECTION`` edges, matching
    what ``spawn_way`` produces and what ``engine.area_statuses._open_neighbours``
    assumes when it looks a way up by its areas.
    """
    a_id = NodeIDHelper.area_node_id(area_a)
    b_id = NodeIDHelper.area_node_id(area_b)
    way = Node(id=way_id, type="way", name="Spell Way",
               properties={"name": "Spell Way", "current_state": state})
    world.graph.add_node(way)
    for area_id in (a_id, b_id):
        world.graph.add_edge(Edge(source=area_id, target=way.id, type=EDGE_CONNECTION))
        world.graph.add_edge(Edge(source=way.id, target=area_id, type=EDGE_CONNECTION))
    return way


def _add_item(world, area, name, item_id=None, **props):
    area_id = NodeIDHelper.area_node_id(area)
    node_id = item_id or f"item_{name.lower().replace(' ', '_')}"
    n = Node(id=node_id, type="item", name=name,
             properties={"name": name, "tags": [], "uses": -1, **props})
    world.graph.add_node(n)
    world.graph.add_edge(Edge(source=n.id, target=area_id, type=EDGE_IN))
    return n


def _place(world, name, area):
    from player import Player
    p = Player(name)
    world.add_player(p)
    world.set_player_area(name, area)
    return p


# ─────────────────────────── polymorph_target ───────────────────────────

def test_polymorph_transforms_and_reverts_exactly():
    """A cast must restore the *original* state, not guess at it."""
    world = _world()
    node = _add_item(world, AREA, "Broken Cart Wheel",
                     current_state="damaged", uses=3)

    params = {"target": "Broken Cart Wheel", "target_template": "chicken"}
    out = _exec(world, "polymorph_target", params, {})
    assert any("chicken" in line.lower() for line in out), out
    assert node.name.lower() == "chicken"
    assert "polymorphed" in node.properties["tags"]

    # The pre-cast state was captured, not overwritten.
    snap = node.properties["_polymorph_snapshot"]
    assert snap["name"] == "Broken Cart Wheel"
    assert snap["properties"]["current_state"] == "damaged"

    _exec(world, "polymorph_target", {"target": "Broken Cart Wheel",
                                               "revert": True}, {})
    assert node.name == "Broken Cart Wheel"
    assert node.properties["current_state"] == "damaged"
    assert "polymorphed" not in node.properties["tags"]
    assert "_polymorph_snapshot" not in node.properties


def test_polymorph_refuses_unknown_template_without_corrupting_node():
    """A missing template must fail clean — a half-applied polymorph strands the
    node in a form nothing can revert, because no snapshot was taken."""
    world = _world()
    node = _add_item(world, AREA, "Solid Rock", current_state="normal")

    out = _exec(world, "polymorph_target",
        {"target": "Solid Rock", "target_template": "no_such_template"}, {})
    assert out, "should explain the failure"
    assert node.name == "Solid Rock"
    assert node.properties["current_state"] == "normal"
    assert "_polymorph_snapshot" not in node.properties


def test_second_cast_keeps_the_true_original_for_revert():
    """Re-casting mid-duration must not overwrite the snapshot with the first
    form, or revert would restore a chicken instead of the cart wheel."""
    world = _world()
    node = _add_item(world, AREA, "Cart Wheel", current_state="damaged")

    _exec(world, "polymorph_target",
                          {"target": "Cart Wheel", "target_template": "chicken"},
                          {})
    _exec(world, "polymorph_target",
                          {"target": "Cart Wheel", "target_template": "chicken"},
                          {})
    _exec(world, "polymorph_target",
                          {"target": "Cart Wheel", "revert": True}, {})
    assert node.name == "Cart Wheel"
    assert node.properties["current_state"] == "damaged"


# ────────────────────── create_illusory_companion ──────────────────────

def test_illusory_companion_spawns_inert_and_expires():
    """A conjured thing must not become an actor, and must not live forever."""
    world = _world()
    _place(world, "Lyrie", AREA)
    world.player_manager.set_active_player("Lyrie")

    _exec(world, "create_illusory_companion",
                          {"character_id": "fluffy", "name": "Fluffy",
                           "duration": 5}, {})

    spawned = [p for p in world.players.values()
               if getattr(p, "illusory", False)]
    assert len(spawned) == 1, "expected exactly one conjured companion"
    fluffy = spawned[0]
    assert fluffy.name == "Fluffy"
    assert fluffy.autonomy is False, "a conjured object must never act"
    assert fluffy.current_area == AREA

    # Still there before the duration elapses.
    from engine.companions import process_companions
    world.time_ticks += 2
    process_companions(world)
    assert any(getattr(p, "illusory", False) for p in world.players.values())

    world.time_ticks += 10
    process_companions(world)
    assert not any(getattr(p, "illusory", False) for p in world.players.values()), \
        "companion should have expired and been removed from the roster"


def test_illusory_companion_follows_nothing_when_caster_is_gone():
    """Caster despawns -> the conjuration is orphaned, not left behind forever."""
    world = _world()
    _place(world, "Lyrie", AREA)
    world.player_manager.set_active_player("Lyrie")
    _exec(world, "create_illusory_companion",
                          {"character_id": "fluffy", "duration": 1000,
                           "vanish_on_area_leave": False}, {})
    assert any(getattr(p, "illusory", False) for p in world.players.values())


# ─────────────────────────── broadcast_emotion ──────────────────────────

def test_broadcast_emotion_hits_neighbours_but_not_caster_by_default():
    world = _world()
    far_area = "Spell Hollow"
    _add_area(world, far_area)
    _add_way(world, AREA, NEXT, way_id="way_spell_link_1")
    _add_way(world, NEXT, far_area, way_id="way_spell_link_2")
    lyrie = _place(world, "Lyrie", AREA)
    bystander = _place(world, "Bystander", AREA)
    neighbour = _place(world, "Neighbour", NEXT)
    distant = _place(world, "Distant", far_area)

    world.player_manager.set_active_player("Lyrie")
    before = dict(bystander.emotions_map())
    neighbour_before = dict(neighbour.emotions_map())
    distant_before = dict(distant.emotions_map())
    caster_before = dict(lyrie.emotions_map())

    out = _exec(world, "broadcast_emotion",
        {"spikes": {"calm": 20.0}, "radius_areas": 1}, {})
    assert out, "should narrate the broadcast"

    # Same area and one hop out are both inside radius_areas=1.
    assert bystander.emotions_map()["calm"] > before["calm"]
    assert neighbour.emotions_map()["calm"] > neighbour_before["calm"]
    # Two hops out is beyond the radius.
    assert distant.emotions_map()["calm"] == distant_before["calm"], \
        "radius_areas=1 must not reach an area two hops away"
    # Caster excluded by default.
    assert lyrie.emotions_map()["calm"] == caster_before["calm"]


def test_broadcast_emotion_tolerates_unknown_emotion_keys():
    """The affect vocabulary is in flux (a planned reword), so an unknown key
    must not take the whole cast down with it."""
    world = _world()
    _place(world, "Lyrie", AREA)
    _place(world, "Bystander", AREA)
    world.player_manager.set_active_player("Lyrie")

    out = _exec(world, "broadcast_emotion",
        {"spikes": {"no_such_emotion": 10.0, "calm": 15.0}}, {})
    assert out, "unknown keys must not raise"


# ──────────────────────────── bind_companion ────────────────────────────

def test_bound_companion_follows_its_owner():
    world = _world()
    _add_way(world, AREA, NEXT)
    _place(world, "Lyrie", AREA)
    world.player_manager.set_active_player("Lyrie")
    ember = _add_item(world, AREA, "Ember", item_id="item_test_ember")

    _exec(world, "bind_companion",
                          {"node_id": ember.id, "duration": 100}, {})
    assert ember.properties["companion"]["owner"] == "Lyrie"

    from engine.companions import process_companions
    world.set_player_area("Lyrie", NEXT)
    process_companions(world)

    holders = [e.target for e in world.graph.get_edges_for_source(ember.id, EDGE_IN)]
    owner_node = world.player_manager.get_player_node_id("Lyrie")
    assert owner_node in holders, "a bound companion should travel with its owner"


def test_companion_bond_expires():
    world = _world()
    _place(world, "Lyrie", AREA)
    world.player_manager.set_active_player("Lyrie")
    ember = _add_item(world, AREA, "Ember", item_id="item_exp_ember")
    _exec(world, "bind_companion",
                          {"node_id": ember.id, "duration": 2}, {})

    from engine.companions import process_companions
    world.time_ticks += 5
    process_companions(world)
    assert "companion" not in ember.properties
    assert "companion" not in ember.properties.get("tags", [])


# ──────────────────────────── reveal_hidden ────────────────────────────

def test_reveal_hidden_sweeps_a_radius_and_re_hides_exactly():
    """A duration must put each node back the way the reveal found it, and must
    not touch anything that was never hidden in the first place."""
    world = _world()
    _add_way(world, AREA, NEXT)
    _place(world, "Lyrie", AREA)
    world.player_manager.set_active_player("Lyrie")

    secret = _add_item(world, AREA, "Buried Cache", current_state="hidden")
    far_secret = _add_item(world, NEXT, "Grove Cache", current_state="hidden")
    beyond = _add_item(world, AREA, "Pebble", current_state="normal")

    _exec(world, "reveal_hidden", {"radius_areas": 1, "duration": 3}, {})
    assert secret.properties["current_state"] == "normal"
    assert far_secret.properties["current_state"] == "normal", \
        "one hop out is still inside radius_areas=1"
    assert beyond.properties["current_state"] == "normal", \
        "an already-visible node is not a reveal and must be left alone"
    assert "_reveal_expires_tick" not in beyond.properties

    from engine.companions import process_companions
    world.time_ticks += 5
    process_companions(world)
    assert secret.properties["current_state"] == "hidden", \
        "a hidden thing must go back to hidden"
    assert far_secret.properties["current_state"] == "hidden"
    assert "_reveal_previous_state" not in secret.properties, \
        "the bookkeeping must not outlive the reveal"


# ─────────────────────── library items smoke test ──────────────────────

def test_all_fifteen_spell_items_load_and_only_use_known_effects():
    """The spellbook must not reference an effect type the engine lacks."""
    import json
    from engine.triggers.constants import EFFECT_TYPES, TRIGGER_TYPES

    ids = [
        "hearth_ember", "tongue_of_the_little_folk", "whisper_of_green",
        "bloom_of_the_well", "transfigure_poultry", "conjure_fluffy",
        "sirens_lullaby", "spark_of_the_baking_incident",
        "apology_to_chickens", "vincents_embrace", "fountain_of_blossoms",
        "ember_companion", "mending_touch", "glimpse_of_the_lost_path",
        "hearth_ward",
    ]
    base = Path(__file__).parent.parent / "data" / "library" / "items"
    for item_id in ids:
        path = base / f"{item_id}.json"
        assert path.exists(), f"missing library item {item_id}"
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        for trig in data.get("triggers", []):
            raw = trig.get("trigger_type")
            types = raw if isinstance(raw, list) else [raw]
            for t in types:
                assert t in TRIGGER_TYPES, f"{item_id}: unknown trigger {t}"
            for eff in trig.get("effects", []):
                assert eff.get("type") in EFFECT_TYPES, \
                    f"{item_id}: unknown effect {eff.get('type')}"
