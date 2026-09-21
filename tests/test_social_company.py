"""Company-aware Social need (task: decay must care about company).

Being alone drains Social FASTER than baseline; company stops the rot. The
`social_gain` trait effect (extrovert: 2, introvert: 0) scales both directions.
Built on a VirtualWorld() plus a real area node so the whole per-tick
environment block runs.

Rates are per in-game minute and now come from the engine defaults (task-431
re-baked the scenario, which used to carry 0.05 for Social against a 0.020
default): baseline Social drains 0.020/min, alone adds 0.020/min (plus 0.020/min
isolation after 5 consecutive alone-ticks), and company adds exactly the
baseline — **maintenance, not a source** (task-431 decision). Interaction is
what fills Social (task-423). Fractional rates mean a single tick usually moves
nothing, so these tests run a span of ticks and compare outcomes rather than
asserting one tick's integer.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from player import Player

AREA = "Blizzard Forest Clearing"
SPAN = 30


def _world():
    from app import create_app
    app = create_app({"TESTING": True})
    return app.world


def _place(world, name, area=AREA):
    """Get (or create) a player and put them in ``area``."""
    if name in world.player_manager.players:
        p = world.player_manager.players[name]
    else:
        p = Player(name)
        world.add_player(p)
    p.current_area = area
    world.set_player_area(name, area)
    return p


def _clear_area(world, keep, area=AREA):
    """Move everyone except ``keep`` out of ``area``."""
    for other in world.player_manager.players.values():
        if other is not keep and other.current_area == area:
            other.current_area = "Kitchen"
            world.set_player_area(other.name, "Kitchen")


def _run(world, n=SPAN):
    for _ in range(n):
        world.tick_turn()


def _social_after(world, name, alone, traits=None, company=False):
    """Place ``name`` (± a companion), tick SPAN times, return final Social."""
    p = _place(world, name)
    if traits:
        p.traits.update(traits)
    p.vitals["Social"] = 80
    if alone:
        _clear_area(world, p)
    if company:
        mate = _place(world, "Other")
        mate.vitals["Social"] = 80
    _run(world)
    return p.vitals["Social"]


def test_alone_social_decays_faster_than_baseline():
    """Default alone (baseline + alone penalty + isolation) drains faster
    than an introvert alone (baseline only)."""
    alone = _social_after(_world(), "Kaelen Voss", alone=True)
    introvert = _social_after(_world(), "Kaelen Voss", alone=True, traits={"introvert": True})
    assert alone < introvert


def test_company_social_is_fed_every_tick():
    """Company gain cancels the baseline drain: Social holds steady.

    This is the task-431 decision, not an accident — `SOCIAL_COMPANY_GAIN` equals
    the Social baseline on purpose. Company is *maintenance*: it stops the rot.
    Filling the meter is interaction's job (task-423). See
    tests/test_decay_rate_bake.py::test_company_is_maintenance_not_a_source.
    """
    world = _world()
    world.time_per_tick_minutes = 1
    p1 = _place(world, "Kaelen Voss")
    p2 = _place(world, "Other", AREA)
    p1.vitals["Social"] = 80
    p2.vitals["Social"] = 80
    _run(world)
    assert p1.vitals["Social"] >= 79
    assert p2.vitals["Social"] >= 79


def test_company_alone_does_not_fill_social():
    """A long stretch of constant company must not peg Social at 100.

    It used to: gain 0.030 against a 0.020 baseline is +14.4/day with nothing
    competing, so a week of merely standing near people filled the meter and made
    every social action land on a capped vital.
    """
    world = _world()
    world.time_per_tick_minutes = 1
    p1 = _place(world, "Kaelen Voss")
    p2 = _place(world, "Other", AREA)
    p1.vitals["Social"] = 50
    p2.vitals["Social"] = 50
    _run(world, 600)  # ten in-game hours of company
    assert p1.vitals["Social"] <= 55, "company filled Social on its own"
    assert p2.vitals["Social"] <= 55


def test_extrovert_alone_craves_company_more():
    """Extrovert social_gain=2 doubles the alone penalty, so they drain more
    than a default character with nobody around."""
    default = _social_after(_world(), "Kaelen Voss", alone=True)
    extrovert = _social_after(_world(), "Kaelen Voss", alone=True, traits={"extrovert": True})
    assert extrovert < default


def test_extrovert_company_gains_extra():
    """With company, extrovert social_gain=2 nets positive while a default
    character merely holds steady."""
    default = _social_after(_world(), "Kaelen Voss", alone=False, company=True)
    extrovert = _social_after(_world(), "Kaelen Voss", alone=False, company=True,
                              traits={"extrovert": True})
    assert extrovert > default


def test_introvert_alone_keeps_only_baseline():
    """Introvert social_gain=0 means no company bonus AND no alone penalty,
    so they drain slower than a default character when alone."""
    default = _social_after(_world(), "Kaelen Voss", alone=True)
    introvert = _social_after(_world(), "Kaelen Voss", alone=True, traits={"introvert": True})
    assert introvert > default


def test_alone_log_line_reports_cause_for_active_player():
    world = _world()
    p1 = _place(world, "Kaelen Voss")
    world.set_active_player("Kaelen Voss")
    _clear_area(world, p1)
    p1.vitals["Social"] = 50
    _run(world, 2)
    log_blob = "\n".join(world.game_logger.game_log)
    assert "Social" in log_blob
    assert "alone in Blizzard Forest Clearing" in log_blob
