"""Tests for the grapple system (task-4 + task-159).

Covers grab (grappler always rolls), the grappled-movement block, dragging
grappled targets along on a move, and escape.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from unittest.mock import patch

from virtual_world_engine import VirtualWorld
from area import Area
from player import Player
from graph import Edge


@pytest.fixture
def grapple_world():
    """A two-room world with a default grappler and a Target player."""
    world = VirtualWorld()
    world.movement.add_area(Area("Room A", "First room.", []))
    world.movement.add_area(Area("Room B", "Second room.", []))
    world.movement.connect_areas("Room A", "Room B", "north", "south", state="open")

    grappler = world.player_manager.get_player(world.active_player)
    grappler.current_area = "Room A"
    target = Player("Target")
    target.current_area = "Room A"
    world.add_player(target)
    world.set_active_player(grappler.name)

    world.name_matcher._set_player_area(world.active_player, "Room A")
    world.name_matcher._set_player_area("Target", "Room A")
    return world, grappler, target


class TestGrab:
    def test_grab_applies_grappled(self, grapple_world):
        world, grappler, target = grapple_world
        with patch.object(world.grapple, "_grappler_grab_check", return_value=(True, 12, "[Grab] ...")):
            result = world._grapple_grab(grappler.name, "Target")

        assert target.has_condition("grappled")
        gnode = world._player_node_id(grappler.name)
        tnode = world._player_node_id("Target")
        edges = world.graph.get_edges_for_source(gnode, "grappled")
        assert any(e.target == tnode for e in edges)
        assert "grab" in result.lower()

    def test_grab_can_be_resisted(self, grapple_world):
        world, grappler, target = grapple_world
        with patch.object(world.grapple, "_grappler_grab_check", return_value=(False, 4, "[Grab] ...")):
            result = world._grapple_grab(grappler.name, "Target")

        assert not target.has_condition("grappled")
        assert "slip" in result.lower()

    def test_friend_grab_uses_grappler_check(self, grapple_world):
        """All grabs use a grappler-side roll (unified formula)."""
        world, grappler, target = grapple_world
        target.relationships = {grappler.name: {"closeness": 50}}
        with patch.object(world.grapple, "_grappler_grab_check", return_value=(True, 12, "[Grab] ...")):
            result = world._grapple_grab(grappler.name, "Target")

        assert target.has_condition("grappled")
        gnode = world._player_node_id(grappler.name)
        tnode = world._player_node_id("Target")
        assert any(e.target == tnode for e in world.graph.get_edges_for_source(gnode, "grappled"))
        assert "grab hold" in result.lower()

    def test_friend_grab_can_fumble(self, grapple_world):
        """Even a friend's grab can fail — the grabber slips, no grapple."""
        world, grappler, target = grapple_world
        target.relationships = {grappler.name: {"closeness": 50}}
        with patch.object(world.grapple, "_grappler_grab_check", return_value=(False, 4, "[Grab] ...")):
            result = world._grapple_grab(grappler.name, "Target")

        assert not target.has_condition("grappled")
        assert "slip" in result.lower()


class TestMovementBlock:
    def test_grappled_character_cannot_move(self, grapple_world):
        world, grappler, target = grapple_world
        with patch.object(world.grapple, "_grappler_grab_check", return_value=(True, 12, "[Grab] ...")):
            world._grapple_grab(grappler.name, "Target")

        world.set_active_player("Target")
        with pytest.raises(ValueError, match="grappled"):
            world.movement.move_to_area("north")

    def test_restrained_character_cannot_move(self, grapple_world):
        """The restrained condition (e.g. tied up via a trigger) blocks movement."""
        world, grappler, target = grapple_world
        target.add_condition("restrained")

        world.set_active_player("Target")
        with pytest.raises(ValueError, match="restrained"):
            world.movement.move_to_area("north")

    def test_grappler_can_still_move(self, grapple_world):
        world, grappler, target = grapple_world
        with patch.object(world.grapple, "_grappler_grab_check", return_value=(True, 12, "[Grab] ...")):
            world._grapple_grab(grappler.name, "Target")

        result = world.movement.move_to_area("north")
        assert "Room B" in result or world.player.current_area == "Room B"


class TestDrag:
    def test_drag_moves_grappled_target(self, grapple_world):
        world, grappler, target = grapple_world
        with patch.object(world.grapple, "_grappler_grab_check", return_value=(True, 12, "[Grab] ...")):
            world._grapple_grab(grappler.name, "Target")
            result = world.movement.move_to_area("north")

        assert world.player.current_area == "Room B"
        assert target.current_area == "Room B"
        from engine.character_spatial import get_character_at_way
        tnode = world._player_node_id("Target")
        assert get_character_at_way(world.graph, tnode) == world._way_node_id("Room A_north")
        assert "drag" in result.lower()

    def test_drag_is_mechanical_and_keeps_grapple(self, grapple_world):
        """Dragging has no mid-move resist — the target is pulled along and
        stays grappled. The struggle is their own turn (escape action)."""
        world, grappler, target = grapple_world
        with patch.object(world.grapple, "_grappler_grab_check", return_value=(True, 12, "[Grab] ...")):
            world._grapple_grab(grappler.name, "Target")
            result = world.movement.move_to_area("north")

        assert world.player.current_area == "Room B"
        assert target.current_area == "Room B"
        assert target.has_condition("grappled")
        gnode = world._player_node_id(grappler.name)
        tnode = world._player_node_id("Target")
        assert any(e.target == tnode for e in world.graph.get_edges_for_source(gnode, "grappled"))


class TestEscape:
    def test_escape_breaks_free(self, grapple_world):
        world, grappler, target = grapple_world
        with patch.object(world.grapple, "_grappler_grab_check", return_value=(True, 12, "[Grab] ...")):
            world._grapple_grab(grappler.name, "Target")

        world.set_active_player("Target")
        with patch.object(world.skills, "saving_throw", return_value=(True, 18, "roll")):
            result = world._grapple_escape("Target")

        assert not target.has_condition("grappled")
        gnode = world._player_node_id(grappler.name)
        tnode = world._player_node_id("Target")
        assert not any(e.target == tnode for e in world.graph.get_edges_for_source(gnode, "grappled"))
        assert "break free" in result.lower()

    def test_escape_can_fail(self, grapple_world):
        world, grappler, target = grapple_world
        with patch.object(world.grapple, "_grappler_grab_check", return_value=(True, 12, "[Grab] ...")):
            world._grapple_grab(grappler.name, "Target")

        world.set_active_player("Target")
        with patch.object(world.skills, "saving_throw", return_value=(False, 6, "roll")):
            result = world._grapple_escape("Target")

        assert target.has_condition("grappled")
        assert "holds" in result.lower()

    def test_escape_when_not_grappled(self, grapple_world):
        world, grappler, target = grapple_world
        result = world._grapple_escape("Target")
        assert "aren't grappled" in result.lower()


class TestGrapplerTracking:
    """Grappled edge tracking (bidirectional relationship)."""

    def _grappled_edge(self, world, grappler_name, target_name):
        gnode = world._player_node_id(grappler_name)
        tnode = world._player_node_id(target_name)
        return any(e.target == tnode for e in world.graph.get_edges_for_source(gnode, "grappled"))

    def test_grab_creates_edge(self, grapple_world):
        world, grappler, target = grapple_world
        with patch.object(world.grapple, "_grappler_grab_check", return_value=(True, 12, "[Grab] ...")):
            world._grapple_grab(grappler.name, "Target")

        assert self._grappled_edge(world, grappler.name, "Target")

    def test_escape_removes_edge(self, grapple_world):
        world, grappler, target = grapple_world
        with patch.object(world.grapple, "_grappler_grab_check", return_value=(True, 12, "[Grab] ...")):
            world._grapple_grab(grappler.name, "Target")

        world.set_active_player("Target")
        with patch.object(world.skills, "saving_throw", return_value=(True, 18, "roll")):
            world._grapple_escape("Target")

        assert not self._grappled_edge(world, grappler.name, "Target")
        assert not target.has_condition("grappled")

    def test_release_drops_specific_target(self, grapple_world):
        world, grappler, target = grapple_world
        with patch.object(world.grapple, "_grappler_grab_check", return_value=(True, 12, "[Grab] ...")):
            world._grapple_grab(grappler.name, "Target")

        result = world._grapple_release(grappler.name, "Target")
        assert "let go" in result.lower()
        assert not target.has_condition("grappled")
        assert not self._grappled_edge(world, grappler.name, "Target")

    def test_release_all_when_no_target_named(self, grapple_world):
        world, grappler, target = grapple_world
        with patch.object(world.grapple, "_grappler_grab_check", return_value=(True, 12, "[Grab] ...")):
            world._grapple_grab(grappler.name, "Target")

        result = world._grapple_release(grappler.name)
        assert "release everyone" in result.lower()
        assert not target.has_condition("grappled")
        assert not self._grappled_edge(world, grappler.name, "Target")

    def test_sync_clears_orphan_grappled(self, grapple_world):
        """A grappled condition with no matching edge is cleared by sync()."""
        world, grappler, target = grapple_world
        target.add_condition("grappled")  # no edge

        world.grapple.sync()
        assert not target.has_condition("grappled")

    def test_sync_repairs_missing_condition(self, grapple_world):
        """An edge whose target lacks the condition gets the condition re-added."""
        world, grappler, target = grapple_world
        gnode = world._player_node_id(grappler.name)
        tnode = world._player_node_id("Target")
        world.graph.add_edge(Edge(source=gnode, target=tnode, type="grappled"))
        # target has NO grappled condition yet (desync)

        world.grapple.sync()
        assert target.has_condition("grappled")

    def test_sync_drops_legacy_grappling_condition(self, grapple_world):
        """Old `grappling` condition instances are dropped by sync()."""
        world, grappler, target = grapple_world
        grappler.add_condition("grappling", source="Target")

        world.grapple.sync()
        assert not grappler.has_condition("grappling")


class TestGrappleLimits:
    """Hand limits + harder second grab."""

    def test_grappler_limited_to_two_targets(self, grapple_world):
        world, grappler, target = grapple_world
        third = Player("Third")
        third.current_area = "Room A"
        world.add_player(third)
        fourth = Player("Fourth")
        fourth.current_area = "Room A"
        world.add_player(fourth)
        world.set_active_player(grappler.name)
        world.name_matcher._set_player_area("Third", "Room A")
        world.name_matcher._set_player_area("Fourth", "Room A")

        with patch.object(world.grapple, "_grappler_grab_check", return_value=(True, 12, "[Grab] ...")):
            world._grapple_grab(grappler.name, "Target")
            world._grapple_grab(grappler.name, "Third")
            result3 = world._grapple_grab(grappler.name, "Fourth")

        assert target.has_condition("grappled")
        assert third.has_condition("grappled")
        assert not fourth.has_condition("grappled")
        assert "hands are full" in result3.lower()

    def test_one_armed_grappler_holds_one(self, grapple_world):
        world, grappler, target = grapple_world
        second = Player("Second")
        second.current_area = "Room A"
        world.add_player(second)
        third = Player("Third")
        third.current_area = "Room A"
        world.add_player(third)
        world.set_active_player(grappler.name)
        world.name_matcher._set_player_area("Second", "Room A")
        world.name_matcher._set_player_area("Third", "Room A")
        grappler.traits["one_armed"] = True

        with patch.object(world.grapple, "_grappler_grab_check", return_value=(True, 12, "[Grab] ...")):
            world._grapple_grab(grappler.name, "Target")
            result2 = world._grapple_grab(grappler.name, "Second")
            result3 = world._grapple_grab(grappler.name, "Third")

        assert target.has_condition("grappled")
        assert not second.has_condition("grappled")
        assert "hands are full" in result2.lower()
        assert not third.has_condition("grappled")


class TestRelationshipDC:
    """Relationship-modulated grapple DCs."""

    def test_friend_lowers_relationship_mod(self, grapple_world):
        world, grappler, target = grapple_world
        target.relationships = {grappler.name: {"closeness": 70}}
        assert world.grapple._relationship_mod("Target", grappler.name) == -4

    def test_enemy_raises_relationship_mod(self, grapple_world):
        world, grappler, target = grapple_world
        target.relationships = {grappler.name: {"closeness": -70}}
        # -70 // 25 = -3 (floor division), so -( -3 ) * 2 = 6
        assert world.grapple._relationship_mod("Target", grappler.name) == 6

    def test_grab_dc_formula(self, grapple_world):
        """Grab DC = 10 + grabber_athletics + rel + extra - target_skill."""
        world, grappler, target = grapple_world
        target.relationships = {grappler.name: {"closeness": -50}}
        grappler.skills["Athletics"] = 5
        target.skills["Acrobatics"] = 6

        # closeness -50 → rel = 4
        # DC = 10 + 5 + 4 - 6 = 13
        assert world.grapple._grab_dc(grappler.name, target.name) == 13

    def test_escape_dc_formula(self, grapple_world):
        """Escape DC = 10 + grabber_athletics + rel - extra - target_skill."""
        world, grappler, target = grapple_world
        target.relationships = {grappler.name: {"closeness": -50}}
        grappler.skills["Athletics"] = 5
        target.skills["Acrobatics"] = 6

        gnode = world._player_node_id(grappler.name)
        tnode = world._player_node_id(target.name)
        world.graph.add_edge(Edge(source=gnode, target=tnode, type="grappled"))

        # closeness -50 → rel = 4, held = 1 target → extra = 2
        # DC = 10 + 5 + 4 - 2 - 6 = 11
        assert world.grapple._escape_dc(target.name) == 11

    def test_escape_dc_lower_with_multiple_targets(self, grapple_world):
        """Escape is easier when the grabber is holding multiple people."""
        world, grappler, target = grapple_world
        target.relationships = {grappler.name: {"closeness": 0}}
        grappler.skills["Athletics"] = 5
        target.skills["Acrobatics"] = 4

        gnode = world._player_node_id(grappler.name)
        tnode = world._player_node_id(target.name)
        world.graph.add_edge(Edge(source=gnode, target=tnode, type="grappled"))

        # With 1 held target: DC = 10 + 5 + 0 - 2 - 4 = 9
        assert world.grapple._escape_dc(target.name) == 9

    def test_escape_uses_best_skill(self, grapple_world):
        """Best escape skill is max of Athletics / Acrobatics."""
        world, grappler, target = grapple_world
        target.skills["Acrobatics"] = 6
        target.skills["Athletics"] = 2

        assert world.grapple._best_escape_skill(target) == 6


class TestExperienceDrivenGrab:
    """task-350: at equal closeness, trust/fear from experience changes the DC.

    The mechanic reads *consent* (trust - fear, derived from memories), not the
    raw closeness scalar, so a distrusted person is harder to grab than a
    trusted one even when the `closeness` number is identical.
    """

    def _fixed_closeness(self, target, grappler_name, closeness=50):
        """Seed a +50 closeness (identical for every case) so only experience differs."""
        target.relationships[grappler_name] = {
            "closeness": closeness,
            "last_interaction_tick": 1,
            "interaction_count": 1,
        }
        target.memories = []

    def test_no_signal_falls_back_to_closeness(self, grapple_world):
        """Plain relationships (no dimensional memories) keep the legacy rule."""
        world, grappler, target = grapple_world
        self._fixed_closeness(target, grappler.name, closeness=50)
        mod = world.grapple._relationship_mod("Target", grappler.name)
        assert mod == -4  # -(50 // 25) * 2

    def test_distrusted_person_harder_to_grab(self, grapple_world):
        """Distrust/fear (experience) raises the at-equal-closeness grab DC."""
        world, grappler, target = grapple_world
        self._fixed_closeness(target, grappler.name, closeness=50)
        target.felt_toward(grappler.name, "distrustful", 8, tick=1)
        target.felt_toward(grappler.name, "uneasy", 8, tick=2)
        mod = world.grapple._relationship_mod("Target", grappler.name)
        assert mod > 0, f"expected a positive (harder) mod, got {mod}"

    def test_trusted_person_easier_to_grab(self, grapple_world):
        """Trust (experience) keeps the at-equal-closeness grab DC low."""
        world, grappler, target = grapple_world
        self._fixed_closeness(target, grappler.name, closeness=50)
        target.felt_toward(grappler.name, "grateful", 8, tick=1)
        mod = world.grapple._relationship_mod("Target", grappler.name)
        assert mod < 0, f"expected a negative (easier) mod, got {mod}"

    def test_identical_closeness_different_consent_changes_dc(self, grapple_world):
        """THE proof: same closeness, opposite trust -> distrusted is harder."""
        world, grappler, target = grapple_world

        self._fixed_closeness(target, grappler.name, closeness=50)
        target.felt_toward(grappler.name, "distrustful", 9, tick=1)
        target.felt_toward(grappler.name, "uneasy", 9, tick=2)
        mod_distrusted = world.grapple._relationship_mod("Target", grappler.name)

        self._fixed_closeness(target, grappler.name, closeness=50)
        target.felt_toward(grappler.name, "grateful", 9, tick=1)
        mod_trusted = world.grapple._relationship_mod("Target", grappler.name)

        assert mod_distrusted > mod_trusted, (
            f"distrusted {mod_distrusted} should be > trusted {mod_trusted}")
