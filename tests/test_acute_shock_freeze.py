"""Tests for acute shock freeze saving throws and recovery (task-956)."""

from __future__ import annotations

from player import Player
from engine.fear import release_acute_shock_on_damage, trigger_acute_shock_freeze


class _DummyWorld:
    time_ticks = 10
    time_per_tick_minutes = 5


def test_acute_shock_save_modulated_by_traits_and_recovers_on_damage():
    gs = _DummyWorld()

    coward = Player("Timmy")
    coward.traits = {"cowardly": True}
    res = trigger_acute_shock_freeze(gs, coward, "Raider", trigger_kind="combat_threat", roll_fn=lambda: 10)
    assert res is not None and res["saved"] is False
    assert res["total"] == 6
    assert coward.flags.get("frozen_by_fear") is True
    assert coward._fear_freeze_until_tick == 11
    assert any(inst.get("source") == "acute_shock" for inst in (coward.conditions or {}).get("stunned", []))

    # Damage breaks acute shock freeze immediately
    assert release_acute_shock_on_damage(coward) is True
    assert "frozen_by_fear" not in (coward.flags or {})
    assert coward._fear_freeze_until_tick is None
    assert "stunned" not in (coward.conditions or {})

    # Brave character passes the same roll (10 + 4 = 14 >= DC 12)
    brave = Player("Brienne")
    brave.traits = {"brave": True}
    bres = trigger_acute_shock_freeze(gs, brave, "Raider", trigger_kind="combat_threat", roll_fn=lambda: 10)
    assert bres is not None and bres["saved"] is True
    assert "frozen_by_fear" not in (brave.flags or {})
    assert "stunned" not in (brave.conditions or {})

    # Fearless character is immune
    fearless = Player("Golem")
    fearless.traits = {"fearless": True}
    assert trigger_acute_shock_freeze(gs, fearless, "Raider", trigger_kind="combat_threat", roll_fn=lambda: 1) is None
