"""The dash burst: a dash is a two-hop action (task-784).

A dash is paid for by a major (the initiate) and a minor (the finish hop), and
while a burst is armed the finish is the ONLY valid action. The rule lives in
`engine.action_tiers.apply_action_gate` so every budgeted actor shares it (humans
and LLM agents submit through `_slot_gate`, which calls this). These tests pin
the mechanism: the two-slot cost, the finish-only window, the abort, and that a
refused dash does not spend the major.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine import action_tiers as at  # noqa: E402


def _slots():
    return dict(at.DEFAULT_BUDGET)


def test_a_dash_needs_both_a_major_and_a_minor():
    # No minor to finish with: the dash cannot even be started.
    slots = _slots()
    slots["minor"] = 0
    err, burst = at.apply_action_gate(slots, "dash", 0)
    assert err and burst == "none"
    assert slots["major"] == 1, "a refused dash must not spend the major"

    slots = _slots()
    slots["major"] = 0
    err, burst = at.apply_action_gate(slots, "dash", 0)
    assert err and burst == "none"


def test_a_dash_spends_the_major_and_arms_the_burst():
    slots = _slots()
    err, burst = at.apply_action_gate(slots, "dash", 0)
    assert err is None and burst == "arm"
    # The major pays for the hop; the minor is held for the finish.
    assert slots["major"] == 0 and slots["minor"] == 1


def test_the_finish_hop_costs_the_minor_and_clears_the_burst():
    slots = _slots()
    slots["major"] = 0          # the dash already spent it
    err, burst = at.apply_action_gate(slots, "go", 1)
    assert err is None and burst == "clear"
    assert slots["minor"] == 0


def test_only_a_finish_is_valid_while_the_burst_is_armed():
    slots = _slots()
    slots["major"] = 0
    err, burst = at.apply_action_gate(slots, "look", 1)
    assert err and burst == "none"
    assert slots["minor"] == 1, "an unrelated action must not consume the finish"


def test_approach_does_not_finish_a_dash():
    # approach stops short of crossing, so it cannot complete the burst.
    slots = _slots()
    slots["major"] = 0
    err, burst = at.apply_action_gate(slots, "approach", 1)
    assert err and burst == "none"


def test_every_movement_verb_finishes_the_dash():
    for verb in ("go", "dash", "climb", "crawl", "jump"):
        slots = _slots()
        slots["major"] = 0
        err, burst = at.apply_action_gate(slots, verb, 1)
        assert err is None and burst == "clear", verb
        assert slots["minor"] == 0, verb


def test_wait_abandons_the_dash_without_spending_the_minor():
    slots = _slots()
    slots["major"] = 0
    err, burst = at.apply_action_gate(slots, "wait", 1)
    assert err is None and burst == "clear"
    assert slots["minor"] == 1, "an abort frees the minor instead of spending it"


def test_a_normal_action_spends_its_own_tier():
    slots = _slots()
    err, burst = at.apply_action_gate(slots, "look", 0)
    assert err is None and burst == "none"
    assert slots["free"] == 2

    slots = _slots()
    err, burst = at.apply_action_gate(slots, "go", 0)
    assert err is None and burst == "none"
    assert slots["major"] == 0


def test_a_normal_action_is_refused_when_its_slot_is_gone():
    slots = _slots()
    slots["major"] = 0
    slots["minor"] = 0
    slots["free"] = 0
    err, burst = at.apply_action_gate(slots, "go", 0)
    assert err
