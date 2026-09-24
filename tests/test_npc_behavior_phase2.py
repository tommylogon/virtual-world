"""NPC behavior phase 2 tests (task-390).

Sensory conditions (player_has_tag, sight_holds, smell_detected, sound_above),
flag logic, and the add_tag/remove_tag behavior actions.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from player import Player
from app import create_app
from graph import Node, Edge, EDGE_IN, EDGE_CARRYING


def _world():
    app = create_app({"TESTING": True})
    world = app.world
    world.time_per_tick_minutes = 1
    return world


def _add_char(world, name, area="Study"):
    p = Player(name)
    world.add_player(p)
    world.set_player_area(name, area)
    return p


def _area_id(world, name):
    node = world.graph.get_node("area_" + name.lower().replace(" ", "_"))
    if node is not None:
        return node.id
    for n in world.graph.nodes.values():
        if n.type == "area" and n.name == name:
            return n.id
    return None


def _item(world, item_id, name, tags, area=None, carrier=None):
    node = Node(id=item_id, type="item", name=name)
    node.properties["tags"] = list(tags)
    world.graph.add_node(node)
    if area:
        world.graph.add_edge(Edge(source=node.id, target=_area_id(world, area), type=EDGE_IN))
    if carrier:
        pid = world.player_manager.get_player_node_id(carrier)
        world.graph.add_edge(Edge(source=node.id, target=pid, type=EDGE_CARRYING))
    return node


def _eval(world, conditions, **context):
    ctx = {"npc_area": "Study", "current_tick": world.time_ticks}
    ctx.update(context)
    return world.triggers._evaluate_conditions(conditions, ctx, game_state=world)


# ── player_has_tag / sight_holds ────────────────────────────────────────

class TestItemTagSenses:

    def test_player_has_tag_true_for_carried_item(self):
        world = _world()
        _add_char(world, "Guard")
        _item(world, "item_bread", "bread", ["food"], carrier="Guard")
        assert _eval(world, {"type": "player_has_tag", "tag": "food", "target": "Guard"}) is True

    def test_player_has_tag_false_without_item(self):
        world = _world()
        _add_char(world, "Guard")
        assert _eval(world, {"type": "player_has_tag", "tag": "food", "target": "Guard"}) is False

    def test_player_has_tag_finds_equipped_item(self):
        world = _world()
        guard = _add_char(world, "Guard")
        node = _item(world, "item_uniform", "uniform", ["faction_guards"])
        guard.equipped.setdefault("torso", []).append(node.id)
        assert _eval(world, {"type": "player_has_tag", "tag": "faction_guards", "target": "Guard"}) is True

    def test_sight_holds_same_area(self):
        world = _world()
        _add_char(world, "Guard")
        _item(world, "item_sword", "sword", ["weapon"], carrier="Guard")
        assert _eval(world, {"type": "sight_holds", "tag": "weapon", "target": "Guard"}) is True

    def test_sight_holds_hidden_target_fails(self):
        world = _world()
        guard = _add_char(world, "Guard")
        guard.hidden = True
        _item(world, "item_sword", "sword", ["weapon"], carrier="Guard")
        assert _eval(world, {"type": "sight_holds", "tag": "weapon", "target": "Guard"}) is False

    def test_sight_holds_other_area_fails(self):
        world = _world()
        _add_char(world, "Guard", area="Study")
        _add_char(world, "Stranger", area="Kitchen")
        _item(world, "item_sword", "sword", ["weapon"], carrier="Stranger")
        assert _eval(
            world,
            {"type": "sight_holds", "tag": "weapon", "target": "Stranger"},
            npc_area="Study",
        ) is False


# ── flag_equals ─────────────────────────────────────────────────────────

class TestFlagEquals:

    def test_true_flag(self):
        world = _world()
        guard = _add_char(world, "Guard")
        guard.flags["player_fed_me"] = True
        assert _eval(world, {"type": "flag_equals", "key": "player_fed_me", "value": True, "target": "Guard"}) is True

    def test_wrong_value(self):
        world = _world()
        guard = _add_char(world, "Guard")
        guard.flags["player_fed_me"] = False
        assert _eval(world, {"type": "flag_equals", "key": "player_fed_me", "value": True, "target": "Guard"}) is False

    def test_missing_flag(self):
        world = _world()
        _add_char(world, "Guard")
        assert _eval(world, {"type": "flag_equals", "key": "nope", "value": True, "target": "Guard"}) is False


# ── sound_above ─────────────────────────────────────────────────────────

class TestSoundAbove:

    def test_shout_passes_half_threshold(self):
        world = _world()
        guard = _add_char(world, "Guard")
        guard.recent_hearing = [{"speech_level": "shout", "text": "Halt!"}]
        assert _eval(world, {"type": "sound_above", "threshold": 0.5, "target": "Guard"}) is True

    def test_whisper_fails_half_threshold(self):
        world = _world()
        guard = _add_char(world, "Guard")
        guard.recent_hearing = [{"speech_level": "whisper"}]
        assert _eval(world, {"type": "sound_above", "threshold": 0.5, "target": "Guard"}) is False

    def test_scream_passes_high_threshold(self):
        world = _world()
        guard = _add_char(world, "Guard")
        guard.recent_hearing = [{"speech_level": "scream"}]
        assert _eval(world, {"type": "sound_above", "threshold": 0.9, "target": "Guard"}) is True

    def test_no_hearing(self):
        world = _world()
        _add_char(world, "Guard")
        assert _eval(world, {"type": "sound_above", "threshold": 0.5, "target": "Guard"}) is False


# ── smell_detected ──────────────────────────────────────────────────────

class TestSmellDetected:

    def test_same_area_item_detected(self):
        world = _world()
        _add_char(world, "Cat", area="Study")
        _item(world, "item_fish", "fish", ["food"], area="Study")
        assert _eval(world, {"type": "smell_detected", "tag": "food", "range": 0}, npc_area="Study") is True

    def test_item_in_other_area_not_smelled_at_range_0(self):
        world = _world()
        _add_char(world, "Cat", area="Study")
        _item(world, "item_fish", "fish", ["food"], area="Kitchen")
        assert _eval(world, {"type": "smell_detected", "tag": "food", "range": 0}, npc_area="Study") is False

    def test_no_matching_tag(self):
        world = _world()
        _add_char(world, "Cat", area="Study")
        _item(world, "item_rock", "rock", ["mineral"], area="Study")
        assert _eval(world, {"type": "smell_detected", "tag": "food", "range": 0}, npc_area="Study") is False

    def test_range_expansion_reaches_neighbour(self):
        world = _world()
        _add_char(world, "Cat", area="Study")
        _item(world, "item_fish", "fish", ["food"], area="Kitchen")
        # Force Kitchen to be adjacent to Study for the test.
        world._build_exits_for_area = lambda area: (
            {"south": {"target": "Kitchen", "state": "open"}} if area == "Study"
            else ({"north": {"target": "Study", "state": "open"}} if area == "Kitchen" else {})
        )
        assert _eval(world, {"type": "smell_detected", "tag": "food", "range": 1}, npc_area="Study") is True


# ── add_tag / remove_tag behavior actions ───────────────────────────────

class TestTagActions:

    def _run(self, world, actions, char="Guard"):
        return world.triggers._execute_behavior_actions(char, actions, game_state=world)

    def test_add_tag_to_self(self):
        world = _world()
        guard = _add_char(world, "Guard")
        self._run(world, [{"type": "add_tag", "tag": "hostile", "target": "self"}])
        assert "hostile" in (guard.tags or [])

    def test_add_tag_is_idempotent(self):
        world = _world()
        guard = _add_char(world, "Guard")
        self._run(world, [{"type": "add_tag", "tag": "hostile", "target": "self"}])
        self._run(world, [{"type": "add_tag", "tag": "hostile", "target": "self"}])
        assert (guard.tags or []).count("hostile") == 1

    def test_remove_tag(self):
        world = _world()
        guard = _add_char(world, "Guard")
        guard.tags = ["hostile", "guard"]
        self._run(world, [{"type": "remove_tag", "tag": "hostile", "target": "self"}])
        assert "hostile" not in (guard.tags or [])
        assert "guard" in (guard.tags or [])

    def test_add_tag_to_named_character(self):
        world = _world()
        _add_char(world, "Guard")
        other = _add_char(world, "Stranger")
        self._run(world, [{"type": "add_tag", "tag": "marked", "target": "Stranger"}])
        assert "marked" in (other.tags or [])


# ── faction example end to end ──────────────────────────────────────────

def test_guard_faction_condition_then_attack_action():
    """The task's worked example: a guard reacts to a non-faction intruder."""
    world = _world()
    guard = _add_char(world, "Guard", area="Study")
    _add_char(world, "Stranger", area="Study")
    # Guard has the faction tag; stranger does not.
    guard.tags = ["faction_guards"]
    conditions = {"type": "character_has_tag", "tag": "faction_guards", "target": "triggering"}
    ctx = {"triggering_character": guard, "npc_area": "Study"}
    assert world.triggers._evaluate_conditions(conditions, ctx, game_state=world) is True

    outputs = world.triggers._execute_behavior_actions(
        "Guard",
        [{"type": "message", "text": "Halt! You're not one of us."},
         {"type": "add_tag", "tag": "hostile", "target": "self"}],
        game_state=world,
    )
    assert any("Halt!" in o for o in outputs)
    assert "hostile" in guard.tags
