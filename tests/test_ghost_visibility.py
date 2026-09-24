"""Ghost / undead semantics tests (task-309, 5e-aligned split).

`undead` = not alive (no vitals) but corporeal and visible.
`ghost` = incorporeal (phases) and unseen until it manifests.
Visibility is a state: a manifested ghost is listed and targetable.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from player import Player
from app import create_app


def _world():
    app = create_app({"TESTING": True})
    world = app.world
    world.time_per_tick_minutes = 1
    return world


def _add(world, name, tags=(), area="Study"):
    p = Player(name)
    p.tags = list(tags)
    world.add_player(p)
    world.set_player_area(name, area)
    return p


def _setup(world):
    """A viewer (active player) plus a zombie and a ghost in Study."""
    _add(world, "Viewer", area="Study")
    zombie = _add(world, "Zombie", tags=["undead"], area="Study")
    ghost = _add(world, "Ghost", tags=["ghost"], area="Study")
    # add_player makes the newest character active; pin the viewer instead.
    world.active_player = "Viewer"
    return zombie, ghost


# ── identity helpers ────────────────────────────────────────────────────

class TestIdentityHelpers:

    def test_undead_only(self):
        world = _world()
        _add(world, "Zombie", tags=["undead"])
        pm = world.player_manager
        assert pm.is_undead("Zombie") is True
        assert pm.is_incorporeal("Zombie") is False
        assert pm.is_undead_ghost("Zombie") is True

    def test_ghost_only(self):
        world = _world()
        _add(world, "Ghost", tags=["ghost"])
        pm = world.player_manager
        assert pm.is_incorporeal("Ghost") is True
        assert pm.is_undead("Ghost") is False

    def test_neither(self):
        world = _world()
        _add(world, "Mortal")
        pm = world.player_manager
        assert pm.is_undead_ghost("Mortal") is False

    def test_facades(self):
        world = _world()
        _add(world, "Ghost", tags=["ghost"])
        assert world.is_incorporeal("Ghost") is True
        assert world.is_visible("Ghost") is False


# ── visibility state ────────────────────────────────────────────────────

class TestVisibility:

    def test_mortal_visible(self):
        world = _world()
        _add(world, "Mortal")
        assert world.player_manager.is_visible("Mortal") is True

    def test_zombie_stays_visible(self):
        world = _world()
        _add(world, "Zombie", tags=["undead"])
        assert world.player_manager.is_visible("Zombie") is True

    def test_ghost_unseen_until_manifested(self):
        world = _world()
        ghost = _add(world, "Ghost", tags=["ghost"])
        assert world.player_manager.is_visible("Ghost") is False
        ghost.manifested = True
        assert world.player_manager.is_visible("Ghost") is True

    def test_mundane_hidden_always_unseen(self):
        world = _world()
        hider = _add(world, "Hider")
        hider.hidden = True
        assert world.player_manager.is_visible("Hider") is False

    def test_hidden_beats_manifested(self):
        world = _world()
        ghost = _add(world, "Ghost", tags=["ghost"])
        ghost.manifested = True
        ghost.hidden = True
        assert world.player_manager.is_visible("Ghost") is False


# ── room listing ────────────────────────────────────────────────────────

class TestRoomListing:

    def test_zombie_listed_ghost_and_hider_not(self):
        world = _world()
        zombie, ghost = _setup(world)
        hider = _add(world, "Hider", area="Study")
        hider.hidden = True
        world.active_player = "Viewer"

        names = {p["name"] for p in world.player_manager.get_players_in_area("Study")}
        assert "Zombie" in names
        assert "Ghost" not in names
        assert "Hider" not in names

    def test_include_ghosts_reveals_unseen(self):
        world = _world()
        _setup(world)
        names = {p["name"] for p in world.player_manager.get_players_in_area("Study", include_ghosts=True)}
        assert "Ghost" in names

    def test_manifested_ghost_is_listed(self):
        world = _world()
        _, ghost = _setup(world)
        ghost.manifested = True
        names = {p["name"] for p in world.player_manager.get_players_in_area("Study")}
        assert "Ghost" in names


# ── combat targeting ────────────────────────────────────────────────────

class TestCombatTargeting:

    def test_zombie_is_hittable(self):
        world = _world()
        _add(world, "Knight", area="Study")
        _add(world, "Zombie", tags=["undead"], area="Study")
        result = world.combat.player_attack("Knight", "Zombie")
        assert "empty air" not in result

    def test_unmanifested_ghost_cannot_be_hit(self):
        world = _world()
        _add(world, "Knight", area="Study")
        _add(world, "Ghost", tags=["ghost"], area="Study")
        result = world.combat.player_attack("Knight", "Ghost")
        assert "empty air" in result

    def test_manifested_ghost_is_hittable(self):
        world = _world()
        _add(world, "Knight", area="Study")
        ghost = _add(world, "Ghost", tags=["ghost"], area="Study")
        ghost.manifested = True
        result = world.combat.player_attack("Knight", "Ghost")
        assert "empty air" not in result


# ── vitals guard ────────────────────────────────────────────────────────

def test_undead_and_ghost_both_skip_vitals():
    """tick_manager skips decay for anyone `is_undead_ghost`."""
    world = _world()
    _add(world, "Zombie", tags=["undead"])
    _add(world, "Ghost", tags=["ghost"])
    assert world.is_undead_ghost("Zombie") is True
    assert world.is_undead_ghost("Ghost") is True


# ── manifest / vanish actions ───────────────────────────────────────────

class TestManifestVanish:

    def _run(self, world, char, actions):
        return world.triggers._execute_behavior_actions(char, actions, game_state=world)

    def test_manifest_makes_ghost_seen(self):
        world = _world()
        ghost = _add(world, "Ghost", tags=["ghost"])
        self._run(world, "Ghost", [{"type": "manifest"}])
        assert ghost.manifested is True
        assert world.player_manager.is_visible("Ghost") is True

    def test_vanish_hides_ghost_again(self):
        world = _world()
        ghost = _add(world, "Ghost", tags=["ghost"])
        ghost.manifested = True
        self._run(world, "Ghost", [{"type": "vanish"}])
        assert ghost.manifested is False
        assert world.player_manager.is_visible("Ghost") is False
