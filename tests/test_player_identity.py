"""id-first player identity (task-446 Slice A).

Registry keys are unique identities; a display name may repeat. Unique names
keep their legacy name-derived key and anchor (no churn on existing worlds);
duplicates get a stable id-derived key and anchor.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from player import Player


def _world():
    from virtual_world_engine import VirtualWorld
    from area import Area

    world = VirtualWorld()
    world.player_manager.players = {}
    world.player_manager.active_player = None
    world.add_area(Area("Room", "A small room.", []))
    return world


def _add(world, name):
    p = Player(name)
    p.current_area = "Room"
    world.player_manager.add_player(p)
    return p


def test_unique_name_keeps_legacy_key_and_anchor():
    world = _world()
    miki = _add(world, "Miki")
    assert "Miki" in world.player_manager.players
    assert world.player_manager.get_player_node_id("Miki") == "player_Miki"
    assert world.graph.get_node("player_Miki") is not None


def test_duplicate_display_names_coexist():
    world = _world()
    a = _add(world, "Jon")
    b = _add(world, "Jon")

    assert len(world.player_manager.players) == 2
    assert len(world.player_manager.find_by_name("Jon")) == 2
    assert world.player_manager.get_by_id(a.id) is a
    assert world.player_manager.get_by_id(b.id) is b
    assert world.player_manager.resolve("Jon") is not None
    # Distinct identities → distinct anchors, same display name.
    assert world.player_manager.get_player_node_id(a) != world.player_manager.get_player_node_id(b)
    assert a.name == b.name == "Jon"


def test_duplicate_names_round_trip_through_save():
    world = _world()
    a = _add(world, "Jon")
    b = _add(world, "Jon")

    data = world.to_dict()
    assert len(data["players"]) == 2

    reloaded = _world()
    reloaded.load_from_dict(data)
    jons = reloaded.player_manager.find_by_name("Jon")
    assert len(jons) == 2
    # task-316: identity is stable across the round-trip, not regenerated.
    assert {p.id for p in jons} == {a.id, b.id}
    # Both landed in the room with distinct anchors.
    anchors = {reloaded.player_manager.get_player_node_id(p) for p in jons}
    assert len(anchors) == 2
    for p in jons:
        assert reloaded.player_manager.resolve(p.id) is p


def test_resolve_accepts_name_key_and_id():
    world = _world()
    p = _add(world, "Solo")
    pm = world.player_manager
    assert pm.resolve("Solo") is p
    assert pm.resolve(p.id) is p
    assert pm.uid_of("Solo") == p.id


def test_duplicates_list_by_display_name_with_distinct_anchors():
    world = _world()
    _add(world, "Jon")
    _add(world, "Jon")
    world.player_manager.active_player = "Traveler" if "Traveler" in world.player_manager.players else None

    here = world.player_manager.get_players_in_area("Room")
    jons = [c for c in here if c["name"] == "Jon"]
    assert len(jons) == 2
    assert len({c["at_way_id"] for c in jons} | {c["name"] for c in jons}) >= 1
    # Distinct anchors distinguish them even though the display name repeats.
    anchors = {
        world.player_manager.get_player_node_id(p)
        for p in world.player_manager.find_by_name("Jon")
    }
    assert len(anchors) == 2


def test_duplicate_name_targeting_is_ambiguous():
    """Two same-named characters in one room must not silently pick one."""
    world = _world()
    _add(world, "Jon")
    _add(world, "Jon")
    world.player_manager.active_player = "Jon"
    name, candidates = world.name_matcher._match_character_name("Jon", exclude_self=False)
    assert name is None
    assert len(candidates) == 2
    assert len(set(candidates)) == 2


def test_relationships_are_per_identity_not_name():
    """task-446: a relationship is keyed by identity, so two characters sharing
    a display name keep separate records, and a rename does not drop it."""
    from engine.relationships import apply_relationship_delta, get_relationship

    world = _world()
    a = _add(world, "Jon")
    b = _add(world, "Jon")
    observer = _add(world, "Observer")

    apply_relationship_delta(observer, a, 30, "test", tick=1)
    apply_relationship_delta(observer, b, -20, "test", tick=2)

    ra = get_relationship(observer, a)
    rb = get_relationship(observer, b)
    assert ra["closeness"] == 30
    assert rb["closeness"] == -20
    assert ra is not rb
    assert ra["name"] == "Jon" and rb["name"] == "Jon"

    # Renaming the display does not move the record (identity kept it).
    a.name = "Jonathan"
    assert get_relationship(observer, a)["closeness"] == 30
    assert observer.has_met(a)


def test_spawn_character_is_fresh_per_call():
    """task-316: spawn_character always materializes a *distinct* entity, so the
    same library character can be spawned repeatedly as same-named copies, each
    with its own identity/anchor and placed in the room independently."""
    import json
    import os

    from engine.effects import Effects

    world = _world()
    _add(world, "Spawner")  # active player standing in Room
    effects = Effects(world.graph, None)

    for _ in range(2):
        result = effects.execute(
            "spawn_character", {"character_id": "jake"}, {}, game_state=world
        )
        assert result

    lib_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "data", "library", "characters", "jake.json",
    )
    with open(lib_path, encoding="utf-8-sig") as f:
        lib_name = json.load(f)["name"]

    copies = world.player_manager.find_by_name(lib_name)
    assert len(copies) == 2, "second spawn must not return the first"
    assert len({p.id for p in copies}) == 2

    anchors = {world.player_manager.get_player_node_id(p) for p in copies}
    assert len(anchors) == 2
    for anchor in anchors:
        assert world.graph.get_node(anchor) is not None
        assert any(
            e.source == anchor and e.type == "in" for e in world.graph.edges
        ), f"{anchor} was not placed in the room"
