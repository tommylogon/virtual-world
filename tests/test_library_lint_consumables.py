"""`tools/lint_library.py` — the consumable-authoring check (task-506).

The check itself is the deliverable that matters here: it turns "an item claims
to be food and restores nothing" from a data bug nobody notices into a lint
error. These tests pin the *rules*, not the library's current contents, so a
future content pass can legitimately add and remove items.

The three rules that were each got wrong at least once while writing this, and
are therefore each pinned by a test:

1. `trigger_type` may be a **list**. `apple.json` ships `["on_eat"]`, and a
   checker that only compares against a string reports all 71 edible/drinkable
   library items as unauthored — or, read the other way, misses real gaps.
2. Hunger and Thirst are **drives** that fill upward, so relief is a **negative**
   `adjust_vital` amount. Checking the sign the other way round flags every
   correctly-authored item.
3. Both trigger shapes exist in the data: the modern
   `effects: [{type, params}]` list and the older flat
   `effect_type`/`effect_params` pair.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import lint_library  # noqa: E402

REPO_LIB = ROOT / "data" / "library"


def _item(name, tags, actions="", triggers=None, uses=1):
    return {
        "name": name,
        "tags": tags,
        "actions": actions,
        "uses": uses,
        "triggers": triggers or [],
        "description": f"A {name}.",
        "weight": 0.5,
    }


def _modern(stat, amount, trigger_type="on_eat"):
    return {
        "trigger_type": trigger_type,
        "effects": [
            {"type": "adjust_vital",
             "params": {"stat": stat, "amount": amount, "target": "self"}}
        ],
        "conditions": {},
    }


def _errors(items):
    report = lint_library.Report()
    lint_library.check_unauthored_consumables(items, report)
    return [message for check, message in report.errors if check == "unauthored_consumables"]


# ── the happy path ────────────────────────────────────────────────────────


def test_a_food_with_relief_passes():
    items = {"bread": _item("bread", ["food"], "eat", [_modern("Hunger", -25)])}
    assert _errors(items) == []


def test_a_drink_with_relief_passes():
    items = {"flask": _item("flask", ["drink"], "drink",
                            [_modern("Thirst", -50, "on_drink")])}
    assert _errors(items) == []


def test_a_non_consumable_is_not_asked_for_a_trigger():
    items = {"rock": _item("rock", ["mineral"]), "sword": _item("sword", ["weapon"])}
    assert _errors(items) == []


# ── the gap this exists to catch ──────────────────────────────────────────


def test_a_tag_only_food_is_an_error():
    """The case task-506 measured 64 times over: a `food` tag and nothing else."""
    items = {"mystery_stew": _item("mystery_stew", ["food"], "eat")}
    errors = _errors(items)
    assert len(errors) == 1
    assert "on_eat" in errors[0]
    assert "Hunger" in errors[0]


def test_a_trigger_with_no_relief_is_still_an_error():
    """`bread.json` shipped exactly this: an `on_eat` whose only effect was a
    `message`. It looked authored and restored nothing."""
    items = {"bread": _item("bread", ["food"], "eat", [{
        "trigger_type": "on_eat",
        "effects": [{"type": "message", "params": {"success_message": "It tastes good"}}],
    }])}
    assert _errors(items), "a message-only on_eat is not a restore"


def test_a_positive_amount_is_not_relief():
    """Drives fill upward, so +25 on Hunger is starvation, not supper."""
    items = {"bread": _item("bread", ["food"], "eat", [_modern("Hunger", 25)])}
    assert _errors(items)


def test_a_stat_that_is_not_a_drive_does_not_count():
    items = {"bread": _item("bread", ["food"], "eat", [_modern("Sanity", -10)])}
    assert _errors(items)


def test_a_missing_amount_does_not_count():
    items = {"bread": _item("bread", ["food"], "eat", [{
        "trigger_type": "on_eat",
        "effects": [{"type": "adjust_vital", "params": {"stat": "Hunger"}}],
    }])}
    assert _errors(items)


# ── the shapes the data actually uses ─────────────────────────────────────


def test_trigger_type_as_a_list_counts():
    """`apple.json` ships `"trigger_type": ["on_eat"]`. Missing this is how 64
    items came to look authored when they were not."""
    trigger = _modern("Hunger", -2)
    trigger["trigger_type"] = ["on_eat"]
    items = {"apple": _item("apple", ["food"], "eat", [trigger])}
    assert _errors(items) == []


def test_the_older_flat_effect_shape_counts():
    items = {"rations": _item("rations", ["food"], "eat", [{
        "trigger_type": "on_eat",
        "effect_type": "adjust_vital",
        "effect_params": {"stat": "Hunger", "amount": -25},
    }])}
    assert _errors(items) == []


def test_stat_casing_does_not_matter():
    """`rations_of_dried_meat.json` ships `"Hunger"`, `apple.json` shipped
    `"hunger"`. Both are the same stat."""
    items = {"a": _item("a", ["food"], "eat", [_modern("hunger", -25)]),
             "b": _item("b", ["food"], "eat", [_modern("HUNGER", -25)])}
    assert _errors(items) == []


def test_an_item_that_is_both_still_needs_both():
    items = {"flask": _item("flask", ["food", "drink"], "eat,drink",
                            [_modern("Hunger", -25)])}
    errors = _errors(items)
    assert len(errors) == 1 and "on_drink" in errors[0]


# ── the fixture escape hatch ──────────────────────────────────────────────


def test_a_declared_fixture_is_not_demanded_a_trigger():
    """A barrel is not bread. `ConsumeActionsMixin._is_valid_for` accepts a
    consumable by tag alone, so a mistagged fixture is not cosmetic — a
    background character will eat the barrel."""
    items = {"barrel": _item("barrel", ["food"], "eat", uses=-1)}
    assert _errors(items) == [], "barrel is in FOOD_ADJACENT_FIXTURES"


def test_the_fixture_list_only_exempts_those_items():
    """The list must not become a blanket exemption."""
    assert "barrel" in lint_library.FOOD_ADJACENT_FIXTURES
    assert "bread" not in lint_library.FOOD_ADJACENT_FIXTURES
    assert "berries" not in lint_library.FOOD_ADJACENT_FIXTURES


# ── the real library ──────────────────────────────────────────────────────


def test_the_shipped_library_passes():
    """The acceptance criterion, as a test, so it cannot silently regress."""
    items = lint_library.load_registry(str(REPO_LIB), "items")
    assert len(items) > 100
    assert _errors(items) == []


def test_the_check_is_registered_and_runs_from_the_cli():
    assert "unauthored_consumables" in lint_library.ERROR_CHECKS
    assert "unauthored_consumables" in lint_library.ALL_CHECKS
    result = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "lint_library.py"),
         "--check", "unauthored_consumables"],
        capture_output=True, text=True, cwd=str(ROOT))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "0 errors" in result.stdout
