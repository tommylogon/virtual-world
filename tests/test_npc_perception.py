"""NPC perception & reaction framework tests (task-214).

Simple NPCs mechanically notice another character's state/action (a perception
DC roll) and react according to traits (prudish → disapprove, open_minded /
attracted → approach). Sexual stimuli are mature-gated; generic ones are always
active.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from player import Player
from app import create_app
import engine.npc_behaviors as nb
from engine.pleasure_actions import execute_intimacy_action


def _world():
    app = create_app({"TESTING": True})
    world = app.world
    world.time_per_tick_minutes = 1
    return world


def _pair(world, area="Study"):
    actor = Player("Actor")
    target = Player("Lydia")
    world.add_player(actor)
    world.add_player(target)
    world.set_player_area("Actor", area)
    world.set_player_area("Lydia", area)
    for other in list(world.player_manager.players.values()):
        if other.name not in ("Actor", "Lydia") and other.current_area == area:
            world.set_player_area(other.name, "Kitchen")
    world.tick_turn()
    return actor, target


def _add_npc(world, name, area="Study", traits=None, simple=True, social=60):
    npc = Player(name)
    npc.simple_npc = simple
    npc.traits = traits or {}
    npc.vitals["Social"] = social
    world.add_player(npc)
    world.set_player_area(name, area)
    return npc


def _force_roll(monkeypatch, value):
    """Pin the perception d20 and the reaction-line pick."""
    monkeypatch.setattr(nb.random, "randint", lambda a, b: value)
    monkeypatch.setattr(nb.random, "choice", lambda seq: seq[0])


# ── perception DC ───────────────────────────────────────────────────────

class TestPerceptionDifficulty:

    def test_base_dc(self, monkeypatch):
        world = _world()
        _, target = _pair(world)
        npc = _add_npc(world, "Watcher")
        monkeypatch.setattr(nb.NPCBehaviorSystem, "_ambient_light", lambda self, a: 60)
        assert world.npc_behaviors.calculate_perception_difficulty(npc, target, "combat") == 10

    def test_observant_lowers_dc(self, monkeypatch):
        world = _world()
        _, target = _pair(world)
        npc = _add_npc(world, "Watcher", traits={"observant": True})
        monkeypatch.setattr(nb.NPCBehaviorSystem, "_ambient_light", lambda self, a: 60)
        assert world.npc_behaviors.calculate_perception_difficulty(npc, target, "combat") == 5

    def test_oblivious_raises_dc(self, monkeypatch):
        world = _world()
        _, target = _pair(world)
        npc = _add_npc(world, "Watcher", traits={"oblivious": True})
        monkeypatch.setattr(nb.NPCBehaviorSystem, "_ambient_light", lambda self, a: 60)
        assert world.npc_behaviors.calculate_perception_difficulty(npc, target, "combat") == 15

    def test_dark_raises_dc(self, monkeypatch):
        world = _world()
        _, target = _pair(world)
        npc = _add_npc(world, "Watcher")
        monkeypatch.setattr(nb.NPCBehaviorSystem, "_ambient_light", lambda self, a: 5)
        assert world.npc_behaviors.calculate_perception_difficulty(npc, target, "combat") == 20

    def test_bright_lowers_dc(self, monkeypatch):
        world = _world()
        _, target = _pair(world)
        npc = _add_npc(world, "Watcher")
        monkeypatch.setattr(nb.NPCBehaviorSystem, "_ambient_light", lambda self, a: 95)
        assert world.npc_behaviors.calculate_perception_difficulty(npc, target, "combat") == 5

    def test_covered_skin_is_harder_to_read(self):
        world = _world()
        _, target = _pair(world)
        npc = _add_npc(world, "Watcher")
        bare = world.npc_behaviors.calculate_perception_difficulty(npc, target, "nipple_hard")

        from graph import Node, Edge, EDGE_EQUIPPED
        coat = Node(id="item_heavy_coat", name="heavy coat", type="item")
        coat.properties["coverage"] = 1.0
        world.graph.add_node(coat)
        target_node_id = world.player_manager.get_player_node_id("Lydia")
        world.graph.add_edge(Edge(source=coat.id, target=target_node_id, type=EDGE_EQUIPPED))
        target.equipped.setdefault("torso", []).append(coat.id)

        covered = world.npc_behaviors.calculate_perception_difficulty(npc, target, "nipple_hard")
        assert covered == bare + 10


# ── reactions ───────────────────────────────────────────────────────────

class TestReactions:

    def test_prudish_disapproves(self, monkeypatch):
        world = _world()
        world.mature_content = True
        _, target = _pair(world)
        npc = _add_npc(world, "Prude", traits={"prudish": True})
        _force_roll(monkeypatch, 20)
        line = world.npc_behaviors.process_npc_reaction(npc, target, "intimacy")
        assert line and "looks away" in line

    def test_open_minded_approaches_when_social(self, monkeypatch):
        world = _world()
        world.mature_content = True
        _, target = _pair(world)
        npc = _add_npc(world, "Free", traits={"open_minded": True}, social=80)
        _force_roll(monkeypatch, 20)
        line = world.npc_behaviors.process_npc_reaction(npc, target, "intimacy")
        assert line and "closer" in line

    def test_open_minded_ignores_when_unsocial(self, monkeypatch):
        world = _world()
        world.mature_content = True
        _, target = _pair(world)
        npc = _add_npc(world, "Free", traits={"open_minded": True}, social=10)
        _force_roll(monkeypatch, 20)
        assert world.npc_behaviors.process_npc_reaction(npc, target, "intimacy") is None

    def test_attracted_approaches_arousal(self, monkeypatch):
        world = _world()
        world.mature_content = True
        _, target = _pair(world)
        npc = _add_npc(world, "Wanting", traits={"attracted": True})
        _force_roll(monkeypatch, 20)
        line = world.npc_behaviors.process_npc_reaction(npc, target, "aroused")
        assert line and "closer" in line

    def test_failed_perception_reacts_not(self, monkeypatch):
        world = _world()
        world.mature_content = True
        _, target = _pair(world)
        npc = _add_npc(world, "Prude", traits={"prudish": True})
        _force_roll(monkeypatch, 1)
        assert world.npc_behaviors.process_npc_reaction(npc, target, "intimacy") is None

    def test_mature_off_blocks_sexual_stimulus(self, monkeypatch):
        world = _world()
        world.mature_content = False
        _, target = _pair(world)
        npc = _add_npc(world, "Prude", traits={"prudish": True})
        _force_roll(monkeypatch, 20)
        assert world.npc_behaviors.process_npc_reaction(npc, target, "intimacy") is None

    def test_generic_stimulus_comments(self, monkeypatch):
        world = _world()
        _, target = _pair(world)
        npc = _add_npc(world, "Bystander")
        _force_roll(monkeypatch, 20)
        line = world.npc_behaviors.process_npc_reaction(npc, target, "combat")
        assert line and "nothing" in line


# ── bystander selection ─────────────────────────────────────────────────

class TestBystanders:

    def test_simple_npc_in_area_reacts(self, monkeypatch):
        world = _world()
        world.mature_content = True
        _pair(world)
        npc = _add_npc(world, "Guard", traits={"prudish": True})
        _force_roll(monkeypatch, 20)
        lines = world.npc_behaviors.process_bystander_reactions("Actor", "Lydia", "intimacy")
        assert len(lines) == 1 and "Guard" in lines[0]

    def test_agent_is_not_double_handled(self, monkeypatch):
        world = _world()
        world.mature_content = True
        _pair(world)
        _add_npc(world, "AgentFriend", traits={"prudish": True}, simple=False)
        _force_roll(monkeypatch, 20)
        assert world.npc_behaviors.process_bystander_reactions("Actor", "Lydia", "intimacy") == []

    def test_npc_in_other_area_ignored(self, monkeypatch):
        world = _world()
        world.mature_content = True
        _pair(world)
        _add_npc(world, "FarAway", area="Kitchen", traits={"prudish": True})
        _force_roll(monkeypatch, 20)
        assert world.npc_behaviors.process_bystander_reactions("Actor", "Lydia", "intimacy") == []

    def test_actor_and_target_excluded(self, monkeypatch):
        world = _world()
        world.mature_content = True
        _, target = _pair(world)
        target.simple_npc = True
        target.traits = {"prudish": True}
        _force_roll(monkeypatch, 20)
        assert world.npc_behaviors.process_bystander_reactions("Actor", "Lydia", "intimacy") == []

    def test_combat_entry_point(self, monkeypatch):
        world = _world()
        _pair(world)
        _add_npc(world, "Guard")
        _force_roll(monkeypatch, 20)
        lines = world.npc_behaviors.process_npcs_on_combat(
            {"combat_actors": ["Actor", "Lydia"]})
        assert len(lines) == 1

    def test_crowd_emits_at_most_one_reaction(self, monkeypatch):
        world = _world()
        world.mature_content = True
        _pair(world)
        for name in ("Prude1", "Prude2", "Prude3"):
            _add_npc(world, name, traits={"prudish": True})
        _force_roll(monkeypatch, 20)
        lines = world.npc_behaviors.process_bystander_reactions("Actor", "Lydia", "intimacy")
        assert len(lines) == 1


# ── integration with intimacy actions ───────────────────────────────────

def test_intimacy_action_includes_watcher_reaction(monkeypatch):
    world = _world()
    world.mature_content = True
    _pair(world)
    _add_npc(world, "Prude", traits={"prudish": True})
    _force_roll(monkeypatch, 20)
    result = execute_intimacy_action(world, "Actor", "kiss", "Lydia")
    assert "kisses Lydia" in result
    assert "Prude" in result and "looks away" in result
