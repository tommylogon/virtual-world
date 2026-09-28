"""Who saw whom this turn, and whether it was public (task-547).

``engine.observation`` is the record; ``NPCBehaviorSystem.record_observations``
is the pass that fills it. These tests pin the acceptance criteria directly:
an observer in the same area is recorded, one in another area or one who fails
the perception roll is not, public and covert are distinguishable, every
character tier that can look is included, and the record ages out.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from app import create_app
from engine.observation_signal import (
    DEFAULT_MEMORY_TURNS,
    PUBLIC_LIGHT_FLOOR,
    ObservationSignalLog,
    get_observation_signals,
    reset_observation_signals,
)
from player import Player
import engine.npc_behaviors as nb


@pytest.fixture(autouse=True)
def _clean_log():
    reset_observation_signals()
    yield
    reset_observation_signals()


def _world():
    app = create_app({"TESTING": True})
    world = app.world
    world.time_per_tick_minutes = 1
    return world


def _pair(world, area="Study"):
    actor = Player("Actor")
    target = Player("Lydia")
    world.add_player(actor)
    world.add_player(target)
    world.set_player_area("Actor", area)
    world.set_player_area("Lydia", area)
    for other in list(world.player_manager.players.values()):
        if other.name not in ("Actor", "Lydia") and other.current_area == area:
            world.set_player_area(other.name, "Kitchen")
    return actor, target


def _watcher(world, name, area="Study", simple=True, traits=None):
    who = Player(name)
    who.simple_npc = simple
    who.traits = traits or {}
    world.add_player(who)
    world.set_player_area(name, area)
    return who


def _light(monkeypatch, value):
    monkeypatch.setattr(nb.NPCBehaviorSystem, "_ambient_light",
                        lambda self, area: value)


def _always_see(monkeypatch):
    monkeypatch.setattr(nb.random, "randint", lambda a, b: 20)
    monkeypatch.setattr(nb.random, "choice", lambda seq: seq[0])


def _never_see(monkeypatch):
    monkeypatch.setattr(nb.random, "randint", lambda a, b: 1)
    monkeypatch.setattr(nb.random, "choice", lambda seq: seq[0])


# ── the record itself ──

class TestObservationLog:

    def test_starts_empty(self):
        log = ObservationSignalLog()
        assert log.observations_of("Lydia", tick=5) == []
        assert log.was_observed("Lydia", tick=5) is False
        assert log.last_observed_tick("Lydia", tick=5) is None

    def test_record_then_read_without_recomputing(self):
        log = ObservationSignalLog()
        log.record("Guard", "Lydia", tick=5, public=True, stimulus_type="combat")
        assert log.observers_of("Lydia", tick=5) == ["Guard"]
        assert log.was_observed("Lydia", tick=5) is True
        assert log.last_observed_tick("Lydia", tick=5) == 5

    def test_repeat_sighting_refreshes_rather_than_duplicates(self):
        log = ObservationSignalLog()
        log.record("Guard", "Lydia", tick=5, public=True)
        log.record("Guard", "Lydia", tick=6, public=False)
        live = log.observations_of("Lydia", tick=6)
        assert len(live) == 1
        assert live[0]["tick"] == 6
        assert live[0]["public"] is False

    def test_public_only_filter(self):
        log = ObservationSignalLog()
        log.record("Guard", "Lydia", tick=5, public=True)
        log.record("Shadow", "Lydia", tick=5, public=False)
        assert log.observers_of("Lydia", tick=5) == ["Guard", "Shadow"]
        assert log.public_observers_of("Lydia", tick=5) == ["Guard"]
        assert log.was_observed_publicly("Lydia", tick=5) is True

    def test_observed_by_one_named_witness(self):
        log = ObservationSignalLog()
        log.record("Guard", "Lydia", tick=5, public=True)
        assert log.observed_by("Lydia", "Guard", tick=5)["public"] is True
        assert log.observed_by("Lydia", "Someone Else", tick=5) is None

    def test_record_ages_out_after_the_window(self):
        log = ObservationSignalLog(memory_turns=3)
        log.record("Guard", "Lydia", tick=10, public=True)
        assert log.was_observed("Lydia", tick=10) is True
        assert log.was_observed("Lydia", tick=13) is True   # still inside
        assert log.was_observed("Lydia", tick=14) is False  # one turn too far

    def test_a_read_past_the_window_reports_nothing(self):
        log = ObservationSignalLog(memory_turns=2)
        log.record("Guard", "Lydia", tick=10, public=True)
        assert log.observers_of("Lydia", tick=40) == []
        assert log.was_observed_publicly("Lydia", tick=40) is False

    def test_the_next_write_ages_the_expired_rows_out(self):
        log = ObservationSignalLog(memory_turns=2)
        log.record("Guard", "Lydia", tick=10, public=True)
        log.record("Bystander", "Lydia", tick=40, public=True)
        # the stale pair is gone from storage, not merely filtered on read
        assert set(log._by_target["Lydia"]) == {"Bystander"}

    def test_the_store_is_bounded_by_pairs_not_turns(self):
        log = ObservationSignalLog(memory_turns=3)
        for tick in range(0, 100, 2):
            log.record("Guard", "Lydia", tick=tick, public=True)
        assert len(log._by_target["Lydia"]) == 1

    def test_explicit_max_age_overrides_the_default(self):
        log = ObservationSignalLog(memory_turns=3)
        log.record("Guard", "Lydia", tick=10, public=True)
        assert log.observers_of("Lydia", tick=30, max_age=1) == []
        assert log.observers_of("Lydia", tick=30, max_age=99) == ["Guard"]

    def test_default_window_is_the_documented_one(self):
        assert ObservationSignalLog().memory_turns == DEFAULT_MEMORY_TURNS

    def test_unlimited_window_never_expires(self):
        log = ObservationSignalLog(memory_turns=None)
        log.record("Guard", "Lydia", tick=10, public=True)
        assert log.observers_of("Lydia", tick=10_000) == ["Guard"]


# ── the pass ──

class TestRecordObservations:

    def test_observer_in_the_same_area_is_recorded(self, monkeypatch):
        world = _world()
        _pair(world)
        _watcher(world, "Guard")
        _light(monkeypatch, 60)
        _always_see(monkeypatch)

        records = world.npc_behaviors.record_observations("Actor", "Lydia", "combat")

        assert [r["observer"] for r in records] == ["Guard"]
        assert get_observation_signals().observers_of("Lydia", tick=world.time_ticks) == ["Guard"]

    def test_observer_in_another_area_is_not_recorded(self, monkeypatch):
        world = _world()
        _pair(world)
        _watcher(world, "Guard", area="Kitchen")
        _light(monkeypatch, 60)
        _always_see(monkeypatch)

        assert world.npc_behaviors.record_observations("Actor", "Lydia", "combat") == []
        assert get_observation_signals().was_observed("Lydia", tick=world.time_ticks) is False

    def test_a_failed_perception_check_is_not_recorded(self, monkeypatch):
        world = _world()
        _pair(world)
        _watcher(world, "Guard")
        _light(monkeypatch, 60)
        _never_see(monkeypatch)

        assert world.npc_behaviors.record_observations("Actor", "Lydia", "combat") == []
        assert get_observation_signals().was_observed("Lydia", tick=world.time_ticks) is False

    def test_the_actor_and_target_are_never_their_own_observers(self, monkeypatch):
        world = _world()
        _pair(world)
        _light(monkeypatch, 60)
        _always_see(monkeypatch)

        names = [r["observer"] for r in
                 world.npc_behaviors.record_observations("Actor", "Lydia", "combat")]
        assert "Actor" not in names and "Lydia" not in names

    def test_agent_and_human_tiers_are_included(self, monkeypatch):
        """The tiers the old pass skipped are the ones players expect to watch."""
        world = _world()
        _pair(world)
        _watcher(world, "Simple", simple=True)
        _watcher(world, "Driven", simple=False)
        _watcher(world, "Human", simple=False)
        _light(monkeypatch, 60)
        _always_see(monkeypatch)

        names = [r["observer"] for r in
                 world.npc_behaviors.record_observations("Actor", "Lydia", "combat")]
        assert set(names) == {"Simple", "Driven", "Human"}

    def test_a_dead_character_does_not_observe(self, monkeypatch):
        world = _world()
        _pair(world)
        ghost = _watcher(world, "Corpse")
        ghost.state = "dead"
        _light(monkeypatch, 60)
        _always_see(monkeypatch)

        assert world.npc_behaviors.record_observations("Actor", "Lydia", "combat") == []

    def test_non_mature_world_records_nothing_for_a_sexual_stimulus(self, monkeypatch):
        world = _world()
        world.mature_content = False
        _pair(world)
        _watcher(world, "Guard")
        _light(monkeypatch, 60)
        _always_see(monkeypatch)

        assert world.npc_behaviors.record_observations("Actor", "Lydia", "intimacy") == []
        assert get_observation_signals().was_observed("Lydia", tick=world.time_ticks) is False


# ── public vs covert ──

class TestPublicVersusCovert:

    def test_a_witness_in_the_dark_is_covert(self, monkeypatch):
        world = _world()
        _pair(world)
        _watcher(world, "Guard")
        _light(monkeypatch, PUBLIC_LIGHT_FLOOR - 5)
        _always_see(monkeypatch)

        record = world.npc_behaviors.record_observations("Actor", "Lydia", "combat")[0]

        assert record["public"] is False
        log = get_observation_signals()
        # still an observer — being unseen is not the same as unwitnessed
        assert log.observers_of("Lydia", tick=world.time_ticks) == ["Guard"]
        assert log.public_observers_of("Lydia", tick=world.time_ticks) == []

    def test_a_witness_in_the_light_is_public(self, monkeypatch):
        world = _world()
        _pair(world)
        _watcher(world, "Guard")
        _light(monkeypatch, PUBLIC_LIGHT_FLOOR)
        _always_see(monkeypatch)

        record = world.npc_behaviors.record_observations("Actor", "Lydia", "combat")[0]
        assert record["public"] is True

    def test_a_sleeping_witness_is_covert(self, monkeypatch):
        world = _world()
        _pair(world)
        sleeper = _watcher(world, "Sleeper")
        sleeper.activity = {"type": "sleeping"}
        _light(monkeypatch, 90)
        _always_see(monkeypatch)

        record = world.npc_behaviors.record_observations("Actor", "Lydia", "combat")[0]
        assert record["public"] is False

    def test_sleeping_is_read_from_the_activity_not_the_state(self, monkeypatch):
        """`state` is hierarchy-derived, so a sleeping character reads 'awake'."""
        world = _world()
        _pair(world)
        sleeper = _watcher(world, "Sleeper")
        sleeper.add_condition("sleeping")
        _light(monkeypatch, 90)
        _always_see(monkeypatch)

        # the derived state genuinely does not show the sleep ...
        assert sleeper.state != "sleeping"
        # ... but the observation is still correctly marked covert
        record = world.npc_behaviors.record_observations("Actor", "Lydia", "combat")[0]
        assert record["public"] is False

    def test_an_unconscious_witness_is_covert(self, monkeypatch):
        world = _world()
        _pair(world)
        _out = _watcher(world, "Out")
        _out.add_condition("unconscious")
        _light(monkeypatch, 90)
        _always_see(monkeypatch)

        record = world.npc_behaviors.record_observations("Actor", "Lydia", "combat")[0]
        assert record["public"] is False

    def test_a_blind_witness_is_covert(self, monkeypatch):
        world = _world()
        _pair(world)
        blind = _watcher(world, "Blind")
        blind.conditions["blind"] = [{}]
        _light(monkeypatch, 90)
        _always_see(monkeypatch)

        record = world.npc_behaviors.record_observations("Actor", "Lydia", "combat")[0]
        assert record["public"] is False

    def test_public_and_covert_witnesses_coexist(self, monkeypatch):
        world = _world()
        _pair(world)
        _watcher(world, "Lit")                       # 90
        _watcher(world, "Watcher")                   # pinned to 60 below
        _light(monkeypatch, 60)
        _always_see(monkeypatch)

        log = get_observation_signals()
        log.record("Lit", "Lydia", tick=world.time_ticks, public=True)
        log.record("Watcher", "Lydia", tick=world.time_ticks, public=False)

        assert set(log.observers_of("Lydia", tick=world.time_ticks)) == {"Lit", "Watcher"}
        assert log.public_observers_of("Lydia", tick=world.time_ticks) == ["Lit"]


# ── the cap bounds lines, not observers ──

class TestReactionCapDoesNotTruncateObservers:

    def test_every_observer_is_recorded_despite_the_line_cap(self, monkeypatch):
        world = _world()
        _pair(world)
        for name in ("A", "B", "C", "D"):
            _watcher(world, name)
        _light(monkeypatch, 60)
        _always_see(monkeypatch)

        lines = world.npc_behaviors.process_bystander_reactions(
            "Actor", "Lydia", "combat")

        assert len(lines) == 1, "the default cap of 1 line still holds"
        observed = get_observation_signals().observers_of("Lydia", tick=world.time_ticks)
        assert set(observed) == {"A", "B", "C", "D"}

    def test_raising_the_cap_only_raises_the_line_count(self, monkeypatch):
        world = _world()
        _pair(world)
        for name in ("A", "B", "C"):
            _watcher(world, name)
        _light(monkeypatch, 60)
        _always_see(monkeypatch)

        lines = world.npc_behaviors.process_bystander_reactions(
            "Actor", "Lydia", "combat", max_reactions=3)

        assert len(lines) == 3
        assert len(get_observation_signals().observers_of("Lydia", tick=world.time_ticks)) == 3

    def test_an_observer_who_ignores_is_still_recorded(self, monkeypatch):
        """Noticing and commenting are different facts (task-547)."""
        world = _world()
        world.mature_content = True
        _pair(world)
        # `attracted` approaches an arousal stimulus; a plain bystander ignores
        # one by default (`_reaction_type` -> "ignore" on SEXUAL_STIMULI).
        _watcher(world, "Wants", traits={"attracted": True})
        _watcher(world, "Indifferent")
        _light(monkeypatch, 60)
        _always_see(monkeypatch)

        lines = world.npc_behaviors.process_bystander_reactions(
            "Actor", "Lydia", "aroused")

        assert "Wants" in " ".join(lines)
        observed = get_observation_signals().observers_of("Lydia", tick=world.time_ticks)
        assert set(observed) == {"Wants", "Indifferent"}

    def test_only_simple_npcs_emit_lines(self, monkeypatch):
        world = _world()
        _pair(world)
        _watcher(world, "Simple", simple=True)
        _watcher(world, "Driven", simple=False)
        _light(monkeypatch, 60)
        _always_see(monkeypatch)

        lines = world.npc_behaviors.process_bystander_reactions(
            "Actor", "Lydia", "combat")

        assert len(lines) == 1 and "Simple" in lines[0]
        observed = get_observation_signals().observers_of("Lydia", tick=world.time_ticks)
        assert set(observed) == {"Simple", "Driven"}
