"""The camp's five consumables author their own consumption (task-424).

Regression guard for ``tools/author_camp_consumables.py``. The shipped items must
carry ``on_eat``/``on_drink`` triggers whose ``adjust_vital`` *relieves* the drive
(negative, because Hunger/Thirst are drives that rise) and whose depletion is
authored (``adjust_uses``), plus the water skin's ``on_depleted`` → ``set_state
empty`` so it empties and persists.

This is not cosmetic: the earlier data used **positive** amounts (legacy satiation
semantics), which under drive semantics *feed the fire instead of the character*
and starved the camp the moment the authored path went live.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SCENARIO = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..",
    "data", "scenarios", "kraktooth_goblin_camp.json",
)

#: item_id -> the drive its food relieves.
FOOD_ITEMS = {
    "item_berries": "Hunger",
    "item_bread": "Hunger",
    "item_dried_meat": "Hunger",
    "item_mushrooms": "Hunger",
}
#: item_id -> the drive its drink relieves.
DRINK_ITEMS = {"item_water_skin": "Thirst"}


def _camp():
    with open(SCENARIO, encoding="utf-8-sig") as f:
        return json.load(f)


def _nodes(data):
    nodes = data["graph"]["nodes"]
    return nodes if isinstance(nodes, dict) else {n["id"]: n for n in nodes}


def _trigger(data, item_id, trigger_type):
    """The trigger node on *item_id* for *trigger_type*, or None."""
    nodes = _nodes(data)
    for edge in data["graph"]["edges"]:
        if edge.get("source") != item_id or edge.get("type") != "triggers":
            continue
        if (edge.get("properties") or {}).get("trigger_type") == trigger_type:
            return nodes.get(edge.get("target"))
    return None


def _effects(trigger, effect_type):
    return [e for e in (trigger["properties"].get("effects") or [])
            if e.get("type") == effect_type]


def _test_one_drives_negative(trigger, stat, item_id):
    vitals = [e for e in _effects(trigger, "adjust_vital")
              if (e.get("params") or {}).get("stat") == stat]
    assert vitals, f"{item_id} does not adjust {stat}"
    amount = vitals[0]["params"].get("amount")
    assert isinstance(amount, int) and amount < 0, (
        f"{item_id} adjusts {stat} by {amount!r}; drive semantics need a "
        f"negative (relieving) amount"
    )


def test_each_camp_food_authors_a_relieving_on_eat():
    data = _camp()
    for item_id, stat in FOOD_ITEMS.items():
        trigger = _trigger(data, item_id, "on_eat")
        assert trigger is not None, f"{item_id} authors no on_eat trigger"
        _test_one_drives_negative(trigger, stat, item_id)
        assert _effects(trigger, "adjust_uses"), (
            f"{item_id} on_eat does not deplete uses — an infinite loaf"
        )


def test_each_camp_drink_authors_a_relieving_on_drink():
    data = _camp()
    for item_id, stat in DRINK_ITEMS.items():
        trigger = _trigger(data, item_id, "on_drink")
        assert trigger is not None, f"{item_id} authors no on_drink trigger"
        _test_one_drives_negative(trigger, stat, item_id)
        assert _effects(trigger, "adjust_uses"), (
            f"{item_id} on_drink does not deplete uses"
        )


def test_the_water_skin_empties_and_persists():
    data = _camp()
    trigger = _trigger(data, "item_water_skin", "on_depleted")
    assert trigger is not None, "the water skin never authors on_depleted"
    states = _effects(trigger, "set_state")
    assert states, "on_depleted does not set a state"
    assert states[0]["params"].get("state") == "empty", (
        "on_depleted must leave the skin empty (a persistent state) or it will "
        "be removed on the last charge"
    )
