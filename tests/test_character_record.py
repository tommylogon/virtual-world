"""The character-definition audit (task-457).

The task's real content is a migration with two sides: somebody has to *write* a
character's definition onto its graph node, and that write belongs to
`engine/serialization.py` and `engine/player_manager.py` — hub files. This file
covers the side that does not: the enumerated list, and a read-only drift reader
that says how far any character is from canonical.

The tests below are written against what is **true now**, not against the target
state. A character node is created bare
(`Node(id=..., type="character", name=...)` in `add_player`), so today essentially
every canonical field is missing from it. Asserting the target state would mean
shipping a red test, and asserting "it is all missing" would be a test that
breaks on success. So what is pinned is the *list* — that it names the real
fields, classifies them honestly, and reports the current gap — which is the
thing that has to stay true across the migration.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from app import create_app
from area import Area
from player import Player

from engine.character_record import (
    CANONICAL_FIELDS,
    DEFINITION_FIELDS,
    DERIVED,
    EDGE_BACKED_FIELDS,
    ON_EDGES,
    ON_NODE,
    ON_PLAYER,
    PLAYER_ONLY_FIELDS,
    audit,
    definition_drift,
    field,
    groups,
    is_canonical,
    node_definition,
)

AREA = "Verdant Hollow"


def _world():
    world = create_app({"TESTING": True}).world
    world.movement.add_area(Area(AREA, "A hollow.", []))
    return world


def _character(world, name, **attrs):
    p = Player(name)
    world.add_player(p)
    world.set_player_area(name, AREA)
    for key, value in attrs.items():
        setattr(p, key, value)
    return p


def _node(world, name):
    return world.graph.get_node(world._player_node_id(name))


# ── the list ──

class TestDefinitionFieldList:

    def test_every_field_is_grouped_and_described(self):
        assert DEFINITION_FIELDS
        for entry in DEFINITION_FIELDS:
            assert entry.group
            assert entry.lives_on in (ON_PLAYER, ON_NODE, ON_EDGES, DERIVED)
            assert isinstance(entry.canonical, bool)

    def test_field_names_are_unique(self):
        names = [f.name for f in DEFINITION_FIELDS]
        assert len(names) == len(set(names)), "a field is listed twice"

    def test_the_task_named_fields_are_all_listed(self):
        """Every field task-457's goal paragraph names must be in the list."""
        named = {
            "stats", "skills", "vitals", "traits", "tags", "interest_tags",
            "personality", "description", "base_description", "emotion",
            "conditions", "simple_npc", "autonomy", "npc_behavior",
            "behaviors", "equipped", "fear_tags", "relationships",
        }
        assert named <= set(CANONICAL_FIELDS)

    def test_the_tier_fields_are_listed(self):
        """The task requires uniformity across human, agent and simple NPC.

        `simple_npc` is the field that draws that line, so a list that omitted it
        would let the migration quietly exempt simple NPCs.
        """
        for name in ("simple_npc", "autonomy", "npc_behavior", "simulation_mode"):
            assert name in CANONICAL_FIELDS

    def test_name_is_already_canonical(self):
        assert field("name").lives_on == ON_NODE
        assert field("name").canonical is True

    def test_equipped_is_edge_backed_not_duplicated(self):
        assert field("equipped").lives_on == ON_EDGES
        assert "equipped" in EDGE_BACKED_FIELDS

    def test_current_area_is_edge_backed_not_duplicated(self):
        assert field("current_area").lives_on == ON_EDGES

    def test_derived_fields_are_not_canonical(self):
        """`Player.state` is computed; storing it would cache a stale value."""
        assert field("state").lives_on == DERIVED
        assert field("state").canonical is False

    def test_the_working_list_is_the_player_only_one(self):
        """The migration's work list, derived rather than hand-maintained."""
        expected = [f.name for f in DEFINITION_FIELDS
                    if f.canonical and f.lives_on == ON_PLAYER]
        assert PLAYER_ONLY_FIELDS == expected
        assert "stats" in PLAYER_ONLY_FIELDS
        assert "name" not in PLAYER_ONLY_FIELDS
        assert "equipped" not in PLAYER_ONLY_FIELDS

    def test_groups_cover_every_field(self):
        grouped = [f for fields in groups().values() for f in fields]
        assert {f.name for f in grouped} == {f.name for f in DEFINITION_FIELDS}

    def test_field_lookup(self):
        assert field("stats").group == "capability"
        assert field("no_such_field") is None

    def test_every_listed_field_exists_on_a_real_player(self):
        """A typo in the list would make the migration skip a real field."""
        player = Player("Probe")
        listed = set(CANONICAL_FIELDS) | {f.name for f in DEFINITION_FIELDS}
        unknown = sorted(n for n in listed if not hasattr(player, n))
        assert unknown == [], f"listed but not a Player attribute: {unknown}"


# ── the reader ──

class TestNodeDefinition:

    def test_a_missing_node_defines_nothing(self):
        assert node_definition(None) == {}

    def test_node_metadata_is_not_definition(self):
        world = _world()
        _character(world, "Fen")
        props = node_definition(_node(world, "Fen"))
        assert "name" not in props
        assert "type" not in props

    def test_a_bare_character_node_carries_no_definition(self):
        """The gap itself. If this ever goes green, task-457 has landed."""
        world = _world()
        _character(world, "Fen", stats={"STR": 14})
        assert node_definition(_node(world, "Fen")) == {}


class TestDefinitionDrift:

    def test_a_fresh_character_is_all_missing(self):
        world = _world()
        _character(world, "Fen")
        drift = definition_drift(_node(world, "Fen") and
                                 world.player_manager.get_player("Fen"),
                                 _node(world, "Fen"))
        assert "stats" in drift["missing"]
        assert "personality" in drift["missing"]

    def test_drift_never_lists_a_disagreeing_field_as_missing(self):
        world = _world()
        player = _character(world, "Fen")
        node = _node(world, "Fen")
        node.properties["personality"] = "grumpy"
        drift = definition_drift(player, node)
        assert "personality" in drift["differs"]
        assert "personality" not in drift["missing"]

    def test_drift_ignores_edge_backed_fields(self):
        """Storing `equipped` on the node too would duplicate the record."""
        world = _world()
        player = _character(world, "Fen")
        drift = definition_drift(player, _node(world, "Fen"))
        assert "equipped" not in drift["missing"]
        assert "current_area" not in drift["missing"]

    def test_drift_ignores_non_canonical_fields(self):
        world = _world()
        player = _character(world, "Fen")
        drift = definition_drift(player, _node(world, "Fen"))
        for name in ("memory_index", "recent_hearing", "activity",
                     "next_due_tick", "state"):
            assert name not in drift["missing"]
            assert name not in drift["differs"]

    def test_drift_ignores_fields_the_node_already_owns(self):
        """`name` is node metadata, so it can never be 'missing'."""
        world = _world()
        player = _character(world, "Fen")
        drift = definition_drift(player, _node(world, "Fen"))
        for name in ("name", "node_id"):
            assert name not in drift["missing"]
            assert name not in drift["differs"]

    def test_memories_are_canonical(self):
        """Unlike memory_index, the memories themselves are the record."""
        assert field("memories").canonical is True
        assert field("memory_index").canonical is False

    def test_drift_ignores_a_field_the_player_lacks(self):
        """A subclass without the field is not drift."""

        class Partial:
            name = "Partial"

        world = _world()
        drift = definition_drift(Partial(), None)
        assert "stats" not in drift["missing"]

    def test_matching_values_are_not_drift(self):
        world = _world()
        player = _character(world, "Fen", tags=["goblin", "teen"])
        node = _node(world, "Fen")
        node.properties["tags"] = ["goblin", "teen"]
        drift = definition_drift(player, node)
        assert "tags" not in drift["missing"]
        assert "tags" not in drift["differs"]

    def test_disagreeing_values_are_drift(self):
        world = _world()
        player = _character(world, "Fen", tags=["goblin"])
        node = _node(world, "Fen")
        node.properties["tags"] = ["elf"]
        assert "tags" in definition_drift(player, node)["differs"]

    def test_a_set_is_compared_by_content(self):
        world = _world()
        player = _character(world, "Fen", visited_areas={"a", "b"})
        node = _node(world, "Fen")
        node.properties["visited_areas"] = ["b", "a"]
        # a set and a list are structurally the same fact
        assert "visited_areas" not in definition_drift(player, node)["differs"]

    def test_is_canonical(self):
        world = _world()
        player = _character(world, "Fen")
        node = _node(world, "Fen")
        assert is_canonical(player, node) is False
        for name in PLAYER_ONLY_FIELDS:
            node.properties[name] = getattr(player, name, None)
        assert is_canonical(player, node) is True


class TestAudit:

    def test_audit_reports_the_characters_it_was_given(self):
        world = _world()
        _character(world, "Fen")
        _character(world, "Vekka")
        report = audit(world)
        # the world template ships its own characters, so check ours by name
        assert "Fen" in report["characters"]
        assert "Vekka" in report["characters"]
        assert {"Fen", "Vekka"} <= set(report["with_drift"])
        assert report["totally_canonical"] == []

    def test_audit_of_a_world_with_nobody_is_empty(self):
        world = _world()
        world.player_manager.players.clear()
        report = audit(world)
        assert report["characters"] == {}
        assert report["with_drift"] == []
        assert report["totally_canonical"] == []

    def test_audit_separates_the_canonical_from_the_drifted(self):
        world = _world()
        world.player_manager.players.clear()
        _character(world, "Fen")
        _character(world, "Vekka")
        vekka = world.player_manager.get_player("Vekka")
        node = _node(world, "Vekka")
        for name in PLAYER_ONLY_FIELDS:
            node.properties[name] = getattr(vekka, name, None)
        report = audit(world)
        assert report["totally_canonical"] == ["Vekka"]
        assert report["with_drift"] == ["Fen"]


def test_the_list_has_no_dead_weight():
    """A guard on the module's own honesty, cheap to keep."""
    canonical = set(CANONICAL_FIELDS)
    for entry in DEFINITION_FIELDS:
        if entry.canonical:
            assert entry.name in canonical
        else:
            assert entry.name not in canonical
