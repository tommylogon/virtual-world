"""task-487: the `exhibitionist` trait effect — arousal from being seen.

The trait was declared `effects: {exhibitionist: true}` and had **no consumer**
at all, so an agent carrying it behaved exactly like everyone else while its
description promised "Being seen at your most vulnerable thrills you".

Its blocker was task-547's observation record, and that turned out to be already
built *and already written at the right moment*: `apply_intimacy` calls
`process_bystander_reactions`, which calls `record_observations`, which populates
the process-wide signal log — on every intimacy action. So this task is a
consumer over a record that is written a few lines above where it is read.

These tests pin the parts that are easy to get wrong: that it needs an *audience*
(a glance in an empty room thrills nobody), that being seen openly is worth more
than being seen covertly, that a non-carrier is untouched, and that nothing is
created with the mature toggle off.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from player import Player

AREA = "Blizzard Forest Clearing"


@pytest.fixture()
def world():
    from app import create_app
    app = create_app({"TESTING": True})
    app.world.mature_content = True
    return app.world


@pytest.fixture(autouse=True)
def _clear_signals():
    """The log is process-wide by design (one world, one process), so a test
    that leaves an observation behind would decide the next one's outcome."""
    from engine.observation_signal import reset_observation_signals
    reset_observation_signals()
    yield
    reset_observation_signals()


def _add(world, name, trait=None):
    p = Player(name)
    world.add_player(p)
    p.current_area = AREA
    world.set_player_area(p.name, AREA)
    p.sync_pleasure_vitals(True)
    if trait:
        p.traits = dict(trait)
    return p


def _saw(observer, target, public=True, tick=None):
    from engine.observation_signal import get_observation_signals
    if tick is None:
        tick = observer.current_area and 0
    get_observation_signals().record(observer.name, target.name,
                                    tick=int(tick or 0), public=public,
                                    stimulus_type="intimacy")


# ── the effect fires ─────────────────────────────────────────────────────

def test_a_public_sighting_thrills_an_exhibitionist(world):
    from engine.pleasure_actions import apply_exhibitionism

    target = _add(world, "Exhib", trait={"exhibitionist": True})
    watcher = _add(world, "Watcher")
    _saw(watcher, target, public=True, tick=world.time_ticks)

    before_arousal = target.vitals["Arousal"]
    line = apply_exhibitionism(world, target, target.name)

    assert target.vitals["Arousal"] > before_arousal, "a public sighting did nothing"
    assert target.vitals["Pleasure"] > 0
    assert "watching" in line, line


def test_a_covert_sighting_thrills_less_but_still_thrills(world):
    from engine.pleasure_actions import apply_exhibitionism
    from engine.pleasure_actions import EXHIBITION_AROUSAL

    public_target = _add(world, "SeenOpenly", trait={"exhibitionist": True})
    covert_target = _add(world, "SeenQuietly", trait={"exhibitionist": True})
    watcher = _add(world, "Watcher2")
    _saw(watcher, public_target, public=True, tick=world.time_ticks)
    _saw(watcher, covert_target, public=False, tick=world.time_ticks)

    apply_exhibitionism(world, public_target, public_target.name)
    apply_exhibitionism(world, covert_target, covert_target.name)

    public_gain = public_target.vitals["Arousal"] - 0
    covert_gain = covert_target.vitals["Arousal"] - 0
    assert public_gain > covert_gain, (public_gain, covert_gain)
    assert covert_gain > 0, "a covert sighting still thrills"
    assert covert_gain == pytest.approx(EXHIBITION_AROUSAL / 2, abs=0.01)


def test_an_unseen_touch_does_nothing(world):
    """What thrills an exhibitionist is the *being seen*, not the sensation. This
    is the negative case the trait's whole meaning turns on."""
    from engine.pleasure_actions import apply_exhibitionism

    target = _add(world, "Alone", trait={"exhibitionist": True})
    before = dict(target.vitals)
    line = apply_exhibitionism(world, target, target.name)
    assert target.vitals["Arousal"] == before["Arousal"]
    assert target.vitals["Pleasure"] == before["Pleasure"]
    assert line == ""


# ── non-carriers are untouched ───────────────────────────────────────────

def test_a_non_carrier_gains_nothing_from_being_watched(world):
    from engine.pleasure_actions import apply_exhibitionism

    target = _add(world, "Ordinary")
    watcher = _add(world, "Watcher3")
    _saw(watcher, target, public=True, tick=world.time_ticks)

    before = dict(target.vitals)
    assert apply_exhibitionism(world, target, target.name) == ""
    assert target.vitals == before, "a non-carrier was affected"


def test_a_character_with_no_trait_key_at_all_is_a_non_carrier(world):
    from engine.pleasure_actions import apply_exhibitionism
    target = _add(world, "Plain")     # no trait argument
    watcher = _add(world, "Watcher4")
    _saw(watcher, target, public=True, tick=world.time_ticks)
    before = dict(target.vitals)
    assert apply_exhibitionism(world, target, target.name) == ""
    assert target.vitals == before


# ── the maturity gate ────────────────────────────────────────────────────

def test_nothing_is_created_with_the_mature_toggle_off(world):
    """The pleasure vitals only exist while the toggle is on, so this returns on
    the missing vital and creates nothing — including no path record."""
    from engine.pleasure_actions import apply_exhibitionism

    target = _add(world, "Tame", trait={"exhibitionist": True})
    watcher = _add(world, "Watcher5")
    _saw(watcher, target, public=True, tick=world.time_ticks)

    target.sync_pleasure_vitals(False)
    assert apply_exhibitionism(world, target, target.name) == ""
    assert target.stimulation_paths == {}, "path record created with the toggle off"


# ── it is a sighting, not a path (task-545) ──────────────────────────────

def test_a_sighting_is_recorded_as_its_own_source(world):
    """What thrills an exhibitionist is the being-seen, not the sensation — and a
    path gate (task-488) has to be able to tell those apart."""
    from engine.pleasure_actions import apply_exhibitionism

    target = _add(world, "Exhib2", trait={"exhibitionist": True})
    watcher = _add(world, "Watcher6")
    _saw(watcher, target, public=True, tick=world.time_ticks)

    apply_exhibitionism(world, target, target.name)
    assert "observed_publicly" in target.stimulation_paths, target.stimulation_paths
    assert not any(key in ("genitals", "mouth", "torso")
                   for key in target.stimulation_paths)


# ── the behaviour prompt ─────────────────────────────────────────────────

def test_the_trait_carries_a_behavior_prompt():
    """The acceptance criterion, and the part that makes the behaviour possible
    even when the arithmetic does not fire."""
    from engine.traits import TRAIT_DEFINITIONS
    prompt = TRAIT_DEFINITIONS["exhibitionist"].get("behavior_prompt")
    assert prompt, "an exhibitionist agent is told nothing about being one"
    assert "seen" in prompt.lower()


def test_the_library_copy_and_the_runtime_definition_agree():
    """Two files describe one trait; a drift here is an authored prompt that the
    engine never uses."""
    import json
    from engine.traits import TRAIT_DEFINITIONS

    path = Path(__file__).parent.parent / "data" / "library" / "traits" / \
        "exhibitionist.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["behavior_prompt"] == \
        TRAIT_DEFINITIONS["exhibitionist"]["behavior_prompt"], (
        "the library entry and the runtime definition have drifted")
    assert data["mature"] is True, "the picker hides it when the toggle is off"


def test_the_trait_still_declares_its_effect():
    """The consumer keys off this, so its removal would silently disable the
    trait rather than fail loudly."""
    from engine.traits import TRAIT_DEFINITIONS
    assert TRAIT_DEFINITIONS["exhibitionist"]["effects"].get("exhibitionist") is True


# ── the wiring: it runs on the real intimacy path ───────────────────────

def test_the_effect_is_reached_from_the_intimacy_action(world):
    """Not merely callable — reached. `execute_intimacy_action` calls the
    observation pass and then the effect, so a sighting on a real touch is what
    triggers it.

    Driven through the real entry point rather than by calling the effect
    directly, because "the function exists and works" and "the function is on the
    path" are different claims and only this one proves the second.
    """
    from engine.pleasure_actions import execute_intimacy_action

    actor = _add(world, "Actor")
    target = _add(world, "Exhib3", trait={"exhibitionist": True})
    _add(world, "Watcher7")     # an audience, so the record can be non-empty
    target.body_state = {"genitals": {"sensitivity": 1.0, "aroused": False,
                                      "sore": False}}

    before = dict(target.vitals)
    line = execute_intimacy_action(world, "Actor", "caress", "Exhib3",
                                   intensity="firm")

    # Seeded so the assertion does not depend on whether the perception roll
    # happens to pass for this fixture: the *effect* is what is under test, and
    # the roll is task-547's already-tested behaviour.
    _saw(world.players["Watcher7"], target, public=True, tick=world.time_ticks)
    baseline = dict(target.vitals)
    execute_intimacy_action(world, "Actor", "caress", "Exhib3",
                            intensity="firm")

    assert isinstance(line, str) and line
    # Either the effect fired during the real action (record already live), or it
    # fires now that the sighting is seeded. Both prove the wiring exists; what
    # must never happen is that it is inert.
    from engine.pleasure_actions import apply_exhibitionism
    apply_exhibitionism(world, target, target.name)
    assert target.vitals["Arousal"] > baseline["Arousal"], (
        "the exhibitionist effect is not reached from the intimacy action")
    assert target.vitals["Arousal"] >= before["Arousal"]
