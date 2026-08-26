"""Tests for the GhostSystem: ghost action blocking and body item spawning."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from graph import WorldGraph, Node, Edge, EDGE_IN
from engine.ghost import GhostSystem
from engine.logging_events import GameLogger


class FakeVirtualWorld:
    """Duck-typed VirtualWorld for GhostSystem tests.

    Provides the minimal interface GhostSystem expects:
    - ``.players`` dict of {name: Player}
    - ``.active_player`` string
    - ``.ghost_mode`` bool
    - ``.skill_check(skill_name, dc)`` returning (success, total, message)
    """
    def __init__(self):
        self.players = {}
        self.active_player = None
        self.ghost_mode = False

    def skill_check(self, skill_name, difficulty_class=15):
        """Default stub: always fails the check."""
        return (False, 0, "Roll failed - ghost cannot interact")


class FakeSkillCheckSuccess(FakeVirtualWorld):
    """Variant that always succeeds on skill checks."""
    def skill_check(self, skill_name, difficulty_class=15):
        return (True, 20, "Roll succeeded")


# ─────────────────── Fixtures ───────────────────


@pytest.fixture
def graph():
    """Create a bare WorldGraph."""
    return WorldGraph()


@pytest.fixture
def logging_events():
    """Create a GameLogger."""
    return GameLogger()


@pytest.fixture
def ghost_system(graph, logging_events):
    """Create a GhostSystem with stub dependencies."""
    skills_stub = FakeVirtualWorld()
    return GhostSystem(graph, skills_stub, logging_events)


# ─────────────────── TestCheckGhostAction ───────────────────


class TestCheckGhostAction:
    """Ghost action blocking for dead players."""

    # ── Basic alive / dead ─────────────────────────────────────────

    def test_alive_player_not_blocked(self, ghost_system):
        """Alive players are not blocked by ghost checks."""
        world = FakeVirtualWorld()
        from player import Player
        hero = Player("AliveHero")
        hero.state = "awake"
        world.players["AliveHero"] = hero
        world.active_player = "AliveHero"
        world.ghost_mode = False

        result = ghost_system.check_ghost_action(world, "look")
        assert result is None

    def test_dead_player_no_ghost_mode(self, ghost_system):
        """Dead players with ghost_mode off get a blocking message."""
        world = FakeVirtualWorld()
        from player import Player
        dead = Player("DeadHero")
        dead.state = "dead"
        world.players["DeadHero"] = dead
        world.active_player = "DeadHero"
        world.ghost_mode = False

        result = ghost_system.check_ghost_action(world, "look")
        assert result is not None
        assert "cannot" in result.lower() or "nothing" in result.lower()

    def test_no_active_player_returns_none(self, ghost_system):
        """With no active player, the check passes through (not blocked)."""
        world = FakeVirtualWorld()
        world.active_player = None
        result = ghost_system.check_ghost_action(world, "look")
        assert result is None

    # ── Free ghost actions ─────────────────────────────────────────

    @pytest.mark.parametrize("free_action", [
        "look", "inventory", "stats", "status", "examine", "fumble"
    ])
    def test_free_actions_allowed(self, ghost_system, free_action):
        """Free ghost actions (look, inventory, etc.) are allowed."""
        world = FakeVirtualWorld()
        from player import Player
        ghost = Player("GhostFree")
        ghost.state = "dead"
        world.players["GhostFree"] = ghost
        world.active_player = "GhostFree"
        world.ghost_mode = True

        result = ghost_system.check_ghost_action(world, free_action)
        assert result is None, f"{free_action} should be allowed"

    def test_manifest_allowed(self, ghost_system):
        """'manifest' action is always allowed for ghosts."""
        world = FakeVirtualWorld()
        from player import Player
        ghost = Player("GhostManifest")
        ghost.state = "dead"
        world.players["GhostManifest"] = ghost
        world.active_player = "GhostManifest"
        world.ghost_mode = True

        result = ghost_system.check_ghost_action(world, "manifest")
        assert result is None

    def test_move_allowed(self, ghost_system):
        """'go' / 'move' actions are allowed for ghosts."""
        world = FakeVirtualWorld()
        from player import Player
        ghost = Player("GhostMove")
        ghost.state = "dead"
        world.players["GhostMove"] = ghost
        world.active_player = "GhostMove"
        world.ghost_mode = True

        result = ghost_system.check_ghost_action(world, "go")
        assert result is None

    # ── Physical actions require skill check ───────────────────────

    def test_take_blocked_on_failed_check(self, ghost_system):
        """'take' is blocked when the perception check fails."""
        world = FakeVirtualWorld()  # always fails
        from player import Player
        ghost = Player("GhostTake")
        ghost.state = "dead"
        world.players["GhostTake"] = ghost
        world.active_player = "GhostTake"
        world.ghost_mode = True

        result = ghost_system.check_ghost_action(world, "take")
        assert result is not None
        assert "pass right through" in result.lower()

    def test_drop_blocked_on_failed_check(self, ghost_system):
        """'drop' is blocked when the perception check fails."""
        world = FakeVirtualWorld()
        from player import Player
        ghost = Player("GhostDrop")
        ghost.state = "dead"
        world.players["GhostDrop"] = ghost
        world.active_player = "GhostDrop"
        world.ghost_mode = True

        result = ghost_system.check_ghost_action(world, "drop")
        assert result is not None
        assert "pass right through" in result.lower()

    def test_open_blocked_on_failed_check(self, ghost_system):
        """'open' is blocked when the perception check fails."""
        world = FakeVirtualWorld()
        from player import Player
        ghost = Player("GhostOpen")
        ghost.state = "dead"
        world.players["GhostOpen"] = ghost
        world.active_player = "GhostOpen"
        world.ghost_mode = True

        result = ghost_system.check_ghost_action(world, "open", "door")
        assert result is not None
        assert "pass through" in result.lower()

    def test_use_blocked_on_failed_check(self, ghost_system):
        """'use' is blocked when the perception check fails."""
        world = FakeVirtualWorld()
        from player import Player
        ghost = Player("GhostUse")
        ghost.state = "dead"
        world.players["GhostUse"] = ghost
        world.active_player = "GhostUse"
        world.ghost_mode = True

        result = ghost_system.check_ghost_action(world, "use")
        assert result is not None
        assert "cannot interact" in result.lower()

    def test_take_allowed_on_successful_check(self, ghost_system):
        """'take' is allowed when the perception check succeeds."""
        world = FakeSkillCheckSuccess()
        from player import Player
        ghost = Player("GhostTakeOK")
        ghost.state = "dead"
        world.players["GhostTakeOK"] = ghost
        world.active_player = "GhostTakeOK"
        world.ghost_mode = True

        result = ghost_system.check_ghost_action(world, "take")
        assert result is None

    def test_speak_allowed_on_successful_check(self, ghost_system):
        """'speak' is allowed when the perception check succeeds."""
        world = FakeSkillCheckSuccess()
        from player import Player
        ghost = Player("GhostSpeak")
        ghost.state = "dead"
        world.players["GhostSpeak"] = ghost
        world.active_player = "GhostSpeak"
        world.ghost_mode = True

        result = ghost_system.check_ghost_action(world, "speak")
        assert result is None

    def test_speak_blocked_on_failed_check(self, ghost_system):
        """'speak' from a ghost is blocked on failed check."""
        world = FakeVirtualWorld()
        from player import Player
        ghost = Player("GhostMute")
        ghost.state = "dead"
        world.players["GhostMute"] = ghost
        world.active_player = "GhostMute"
        world.ghost_mode = True

        result = ghost_system.check_ghost_action(world, "speak")
        assert result is not None
        assert "cannot hear" in result.lower()

    # ── Actions that always fail for ghosts ────────────────────────

    def test_sleep_blocked(self, ghost_system):
        """Ghosts cannot sleep."""
        world = FakeVirtualWorld()
        from player import Player
        ghost = Player("GhostSleep")
        ghost.state = "dead"
        world.players["GhostSleep"] = ghost
        world.active_player = "GhostSleep"
        world.ghost_mode = True

        result = ghost_system.check_ghost_action(world, "sleep")
        assert result is not None
        assert "dead do not sleep" in result.lower()

    def test_rest_blocked(self, ghost_system):
        """Ghosts cannot rest."""
        world = FakeVirtualWorld()
        from player import Player
        ghost = Player("GhostRest")
        ghost.state = "dead"
        world.players["GhostRest"] = ghost
        world.active_player = "GhostRest"
        world.ghost_mode = True

        result = ghost_system.check_ghost_action(world, "rest")
        assert result is not None
        assert "beyond rest" in result.lower()

    def test_eat_blocked(self, ghost_system):
        """Ghosts cannot eat."""
        world = FakeVirtualWorld()
        from player import Player
        ghost = Player("GhostEat")
        ghost.state = "dead"
        world.players["GhostEat"] = ghost
        world.active_player = "GhostEat"
        world.ghost_mode = True

        result = ghost_system.check_ghost_action(world, "eat")
        assert result is not None
        assert "cannot eat" in result.lower()

    def test_drink_blocked(self, ghost_system):
        """Ghosts cannot drink."""
        world = FakeVirtualWorld()
        from player import Player
        ghost = Player("GhostDrink")
        ghost.state = "dead"
        world.players["GhostDrink"] = ghost
        world.active_player = "GhostDrink"
        world.ghost_mode = True

        result = ghost_system.check_ghost_action(world, "drink")
        assert result is not None
        assert "cannot eat or drink" in result.lower()

    def test_unknown_action_falls_through(self, ghost_system):
        """An action type not in any list returns None (not blocked)."""
        world = FakeVirtualWorld()
        from player import Player
        ghost = Player("GhostCustom")
        ghost.state = "dead"
        world.players["GhostCustom"] = ghost
        world.active_player = "GhostCustom"
        world.ghost_mode = True

        result = ghost_system.check_ghost_action(world, "custom_action_xyz")
        assert result is None


# ─────────────────── TestSpawnBodyItem ───────────────────


class TestSpawnBodyItem:
    """Body item creation upon player death."""

    def test_spawn_body_creates_node(self, graph, ghost_system, logging_events):
        """spawn_body_item creates a body item node in the graph."""
        from player import Player
        hero = Player("FallenHero")
        hero.current_area = "Dungeon"

        ghost_system.skills.players["FallenHero"] = hero

        dungeon = Node(id="area_dungeon", type="area", name="Dungeon",
                       properties={"description": "A dark dungeon."})
        graph.add_node(dungeon)

        ghost_system.spawn_body_item("FallenHero", "a terrible curse")

        body_node = graph.get_node("body_FallenHero")
        assert body_node is not None
        assert body_node.type == "item"
        assert "FallenHero" in body_node.name
        assert "terrible curse" in body_node.properties["description"]
        assert body_node.properties.get("is_body") is True
        assert body_node.properties.get("character_name") == "FallenHero"

    def test_spawn_body_location_edge(self, graph, ghost_system):
        """Body node is linked to the player's area via a location edge."""
        from player import Player
        corpse = Player("Corpse")
        corpse.current_area = "Crypt"

        ghost_system.skills.players["Corpse"] = corpse

        crypt_node = Node(id="area_crypt", type="area", name="Crypt",
                          properties={})
        graph.add_node(crypt_node)

        ghost_system.spawn_body_item("Corpse", "unknown causes")

        edges = graph.get_edges_for_source("body_Corpse", EDGE_IN)
        assert len(edges) >= 1
        assert any(e.target == "area_crypt" for e in edges)

    def test_spawn_body_no_area(self, ghost_system):
        """If the player has no current_area, no body is spawned."""
        from player import Player
        void_player = Player("VoidWalker")
        void_player.current_area = None

        ghost_system.skills.players["VoidWalker"] = void_player
        ghost_system.spawn_body_item("VoidWalker", "void")

        body_node = ghost_system.graph.get_node("body_VoidWalker")
        assert body_node is None

    def test_spawn_body_player_not_in_world(self, ghost_system):
        """spawn_body_item with a player not in the world does nothing."""
        ghost_system.spawn_body_item("NowhereMan", "loneliness")
        # No crash is the assertion
        body_node = ghost_system.graph.get_node("body_NowhereMan")
        assert body_node is None

    def test_spawn_body_logs_entry(self, graph, ghost_system, logging_events):
        """A log entry is added when a body spawns."""
        from player import Player
        logged = Player("LoggedHero")
        logged.current_area = "Hall"

        ghost_system.skills.players["LoggedHero"] = logged

        hall = Node(id="area_hall", type="area", name="Hall",
                    properties={})
        graph.add_node(hall)

        log_count_before = len(logging_events.game_log)
        ghost_system.spawn_body_item("LoggedHero", "fire")
        assert len(logging_events.game_log) > log_count_before
        assert "LoggedHero" in logging_events.game_log[-1]
        assert "Hall" in logging_events.game_log[-1]

    def test_spawn_body_updates_existing(self, graph, ghost_system):
        """If a body node already exists, its description is updated."""
        from player import Player
        respawned = Player("Respawned")
        respawned.current_area = "Crypt"

        ghost_system.skills.players["Respawned"] = respawned

        crypt_node = Node(id="area_crypt", type="area", name="Crypt",
                          properties={})
        graph.add_node(crypt_node)

        # First death
        ghost_system.spawn_body_item("Respawned", "first death")
        body_node = graph.get_node("body_Respawned")
        assert "first death" in body_node.properties["description"]

        # Second death with different cause — description updates
        ghost_system.spawn_body_item("Respawned", "second death")
        assert "second death" in body_node.properties["description"]

    def test_spawn_body_does_not_duplicate_node(self, graph, ghost_system):
        """Calling spawn_body_item twice does not create duplicate nodes."""
        from player import Player
        hero = Player("SoloHero")
        hero.current_area = "Dungeon"

        ghost_system.skills.players["SoloHero"] = hero

        dungeon = Node(id="area_dungeon", type="area", name="Dungeon",
                       properties={})
        graph.add_node(dungeon)

        ghost_system.spawn_body_item("SoloHero", "first")
        ghost_system.spawn_body_item("SoloHero", "second")

        # Only one body node should exist
        body_node = graph.get_node("body_SoloHero")
        assert body_node is not None

        # Count nodes named "SoloHero's Body" — should be 1
        body_nodes = [
            n for n in graph.nodes.values()
            if n.name == "SoloHero's Body"
        ]
        assert len(body_nodes) == 1

    def test_spawn_body_weight(self, graph, ghost_system):
        """Body item has a reasonable weight assigned."""
        from player import Player
        heavy = Player("HeavyHero")
        heavy.current_area = "Cave"

        ghost_system.skills.players["HeavyHero"] = heavy

        cave = Node(id="area_cave", type="area", name="Cave",
                    properties={})
        graph.add_node(cave)

        ghost_system.spawn_body_item("HeavyHero", "old age")
        body_node = graph.get_node("body_HeavyHero")
        assert body_node.properties.get("weight") == 50.0

    def test_spawn_body_cause_descriptions(self, graph, ghost_system):
        """Different causes of death produce different body descriptions."""
        from player import Player

        cause_checks = {
            "hunger and starvation": "emaciated",
            "thirst and dehydration": "dry and cracked",
            "extreme cold": "harsh environment",
            "poison damage": "discoloration",
            "massive damage": "Wounds",
            "old age": "claimed by",
        }

        for cause, keyword in cause_checks.items():
            player_name = f"Hero_{cause.replace(' ', '_')}"
            p = Player(player_name)
            p.current_area = "TestRoom"

            ghost_system.skills.players[player_name] = p

            area_node = Node(id="area_testroom", type="area", name="TestRoom",
                             properties={})
            # Only add if not already present
            if not graph.get_node("area_testroom"):
                graph.add_node(area_node)

            ghost_system.spawn_body_item(player_name, cause)
            body_node = graph.get_node(f"body_{player_name}")
            assert body_node is not None
            assert keyword in body_node.properties["description"], (
                f"Expected '{keyword}' in description for cause '{cause}'"
            )
