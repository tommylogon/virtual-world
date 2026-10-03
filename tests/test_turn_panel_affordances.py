"""Regression tests for the human-turn panel affordance gates.

Each test pins ONE mechanism at the layer it lives in, so a failure names
the layer instead of "the panel changed".

- room_perception: presence is per NODE. ``get_edges_for_target`` returns a
  direct ``in`` edge *and* the spatial expansion (a character ``at`` a surface
  in the room), so an edge-wise append listed three people as six.
- _get_available_actions: ``drop`` is a capability every takeable declares,
  so it is an affordance only once the actor actually holds the item. The
  toggle label reads the engine's lit/unlit vocabulary, and the toggleable tag
  is the gate ToggleableItems.toggle_item_status actually enforces.
- scene_snapshot: per-person activity (gates Wake) and the held list (gates
  Release), plus prevent_close on a way (gates Close, which
  movement._open_passage_block refuses).
"""
import pytest
from unittest.mock import MagicMock

from graph import (
    WorldGraph,
    Node,
    Edge,
    EDGE_AT,
    EDGE_IN,
    EDGE_TRIGGERS,
    EDGE_CONNECTION,
)
from player import Player
from engine.room_perception import characters_in_area, visible_area_items
from engine.scene_snapshot import build_scene


# ── presence is per node ────────────────────────────────────────────

def _area(g, area_id="area_room", name="Room"):
    g.add_node(Node(id=area_id, type="area", name=name,
                    properties={"environment": {"light": 80}}))


def test_character_at_a_surface_in_the_room_is_listed_once():
    """`in area` plus `at surface` is one presence, not two."""
    g = WorldGraph()
    _area(g)
    g.add_node(Node(id="player_mara", type="character", name="mara",
                    properties={"description": "A guard."}))
    g.add_node(Node(id="item_bench", type="item", name="bench",
                    properties={"current_state": "normal"}))
    g.add_edge(Edge(source="player_mara", target="area_room", type=EDGE_IN))
    g.add_edge(Edge(source="item_bench", target="area_room", type=EDGE_IN))
    # the spatial edge the expansion adds: standing at the bench
    g.add_edge(Edge(source="player_mara", target="item_bench", type=EDGE_AT))

    assert [n.name for n in characters_in_area(g, "area_room")] == ["mara"]


def test_item_in_the_room_and_on_a_table_in_it_is_listed_once():
    g = WorldGraph()
    _area(g)
    g.add_node(Node(id="item_table", type="item", name="table",
                    properties={"current_state": "normal"}))
    g.add_node(Node(id="item_lamp", type="item", name="lamp",
                    properties={"current_state": "normal"}))
    g.add_edge(Edge(source="item_table", target="area_room", type=EDGE_IN))
    g.add_edge(Edge(source="item_lamp", target="area_table", type=EDGE_AT))

    assert [n.name for n in visible_area_items(g, "area_room")] == ["table"]


# ── affordance gates ────────────────────────────────────────────────

def _system():
    """A real TriggerSystem over a real graph — _get_available_actions reads
    both the node's properties and its `triggers` edges, so a stub would skip
    the mechanism that decides whether the toggle verb appears at all."""
    from engine.trigger_system import TriggerSystem
    g = WorldGraph()
    g.add_node(Node(id="area_room", type="area", name="Room",
                    properties={"environment": {"light": 80}}))
    return TriggerSystem(g, MagicMock(), MagicMock()), g


def _labels(system, node, **kw):
    return [e["label"] for e in system._get_available_actions(node, **kw)]


def _item(g, name="matches", tags=("light_source",), actions="examine,take,drop",
          state=None, trigger_types=()):
    node = Node(id="item_" + name, type="item", name=name, properties={
        "tags": list(tags), "actions": actions.split(","), "current_state": state,
    })
    g.add_node(node)
    for i, tt in enumerate(trigger_types):
        tid = f"trigger_{name}_{tt}_{i}"
        g.add_node(Node(id=tid, type="logic_trigger", name=tt,
                        properties={"trigger_type": tt}))
        g.add_edge(Edge(source=node.id, target=tid, type=EDGE_TRIGGERS))
    return node


def test_drop_is_not_offered_for_an_item_the_actor_does_not_hold():
    system, g = _system()
    node = _item(g)
    assert "Drop from inventory" not in _labels(system, node, carrying=False)
    assert "Drop from inventory" in _labels(system, node, carrying=True)


def test_toggle_label_follows_the_lit_state_not_an_off_literal():
    """The engine's vocabulary is lit/unlit (ToggleableItems); reading "off"
    matched nothing, so an unlit match was offered 'Toggle off'."""
    system, g = _system()
    unlit = _item(g, "candle_a", tags=("toggleable",), state="unlit",
                  trigger_types=("on_toggle_off",))
    labels = _labels(system, unlit)
    assert "Light" in labels
    assert "Extinguish" not in labels

    lit = _item(g, "candle_b", tags=("toggleable",), state="lit",
                trigger_types=("on_toggle_off",))
    lit_labels = _labels(system, lit)
    assert "Extinguish" in lit_labels
    assert "Light" not in lit_labels


def test_toggle_offers_nothing_when_the_engine_would_refuse_it():
    """toggle_item_status requires the `toggleable` tag. A trigger alone must
    not render a verb the engine rejects."""
    system, g = _system()
    node = _item(g, tags=("light_source",), state="unlit",
                 trigger_types=("on_toggle_off",))
    assert not any(l in ("Light", "Extinguish") for l in _labels(system, node))


def test_on_light_alone_still_offers_the_verb():
    system, g = _system()
    node = _item(g, tags=("toggleable",), state="unlit",
                 trigger_types=("on_light",))
    assert "Light" in _labels(system, node)


def test_a_drop_only_item_on_the_floor_offers_nothing_extra():
    """Negative case: gating drop must not also drop the other verbs."""
    system, g = _system()
    node = _item(g, "rock", actions="examine,drop")
    labels = _labels(system, node, carrying=False)
    assert "Drop from inventory" not in labels
    assert "Examine the object" in labels


# ── scene payload carries the gates ─────────────────────────────────

@pytest.fixture
def world():
    g = WorldGraph()
    add_area = lambda i, n: g.add_node(Node(  # noqa: E731
        id=i, type="area", name=n, properties={"environment": {"light": 80}}))
    add_area("area_room", "Room")

    sleeper = Node(id="player_rosa", type="character", name="rosa",
                   properties={"description": "Asleep on the cot.", "tags": ["female"]})
    awake = Node(id="player_theo", type="character", name="theo",
                 properties={"description": "Standing by the door.", "tags": ["male"]})
    for n in (sleeper, awake):
        g.add_node(n)
        g.add_edge(Edge(source=n.id, target="area_room", type=EDGE_IN))

    passage = Node(id="way_arch", type="way", name="room-arch", properties={
        "current_state": "open", "direction": "arch", "prevent_close": True,
    })
    g.add_node(passage)
    g.add_edge(Edge(source="area_room", target="way_arch", type=EDGE_CONNECTION))
    g.add_edge(Edge(source="way_arch", target="area_room", type=EDGE_CONNECTION))

    jake = Player("jake halloway")
    jake.current_area = "Room"
    jake.relationships["rosa"] = {"closeness": 5, "interaction_count": 1}
    jake.relationships["theo"] = {"closeness": 5, "interaction_count": 1}

    rosa_p, theo_p = Player("rosa"), Player("theo")
    rosa_p.current_area = "Room"
    theo_p.current_area = "Room"
    rosa_p.activity = {"type": "sleeping"}

    pm = MagicMock()
    pm.players = {"jake halloway": jake, "rosa": rosa_p, "theo": theo_p}
    pm.current_area.name = "Room"
    pm._player_node_id = lambda name: "player_" + str(name).replace(" ", "_")
    pm.get_player_node_id = pm._player_node_id
    pm.key_for_node_id = lambda nid: str(nid)[len("player_"):].replace("_", " ")
    pm.is_slasher = MagicMock(return_value=False)

    w = MagicMock()
    w.graph = g
    w.player_manager = pm
    w.area_node_id = lambda name: "area_" + str(name).lower().replace(" ", "_")
    w.lighting.get_ambient_light = MagicMock(return_value=80)
    w.area_description._render_node = MagicMock(
        side_effect=lambda n: str(n.properties.get("description", "")))
    w.name_matcher.way_handle = MagicMock(
        side_effect=lambda way, d, area: d or way.name)
    w.grapple = None
    w._get_available_actions = MagicMock(return_value=[])
    return w


def test_scene_reports_who_has_an_activity_so_wake_can_be_gated(world):
    scene = build_scene(world, "jake halloway")
    by_id = {p["id"]: p for p in scene["people"]}
    assert by_id["player_rosa"]["activity"] == "sleeping"
    assert by_id["player_theo"]["activity"] is None


def test_scene_reports_the_held_list_so_release_can_be_gated(world):
    scene = build_scene(world, "jake halloway")
    # no grapple system on the fixture -> nothing held, and the key still exists
    assert scene["you"]["holding"] == []


def test_scene_reports_prevent_close_so_close_is_not_offered(world):
    scene = build_scene(world, "jake halloway")
    arch = next(w for w in scene["ways"] if w["id"] == "way_arch")
    assert arch["prevent_close"] is True


def test_scene_marks_a_normal_way_closable(world):
    world.graph.get_node("way_arch").properties.pop("prevent_close")
    scene = build_scene(world, "jake halloway")
    arch = next(w for w in scene["ways"] if w["id"] == "way_arch")
    assert arch["prevent_close"] is False