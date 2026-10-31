"""Unit tests for TriggerSystem effects, tag/trait mutations, and targeting."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from unittest.mock import MagicMock
from graph import Node, Edge, EDGE_TRIGGERS, EDGE_EQUIPPED, EDGE_CONNECTION
from engine.trigger_system import TriggerSystem
from engine.effects import Effects


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ Fixtures â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


@pytest.fixture
def graph():
    """Create a bare WorldGraph."""
    from graph import WorldGraph
    return WorldGraph()


@pytest.fixture
def skills():
    """Create a SkillSystem with mock dependencies."""
    from engine.skills import SkillSystem
    from engine.player_manager import PlayerManager
    from engine.logging_events import GameLogger
    pm = PlayerManager(None)  # graph can be None for basic tests
    return SkillSystem(pm, GameLogger())


@pytest.fixture
def logging_events():
    """Create a GameLogger."""
    from engine.logging_events import GameLogger
    return GameLogger()


@pytest.fixture
def trigger_system(graph, skills, logging_events):
    """Create a TriggerSystem with all dependencies."""
    return TriggerSystem(graph, skills, logging_events)


@pytest.fixture
def sample_item(graph):
    """Create a basic item node in the graph."""
    item = Node(
        id="item_test_item",
        type="item",
        name="Test Item",
        properties={
            "description": "A test item.",
            "uses": 1,
            "current_state": "normal",
            "actions": ["examine", "take", "use"],
        }
    )
    graph.add_node(item)
    return item




class TestEffects:
    """Effect execution through the Effects class."""

    def test_message_effect(self, graph, logging_events):
        """message effect returns the configured message."""
        effects = Effects(graph, logging_events)
        result = effects.execute("message", {"message": "Hello world!"}, {})
        assert result == ["Hello world!"]

    def test_message_effect_empty_message_returns_nothing(self, graph, logging_events):
        """message effect with no message produces no output (no "Something happens.")."""
        effects = Effects(graph, logging_events)
        result = effects.execute("message", {}, {})
        assert result == []

    @staticmethod
    def _make_game_state(player, extra_players=None):
        """Build a minimal duck-typed game_state for testing effect handlers."""
        game_state = type("FakeGameState", (), {})()
        game_state.player = player
        game_state.players = extra_players or {player.name: player}
        game_state.get_players_in_area = lambda area_name=None, exclude_self=True: []
        return game_state

    def test_damage_effect_self(self, graph, logging_events):
        """damage effect reduces the player's HP."""
        effects = Effects(graph, logging_events)
        from player import Player
        test_player = Player("TestPlayer")
        test_player.vitals["HP"] = 100
        game_state = self._make_game_state(test_player)

        result = effects.execute("damage", {"amount": 15}, {},
                                 game_state=game_state)
        assert test_player.vitals["HP"] == 85
        assert any("15 damage" in msg for msg in result)

    def test_heal_effect(self, graph, logging_events):
        """heal effect restores HP."""
        effects = Effects(graph, logging_events)
        from player import Player
        test_player = Player("TestPlayer")
        test_player.vitals["HP"] = 50
        game_state = self._make_game_state(test_player)

        result = effects.execute("heal", {"amount": 30, "stat": "HP"}, {},
                                 game_state=game_state)
        assert test_player.vitals["HP"] == 80
        assert any("restore 30 HP" in msg for msg in result)

    def test_damage_does_not_below_zero(self, graph, logging_events):
        """damage effect clamps HP to 0."""
        effects = Effects(graph, logging_events)
        from player import Player
        test_player = Player("TestPlayer")
        test_player.vitals["HP"] = 10
        game_state = self._make_game_state(test_player)

        effects.execute("damage", {"amount": 100}, {},
                        game_state=game_state)
        assert test_player.vitals["HP"] == 0

    def test_heal_does_not_exceed_100(self, graph, logging_events):
        """heal effect clamps HP to 100."""
        effects = Effects(graph, logging_events)
        from player import Player
        test_player = Player("TestPlayer")
        test_player.vitals["HP"] = 90
        game_state = self._make_game_state(test_player)

        effects.execute("heal", {"amount": 50, "stat": "HP"}, {},
                        game_state=game_state)
        assert test_player.vitals["HP"] == 100

    def test_adjust_vital(self, graph, logging_events):
        """adjust_vital modifies a vital stat."""
        effects = Effects(graph, logging_events)
        from player import Player
        test_player = Player("TestPlayer")
        test_player.vitals["Energy"] = 50
        game_state = self._make_game_state(test_player)

        result = effects.execute("adjust_vital",
                                 {"stat": "Energy", "amount": 20}, {},
                                 game_state=game_state)
        assert test_player.vitals["Energy"] == 70

    def test_adjust_vital_clamped(self, graph, logging_events):
        """adjust_vital clamps between 0 and 100."""
        effects = Effects(graph, logging_events)
        from player import Player
        test_player = Player("TestPlayer")
        test_player.vitals["Energy"] = 90
        game_state = self._make_game_state(test_player)

        effects.execute("adjust_vital",
                        {"stat": "Energy", "amount": 50}, {},
                        game_state=game_state)
        assert test_player.vitals["Energy"] == 100

    def test_adjust_vital_negative(self, graph, logging_events):
        """adjust_vital can reduce a vital stat."""
        effects = Effects(graph, logging_events)
        from player import Player
        test_player = Player("TestPlayer")
        test_player.vitals["Sanity"] = 80
        game_state = self._make_game_state(test_player)

        effects.execute("adjust_vital",
                        {"stat": "Sanity", "amount": -25}, {},
                        game_state=game_state)
        assert test_player.vitals["Sanity"] == 55

    def test_spawn_item(self, graph, logging_events):
        """spawn_item creates an item node in the current area."""
        effects = Effects(graph, logging_events)

        class FakeGameState:
            def get_current_area_id(self):
                return "area_Test_Room"

        from graph import Node
        area_node = Node(id="area_Test_Room", type="area", name="Test Area")
        graph.add_node(area_node)

        result = effects.execute("spawn_item",
                                 {"item_id": "item_new_sword",
                                  "name": "New Sword",
                                  "description": "A shiny new sword."}, {},
                                 game_state=FakeGameState())
        assert "New Sword" in result[0]
        spawned = graph.get_node("item_new_sword")
        assert spawned is not None
        assert spawned.name == "New Sword"

    def test_spawn_item_into_container(self, graph, logging_events):
        """spawn_item with into=container places a fresh item copy inside."""
        from graph import Node, EDGE_IN

        effects = Effects(graph, logging_events)
        container = Node(
            id="item_crate",
            type="item",
            name="crate",
            properties={"tags": ["container"], "max_weight_capacity": 2},
        )
        graph.add_node(container)

        result = effects.execute(
            "spawn_item",
            {"item_id": "item_key", "into": "container"},
            {},
            item_node=container,
            game_state=type("GS", (), {"get_current_area_id": lambda self: None})(),
        )
        assert "key" in result[0].lower()
        edges = graph.get_edges_for_target("item_crate", EDGE_IN)
        assert len(edges) == 1
        assert edges[0].source.startswith("item_key")

    def test_spawn_item_into_container_rejects_over_capacity(self, graph, logging_events):
        from graph import Node, EDGE_IN

        effects = Effects(graph, logging_events)
        container = Node(
            id="item_crate",
            type="item",
            name="crate",
            properties={"tags": ["container"], "max_weight_capacity": 2},
        )
        graph.add_node(container)

        result = effects.execute(
            "spawn_item",
            {"item_id": "item_anvil", "weight": 5, "into": "container"},
            {},
            item_node=container,
            game_state=type("GS", (), {"get_current_area_id": lambda self: None})(),
        )
        assert "can't hold" in result[0].lower()
        assert not graph.get_edges_for_target("item_crate", EDGE_IN)

    def test_give_item_rejects_when_over_capacity(self, graph, logging_events):
        """give_item respects player carry capacity (task-103 Phase 3)."""
        from graph import Node, Edge, EDGE_CARRYING
        from player import Player

        effects = Effects(graph, logging_events)
        graph.add_node(Node(id="player_Hero", type="player", name="Hero", properties={}))
        for item_id, weight in (("item_a", 60), ("item_b", 35)):
            graph.add_node(Node(id=item_id, type="item", name=item_id, properties={"weight": weight}))
            graph.add_edge(Edge(source=item_id, target="player_Hero", type=EDGE_CARRYING))
        graph.add_node(Node(id="item_heavy", type="item", name="heavy", properties={"weight": 10}))

        gs = type("GS", (), {"players": {}, "active_player": "Hero"})()

        result = effects.execute(
            "give_item",
            {"item_id": "item_heavy", "target": "self", "weight": 10},
            {},
            game_state=gs,
        )
        assert any("can't carry" in msg.lower() for msg in result)
        assert not any(
            e.source == "item_heavy"
            for e in graph.get_edges_for_target("player_Hero", EDGE_CARRYING)
        )

    def test_spawn_item_copies_heat_props_from_library(self, graph, logging_events):
        """spawn_item hydrates heat/light/contents props from the library file."""
        import json as _json
        import os as _os
        effects = Effects(graph, logging_events)

        class FakeGameState:
            def get_current_area_id(self):
                return "area_Test_Room"

        area_node = Node(id="area_Test_Room", type="area", name="Test Area")
        graph.add_node(area_node)

        result = effects.execute("spawn_item",
                                 {"item_id": "everflame_ember"}, {},
                                 game_state=FakeGameState())
        # Expectations come FROM the library entry, so retuning the data
        # doesn't stale the test  -  the contract is "spawn copies the library".
        lib_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                                 '..', 'data', 'library', 'items', 'everflame_ember.json')
        with open(lib_path, encoding='utf-8-sig') as f:
            lib = _json.load(f)
        assert lib["name"] in result[0]
        ember = graph.get_node("everflame_ember")
        assert ember is not None
        assert ember.properties["uses"] == lib.get("uses")
        assert ember.properties["current_state"] == lib.get("current_state")
        assert ember.properties["light_level"] == lib.get("light_level")
        assert ember.properties.get("target_temperature") == lib.get("target_temperature")
        assert ember.properties.get("heating_rate") == lib.get("heating_rate")
        assert ember.properties["contents"] == lib.get("contents", [])

    def test_spawn_item_materializes_triggers(self, graph, trigger_system, logging_events):
        """spawned library items get trigger nodes/edges so on_tick burns them down."""
        effects = Effects(graph, logging_events)

        game_state = type("FakeGameState", (), {})()
        game_state.get_current_area_id = lambda: "area_Test_Room"
        game_state.get_current_time = lambda: "10:00"
        game_state.time_ticks = 1
        game_state.turn_number = 1
        game_state.active_player = "TestPlayer"
        game_state.player = None
        game_state.current_area = None

        area_node = Node(id="area_Test_Room", type="area", name="Test Area")
        graph.add_node(area_node)

        effects.execute("spawn_item", {"item_id": "everflame_ember"}, {},
                        game_state=game_state)
        ember = graph.get_node("everflame_ember")

        trigger_edges = graph.get_edges_for_source("everflame_ember", EDGE_TRIGGERS)
        assert len(trigger_edges) == 2
        trigger_types = {e.properties["trigger_type"] for e in trigger_edges}
        assert trigger_types == {"on_tick", "on_depleted"}
        for edge in trigger_edges:
            trigger_node = graph.get_node(edge.target)
            assert trigger_node is not None
            assert trigger_node.type == "logic_trigger"
            assert "effects" in trigger_node.properties

        # Seed a known uses count  -  the library entry is user-tuned data and
        # may legitimately hold any value; this test verifies the burn-down.
        ember.properties["uses"] = 3
        trigger_system._execute_triggers(ember, "on_tick", game_state=game_state)
        assert ember.properties["uses"] == 2

    def test_spawn_character_from_library(self, graph, logging_events):
        """spawn_character hydrates a Player from the library and places them."""
        effects = Effects(graph, logging_events)

        class FakeGameState:
            def __init__(self, graph):
                self.graph = graph
                self.players = {}
                self.active_player = "TestPlayer"

            def get_current_area_id(self):
                return "area_Test_Room"

            def get_player(self, name):
                return self.players.get(name)

            def add_player(self, player_obj):
                self.players[player_obj.name] = player_obj
                self.active_player = player_obj.name
                from graph import Node
                player_node_id = f"player_{player_obj.name}".replace(' ', '_')
                if not self.graph.get_node(player_node_id):
                    self.graph.add_node(Node(id=player_node_id, type="character", name=player_obj.name))

            def set_player_area(self, name, area_name):
                from graph import Edge, EDGE_IN
                player_node_id = f"player_{name}".replace(' ', '_')
                area_id = f"area_{area_name.lower()}".replace(' ', '_')
                for edge in list(self.graph.get_edges_for_source(player_node_id, EDGE_IN)):
                    self.graph.remove_edge(edge.source, edge.target, edge.type)
                self.graph.add_edge(Edge(source=player_node_id, target=area_id, type=EDGE_IN))

        game_state = FakeGameState(graph)
        area_node = Node(id="area_Test_Room", type="area", name="Test Area")
        graph.add_node(area_node)

        result = effects.execute("spawn_character",
                                 {"character_id": "jake"}, {},
                                 game_state=game_state)
        # The library entry is the source of truth for display name + node id
        # casing (it was lowercased at some point; derive, don't hardcode).
        import json as _json
        import os as _os
        lib_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)),
                                 '..', 'data', 'library', 'characters', 'jake.json')
        with open(lib_path, encoding='utf-8-sig') as f:
            lib_name = _json.load(f)["name"]
        assert lib_name in result[0]
        player_node_id = f"player_{lib_name}".replace(' ', '_')
        player_node = graph.get_node(player_node_id)
        assert player_node is not None
        assert player_node.type == "character"
        area_edge = next(
            (e for e in graph.edges
             if e.source == player_node_id and e.type == "in"),
            None,
        )
        assert area_edge is not None
        assert area_edge.target == "area_test_area"

    def test_despawn_character_effect(self, graph, logging_events):
        """task-708: despawn_character removes a character from roster, lookup maps, and graph."""
        from engine.player_manager import PlayerManager
        from player import Player
        effects = Effects(graph, logging_events)

        class FakeGameState:
            def __init__(self, graph):
                self.graph = graph
                self.player_manager = PlayerManager(graph)
                self.players = self.player_manager.players
                self.active_player = None

        game_state = FakeGameState(graph)
        area_node = Node(id="area_chamber", type="area", name="Chamber")
        graph.add_node(area_node)

        ghost = Player("Casper")
        ghost.current_area = "Chamber"
        game_state.player_manager.add_player(ghost)
        assert "Casper" in game_state.player_manager.players
        ghost_node_id = game_state.player_manager.get_player_node_id("Casper")
        assert graph.get_node(ghost_node_id) is not None

        # Execute despawn_character effect with custom message
        result = effects.execute(
            "despawn_character",
            {"target": "Casper", "message": "{character_name} ascends into the light."},
            {},
            game_state=game_state
        )

        assert result == ["Casper ascends into the light."]
        assert "Casper" not in game_state.player_manager.players
        assert graph.get_node(ghost_node_id) is None
        assert not any(e.source == ghost_node_id for e in graph.edges)

        # Negative case: despawning again reports miss and removes nothing
        res2 = effects.execute("despawn_character", {"target": "Casper"}, {}, game_state=game_state)
        assert res2 == []

    def test_spawn_character_unknown_id(self, graph, logging_events):
        """spawn_character with unknown id returns empty (no-op)."""
        effects = Effects(graph, logging_events)
        result = effects.execute("spawn_character",
                                 {"character_id": "nonexistent_hero"}, {},
                                 game_state=type("GS", (), {"get_current_area_id": lambda: None})())
        assert result == []

    def test_destroy_self(self, graph, logging_events):
        """destroy_self removes the triggering item from the graph."""
        effects = Effects(graph, logging_events)
        item = Node(id="item_disposable", type="item", name="Disposable",
                    properties={})
        graph.add_node(item)

        effects.execute("destroy_self", {"message": "It crumbles!"}, {},
                        item_node=item)
        assert graph.get_node("item_disposable") is None

    def test_set_state(self, graph, logging_events):
        """set_state changes the current_state property on a node."""
        effects = Effects(graph, logging_events)
        chest = Node(id="item_chest", type="item", name="Chest",
                     properties={"current_state": "closed"})
        graph.add_node(chest)

        result = effects.execute("set_state",
                                 {"node_id": "item_chest", "state": "open"}, {})
        assert chest.properties["current_state"] == "open"
        assert "now open" in result[0]

    def test_set_state_self_resolves_to_host_node(self, graph, logging_events):
        """set_state with node_id 'self' targets the triggering node (door-lock pattern).

        The trigger editor authors node_id 'self' for the host node; the
        handler must resolve it to the way/item that fired the trigger.
        """
        effects = Effects(graph, logging_events)
        door = Node(id="way_test_door", type="way", name="Test Door",
                    properties={"current_state": "closed"})
        graph.add_node(door)

        result = effects.execute(
            "set_state",
            {"node_id": "self", "state": "locked",
             "message": "the door locks behind you"},
            {}, item_node=door)
        assert door.properties["current_state"] == "locked"
        assert "locks behind you" in result[0]

    def test_set_hidden_self_resolves_to_host_node(self, graph, logging_events):
        """set_hidden with node_id 'self' targets the triggering node."""
        effects = Effects(graph, logging_events)
        item = Node(id="item_trapdoor", type="item", name="Trapdoor",
                    properties={"current_state": "normal"})
        graph.add_node(item)

        effects.execute("set_hidden", {"node_id": "self", "hidden": True}, {},
                        item_node=item)
        assert item.properties["current_state"] == "hidden"

    def test_unlock_way(self, graph, logging_events):
        """unlock_way unlocks a way node to closed state."""
        effects = Effects(graph, logging_events)
        door = Node(id="way_test", type="way", name="Test Way",
                    properties={"current_state": "locked"})
        graph.add_node(door)

        effects.execute("unlock_way",
                        {"way_id": "way_test",
                         "message": "A lock clicks open!"}, {})
        assert door.properties["current_state"] == "closed"

    def test_unlock_way_target_fallback(self, graph, logging_events):
        """unlock_way with way_id 'target'/blank unlocks the on_use_on target."""
        effects = Effects(graph, logging_events)
        door = Node(id="way_vault", type="way", name="Vault Door",
                    properties={"current_state": "locked"})
        graph.add_node(door)

        result = effects.execute(
            "unlock_way",
            {"way_id": "target", "message": "The vault unlocks!"},
            {}, item_node=None, target_item_node=door)
        assert door.properties["current_state"] == "closed"
        assert "unlocks" in result[0]

        door2 = Node(id="way_office", type="way", name="Office Door",
                     properties={"current_state": "locked"})
        graph.add_node(door2)
        effects.execute("unlock_way", {}, {}, target_item_node=door2)
        assert door2.properties["current_state"] == "closed"

    def test_unlock_way_target_fallback_ignores_non_way(self, graph, logging_events):
        """unlock_way 'target' against a non-way target is a no-op."""
        effects = Effects(graph, logging_events)
        chest = Node(id="item_chest", type="item", name="Chest",
                     properties={"current_state": "closed"})
        graph.add_node(chest)

        result = effects.execute("unlock_way", {"way_id": "target"}, {},
                                 target_item_node=chest)
        assert result == []
        assert chest.properties["current_state"] == "closed"

    def test_adjust_uses(self, graph, logging_events):
        """adjust_uses changes the uses count on a node."""
        effects = Effects(graph, logging_events)
        item = Node(id="item_battery", type="item", name="Battery",
                    properties={"uses": 5})
        graph.add_node(item)

        effects.execute("adjust_uses",
                        {"node_id": "item_battery", "delta": -1}, {})
        assert item.properties["uses"] == 4

    def test_unknown_effect_type(self, graph, logging_events):
        """Unknown effect type returns an error message."""
        effects = Effects(graph, logging_events)
        result = effects.execute("teleport_to_moon", {}, {})
        assert len(result) == 1
        assert "Unknown effect" in result[0]

    def test_rename_defaults_to_triggering_item(self, graph, logging_events):
        """rename without node_id targets the triggering item node."""
        effects = Effects(graph, logging_events)
        photo = Node(id="item_photo", type="item", name="photo",
                     properties={})
        graph.add_node(photo)

        result = effects.execute("rename", {"name": "photo of james"}, {},
                                 item_node=photo)
        assert photo.name == "photo of james"
        assert photo.properties["name"] == "photo of james"
        assert "photo of james" in result[0]

    def test_rename_with_node_id(self, graph, logging_events):
        """rename with an explicit node_id targets that node, not the trigger."""
        effects = Effects(graph, logging_events)
        trigger = Node(id="item_locket", type="item", name="Locket",
                       properties={})
        other = Node(id="item_painting", type="item", name="painting",
                     properties={})
        graph.add_node(trigger)
        graph.add_node(other)

        effects.execute("rename", {"node_id": "item_painting",
                                   "name": "painting of the valerius estate"}, {},
                        item_node=trigger)
        assert trigger.name == "Locket"
        assert other.name == "painting of the valerius estate"

    def test_rename_self_targets_triggering_item(self, graph, logging_events):
        """rename with node_id='self' targets the triggering item."""
        effects = Effects(graph, logging_events)
        vial = Node(id="item_vial", type="item", name="vial",
                    properties={})
        graph.add_node(vial)

        effects.execute("rename", {"node_id": "self", "name": "Vial of Antidote"}, {},
                        item_node=vial)
        assert vial.name == "Vial of Antidote"

    def test_rename_missing_name_returns_empty(self, graph, logging_events):
        """rename with no name is a no-op (no output, no change)."""
        effects = Effects(graph, logging_events)
        item = Node(id="item_test", type="item", name="Test",
                    properties={})
        graph.add_node(item)

        result = effects.execute("rename", {}, {}, item_node=item)
        assert result == []
        assert item.name == "Test"


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ TestTemplateRendering â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


class TestAddRemoveTagEffect:
    """add_tag / remove_tag trigger effects (task-169)."""

    def _make_item(self, graph, tags=None):
        item = Node(
            id="item_tagged",
            type="item",
            name="Tagged Item",
            properties={"description": "An item.", "tags": tags or []},
        )
        graph.add_node(item)
        return item

    def test_add_tag_adds_to_properties(self, graph, logging_events):
        effects = Effects(graph, logging_events)
        item = self._make_item(graph)
        result = effects.execute("add_tag", {"tag": "flammable", "node_id": item.id}, {}, item_node=item)
        assert "flammable" in item.properties["tags"]
        assert any("flammable" in msg for msg in result)

    def test_remove_tag_removes(self, graph, logging_events):
        effects = Effects(graph, logging_events)
        item = self._make_item(graph, tags=["flammable", "tool"])
        result = effects.execute("remove_tag", {"tag": "flammable", "node_id": item.id}, {}, item_node=item)
        assert "tool" in item.properties["tags"]
        assert "flammable" not in item.properties["tags"]
        assert any("Removed tag" in msg for msg in result)

    def test_works_with_comma_string_tags(self, graph, logging_events):
        effects = Effects(graph, logging_events)
        item = self._make_item(graph, tags="flammable,tool")
        effects.execute("add_tag", {"tag": "magic", "node_id": item.id}, {}, item_node=item)
        assert isinstance(item.properties["tags"], list)
        assert "magic" in item.properties["tags"]
        assert "flammable" in item.properties["tags"]

    def test_tag_based_targeting_sees_new_tag(self, graph, skills, logging_events):
        """After add_tag, tag-based targeting in the same trigger finds the item."""
        trigger_system = TriggerSystem(graph, skills, logging_events)
        area = Node(id="area_test", type="area", name="Test",
                    properties={"environment": {}})
        graph.add_node(area)
        item = self._make_item(graph)
        from graph import EDGE_IN
        graph.add_edge(Edge(source=item.id, target=area.id, type=EDGE_IN))

        # Trigger that tags the item with light_source on use
        graph.add_edge(Edge(
            source=item.id,
            target="trigger_tag",  # stub target â€” effects live on the edge
            type=EDGE_TRIGGERS,
            properties={
                "trigger_type": "on_use",
                "effects": [{"type": "add_tag", "params": {"tag": "light_source", "node_id": "self"}}]
            }
        ))

        trigger_system._execute_triggers(item, "on_use")
        assert "light_source" in item.properties["tags"]

        # Tag-based targeting must now see the item
        matches = trigger_system._get_items_by_tag_in_area("light_source", None, "area_test")
        assert any(m.id == item.id for m in matches)


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ TestApplyRemoveTraitEffect â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


class TestApplyRemoveTraitEffect:
    """apply_trait / remove_trait trigger effects."""

    @staticmethod
    def _make_game_state(player, extra_players=None):
        game_state = type("FakeGameState", (), {})()
        game_state.player = player
        game_state.players = extra_players or {player.name: player}
        game_state.active_player = player.name
        game_state.get_players_in_area = lambda area_name=None, exclude_self=True: []
        game_state.log_entries = []
        game_state.add_log_entry = lambda text: game_state.log_entries.append(text)
        return game_state

    def test_apply_trait_self(self, graph, logging_events):
        from player import Player
        effects = Effects(graph, logging_events)
        test_player = Player("TestPlayer")
        game_state = self._make_game_state(test_player)

        result = effects.execute(
            "apply_trait", {"trait": "dark_vision", "target": "self", "param": True},
            {}, game_state=game_state,
        )
        assert test_player.traits.get("dark_vision") is True
        # Silent by default â€” no message unless the author specifies one.
        assert result == []

    def test_apply_trait_self_with_message(self, graph, logging_events):
        from player import Player
        effects = Effects(graph, logging_events)
        test_player = Player("TestPlayer")
        game_state = self._make_game_state(test_player)

        result = effects.execute(
            "apply_trait", {"trait": "dark_vision", "target": "self", "param": True,
                            "message": "Your eyes adjust to the dark."},
            {}, game_state=game_state,
        )
        assert test_player.traits.get("dark_vision") is True
        assert "Your eyes adjust to the dark." in result

    def test_apply_trait_with_param(self, graph, logging_events):
        from player import Player
        effects = Effects(graph, logging_events)
        test_player = Player("TestPlayer")
        game_state = self._make_game_state(test_player)

        effects.execute(
            "apply_trait", {"trait": "allergic", "target": "self", "param": "pollen"},
            {}, game_state=game_state,
        )
        assert test_player.traits.get("allergic") == "pollen"

    def test_apply_trait_to_named_target(self, graph, logging_events):
        from player import Player
        effects = Effects(graph, logging_events)
        actor = Player("Actor")
        other = Player("Other")
        game_state = self._make_game_state(actor, {"Actor": actor, "Other": other})

        effects.execute(
            "apply_trait", {"trait": "hardy", "target": "Other", "param": True},
            {}, game_state=game_state,
        )
        assert other.traits.get("hardy") is True
        assert actor.traits.get("hardy") is None

    def test_apply_trait_to_named_target_is_silent_for_actor(self, graph, logging_events):
        """A trait granted to someone else must not be announced in the ACTOR's
        output â€” otherwise pressing a button reads back as 'I gained Hostile'."""
        from player import Player
        effects = Effects(graph, logging_events)
        actor = Player("Actor")
        other = Player("Other")
        game_state = self._make_game_state(actor, {"Actor": actor, "Other": other})

        result = effects.execute(
            "apply_trait", {"trait": "hostile", "target": "Other", "param": True},
            {}, game_state=game_state,
        )
        assert other.traits.get("hostile") is True
        assert actor.traits.get("hostile") is None
        assert result == []

    def test_remove_trait_from_named_target_is_silent_for_actor(self, graph, logging_events):
        """Same for remove_trait: only the affected player hears about it."""
        from player import Player
        effects = Effects(graph, logging_events)
        actor = Player("Actor")
        other = Player("Other")
        other.traits["hostile"] = True
        game_state = self._make_game_state(actor, {"Actor": actor, "Other": other})

        result = effects.execute(
            "remove_trait", {"trait": "hostile", "target": "Other"},
            {}, game_state=game_state,
        )
        assert "hostile" not in other.traits
        assert result == []

    def test_remove_trait_self(self, graph, logging_events):
        from player import Player
        effects = Effects(graph, logging_events)
        test_player = Player("TestPlayer")
        test_player.traits["dark_vision"] = True
        game_state = self._make_game_state(test_player)

        result = effects.execute(
            "remove_trait", {"trait": "dark_vision", "target": "self"},
            {}, game_state=game_state,
        )
        assert "dark_vision" not in test_player.traits
        # Silent by default â€” no message unless the author specifies one.
        assert result == []

    def test_remove_trait_self_with_message(self, graph, logging_events):
        from player import Player
        effects = Effects(graph, logging_events)
        test_player = Player("TestPlayer")
        test_player.traits["dark_vision"] = True
        game_state = self._make_game_state(test_player)

        result = effects.execute(
            "remove_trait", {"trait": "dark_vision", "target": "self",
                             "message": "Your dark vision fades."},
            {}, game_state=game_state,
        )
        assert "dark_vision" not in test_player.traits
        assert "Your dark vision fades." in result

    def test_remove_trait_missing_is_noop(self, graph, logging_events):
        from player import Player
        effects = Effects(graph, logging_events)
        test_player = Player("TestPlayer")
        game_state = self._make_game_state(test_player)

        result = effects.execute(
            "remove_trait", {"trait": "hardy", "target": "self"},
            {}, game_state=game_state,
        )
        assert result == []  # silent no-op â€” no message specified
        assert test_player.traits == {}

    def test_apply_trait_no_id_returns_nothing(self, graph, logging_events):
        from player import Player
        effects = Effects(graph, logging_events)
        test_player = Player("TestPlayer")
        game_state = self._make_game_state(test_player)

        result = effects.execute(
            "apply_trait", {"target": "self"}, {}, game_state=game_state,
        )
        assert result == []

    def test_apply_condition_no_id_returns_nothing(self, graph, logging_events):
        from player import Player
        effects = Effects(graph, logging_events)
        test_player = Player("TestPlayer")
        game_state = self._make_game_state(test_player)
        game_state.conditions = type("C", (), {
            "apply_condition": lambda *a, **k: None,
            "remove_condition": lambda *a, **k: None,
        })()

        result = effects.execute(
            "apply_condition", {"target": "self"}, {}, game_state=game_state,
        )
        assert result == []

    def test_apply_condition_with_symptoms_and_extras(self, graph, logging_events):
        """apply_condition carries per-instance symptoms + extra conditions."""
        from player import Player
        from unittest.mock import MagicMock
        effects = Effects(graph, logging_events)
        test_player = Player("TestPlayer")
        game_state = self._make_game_state(test_player)

        captured = {}
        game_state.conditions = MagicMock()
        game_state.conditions.apply_condition = lambda *a, **k: captured.update(k)

        effects.execute(
            "apply_condition", {
                "condition": "poisoned", "target": "self", "duration": 10,
                "source": "poisoned wine", "periodic": {"HP": -8},
                "symptoms": {"8": "queasy", "1": "spinning"},
                "extra_conditions": [{"condition": "blind", "duration": 3}],
            },
            {}, game_state=game_state,
        )
        assert captured["duration"] == 10
        assert captured["periodic"] == {"HP": -8}
        assert captured["symptoms"] == {"8": "queasy", "1": "spinning"}
        assert captured["extra_conditions"] == [{"condition": "blind", "duration": 3}]

    def test_apply_trait_conflict_is_system_message_not_agent_output(self, graph, logging_events):
        """A conflicting trait grant surfaces in the SYSTEM log (event stream /
        UI) but never in the agent's action result."""
        from player import Player
        effects = Effects(graph, logging_events)
        test_player = Player("TestPlayer")
        test_player.traits["night_owl"] = True
        game_state = self._make_game_state(test_player)

        result = effects.execute(
            "apply_trait", {"trait": "morning_person", "target": "self", "param": True},
            {}, game_state=game_state,
        )
        # Agent sees nothing...
        assert result == []
        # ...but the system log records the conflict.
        assert any("conflict" in e for e in game_state.log_entries)
        assert test_player.traits.get("morning_person") is None


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ TestTriggerTestHelper â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


class TestUnifiedEffectTargeting:
    """target_by name/tag/trait/type/all_in_area fan-out for trigger effects."""

    @staticmethod
    def _world():
        from app import create_app
        app = create_app({'TESTING': True})
        return app.world, app.test_client()

    def _add_players(self, world, names):
        from player import Player
        world.set_active_player(names[0])
        for name in names:
            world.add_player(Player(name))
            world.set_player_area(name, 'Blizzard Forest Clearing')
            world.player_manager.players[name].current_area = 'Blizzard Forest Clearing'

    def _run_condition(self, world, params):
        from graph import Node, Edge, EDGE_TRIGGERS
        cloud = Node(id=f'item_t_{abs(hash(str(params)))%100000}', type='item', name='cloud', properties={})
        world.graph.add_node(cloud)
        world.graph.add_edge(Edge(source=cloud.id, target='trig_t', type='triggers', properties={
            'trigger_type': ['on_tick'],
            'effects': [{'type': 'apply_condition', 'params': dict(params)}],
        }))
        for p in world.player_manager.players.values():
            p.conditions.pop('sick', None)
        world.triggers._execute_triggers(cloud, 'on_tick', game_state=world)
        return sorted(n for n, p in world.player_manager.players.items() if p.conditions.get('sick'))

    def test_by_name(self):
        world, _ = self._world()
        self._add_players(world, ['Kaelen Voss', 'Other'])
        got = self._run_condition(world, {'condition': 'sick', 'target_by': 'name', 'target_value': 'Other', 'duration': 5})
        assert got == ['Other']

    def test_by_trait(self):
        world, _ = self._world()
        self._add_players(world, ['Kaelen Voss', 'Other'])
        world.player_manager.players['Kaelen Voss'].traits['hostile'] = True
        got = self._run_condition(world, {'condition': 'sick', 'target_by': 'trait', 'target_value': 'hostile', 'duration': 5})
        assert got == ['Kaelen Voss']

    def test_by_tag(self):
        world, _ = self._world()
        self._add_players(world, ['Kaelen Voss', 'Other'])
        world.player_manager.players['Other'].tags = ['wolf']
        got = self._run_condition(world, {'condition': 'sick', 'target_by': 'tag', 'target_value': 'wolf', 'duration': 5})
        assert got == ['Other']

    def test_by_type_character_area(self):
        world, _ = self._world()
        self._add_players(world, ['Kaelen Voss', 'Other'])
        got = self._run_condition(world, {'condition': 'sick', 'target_by': 'type', 'target_value': 'character', 'target_scope': 'area', 'duration': 5})
        assert 'Kaelen Voss' in got and 'Other' in got

    def test_all_in_area(self):
        world, _ = self._world()
        self._add_players(world, ['Kaelen Voss', 'Other'])
        got = self._run_condition(world, {'condition': 'sick', 'target_by': 'all_in_area', 'duration': 5})
        assert 'Kaelen Voss' in got and 'Other' in got

    def test_legacy_target_tag_still_works(self):
        from graph import Node, Edge, EDGE_TRIGGERS
        world, _ = self._world()
        world.set_active_player('Kaelen Voss')
        area = 'Blizzard Forest Clearing'
        torch = Node(id='item_torch', type='item', name='torch', properties={'tags': ['flammable']})
        world.graph.add_node(torch)
        world.graph.add_edge(Edge(source=torch.id, target='area_blizzard_forest_clearing', type='in'))
        cloud = Node(id='item_t_legacy', type='item', name='cloud', properties={})
        world.graph.add_node(cloud)
        world.graph.add_edge(Edge(source=cloud.id, target='trig_t', type='triggers', properties={
            'trigger_type': ['on_tick'],
            'effects': [{'type': 'set_state', 'params': {'target_tag': 'flammable', 'state': 'extinguished'}}],
        }))
        world.triggers._execute_triggers(cloud, 'on_tick', game_state=world)
        assert torch.properties.get('current_state') == 'extinguished'


# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€ TestGiveItemEffect â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


class TestGiveItemEffect:
    """give_item places a library item directly into a character's inventory."""

    @staticmethod
    def _world():
        from app import create_app
        app = create_app({'TESTING': True})
        return app.world, app.test_client()

    def _fire(self, world, params, trigger_type="on_use", item_name="giver"):
        from graph import Node, Edge
        src = Node(id=f'item_{item_name}_{abs(hash(str(params)))%100000}', type='item', name=item_name, properties={})
        world.graph.add_node(src)
        world.graph.add_edge(Edge(source=src.id, target='trig_g', type='triggers', properties={
            'trigger_type': [trigger_type],
            'effects': [{'type': 'give_item', 'params': dict(params)}],
        }))
        return world.triggers._execute_triggers(src, trigger_type, game_state=world)

    def _carried(self, world, player_name):
        player_id = f"player_{player_name}".replace(' ', '_')
        ids = [e.source for e in world.graph.edges if e.type == 'carrying' and e.target == player_id]
        return [world.graph.get_node(i).name for i in ids if world.graph.get_node(i)]

    def _carried_matches(self, world, player_name, needle):
        return any(needle.lower() in name.lower() for name in self._carried(world, player_name))

    def test_give_to_self(self):
        world, _ = self._world()
        world.set_active_player('Kaelen Voss')
        outs = self._fire(world, {'item_id': 'rotten_meat', 'target': 'self'})
        assert self._carried_matches(world, 'Kaelen Voss', 'Rotten Meat')
        # triggers from the library were materialized onto the given item
        carried_id = next(e.source for e in world.graph.edges
                          if e.type == 'carrying' and e.target == 'player_Kaelen_Voss')
        assert len(world.graph.get_edges_for_source(carried_id, 'triggers')) >= 1

    def test_give_to_named_character(self):
        from player import Player
        world, _ = self._world()
        world.set_active_player('Kaelen Voss')
        world.add_player(Player('Other'))
        world.set_player_area('Other', 'Blizzard Forest Clearing')
        self._fire(world, {'item_id': 'bandages', 'target': 'Other'})
        assert self._carried_matches(world, 'Other', 'bandages')

    def test_give_to_on_use_on_target(self):
        world, _ = self._world()
        world.set_active_player('Kaelen Voss')
        outs = self._fire(world, {'item_id': 'bandages', 'target': 'target'}, trigger_type='on_use_on')
        assert self._carried_matches(world, 'Kaelen Voss', 'bandages')

    def test_give_unknown_id_creates_blank_item(self):
        world, _ = self._world()
        world.set_active_player('Kaelen Voss')
        # Consistent with spawn_item: unknown ids still materialize a blank node.
        self._fire(world, {'item_id': 'brand_new_gadget', 'target': 'self'})
        assert self._carried_matches(world, 'Kaelen Voss', 'brand_new_gadget')

    def test_carried_item_fires_on_tick(self):
        """A hidden carried item's on_tick trigger fires on tick_turn â€”
        the contagion/sneeze-cloud pattern (carriers aren't 'lit')."""
        from graph import Node, Edge
        world, _ = self._world()
        world.set_active_player('Kaelen Voss')
        player_id = 'player_Kaelen_Voss'
        carrier = Node(id='item_carrier', type='item', name='carrier', properties={
            'current_state': 'hidden', 'uses': -1, 'actions': 'examine,take,use'})
        world.graph.add_node(carrier)
        world.graph.add_edge(Edge(source='item_carrier', target=player_id, type='carrying'))
        world.graph.add_edge(Edge(source='item_carrier', target='trig_c', type='triggers', properties={
            'trigger_type': ['on_tick'],
            'effects': [{'type': 'apply_condition', 'params': {
                'condition': 'sick', 'target_by': 'all_in_area', 'duration': 8, 'source': 'miasma'}}],
            'conditions': {'operator': 'and', 'conditions': [
                {'type': 'random_chance', 'value': 100}]},
        }))
        player = world.player_manager.players['Kaelen Voss']
        player.conditions.pop('sick', None)
        world.tick_turn()
        assert player.has_condition('sick')


class TestLegacyTriggerEffects:
    """Legacy effect_type/effect_params shim (pre-migration scenario triggers)."""

    def _wire_legacy_trigger(self, graph, item, trigger_type, effect_type, effect_params):
        props = {
            "trigger_type": trigger_type,
            "effect_type": effect_type,
            "effect_params": effect_params,
            "target_name": "",
        }
        trigger_id = f"trigger_{item.id}_{trigger_type}"
        tnode = Node(id=trigger_id, type="logic_trigger", name="legacy", properties=props)
        graph.add_node(tnode)
        graph.add_edge(Edge(source=item.id, target=trigger_id, type=EDGE_TRIGGERS, properties=props))

    def test_legacy_message_on_examine(self, graph, trigger_system, sample_item):
        self._wire_legacy_trigger(
            graph,
            sample_item,
            "on_examine",
            "message",
            {"message": "You notice a scratch on the tile."},
        )
        outputs = trigger_system._execute_triggers(sample_item, "on_examine", game_state=None)
        assert outputs == ["You notice a scratch on the tile."]

    def test_legacy_damage_splits_narrative(self, graph, trigger_system, sample_item):
        hero = MagicMock()
        hero.vitals = {"HP": 100}
        hero.name = "Hero"
        game_state = MagicMock()
        game_state.player = hero
        game_state.players = {"Hero": hero}
        game_state.activities = MagicMock()
        game_state.activities.wake_on_damage.return_value = None

        self._wire_legacy_trigger(
            graph,
            sample_item,
            "on_take",
            "damage",
            {
                "amount": 8,
                "target": "self",
                "message": "A searing cold shoots up your arm.",
            },
        )
        outputs = trigger_system._execute_triggers(sample_item, "on_take", game_state=game_state)
        assert hero.vitals["HP"] == 92
        assert any("takes 8 damage" in line for line in outputs)
        assert "A searing cold shoots up your arm." in outputs

    def test_modern_effects_take_precedence_over_legacy(self, graph, trigger_system, sample_item):
        props = {
            "trigger_type": ["on_examine"],
            "effect_type": "message",
            "effect_params": {"message": "legacy text"},
            "effects": [{"type": "message", "params": {"message": "modern text"}}],
        }
        trigger_id = "trigger_hybrid"
        graph.add_node(Node(id=trigger_id, type="logic_trigger", name="hybrid", properties=props))
        graph.add_edge(Edge(source=sample_item.id, target=trigger_id, type=EDGE_TRIGGERS, properties=props))
        outputs = trigger_system._execute_triggers(sample_item, "on_examine", game_state=None)
        assert outputs == ["modern text"]
