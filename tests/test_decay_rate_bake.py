"""Baked decay rates must agree with the engine defaults (task-431).

Scenarios and `world_template.json` serialize each player's full `decay_rates`
dict, and the loader treats those as *overrides* — so the calibrated defaults in
`vital_rates.BASELINE_DECAY` are ignored for any saved world. A scenario baked
before a recalibration therefore keeps the old feel forever, silently.

That is not hypothetical. The camp shipped with `Social: 0.05` against an engine
default of `0.02` and a company gain of `0.03`, so Social fell *even in constant
company*; Sanity is coupled to Social, so all 23 characters ended a week in
`social_breakdown` plus `hallucinating`. Thirteen other scenarios baked the
legacy `1` for every vital, which the per-minute engine applies as -1/min —
vitals empty in about a hundred minutes.

An **absent** `decay_rates` or an empty `{}` is correct and expected: it means
"use the engine defaults", and it keeps following them.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from vital_rates import BASELINE_DECAY, BLADDER_FILL, SOCIAL_COMPANY_GAIN

ROOT = Path(__file__).parent.parent
CANONICAL = {**BASELINE_DECAY, "Bladder": BLADDER_FILL}

#: Scenarios allowed to disagree with a canonical value, with the reason. Empty
#: on purpose: a deliberate per-scenario rate is a balance decision that should be
#: recorded here in the same commit that makes it.
DOCUMENTED_DRIFT = {}


def _scenario_files():
    files = [ROOT / "world_template.json"]
    files += sorted((ROOT / "data" / "scenarios").glob("*.json"))
    return [f for f in files if f.exists()]


def _players(path):
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as e:  # a malformed scenario is another test's problem
        pytest.skip(f"{path.name} unreadable: {e}")
    return data.get("players") or {}


def _drift(path):
    """{(vital, baked, canonical): set(player names)} for this file."""
    found = {}
    for name, pdata in _players(path).items():
        if not isinstance(pdata, dict):
            continue
        for vital, baked in (pdata.get("decay_rates") or {}).items():
            canonical = CANONICAL.get(vital)
            if canonical is None:
                continue
            try:
                differs = abs(float(baked) - float(canonical)) > 1e-9
            except (TypeError, ValueError):
                differs = True
            if differs:
                found.setdefault((vital, baked, canonical), set()).add(name)
    return found


@pytest.mark.parametrize("path", _scenario_files(), ids=lambda p: p.name)
def test_no_scenario_bakes_a_rate_that_contradicts_the_engine_default(path):
    drift = _drift(path)
    if not drift:
        return
    rel = path.relative_to(ROOT).as_posix()
    if rel in DOCUMENTED_DRIFT:
        return
    lines = [f"{rel} bakes decay rates that disagree with vital_rates.BASELINE_DECAY:"]
    for (vital, baked, canonical), names in sorted(drift.items()):
        lines.append(f"  {vital}: baked {baked}, engine {canonical} "
                     f"({len(names)} player(s), e.g. {sorted(names)[0]})")
    lines.append("")
    lines.append("Fix with:  python tools/migrate_decay_rates.py --all")
    lines.append("Or add the file to DOCUMENTED_DRIFT with a reason.")
    pytest.fail("\n".join(lines))


def test_the_boot_template_matches_the_engine_defaults():
    """The world every new game starts from must not freeze stale rates."""
    assert _drift(ROOT / "world_template.json") == {}


def test_the_camp_social_rate_matches_the_engine_default():
    """The specific regression: baked Social 0.05 made Social impossible."""
    camp = ROOT / "data" / "scenarios" / "kraktooth_goblin_camp.json"
    assert _drift(camp) == {}, "the camp's decay rates drifted again"


def test_company_is_maintenance_not_a_source():
    """task-431 decision: company stops the rot, interaction fills the meter.

    `SOCIAL_COMPANY_GAIN` must not exceed the Social baseline, or mere
    co-presence fills Social and every social action lands on a capped vital.
    (It was 0.030 against a 0.020 baseline: +14.4/day with nothing competing.)
    """
    assert SOCIAL_COMPANY_GAIN <= BASELINE_DECAY["Social"], (
        "company gain exceeds the Social baseline — co-presence would fill "
        "Social on its own and task-423's interactions would be decoration"
    )
