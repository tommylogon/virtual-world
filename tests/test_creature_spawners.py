"""Creature spawners, population caps, and the death/carcass path (task-427).

A creature spawner is a *source*, not a creature: an untagged standing item that
grows a counter and spawns a library character while the area holds fewer than N
tagged creatures (`tagged_count`). Killing the creature drops a carcass that is
ordinary food — never a bare "survival check → meat" dispenser.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from graph import Node, Edge, EDGE_IN
from player import Player


def _world():
    return create_app({"TESTING": True}).world


def _area(world, node_id="area_test_meadow", name="Test Meadow"):
    node = Node(id=node_id, type="area", name=name, properties={})
    world.graph.add_node(node)
    return node


def _add_character(world, name, area_name, tags, carcass=None):
    """Register a live character in an area; returns its registry key."""
    p = Player(name)
    p.tags = list(tags)
    p.carcass_item = carcass
    prev = world.active_player
    world.add_player(p)
    key = world.active_player
    world.active_player = prev
    world.player_manager.players[key].current_area = area_name
    return key


def _rabbit(world, name, area_name):
    return _add_character(world, name, area_name, ["animal", "rabbit"], carcass="carcass")


def _burrow(world, area):
    burrow, _ = world.effects._hydrate_item("rabbit_burrow", {}, always_fresh=True)
    world.graph.add_edge(Edge(source=burrow.id, target=area.id, type=EDGE_IN))
    return burrow


def _count(world, condition, anchor=None):
    return world.triggers._evaluate_conditions(
        condition, {"item_node": anchor}, game_state=world
    )


# ── tagged_count ─────────────────────────────────────────────────────────


class TestTaggedCount:
    def test_counts_tagged_characters_in_a_named_area(self):
        world = _world()
        area = _area(world)
        _rabbit(world, "A", area.name)
        _rabbit(world, "B", area.name)
        _rabbit(world, "Elsewhere", "Another Place")

        assert _count(world, {"type": "tagged_count", "target_has_tag": "rabbit",
                              "area": area.name, "value": 2}) is True
        assert _count(world, {"type": "tagged_count", "target_has_tag": "rabbit",
                              "area": area.name, "value": 3}) is False

    def test_lt_is_the_population_cap_check(self):
        world = _world()
        area = _area(world)
        for i in range(4):
            _rabbit(world, f"R{i}", area.name)
        full = {"type": "tagged_count", "target_has_tag": "rabbit",
                "area": area.name, "value": 4, "op": "lt"}
        assert _count(world, full) is False
        # One leaves the area: the cap opens again.
        world.player_manager.players["R3"].current_area = "Elsewhere"
        assert _count(world, full) is True

    def test_world_scope_counts_everywhere(self):
        world = _world()
        area = _area(world)
        _rabbit(world, "A", area.name)
        _rabbit(world, "Far", "Another Place")
        assert _count(world, {"type": "tagged_count", "target_has_tag": "rabbit",
                              "area": "world", "value": 2}) is True

    def test_current_scope_uses_the_anchoring_items_area(self):
        """A burrow counts rabbits where the burrow is, not where the actor is."""
        world = _world()
        area = _area(world, "area_burrow", "Burrow Field")
        _rabbit(world, "Near", area.name)
        _rabbit(world, "Far", "Somewhere Else")
        burrow = _burrow(world, area)

        cap = {"type": "tagged_count", "target_has_tag": "rabbit",
               "area": "current", "value": 2, "op": "lt"}
        assert _count(world, cap, burrow) is True     # only "Near" counts
        assert _count(world, {"type": "tagged_count", "target_has_tag": "rabbit",
                              "area": "current", "value": 1, "op": "eq"}, burrow) is True
        assert _count(world, {"type": "tagged_count", "target_has_tag": "rabbit",
                              "area": "current", "value": 2, "op": "eq"}, burrow) is False

    def test_missing_tag_fails_safe(self):
        world = _world()
        assert _count(world, {"type": "tagged_count", "value": 1}) is False

    def test_registered_with_the_validator(self):
        from engine.trigger_validator import CONDITION_TYPES
        assert "tagged_count" in CONDITION_TYPES


# ── the burrow spawner ───────────────────────────────────────────────────


class TestBurrowSpawner:
    def test_cap_blocks_the_fifth_rabbit(self):
        world = _world()
        area = _area(world)
        burrow = _burrow(world, area)
        burrow.properties.setdefault("parameters", {})["growth"] = 100

        gate = [
            {"type": "parameter_reached", "key": "growth", "value": 100},
            {"type": "tagged_count", "target_has_tag": "rabbit",
             "area": "current", "value": 4, "op": "lt"},
        ]
        for i in range(3):
            _rabbit(world, f"R{i}", area.name)
        assert _count(world, gate, burrow) is True
        _rabbit(world, "R4", area.name)
        assert _count(world, gate, burrow) is False

    def test_spawn_character_lands_in_the_burrows_area(self):
        world = _world()
        area = _area(world, "area_spawn_here", "Spawn Here")
        burrow = _burrow(world, area)

        world.effects.handle_spawn_character(
            {"character_id": "rabbit"}, {}, item_node=burrow, game_state=world
        )

        rabbit = next(p for p in world.player_manager.players.values() if p.name == "Rabbit")
        assert rabbit.current_area == "Spawn Here"

    def test_spawner_is_not_edible(self):
        from engine.background_simulation import FOOD_TAGS
        world = _world()
        area = _area(world)
        burrow = _burrow(world, area)
        tags = {str(t).lower() for t in (burrow.properties.get("tags") or [])}
        assert not (tags & {t.lower() for t in FOOD_TAGS})
        assert burrow.type == "item"  # an item, never a huntable creature


# ── template + death path ────────────────────────────────────────────────


class TestCreatureTemplate:
    def test_rabbit_hydrates_with_species_tag_and_carcass(self):
        world = _world()
        p, lib = world.effects._hydrate_character("rabbit", {}, world, always_fresh=True)
        assert p is not None
        assert "rabbit" in [t.lower() for t in p.tags]
        assert p.carcass_item == "carcass"


class TestDeathYieldsCarcass:
    def _carcasses(self, world):
        return [n for n in world.graph.nodes.values()
                if n.type == "item" and "carcass" in (n.properties.get("tags") or [])]

    def test_creature_death_drops_a_carcass_not_a_body(self):
        world = _world()
        area = _area(world)
        key = _rabbit(world, "Bunny", area.name)

        world._spawn_body_item(key, "slain by a hunter")

        carcasses = self._carcasses(world)
        assert carcasses, "a killed creature must yield a carcass"
        carcass = carcasses[0]
        assert "food" in carcass.properties["tags"]
        assert any(e.target == area.id
                   for e in world.graph.get_edges_for_source(carcass.id, EDGE_IN))
        assert world.graph.get_node(f"body_{key}") is None

    def test_human_death_still_leaves_a_body(self):
        world = _world()
        area = _area(world)
        key = _add_character(world, "Human", area.name, ["human"], carcass=None)

        world._spawn_body_item(key, "the cold")

        assert world.graph.get_node(f"body_{key}") is not None
        assert not self._carcasses(world)

    def test_carcass_carries_a_depleting_authored_eat_trigger(self):
        world = _world()
        area = _area(world)
        key = _rabbit(world, "Snack", area.name)
        world._spawn_body_item(key, "slain")

        carcass = self._carcasses(world)[0]
        triggers = [
            world.graph.get_node(e.target)
            for e in world.graph.get_edges_for_source(carcass.id, "triggers")
        ]
        assert any(t is not None and t.properties.get("trigger_type") == "on_eat"
                   for t in triggers), "carcass must be food via task-424's path"

    def test_two_deaths_leave_two_separate_carcasses(self):
        world = _world()
        area = _area(world)
        k1 = _rabbit(world, "One", area.name)
        k2 = _rabbit(world, "Two", area.name)
        world._spawn_body_item(k1, "slain")
        world._spawn_body_item(k2, "slain")
        assert len(self._carcasses(world)) == 2
