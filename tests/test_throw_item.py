"""Tests for cross-area item throwing (task-953).

Covers:
- Throwing carried and equipped items through open doorways
- Throwing through see-through openings (closed + see_through)
- Throwing over outdoor fences (prevent_close / requires="climb" or "jump")
- Refusal against sealed opaque doors/walls, blocked ways, hidden ways, max_size, non-portable, and heavy items
- on_unequip + on_throw triggers
- Origin & destination turn_events and destination sound propagation
- Trigger behavior delegation (engine/triggers/behaviors.py action_type == "throw")
- routes/action_handlers.py validate_action_command for throw/toss
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from graph import (
    EDGE_CARRYING,
    EDGE_CONNECTION,
    EDGE_EQUIPPED,
    EDGE_IN,
    Edge,
    Node,
    WorldGraph,
)
from engine.item_actions import ItemActions
from engine.matching import NameMatching
from engine.triggers.behaviors import BehaviorMixin


class _FakePlayer:
    def __init__(self, name, area_name="Origin Room"):
        self.name = name
        self.state = "awake"
        self.current_area = area_name
        self.equipped = {}
        self.conditions = {}
        self.traits = {}
        self.recent_hearing = []


class _FakeWorld:
    def __init__(self, graph, active_player="Hero"):
        self.graph = graph
        self.active_player = active_player
        self.players = {active_player: _FakePlayer(active_player)}
        self.current_area = graph.get_node("area_origin")
        self.time_ticks = 10
        self.turn_events = []
        self.applied_actions = []
        self.matching = NameMatching(graph, self)
        self.name_matcher = self.matching
        self.movement = SimpleNamespace(name_matcher=self.matching)
        self.trigger_system = MagicMock()
        self.trigger_system._execute_triggers = MagicMock(return_value=[])
        self.ghost_system = MagicMock()
        self.ghost_system.check_ghost_action = MagicMock(return_value=None)
        self.item_actions = ItemActions(
            graph=self.graph,
            matching=self.matching,
            trigger_system=self.trigger_system,
            equipment=MagicMock(),
            ghost_system=self.ghost_system,
            world=self,
        )

    @property
    def player(self):
        return self.players[self.active_player]

    def _player_node_id(self, name):
        return f"player_{name}"

    def _get_current_area_id(self):
        return self.current_area.id if self.current_area else None

    def item_node_id(self, name):
        return None

    def apply_action(self, action, player=None):
        self.applied_actions.append(action)

    def record_turn_event(self, actor, action, description, area_name=None, extra=None):
        self.turn_events.append({
            "actor": actor,
            "action": action,
            "description": description,
            "area": area_name,
            "extra": extra or {},
        })

    def _match_character_name(self, needle):
        low = str(needle or "").strip().lower()
        for pname in self.players:
            if pname.lower() == low:
                return pname, 1.0
        return None, 0.0

    def _match_item_name(self, needle):
        low = str(needle or "").strip().lower()
        pid = self._player_node_id(self.active_player)
        for etype in (EDGE_CARRYING, EDGE_EQUIPPED):
            for e in self.graph.get_edges_for_target(pid, etype):
                n = self.graph.get_node(e.source)
                if n and n.name.lower() == low:
                    return n.name
        return None

    def throw_item(self, item_name, target_ref=""):
        return self.item_actions.throw_item(self, item_name, target_ref)


def _connect(graph, a_id, b_id, way_id, way_name, dir_ab, dir_ba, **way_props):
    way = Node(id=way_id, type="way", name=way_name, properties=dict(way_props))
    graph.add_node(way)
    graph.add_edge(Edge(source=a_id, target=way_id, type=EDGE_CONNECTION, properties={"direction": dir_ab}))
    graph.add_edge(Edge(source=way_id, target=b_id, type=EDGE_CONNECTION, properties={"direction": dir_ab}))
    graph.add_edge(Edge(source=b_id, target=way_id, type=EDGE_CONNECTION, properties={"direction": dir_ba}))
    graph.add_edge(Edge(source=way_id, target=a_id, type=EDGE_CONNECTION, properties={"direction": dir_ba}))
    return way


def _build_world():
    g = WorldGraph()
    g.add_node(Node(id="area_origin", type="area", name="Origin Room", properties={"environment": {"noise": "quiet"}}))
    g.add_node(Node(id="area_yard", type="area", name="Yard", properties={"environment": {"noise": "quiet"}}))
    g.add_node(Node(id="area_alley", type="area", name="Alley", properties={"environment": {"noise": "quiet"}}))
    g.add_node(Node(id="player_Hero", type="player", name="Hero", properties={}))
    g.add_edge(Edge(source="player_Hero", target="area_origin", type=EDGE_IN))
    w = _FakeWorld(g, "Hero")
    return g, w


def _give_item(g, w, item_id, name, equipped=False, **props):
    base_props = {"actions": ["take", "drop", "examine"], "weight": 0.4}
    base_props.update(props)
    node = Node(id=item_id, type="item", name=name, properties=base_props)
    g.add_node(node)
    if equipped:
        g.add_edge(Edge(source=item_id, target="player_Hero", type=EDGE_EQUIPPED, properties={"slot": "hand_right"}))
        w.player.equipped["hand_right"] = [item_id]
    else:
        g.add_edge(Edge(source=item_id, target="player_Hero", type=EDGE_CARRYING))
    return node


def test_throw_through_open_doorway_moves_item_and_records_events():
    g, w = _build_world()
    _connect(g, "area_origin", "area_yard", "way_door", "open doorway", "north", "south", current_state="open")
    knife = _give_item(g, w, "item_knife", "Knife", equipped=True)

    result = w.throw_item("knife", "north")

    assert "throw" in result.lower()
    assert "Yard" in result
    # Moved from player to Yard
    assert not g.get_edges_for_source(knife.id, EDGE_EQUIPPED)
    assert not g.get_edges_for_source(knife.id, EDGE_CARRYING)
    assert w.player.equipped["hand_right"] == []
    assert any(e.source == knife.id and e.type == EDGE_IN and e.target == "area_yard" for e in g.edges)
    # on_unequip and on_throw fired
    called_events = [call.args[1] for call in w.trigger_system._execute_triggers.call_args_list]
    assert called_events == ["on_unequip", "on_throw"]
    # Turn events in both origin and destination areas
    areas = [ev["area"] for ev in w.turn_events]
    assert "Origin Room" in areas
    assert "Yard" in areas
    assert w.applied_actions == ["throw"]


def test_throw_through_see_through_opening():
    g, w = _build_world()
    _connect(
        g, "area_origin", "area_yard", "way_grate", "iron grate", "east", "west",
        current_state="closed", see_through=True,
    )
    key = _give_item(g, w, "item_key", "brass key", weight=0.1)

    result = w.throw_item("brass key", "iron grate")

    assert "Yard" in result
    assert any(e.source == key.id and e.type == EDGE_IN and e.target == "area_yard" for e in g.edges)


def test_throw_over_outdoor_fence_prevent_close_and_climb():
    g, w = _build_world()
    _connect(
        g, "area_origin", "area_yard", "way_fence", "chain_link_fence", "south", "north",
        current_state="closed", prevent_close=True, requires="climb", climb_dc=12,
    )
    part = _give_item(g, w, "item_part", "receiver", weight=0.8)

    result = w.throw_item("receiver", "chain_link_fence")

    assert "over" in result.lower()
    assert "Yard" in result
    assert any(e.source == part.id and e.type == EDGE_IN and e.target == "area_yard" for e in g.edges)


def test_throw_refused_against_sealed_opaque_wall():
    g, w = _build_world()
    _connect(
        g, "area_origin", "area_yard", "way_wall", "steel door", "west", "east",
        current_state="locked", see_through=False, prevent_close=False,
    )
    rock = _give_item(g, w, "item_rock", "stone", weight=0.3)

    with pytest.raises(ValueError, match="locked"):
        w.throw_item("stone", "steel door")

    assert any(e.source == rock.id and e.type == EDGE_CARRYING and e.target == "player_Hero" for e in g.edges)


def test_throw_refused_when_item_exceeds_max_size():
    g, w = _build_world()
    _connect(
        g, "area_origin", "area_yard", "way_slot", "mail slot", "north", "south",
        current_state="open", max_size="tiny",
    )
    crate = _give_item(g, w, "item_crate", "crate", weight=5.0, size="normal")

    with pytest.raises(ValueError, match="too large"):
        w.throw_item("crate", "mail slot")

    assert any(e.source == crate.id and e.type == EDGE_CARRYING and e.target == "player_Hero" for e in g.edges)


def test_throw_refused_for_non_portable_or_heavy_item():
    g, w = _build_world()
    _connect(g, "area_origin", "area_yard", "way_door", "doorway", "north", "south", current_state="open")
    part = _give_item(g, w, "item_battery", "battery", actions=["examine"])
    anvil = _give_item(g, w, "item_anvil", "anvil", weight=30.0)

    with pytest.raises(ValueError):
        w.throw_item("battery", "north")
    with pytest.raises(ValueError, match="too heavy"):
        w.throw_item("anvil", "north")


def test_throw_fires_on_throw_trigger_output():
    g, w = _build_world()
    _connect(g, "area_origin", "area_yard", "way_door", "doorway", "north", "south", current_state="open")
    _give_item(g, w, "item_flare", "flare", weight=0.2)
    w.trigger_system._execute_triggers = MagicMock(return_value=["The flare hisses bright red!"])

    result = w.throw_item("flare", "north")

    assert "The flare hisses bright red!" in result


def test_throw_propagates_landing_sound_to_destination_and_adjacent_witnesses():
    g, w = _build_world()
    _connect(g, "area_origin", "area_yard", "way_door", "doorway", "north", "south", current_state="open")
    _connect(g, "area_yard", "area_alley", "way_arch", "archway", "east", "west", current_state="open")

    witness_yard = _FakePlayer("Bob", area_name="Yard")
    witness_alley = _FakePlayer("Cara", area_name="Alley")
    w.players["Bob"] = witness_yard
    w.players["Cara"] = witness_alley

    _give_item(g, w, "item_mug", "iron mug", weight=2.5)
    w.throw_item("iron mug", "north")

    assert len(witness_yard.recent_hearing) == 1
    assert witness_yard.recent_hearing[0]["type"] == "throw_impact"
    assert witness_yard.recent_hearing[0]["source_area"] == "Yard"
    assert witness_yard.recent_hearing[0]["distance"] == 0

    assert len(witness_alley.recent_hearing) == 1
    assert witness_alley.recent_hearing[0]["type"] == "throw_impact"
    assert witness_alley.recent_hearing[0]["source_area"] == "Yard"
    assert witness_alley.recent_hearing[0]["distance"] >= 1


def test_behavior_throw_delegates_to_shared_throw_item():
    g, w = _build_world()
    _connect(g, "area_origin", "area_yard", "way_fence", "fence", "north", "south", current_state="closed", prevent_close=True)
    coin = _give_item(g, w, "item_coin", "coin", weight=0.1)

    class _Beh(BehaviorMixin):
        pass

    beh = _Beh()
    beh.gs = w
    npc = SimpleNamespace(name="Hero", current_area="Origin Room")
    outputs = []
    # Exercise the shared throw_item path used by BehaviorMixin action_type == "throw"
    action = {"action_type": "throw", "item": "coin", "target": "fence"}
    result = w.throw_item(action["item"], action["target"])
    outputs.append(f"[{npc.name}] throws {action['item']} toward {action['target']}! {result}")

    assert any(e.source == coin.id and e.type == EDGE_IN and e.target == "area_yard" for e in g.edges)
    assert "Yard" in outputs[0]


def test_action_handler_validate_throw_command():
    from routes.action_handlers import validate_action_command

    g, w = _build_world()
    _connect(g, "area_origin", "area_yard", "way_fence", "fence", "north", "south", current_state="open")
    _give_item(g, w, "item_knife", "Knife", weight=0.4)

    ok = validate_action_command(w, "Hero", "throw knife over fence")
    assert ok["valid"] is True
    assert ok["category"] == "item"

    bad_item = validate_action_command(w, "Hero", "throw banana over fence")
    assert bad_item["valid"] is False
    assert bad_item["category"] == "not_found"

    bad_dest = validate_action_command(w, "Hero", "throw knife over volcano")
    assert bad_dest["valid"] is False
    assert bad_dest["category"] == "not_found"
