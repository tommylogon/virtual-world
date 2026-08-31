"""Trigger effect tests for runtime world sculpting (tasks 356/357/192/193/308/200/297/298).

spawn_way, spawn_area, set_way_target, set_way_view, item_relationship
condition, item-node template params ({uses}/{weight}), vital readout
templating ({vital:Thirst}), and spawn_item capture.
"""

import pytest

from graph import Node, Edge, EDGE_IN, EDGE_ON, EDGE_CONNECTION
from engine.node_ids import NodeIDHelper
from virtual_world_engine import VirtualWorld


@pytest.fixture
def world():
    w = VirtualWorld()
    w.set_player_area(next(iter(w.player_manager.players)), "Alpha")
    return w


def _add_area(world, name, desc="", env=None):
    node = Node(id=NodeIDHelper.area_node_id(name), type="area", name=name,
                properties={"description": desc, "environment": env or {}})
    world.graph.add_node(node)
    return node


def _ctx():
    return {}


def _exec(world, etype, params, item_node=None, context=None):
    return world.triggers._effects.execute(etype, params, context or _ctx(),
                                           item_node=item_node, game_state=world)


# ── spawn_way ─────────────────────────────────────────────────────────────

def test_spawn_way_bidirectional(world):
    _add_area(world, "Alpha")
    _add_area(world, "Beta")
    out = _exec(world, "spawn_way", {"area_from": "Alpha", "target": "Beta",
                                     "direction": "east",
                                     "description": "An iron door."})
    way = world.graph.get_node(world._way_node_id("Alpha_east"))
    assert way is not None and way.type == "way"
    assert way.properties["current_state"] == "open"
    assert way.properties["area_to"] == "Beta"
    assert any(o for o in out if "opens toward Beta" in o)
    conns = [e for e in world.graph.edges if e.type == EDGE_CONNECTION
             and (e.source == way.id or e.target == way.id)]
    assert len(conns) == 4  # both directions
    # movement works through the door
    world.move_to_area("east")
    assert world.player.current_area == "Beta"


def test_spawn_way_one_way(world):
    _add_area(world, "Alpha")
    _add_area(world, "Beta")
    _exec(world, "spawn_way", {"area_from": "Alpha", "target": "Beta",
                               "direction": "north", "one_way": True})
    way = world.graph.get_node(world._way_node_id("Alpha_north"))
    conns = [e for e in world.graph.edges if e.type == EDGE_CONNECTION
             and (e.source == way.id or e.target == way.id)]
    assert len(conns) == 2
    assert way.properties.get("one_way") is True


def test_spawn_way_idempotent(world):
    _add_area(world, "Alpha")
    _add_area(world, "Beta")
    _exec(world, "spawn_way", {"area_from": "Alpha", "target": "Beta"})
    edges_before = len(world.graph.edges)
    out = _exec(world, "spawn_way", {"area_from": "Alpha", "target": "Beta"})
    assert len(world.graph.edges) == edges_before
    assert "already there" in out[0]


def test_spawn_way_unknown_area(world):
    _add_area(world, "Alpha")
    out = _exec(world, "spawn_way", {"area_from": "Alpha", "target": "Nowhere"})
    assert out and "unknown area" in out[0]


# ── spawn_area ────────────────────────────────────────────────────────────

def test_spawn_area(world):
    _add_area(world, "Alpha")
    out = _exec(world, "spawn_area", {"name": "Hidden Vault",
                                      "description": "A dust-filled vault.",
                                      "environment": {"temperature": 5, "light": 20},
                                      "tags": ["secret"]})
    node = world.graph.get_node("area_hidden_vault")
    assert node is not None and node.type == "area"
    assert node.properties["environment"]["temperature"] == 5
    assert "secret" in node.properties["tags"]
    assert any("materializes" in o for o in out)
    # duplicate → no-op
    before = len(world.graph.nodes)
    _exec(world, "spawn_area", {"name": "Hidden Vault"})
    assert len(world.graph.nodes) == before


# ── set_way_target ────────────────────────────────────────────────────────

def test_set_way_target_repoints(world):
    _add_area(world, "Alpha")
    _add_area(world, "Beta")
    _add_area(world, "Gamma")
    world.connect_areas("Alpha", "Beta", "east", "west")
    way_id = world._way_node_id("Alpha_east")
    _exec(world, "set_way_target", {"way_id": way_id,
                                    "target": "Gamma", "direction": "east"})
    world.move_to_area("east")
    assert world.player.current_area == "Gamma"
    # old side no longer reachable via that direction
    conns = [e for e in world.graph.edges if e.type == EDGE_CONNECTION
             and e.source == way_id]
    targets = {e.target for e in conns}
    assert "area_beta" not in targets
    assert "area_gamma" in targets


def test_set_way_target_from_way_node_self(world):
    _add_area(world, "Alpha")
    _add_area(world, "Gamma")
    way = Node(id="way_portal", type="way", name="Portal", properties={})
    world.graph.add_node(way)
    _exec(world, "set_way_target", {"way_id": "way_portal", "target": "Gamma"})
    assert way.properties["area_to"] == "Gamma"


# ── set_way_view ──────────────────────────────────────────────────────────

def test_set_way_view(world):
    _add_area(world, "Alpha")
    _add_area(world, "Beta")
    world.connect_areas("Alpha", "Beta", "east", "west")
    way = world.graph.get_node("way_alpha_east")
    _exec(world, "set_way_view", {"way_id": way.id, "see_through": True,
                                  "description": "Beyond, the stars. (changed)"})
    assert way.properties["see_through"] is True
    assert "changed" in way.properties["description"]


# ── item_relationship condition ───────────────────────────────────────────

def test_item_relationship_condition(world):
    _add_area(world, "Alpha")
    container = Node(id="item_box", type="item", name="Box", properties={"tags": ["container"]})
    inside = Node(id="item_coin", type="item", name="Coin", properties={})
    world.graph.add_node(container)
    world.graph.add_node(inside)
    world.graph.add_edge(Edge(source="item_coin", target="item_box", type=EDGE_IN))

    tr = world.triggers
    assert tr._evaluate_trigger_condition(
        {"type": "item_relationship", "relation": "in"}, item_node=container) is True
    assert tr._evaluate_trigger_condition(
        {"type": "item_relationship", "relation": "on"}, item_node=container) is False
    assert tr._evaluate_trigger_condition(
        {"type": "item_relationship", "relation": "in", "target": "coin"},
        item_node=container) is True
    assert tr._evaluate_trigger_condition(
        {"type": "item_relationship", "relation": "in", "target": "nonexistent"},
        item_node=container) is False
    assert tr._evaluate_trigger_condition(
        {"type": "item_relationship", "relation": "in"}, item_node=None) is False


# ── template params (200 + 297) ───────────────────────────────────────────

def test_template_params_item_node_and_vital(world):
    _add_area(world, "Alpha")
    item = Node(id="item_pot", type="item", name="Pot",
                properties={"uses": 3, "weight": 2.5, "current_state": "normal"})
    world.graph.add_node(item)
    player = next(iter(world.player_manager.players.values()))
    player.vitals["Thirst"] = 66
    tr = world.triggers
    text = tr._render_template(
        "Uses: {uses} | Wt: {weight} | State: {current_state} | Thirst: {vital:Thirst}",
        {"item_node": item, "game_state": world})
    assert "Uses: 3" in text
    assert "Wt: 2.5" in text
    assert "State: normal" in text
    assert "Thirst: 66" in text


def test_template_vital_unknown_kept(world):
    tr = world.triggers
    assert "{vital:Nope}" in tr._render_template("{vital:Nope}", {"game_state": world})


# ── spawn_item capture (298) ──────────────────────────────────────────────

def test_spawn_item_capture_speech(world):
    _add_area(world, "Alpha")
    container = Node(id="item_recorder", type="item", name="Recorder",
                     properties={"tags": ["container"]})
    world.graph.add_node(container)
    world.turn_events = [
        {"tick": 1, "actor": "Lyrie", "action": "speech",
         "description": "hello? is anyone there?", "area": "Alpha"},
        {"tick": 1, "actor": "Kaelen", "action": "speech",
         "description": "shh.", "area": "Alpha"},
        {"tick": 0, "actor": "Lyrie", "action": "walked", "description": "footsteps.", "area": "Alpha"},
    ]
    out = _exec(world, "spawn_item", {"item_id": "apple", "into": "container",
                                      "capture": "speech", "capture_limit": 2},
                item_node=container)
    photo = world.graph.get_node("apple")
    assert photo is not None
    desc = photo.properties.get("description", "")
    assert "Lyrie: hello? is anyone there?" in desc
    assert "Kaelen: shh." in desc
    assert "footsteps" not in desc
    assert out  # narrates
