"""Pleasure system tests (tasks 206/207/208/211/212/213/309).

Everything mature-gated: with mature_content off, no pleasure vitals exist
and intimacy verbs are rejected with a flavor message.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from player import Player
from app import create_app
from engine.pleasure_actions import (
    VERB_BASE, INTIMACY_VERBS, parse_intensity, apply_stimulation,
    resolve_body_part, body_part_multiplier, execute_intimacy_action,
)


def _world():
    from app import create_app
    app = create_app({"TESTING": True})
    return app.world


def _place_pair(world, actor_name="Actor", target_name="Lydia", area="Study"):
    actor = Player(actor_name)
    target = Player(target_name)
    world.add_player(actor)
    world.add_player(target)
    world.set_player_area(actor_name, area)
    world.set_player_area(target_name, area)
    for other in list(world.player_manager.players.values()):
        if other.name not in (actor_name, target_name) and other.current_area == area:
            other.current_area = "Kitchen"
            world.set_player_area(other.name, "Kitchen")
    world.tick_turn()
    return actor, target


# ── task-206/207: vitals gating ─────────────────────────────────────────

def test_pleasure_vitals_absent_when_mature_off():
    world = _world()
    p, _ = _place_pair(world)
    world.mature_content = False
    world.tick_turn()
    assert "Arousal" not in p.vitals
    assert "Stimulation" not in p.vitals
    assert "Pleasure" not in p.vitals


def test_pleasure_vitals_appear_when_mature_on():
    world = _world()
    p, _ = _place_pair(world)
    world.mature_content = True
    world.tick_turn()
    for vital in ("Arousal", "Stimulation", "Pleasure"):
        assert vital in p.vitals
    assert p.decay_rates["Stimulation"] == 2


def test_toggling_off_strips_arousal_conditions():
    world = _world()
    p, _ = _place_pair(world)
    world.mature_content = True
    p.vitals["Arousal"] = 60
    world.tick_turn()
    assert "highly_aroused" in p.conditions
    world.mature_content = False
    world.tick_turn()
    assert "highly_aroused" not in p.conditions
    assert "Arousal" not in p.vitals


# ── task-212: verb pipeline ─────────────────────────────────────────────

def test_verb_base_table_shape():
    for verb, base in VERB_BASE.items():
        assert {"pressure", "pleasure_mult", "pain_potential", "stim_type"} <= set(base)


def test_parse_intensity_adverbs():
    assert parse_intensity("kiss her gently") == ("light", "kiss her")
    assert parse_intensity("pinch her firmly") == ("firm", "pinch her")
    assert parse_intensity("kiss her")[0] == "normal"


def test_apply_stimulation_respects_sensitivity_and_traits():
    world = _world()
    world.mature_content = True
    _, target = _place_pair(world)
    target.traits["wired_differently"] = True
    # nipple sensitivity 0.9, wired_differently x3 -> strong gains
    report = apply_stimulation(None, target, "pinch", "nipple_left", "normal")
    assert report["stim"] > 0
    assert target.vitals["Stimulation"] == report["stim"]
    # genitals x0.1 -> nearly nothing
    before = target.vitals["Stimulation"]
    report2 = apply_stimulation(None, target, "caress", "genitals", "normal")
    assert report2["stim"] < report["stim"]


def test_apply_stimulation_no_vitals_is_flavor_only():
    world = _world()
    _, target = _place_pair(world)
    world.mature_content = False
    world.tick_turn()
    report = apply_stimulation(None, target, "kiss", "lips", "normal")
    assert report["stim"] == 0
    assert "Stimulation" not in target.vitals


def test_pain_flips_pleasure_negative_and_overstims():
    world = _world()
    world.mature_content = True
    _, target = _place_pair(world)
    target.vitals["Pleasure"] = 2
    report = apply_stimulation(None, target, "bite", "torso", "firm")
    assert report["pain"] > 0
    assert target.vitals["Pleasure"] == 0
    assert report.get("overstimulated")


def test_covered_contact_is_damped():
    world = _world()
    world.mature_content = True
    actor, target = _place_pair(world)
    # Firmly dress the torso: legs slot irrelevant; use torso coverage.
    from graph import Node, Edge, EDGE_EQUIPPED
    coat = Node(id="item_coat_test", name="test coat", type="item")
    coat.properties["coverage"] = 0.9
    world.graph.add_node(coat)
    target_node_id = world.player_manager.get_player_node_id("Lydia")
    world.graph.add_edge(Edge(source=coat.id, target=target_node_id, type=EDGE_EQUIPPED))
    target.equipped.setdefault("torso", []).append(coat.id)
    part = resolve_body_part(target, "torso", world.graph)
    assert part["covered"] is True


# ── task-211: intimacy verbs ────────────────────────────────────────────

def test_intimacy_verb_dispatch_and_gate():
    test_app = create_app({"TESTING": True})
    w = test_app.world
    _place_pair(w)
    w.mature_content = False
    client = test_app.test_client()
    resp = client.post('/api/action', json={"command": "kiss lydia", "character": "Actor"})
    assert "isn't part of this world" in resp.get_json()["output"]

    w.mature_content = True
    w.tick_turn()
    resp = client.post('/api/action', json={"command": "firmly kiss lydia on neck", "character": "Actor"})
    out = resp.get_json()["output"]
    assert "firmly kisses Lydia on the neck" in out
    target = w.players["Lydia"]
    assert target.vitals["Stimulation"] > 0


def test_default_region_when_no_where():
    world = _world()
    _place_pair(world)
    world.mature_content = True
    result = execute_intimacy_action(world, "Actor", "kiss", "Lydia")
    assert "on the lips" in result


def test_target_not_here():
    world = _world()
    _place_pair(world)
    world.set_player_area("Lydia", "Kitchen")
    world.mature_content = True
    result = execute_intimacy_action(world, "Actor", "kiss", "Lydia")
    assert "isn't here" in result


# ── task-208: friction / edging / release ───────────────────────────────

def test_release_cascade_resets_meters_and_applies_conditions():
    world = _world()
    world.mature_content = True
    p, _ = _place_pair(world)
    p.vitals["Stimulation"] = 70
    p.vitals["Arousal"] = 50
    p.vitals["Energy"] = 80
    world.tick_turn()
    assert p.vitals["Stimulation"] == 5
    assert "satisfied" in p.conditions
    assert "overstimulated" in p.conditions


def test_edging_stacks_sensitized():
    world = _world()
    world.mature_content = True
    p, _ = _place_pair(world)
    p.vitals["Stimulation"] = 55
    p.vitals["Arousal"] = 10
    world.tick_turn()
    assert "sensitized" in p.conditions


def test_clothing_friction_feeds_arousal():
    world = _world()
    world.mature_content = True
    p, _ = _place_pair(world)
    from graph import Node, Edge, EDGE_EQUIPPED
    rough = Node(id="item_rough_test", name="rough fabric", type="item")
    rough.properties["friction"] = 3
    world.graph.add_node(rough)
    target_node_id = world.player_manager.get_player_node_id("Actor")
    world.graph.add_edge(Edge(source=rough.id, target=target_node_id, type=EDGE_EQUIPPED))
    p.equipped.setdefault("legs", []).append(rough.id)
    before = p.vitals.get("Arousal", 0)
    world.tick_turn()
    assert p.vitals["Arousal"] >= before + 3


def test_quick_recovery_halves_overstimulation():
    world = _world()
    world.mature_content = True
    p, _ = _place_pair(world)
    p.traits["quick_recovery"] = True
    p.vitals["Stimulation"] = 70
    p.vitals["Arousal"] = 50
    world.tick_turn()
    inst = p.conditions["overstimulated"][0]
    assert inst["duration"] <= 2


# ── task-309: undead ghost NPC ──────────────────────────────────────────

def test_undead_ghost_hidden_from_room_and_skips_decay():
    world = _world()
    wraith = Player("Wraith")
    wraith.tags = ["undead", "ghost"]
    world.add_player(wraith)
    # Re-activate a living character so the ghost is a "other" in the room.
    world.player_manager.active_player = "Traveler" if "Traveler" in world.players else next(
        n for n in world.players if n != "Wraith")
    wraith.current_area = "Study"
    world.set_player_area("Wraith", "Study")
    wraith.vitals["Social"] = 100
    world.tick_turn()
    # Not listed among the living
    names = [p["name"] for p in world.player_manager.get_players_in_area("Study")]
    assert "Wraith" not in names
    # No vital decay applied (Social untouched)
    assert wraith.vitals["Social"] == 100
    # Explicitly included when asked
    names_incl = [p["name"] for p in world.player_manager.get_players_in_area("Study", include_ghosts=True)]
    assert "Wraith" in names_incl


def test_attack_passes_through_ghost():
    world = _world()
    wraith = Player("Wraith")
    wraith.tags = ["undead", "ghost"]
    world.add_player(wraith)
    attacker = Player("Fighter")
    world.add_player(attacker)
    world.set_player_area("Wraith", "Study")
    world.set_player_area("Fighter", "Study")
    world.player_manager.active_player = "Fighter"
    result = world.combat.player_attack("Fighter", "Wraith")
    assert "passes straight through" in result
    assert wraith.vitals["HP"] == 100


def test_ghost_phases_through_locked_way():
    from virtual_world_engine import VirtualWorld
    from area import Area
    world = VirtualWorld()
    world.movement.add_area(Area("Room A", "First room.", []))
    world.movement.add_area(Area("Room B", "Second room.", []))
    world.movement.connect_areas("Room A", "Room B", "north", "south", state="locked")

    # A living character is stopped by the lock.
    world.name_matcher._set_player_area(world.active_player, "Room A")
    with pytest.raises(ValueError, match="locked"):
        world.move_to_area("north")

    # The undead ghost phases straight through.
    ghost = Player("Wraith")
    ghost.tags = ["undead", "ghost"]
    world.add_player(ghost)
    world.name_matcher._set_player_area("Wraith", "Room A")
    world.player_manager.active_player = "Wraith"
    world.move_to_area("north")
    assert world.players["Wraith"].current_area == "Room B"


# ── task-316 foundation: stable ids ─────────────────────────────────────

def test_player_id_stable_across_save_load():
    world = _world()
    p, _ = _place_pair(world)
    original_id = p.id
    assert original_id
    data = world.serializer.to_dict()
    pdata = data["players"]["Actor"]
    assert pdata["id"] == original_id
    world.serializer.load_from_dict(data)
    reloaded = world.players["Actor"]
    assert reloaded.id == original_id


def test_graph_suffixes_duplicate_character_nodes():
    from graph import Node
    world = _world()
    first = Node(id="player_dupe_test", name="Dupe", type="character")
    second = Node(id="player_dupe_test", name="Dupe", type="character")
    world.graph.add_node(first)
    world.graph.add_node(second)
    assert first.id == "player_dupe_test"
    assert second.id != first.id
