"""Pack logic for simple NPCs, MVP (task-354).

The task file's own MVP: a shared pack property, packmate awareness in the same
area, and a coordinated-target rule — "attack the same target as the nearest
packmate". Formation, flanking and role assignment are explicitly out of scope
and are not here.

Pack identity is a ``pack:<name>`` entry in the character's existing ``tags``
rather than a new ``Player.pack`` attribute: ``player.py`` is a hub file, and
``tags`` is already where the shipped data puts what a character *is*.

The tests that matter most are the negative ones. A mechanic nobody has
authored must be inert — that is the whole lesson of task-552, where a fear
system existed, worked, and had never been asked a question.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from app import create_app
from area import Area
from player import Player

from engine import pack
from engine.pack import (
    PACK_CALL_COOLDOWN,
    call_for_help,
    coordinated_target,
    on_call_cooldown,
    pack_summary,
    pack_of,
    packmates_in,
)

SEWERS = "Sewer Junction"
DRAIN = "Drain"
RATHOLE = "Rathole"


def _world():
    world = create_app({"TESTING": True}).world
    for name in (SEWERS, DRAIN, RATHOLE, "Far Hall"):
        world.movement.add_area(Area(name, "A tunnel.", []))
    return world


def _rat(world, name, area=SEWERS, pack_name="sewer"):
    rat = Player(name)
    rat.tags = ["rat"] + ([f"pack:{pack_name}"] if pack_name else [])
    rat.simple_npc = True
    rat.npc_behavior = "stationary"   # so the fallback does not wander them
    world.add_player(rat)
    world.set_player_area(name, area)
    return rat


def _stranger(world, name, area=SEWERS, simple=False):
    who = Player(name)
    who.tags = ["human"]
    who.simple_npc = simple
    who.npc_behavior = "stationary"
    world.add_player(who)
    world.set_player_area(name, area)
    return who


# ── identity ──

class TestPackIdentity:

    def test_a_pack_tag_names_the_pack(self):
        world = _world()
        assert pack_of(_rat(world, "Rat A")) == "sewer"

    def test_no_pack_tag_means_no_pack(self):
        world = _world()
        assert pack_of(_stranger(world, "Lyrie")) is None

    def test_pack_names_are_case_insensitive(self):
        """Same reasoning as relationship_key: Sewer and sewer are one pack."""
        world = _world()
        assert pack_of(_rat(world, "Rat A", pack_name="Sewer")) == "sewer"

    def test_a_bare_prefix_is_not_a_pack(self):
        world = _world()
        rat = _rat(world, "Rat A", pack_name="")
        rat.tags = ["rat", "pack:"]
        assert pack_of(rat) is None

    def test_the_summary_reports_the_tag(self):
        world = _world()
        summary = pack_summary(_rat(world, "Rat A"))
        assert summary["in_pack"] is True
        assert summary["tag"] == "pack:sewer"
        assert pack_summary(_stranger(world, "Lyrie"))["in_pack"] is False


# ── awareness ──

class TestPackmateAwareness:

    def test_a_packmate_in_the_same_area_is_seen(self):
        world = _world()
        _rat(world, "Rat A")
        _rat(world, "Rat B")
        assert packmates_in(world, _rat(world, "Rat A") and
                            world.player_manager.get_player("Rat A")) == ["Rat B"]

    def test_another_pack_is_not_a_packmate(self):
        world = _world()
        _rat(world, "Rat A", pack_name="sewer")
        _rat(world, "Wolf", pack_name="pines")
        assert packmates_in(world,
                            world.player_manager.get_player("Rat A")) == []

    def test_a_packmate_in_another_area_is_not_seen(self):
        world = _world()
        _rat(world, "Rat A")
        _rat(world, "Rat B", area=DRAIN)
        assert packmates_in(world,
                            world.player_manager.get_player("Rat A")) == []

    def test_a_dead_packmate_does_not_call(self):
        world = _world()
        _rat(world, "Rat A")
        dead = _rat(world, "Rat B")
        dead.state = "dead"
        assert packmates_in(world,
                            world.player_manager.get_player("Rat A")) == []

    def test_a_character_never_sees_itself(self):
        world = _world()
        rat = _rat(world, "Rat A")
        assert pack_of(rat) in packmates_in(world, rat) + [pack_of(rat)]

    def test_a_non_pack_character_sees_nobody(self):
        world = _world()
        _rat(world, "Rat A")
        _stranger(world, "Lyrie")
        assert packmates_in(world, world.player_manager.get_player("Lyrie")) == []

    def test_a_call_reaches_one_room_further_than_sight(self):
        """The "hear or smell over larger areas" half of the idea."""
        world = _world()
        # Sewer Junction and the Drain are neighbours; the Rathole is not
        # reachable from anywhere in one step.
        world._build_exits_for_area = lambda area: (
            {"north": {"area": DRAIN, "state": "open"}} if area == SEWERS
            else {"south": {"area": SEWERS, "state": "open"}} if area == DRAIN
            else {})
        _rat(world, "Rat A", area=SEWERS)
        _rat(world, "Rat B", area=DRAIN)
        _rat(world, "Rat C", area=RATHOLE)
        _rat(world, "Rat D", area=SEWERS)      # shares a room with A
        rat_a = world.player_manager.get_player("Rat A")

        # Sight: only the packmate standing in the same room.
        assert packmates_in(world, rat_a) == ["Rat D"]
        # Hearing: the neighbouring room is included, the unconnected one is not.
        assert call_for_help(world, rat_a, cause="Lyrie", tick=0) == ["Rat B", "Rat D"]

    def test_wider_awareness_uses_the_area_graph_not_a_flat_range(self):
        world = _world()
        world._build_exits_for_area = lambda area: (
            {"north": {"area": DRAIN, "state": "open"}} if area == SEWERS
            else {"south": {"area": SEWERS, "state": "open"}} if area == DRAIN
            else {})
        _rat(world, "Rat A", area=SEWERS)
        _rat(world, "Rat B", area=DRAIN)
        rat_a = world.player_manager.get_player("Rat A")
        assert "Rat B" in packmates_in(world, rat_a, areas=1)
        assert packmates_in(world, rat_a, areas=0) == []

    def test_no_pack_means_no_awareness_and_no_call(self):
        world = _world()
        _rat(world, "Rat A")
        stranger = _stranger(world, "Lyrie")
        assert packmates_in(world, stranger) == []
        assert call_for_help(world, stranger, cause="anything", tick=0) == []


# ── the coordinated target ──

class TestCoordinatedTarget:

    def test_a_pack_converges_on_a_packmates_target(self):
        world = _world()
        _rat(world, "Rat A")
        _rat(world, "Rat B")
        rat_b = world.player_manager.get_player("Rat B")
        rat_b.pack_target = "Lyrie"
        assert coordinated_target(world,
                                  world.player_manager.get_player("Rat A")) == "Lyrie"

    def test_a_lone_pack_has_no_coordinated_target(self):
        world = _world()
        _rat(world, "Rat A")
        assert coordinated_target(world,
                                  world.player_manager.get_player("Rat A")) is None

    def test_a_packmate_with_no_target_contributes_nothing(self):
        world = _world()
        _rat(world, "Rat A")
        _rat(world, "Rat B")
        assert coordinated_target(world,
                                  world.player_manager.get_player("Rat A")) is None

    def test_a_pack_does_not_inherit_a_grudge_against_its_own(self):
        """Restricting the allowed targets is the guard on that."""
        world = _world()
        _rat(world, "Rat A")
        _rat(world, "Rat B")
        rat_b = world.player_manager.get_player("Rat B")
        rat_b.pack_target = "Rat C"       # a rat, not a threat
        rat_a = world.player_manager.get_player("Rat A")
        assert coordinated_target(world, rat_a, threats=["Lyrie"]) is None

    def test_an_allowed_target_is_accepted(self):
        world = _world()
        _rat(world, "Rat A")
        _rat(world, "Rat B")
        world.player_manager.get_player("Rat B").pack_target = "Lyrie"
        assert coordinated_target(world,
                                  world.player_manager.get_player("Rat A"),
                                  threats=["Lyrie"]) == "Lyrie"

    def test_a_character_never_adopts_its_own_name_as_a_target(self):
        world = _world()
        _rat(world, "Rat A")
        _rat(world, "Rat B")
        world.player_manager.get_player("Rat B").pack_target = "Rat A"
        assert coordinated_target(world,
                                  world.player_manager.get_player("Rat A")) is None

    def test_formation_and_flocking_are_not_here(self):
        """The task puts them out of scope; a growing surface would undo that."""
        public = {name for name in dir(pack) if not name.startswith("_")}
        for out_of_scope in ("formation", "flank", "flanking", "flock",
                             "assign_role", "formation_for"):
            assert out_of_scope not in public


# ── calling ──

class TestCallingForHelp:

    def test_a_call_stamps_the_target_on_every_listener(self):
        world = _world()
        _rat(world, "Rat A")
        _rat(world, "Rat B")
        rat_a = world.player_manager.get_player("Rat A")
        call_for_help(world, rat_a, cause="Lyrie", tick=0)
        assert world.player_manager.get_player("Rat B").pack_target == "Rat A"

    def test_a_call_is_throttled_per_pack(self):
        """A cornered rat must not have the whole sewer howling every tick."""
        world = _world()
        _rat(world, "Rat A")
        _rat(world, "Rat B")
        rat_a = world.player_manager.get_player("Rat A")
        call_for_help(world, rat_a, cause="Lyrie", tick=0)
        assert on_call_cooldown(world, rat_a, tick=1) is True
        assert on_call_cooldown(world, rat_a, tick=PACK_CALL_COOLDOWN) is False

    def test_a_pack_that_never_called_is_not_on_cooldown(self):
        world = _world()
        rat = _rat(world, "Rat A")
        assert on_call_cooldown(world, rat, tick=0) is False

    def test_a_non_pack_is_never_on_cooldown(self):
        world = _world()
        assert on_call_cooldown(world, _stranger(world, "Lyrie"), tick=0) is False

    def test_listeners_are_returned_in_a_stable_order(self):
        world = _world()
        _rat(world, "Rat A")
        _rat(world, "Rat B")
        _rat(world, "Rat C")
        first = call_for_help(world, world.player_manager.get_player("Rat A"),
                              cause="Lyrie", tick=0)
        second = call_for_help(world, world.player_manager.get_player("Rat A"),
                               cause="Lyrie", tick=100)
        assert first == second == ["Rat B", "Rat C"]


# ── the hook ──

class TestSimpleNpcHook:

    def test_the_hook_sets_a_pack_target(self):
        world = _world()
        _rat(world, "Rat A")
        _rat(world, "Rat B")
        world.player_manager.get_player("Rat B").pack_target = "Lyrie"
        world.npc_behaviors.process_simple_npcs(trigger_type="on_tick")
        assert world.player_manager.get_player("Rat A").pack_target == "Lyrie"

    def test_the_hook_does_nothing_to_a_non_pack(self):
        world = _world()
        _rat(world, "Rat A")
        _rat(world, "Rat B")
        world.player_manager.get_player("Rat B").pack_target = "Lyrie"
        rat = _rat(world, "Rat C", pack_name="pines")
        world.npc_behaviors.process_simple_npcs(trigger_type="on_tick")
        assert getattr(rat, "pack_target", None) is None

    def test_a_threat_makes_a_rat_call(self):
        world = _world()
        _rat(world, "Rat A")
        _rat(world, "Rat B")
        _stranger(world, "Lyrie")
        world.npc_behaviors.process_simple_npcs(trigger_type="on_tick")
        assert on_call_cooldown(world, world.player_manager.get_player("Rat A"),
                                tick=world.time_ticks) is True

    def test_no_threat_means_no_call(self):
        world = _world()
        _rat(world, "Rat A")
        _rat(world, "Rat B")
        world.npc_behaviors.process_simple_npcs(trigger_type="on_tick")
        assert on_call_cooldown(world, world.player_manager.get_player("Rat A"),
                                tick=world.time_ticks) is False

    def test_a_herd_of_rats_does_not_howl_every_tick(self):
        world = _world()
        _rat(world, "Rat A")
        _rat(world, "Rat B")
        _stranger(world, "Lyrie")
        world.npc_behaviors.process_simple_npcs(trigger_type="on_tick")
        calls = dict(world._pack_last_call)
        for tick in (1, 2, 3):
            world.time_ticks = tick
            world.npc_behaviors.process_simple_npcs(trigger_type="on_tick")
        assert world._pack_last_call == calls

    def test_the_hook_survives_a_broken_packmate(self):
        """A nicety must never take a tick down."""
        world = _world()
        _rat(world, "Rat A")
        _rat(world, "Rat B")
        broken = world.player_manager.get_player("Rat B")
        broken.tags = None
        world.npc_behaviors.process_simple_npcs(trigger_type="on_tick")
