"""The undead-ghost exclusion in `process_npc_reaction` (found while on task-552).

`is_undead_ghost(player_name: str)` looks the character up **by name** in
`player_manager.players`. `process_npc_reaction` was handing it the `Player`
*object* instead, so the lookup could never match and the exclusion has never
fired in the life of the engine — a ghost was free to gawk and comment like
anything else. The one-word shape of the bug is the reason this file is small
and blunt: a test that passes for the wrong reason is worse than no test, and
that is exactly what happened once already (see task-490's
`TestVisibilityGateStillWins`).

The sibling guard in `_can_observe`, added by task-547, always passed the name
and was always correct — which is how the mismatch between the two was visible
at all.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from app import create_app
from area import Area
from player import Player

import engine.npc_behaviors as nb

AREA = "Verdant Hollow"


@pytest.fixture
def world():
    world = create_app({"TESTING": True}).world
    world.time_per_tick_minutes = 1
    world.movement.add_area(Area(AREA, "A hollow.", []))
    return world


def _character(world, name, tags, simple=True):
    who = Player(name)
    who.tags = list(tags)
    who.simple_npc = simple
    who.npc_behavior = "stationary"
    world.add_player(who)
    world.set_player_area(name, AREA)
    return who


def _always(monkeypatch):
    monkeypatch.setattr(nb.random, "randint", lambda a, b: 20)
    monkeypatch.setattr(nb.random, "choice", lambda seq: seq[0])


class TestUndeadGhostExclusion:

    def test_the_lookup_is_by_name_and_an_object_never_matches(self):
        """The bug itself, pinned at the level it was made."""
        world = create_app({"TESTING": True}).world
        ghost = Player("Wraith")
        ghost.tags = ["undead", "ghost"]
        world.add_player(ghost)

        assert world.is_undead_ghost("Wraith") is True
        assert world.is_undead_ghost(ghost) is False

    def test_a_ghost_does_not_react(self, world, monkeypatch):
        _always(monkeypatch)
        ghost = _character(world, "Wraith", ["undead", "ghost"])
        actor = _character(world, "Lyrie", ["human"])

        assert world.npc_behaviors.process_npc_reaction(
            ghost, actor, "combat") is None

    def test_a_corporeal_zombie_is_excluded_too(self, monkeypatch):
        """Not a regression, but worth pinning because it is surprising.

        This guard calls ``is_undead_ghost``, which is the **broad** alias --
        ``is_undead or is_incorporeal`` -- so a plain zombie is excluded as well
        as a ghost. That is the alias's documented job ("callers that mean
        spectral entity, e.g. skipping vitals or social reactions"), and it
        predates this fix. The fix makes the guard fire for the first time; it
        does not change who the guard covers.

        If a zombie should be allowed to react, that is a different question and
        belongs in a call site using ``is_undead`` / ``is_incorporeal``
        directly, as task-490's profile does.
        """
        world = create_app({"TESTING": True}).world
        world.time_per_tick_minutes = 1
        world.movement.add_area(Area(AREA, "A hollow.", []))
        _always(monkeypatch)
        zombie = _character(world, "Shambler", ["undead"])
        actor = _character(world, "Lyrie", ["human"])

        assert world.is_undead_ghost("Shambler") is True
        assert world.npc_behaviors.process_npc_reaction(
            zombie, actor, "combat") is None

    def test_an_ordinary_character_still_reacts(self, world, monkeypatch):
        _always(monkeypatch)
        mortal = _character(world, "Lyrie", ["human"])
        actor = _character(world, "Tam", ["human"])

        assert world.npc_behaviors.process_npc_reaction(
            mortal, actor, "combat") is not None

    def test_both_guards_use_the_same_shape(self, monkeypatch):
        """_can_observe and process_npc_reaction must not drift apart again."""
        import inspect
        source = inspect.getsource(nb.NPCBehaviorSystem)
        assert "is_undead_ghost(npc)" not in source, \
            "someone reintroduced the object-where-a-name-belongs call"
        assert source.count("is_undead_ghost(npc.name)") == 2

    def test_the_dead_are_still_excluded(self, world, monkeypatch):
        _always(monkeypatch)
        corpse = _character(world, "Corpse", ["human"])
        corpse.state = "dead"
        actor = _character(world, "Lyrie", ["human"])

        assert world.npc_behaviors.process_npc_reaction(
            corpse, actor, "combat") is None
