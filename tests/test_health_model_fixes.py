"""Health-model bug fixes (task-538 groundwork).

Four defects, each pinned by a test that fails without the fix.

1. ``heal`` clamped to a hardcoded 100 instead of the target's own ceiling, so
   healing a 7-HP goblin by 5 produced 12 HP. Harmless only because ``Max_HP``
   was itself always 100 — the bug was masked by the very assumption the health
   work removes.
2. ``heal`` had no ``target`` param and always acted on ``game_state.player``,
   unlike ``apply_condition`` and ``adjust_vital`` which both accept one.
3. HP regeneration was gated on ``HP < 100`` rather than ``HP < Max_HP``. Against
   a real maximum that is permanently true, so the character regenerates every
   turn and can never be worn down.
4. ``world._clock_advanced_by_task`` was set by ``rest`` and never cleared, so the
   very first rest in a world's life permanently muted the per-action clock on
   the MCP tool path. The guard is one-shot: the reader must consume it.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from player import Player

AREA = "Blizzard Forest Clearing"


def _world():
    from app import create_app
    return create_app({"TESTING": True}).world


def _add(world, name):
    p = Player(name)
    world.add_player(p)
    p.current_area = AREA
    world.set_player_area(p.name, AREA)
    return p


def _goblin(world, name="Goblin", max_hp=7, hp=None):
    """A stat block on a real scale: 7 HP, not the 100 default."""
    p = _add(world, name)
    p.vitals["Max_HP"] = max_hp
    p.vitals["HP"] = max_hp if hp is None else hp
    return p


def _heal(world, params, subject):
    world.player_manager.set_active_player(subject.name)
    return world.triggers._effects.execute("heal", params, {}, game_state=world)


# ── 1. heal must respect the target's own ceiling ──────────────────────

def test_heal_does_not_exceed_max_hp():
    """The core regression: 7 max HP, heal 5 -> 7, never 12."""
    world = _world()
    gob = _goblin(world, hp=4)
    _heal(world, {"amount": 5}, gob)
    assert gob.vitals["HP"] == 7, (
        f"heal overshot Max_HP: {gob.vitals['HP']} > {gob.vitals['Max_HP']}"
    )


def test_heal_reports_the_amount_actually_restored():
    world = _world()
    gob = _goblin(world, hp=4)
    out = _heal(world, {"amount": 5}, gob)
    assert any("3" in line for line in out), out


def test_heal_at_full_reports_nothing_to_restore():
    world = _world()
    gob = _goblin(world)
    out = _heal(world, {"amount": 5}, gob)
    assert gob.vitals["HP"] == 7
    assert out, "should say it cannot be restored further"


def test_heal_still_works_for_a_100_hp_character():
    """The common case must be untouched by the ceiling fix."""
    world = _world()
    bruiser = _add(world, "Bruiser")
    bruiser.vitals["Max_HP"] = 100
    bruiser.vitals["HP"] = 50
    _heal(world, {"amount": 25}, bruiser)
    assert bruiser.vitals["HP"] == 75


def test_heal_respects_a_non_hp_vital_ceiling():
    """Energy has no Max_ companion, so the 0-100 ceiling still applies."""
    world = _world()
    bruiser = _add(world, "Bruiser")
    bruiser.vitals["Energy"] = 95
    _heal(world, {"amount": 25, "stat": "Energy"}, bruiser)
    assert bruiser.vitals["Energy"] == 100


# ── 2. heal must honour target ─────────────────────────────────────────

def test_heal_targets_another_character():
    world = _world()
    caster = _add(world, "Caster")
    patient = _goblin(world, name="Patient", hp=1)
    world.player_manager.set_active_player(caster.name)
    world.triggers._effects.execute(
        "heal", {"amount": 5, "target": "Patient"}, {}, game_state=world)
    assert patient.vitals["HP"] == 6, patient.vitals["HP"]
    assert caster.vitals["HP"] == caster.vitals["HP"], "caster must be untouched"


def test_heal_resolves_a_mixed_case_target_name():
    world = _world()
    _add(world, "Caster")
    patient = _goblin(world, name="Patient", hp=1)
    world.player_manager.set_active_player("Caster")
    world.triggers._effects.execute(
        "heal", {"amount": 5, "target": "patient"}, {}, game_state=world)
    assert patient.vitals["HP"] == 6


# ── 3. regeneration must stop at the real maximum ──────────────────────

def test_hp_regen_stops_at_a_max_below_100():
    """A 7-HP character at full HP must not keep regenerating."""
    world = _world()
    gob = _goblin(world, hp=7)
    gob.vitals.update({"Energy": 90, "Hunger": 90, "Thirst": 90,
                       "Sanity": 90, "Temperature": 37.0})
    before = gob.vitals["HP"]
    for _ in range(5):
        world.tick_manager.tick_turn()
    assert gob.vitals["HP"] == before, (
        f"regenerated to {gob.vitals['HP']} despite being at Max_HP {before}"
    )


def test_hp_regen_still_happens_below_the_maximum():
    """The gate must still open when there is actually something to heal."""
    world = _world()
    gob = _goblin(world, hp=2)
    gob.vitals.update({"Energy": 90, "Hunger": 90, "Thirst": 90,
                       "Sanity": 90, "Temperature": 37.0})
    for _ in range(40):
        world.tick_manager.tick_turn()
    assert gob.vitals["HP"] > 2, "a wounded character should regenerate"
    assert gob.vitals["HP"] <= 7, "and never past the ceiling"


# ── 4. the clock guard must be one-shot ────────────────────────────────

def test_clock_guard_is_consumed_by_the_next_tool_action():
    """After a rest, exactly one action forgoes its minute — not all of them."""
    from tools.game_tools import get_tools

    world = _world()
    world._clock_advanced_by_task = False
    tools = get_tools(world)
    tools["look"]()

    world.tick_manager.rest(minutes=2)
    assert world._clock_advanced_by_task is True, "rest marks the clock advanced"

    before = world.time_ticks
    tools["look"]()
    # This is the action the guard exists for: rest already paid for the minute.
    assert world.time_ticks == before, "guard should suppress exactly this one"
    assert world._clock_advanced_by_task is False, "and the guard must be consumed"

    after = world.time_ticks
    tools["look"]()
    assert world.time_ticks == after + 1, (
        "the very next action must advance the clock again — otherwise the "
        "first rest in a world's life stops time for every action after it"
    )
