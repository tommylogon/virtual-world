"""task-545 / 546 / 488: stimulation path tracking, frustration, and the
`single_track` gate — the three that were blocked on each other.

- **545** records *which path* raised `Stimulation`, so a release threshold can
  read it. `apply_stimulation` already received `region_id`/`verb`/`intensity`
  and folded all of it into one integer.
- **546** gives a build with no satisfying outcome somewhere to put the tension,
  as a condition (mirroring `sensitized`) rather than a vital.
- **488** is the consumer: `single_track` gates release to one named route. The
  trait was declared with `effects: {single_track: true}` and had no consumer.

The maturity gate is load-bearing: with `world.mature_content` off nothing is
recorded, no condition is created, and the ordinary cascade is untouched.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.pleasure_actions import apply_stimulation
from player import Player

AREA = "Blizzard Forest Clearing"


@pytest.fixture()
def world():
    from app import create_app
    app = create_app({"TESTING": True})
    app.world.mature_content = True
    return app.world


def _add(world, name, mature=True):
    p = Player(name)
    world.add_player(p)
    p.current_area = AREA
    world.set_player_area(p.name, AREA)
    p.sync_pleasure_vitals(mature)
    # A plain `Player` has an empty `body_state`, so every region reads the
    # default sensitivity and the whole pipeline returns zero. The path record is
    # only meaningful when something actually raised the meter, so these tests
    # need a body that responds.
    p.body_state = {
        region: {"sensitivity": 1.0, "aroused": False, "sore": False}
        for region in ("genitals", "genitals_inner", "mouth", "lips", "torso",
                       "breasts", "hands", "nipple_left")
    }
    return p


def _touch(p, verb="caress", region="genitals", intensity="normal"):
    """`apply_stimulation(actor, target, ...)`. The actor is unused by the
    multiplier pipeline; the target is who is affected."""
    return apply_stimulation(None, p, verb, region, intensity)


def _tick(world, p, times=1):
    for _ in range(times):
        world.tick_manager._pleasure_tick(p, p.name)


# ── task-545: a gain records its source ──────────────────────────────────

def test_an_interaction_records_the_region_as_the_path():
    p = Player("Touched")
    p.sync_pleasure_vitals(True)
    report = _touch(p, "caress", "genitals", "strong")
    assert report.get("path") == "genitals", report
    assert p.stimulation_paths.get("genitals", 0) > 0, p.stimulation_paths
    assert p.stimulation_last_path == "genitals"


def test_the_path_is_the_region_alone_not_the_verb():
    """The task's recommendation, and the reason it is the region: the trait
    talks about a route, not a specific move, so two verbs on one region must
    file under one key."""
    p = Player("Both")
    p.sync_pleasure_vitals(True)
    _touch(p)
    _touch(p, "kiss", "genitals")
    keys = [k for k in p.stimulation_paths if k != "clothing_friction"]
    assert keys == ["genitals"], p.stimulation_paths
    # Both contributions accumulated into the one route.
    assert p.stimulation_paths["genitals"] >= 2


def test_the_record_survives_accumulation():
    p = Player("Accumulates")
    p.sync_pleasure_vitals(True)
    for _ in range(5):
        _touch(p)
    assert p.stimulation_from_path("genitals") > 0
    assert p.stimulation_path_total() > 0


def test_stimulation_from_path_is_zero_for_a_path_never_touched():
    p = Player("Untouched")
    p.sync_pleasure_vitals(True)
    assert p.stimulation_from_path("mouth") == 0.0


def test_a_release_clears_the_record():
    """The record is scoped to a build; a release ends it."""
    p = Player("Releases")
    p.sync_pleasure_vitals(True)
    _touch(p)
    assert p.stimulation_paths
    p.clear_stimulation_paths()
    assert p.stimulation_paths == {}
    assert p.stimulation_last_path is None
    assert p.stimulation_from_path("genitals") == 0.0


def test_a_non_positive_gain_records_nothing():
    """A decay step must not be able to erase the history of what raised it."""
    p = Player("NoOp")
    p.sync_pleasure_vitals(True)
    assert p.record_stimulation_path("genitals", 0) is None
    assert p.record_stimulation_path("genitals", -5) is None
    assert p.record_stimulation_path("", 5) is None
    assert p.stimulation_paths == {}


def test_the_mature_toggle_recognises_the_path_key_shape():
    p = Player("Keys")
    assert p.stimulation_path_key(region_id="genitals") == "genitals"
    # A non-interactive source is its own path, which is what makes the friction
    # drip distinguishable from any touch.
    assert p.stimulation_path_key(source="clothing_friction") == "clothing_friction"


# ── maturity gate: with it off, nothing is created ───────────────────────

def test_nothing_is_recorded_when_mature_content_is_off(world):
    world.mature_content = False
    p = _add(world, "Tame", mature=False)
    _touch(p)
    assert p.stimulation_paths == {}, "path record created with the toggle off"
    assert "Stimulation" not in p.vitals


def test_the_toggle_off_clears_an_existing_record(world):
    """Turning the toggle off must not leave invisible leftover bookkeeping that a
    re-enable would resurrect."""
    p = _add(world, "WasMature", mature=True)
    _touch(p)
    assert p.stimulation_paths
    p.sync_pleasure_vitals(False)
    assert p.stimulation_paths == {}
    assert p.stimulation_last_path is None


# ── the friction drip is a source, not a path ───────────────────────────

def test_clothing_friction_is_recorded_as_its_own_source(world):
    from graph import Edge, EDGE_EQUIPPED, Node
    p = _add(world, "Wearing")
    cloth = Node(id="item_rough_cloth", type="item", name="Rough Cloth",
                 properties={"friction": 3, "equip_slots": ["torso"]})
    world.graph.add_node(cloth)
    world.graph.add_edge(Edge(source=cloth.id,
                              target=world._player_node_id("Wearing"),
                              type=EDGE_EQUIPPED))
    _tick(world, p)
    assert "clothing_friction" in p.stimulation_paths, p.stimulation_paths
    # And it is not filed under any region.
    assert "genitals" not in p.stimulation_paths


# ── task-546: frustration ────────────────────────────────────────────────

def test_the_frustrated_condition_exists_and_is_mature():
    from engine.player_conditions import CONDITION_DEFINITIONS, MATURE_CONDITIONS
    assert "frustrated" in CONDITION_DEFINITIONS
    assert "frustrated" in MATURE_CONDITIONS, "must be stripped with the toggle"
    definition = CONDITION_DEFINITIONS["frustrated"]
    assert definition.get("symptoms"), "an invisible number is not worth building"
    assert definition.get("stack") == "accumulate", \
        "frustration is a build, not a flag"


def test_a_blocked_build_builds_frustration(world):
    p = _add(world, "Blocked")
    p.traits = {"single_track": {"path": "genitals"}}
    # Fill the meter past the release threshold with a DIFFERENT path.
    _touch(p)
    p.stimulation_paths.clear()
    _touch(p, "caress", "mouth")
    p.vitals["Stimulation"] = 70
    p.vitals["Arousal"] = 50
    _tick(world, p)
    assert "frustrated" in p.conditions, (
        "a gate that refuses without an outlet is just a stalled build")


def test_the_ordinary_release_path_is_unchanged(world):
    """The load-bearing negative: no trait, no gate, no frustration."""
    p = _add(world, "Ordinary")
    _touch(p)
    p.vitals["Stimulation"] = 70
    p.vitals["Arousal"] = 50
    _tick(world, p)
    assert "satisfied" in p.conditions, "the ordinary cascade must still fire"
    assert "frustrated" not in p.conditions
    assert p.stimulation_paths == {}, "a release empties the record"


def test_a_release_discharges_frustration(world):
    """Frustration must be worked off, not merely timed out."""
    p = _add(world, "WorksOff")
    p.add_condition("frustrated", duration=15)
    assert "frustrated" in p.conditions
    p.vitals["Stimulation"] = 70
    p.vitals["Arousal"] = 50
    _tick(world, p)
    assert "satisfied" in p.conditions
    assert "frustrated" not in p.conditions, "a release must discharge it"


# ── task-488: the single_track gate ──────────────────────────────────────

def test_a_non_carrier_releases_exactly_as_before(world):
    """Non-carriers are unaffected — stated first because it is the constraint
    that makes the gate safe."""
    p = _add(world, "NoTrait")
    p.traits = {}
    p.vitals["Stimulation"] = 70
    p.vitals["Arousal"] = 50
    _tick(world, p)
    assert "satisfied" in p.conditions
    assert "frustrated" not in p.conditions


def test_the_designated_path_releases(world):
    p = _add(world, "OnTrack")
    p.traits = {"single_track": {"path": "genitals"}}
    _touch(p)
    p.vitals["Stimulation"] = 70
    p.vitals["Arousal"] = 50
    _tick(world, p)
    assert "satisfied" in p.conditions, "the designated route must release"
    assert "frustrated" not in p.conditions


def test_a_non_designated_path_does_not_release(world):
    """The task's own acceptance, stated as the regression it is."""
    p = _add(world, "OffTrack")
    p.traits = {"single_track": {"path": "genitals"}}
    _touch(p, "caress", "mouth")
    p.vitals["Stimulation"] = 70
    p.vitals["Arousal"] = 50
    _tick(world, p)
    assert "satisfied" not in p.conditions, "a wrong path released anyway"
    assert "frustrated" in p.conditions


def test_the_trait_is_inert_when_no_route_is_named(world):
    """'Single track' with no track named is not a rule an engine can execute,
    so the trait does nothing rather than inventing one."""
    p = _add(world, "NoRoute")
    p.traits = {"single_track": {}}
    _touch(p, "caress", "mouth")
    p.vitals["Stimulation"] = 70
    p.vitals["Arousal"] = 50
    _tick(world, p)
    assert "satisfied" in p.conditions, "an unnamed track must not gate anything"
    assert "frustrated" not in p.conditions


def test_an_ancestor_route_matches_a_more_specific_recorded_region(world):
    """Naming `genitals` should cover a record under `genitals_inner`, so an
    author is not forced to know which sub-region the engine resolves."""
    p = _add(world, "Ancestor")
    p.traits = {"single_track": {"path": "torso"}}
    _touch(p)
    p.vitals["Stimulation"] = 70
    p.vitals["Arousal"] = 50
    _tick(world, p)
    assert "satisfied" in p.conditions, (
        "an ancestor route should cover a more specific recorded region")


def test_the_gate_reads_the_record_not_history(world):
    """The point of task-545: the check reads the recorded path, so it does not
    re-derive anything."""
    p = _add(world, "Recorded")
    p.traits = {"single_track": {"path": "genitals"}}
    _touch(p)
    allowed, _reason = world.tick_manager._release_gate(p, 70)
    assert allowed is True
    # Move the contribution to another path and the same call now refuses.
    p.stimulation_paths = {"mouth": p.stimulation_paths["genitals"]}
    allowed, reason = world.tick_manager._release_gate(p, 70)
    assert allowed is False, "the gate ignored the record"
    assert reason


def test_a_gate_is_refused_when_the_record_is_empty(world):
    """A full meter with nothing recorded cannot be on any designated path."""
    p = _add(world, "Empty")
    p.traits = {"single_track": {"path": "genitals"}}
    allowed, _ = world.tick_manager._release_gate(p, 70)
    assert allowed is False
