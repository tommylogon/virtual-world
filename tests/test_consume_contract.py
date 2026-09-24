"""task-508: one depletion contract for consume.

Since task-508 the engine spends an item's ``uses`` on ``eat``/``drink`` exactly
as it does on ``use``, so a consume trigger owns only *what the item does*
(``adjust_vital``, conditions, messages) and must never hand-write a spend.
A hand-written ``adjust_uses``/``remove_item`` in an ``on_eat``/``on_drink``
trigger double-spends the charge (or destroys a multi-charge item on the first
bite) — the invisible failure class this guard exists to catch.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"

CONSUME_TYPES = ("on_eat", "on_drink")
#: Effects that spend/remove the consumed item themselves.
SPEND_EFFECTS = ("adjust_uses", "remove_item", "destroy_item")


def _trigger_types(props):
    tt = (props or {}).get("trigger_type")
    if isinstance(tt, (list, tuple)):
        return list(tt)
    return [tt] if tt else []


def _consume_triggers_in_scenarios():
    """Yield (file, trigger_id, trigger_type, effects) for scenario saves.

    Covers both the trigger node's properties and the ``triggers`` edge's
    duplicated properties, since the engine filters on either.
    """
    for path in sorted((DATA / "scenarios").glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue

        def walk(obj, seen):
            if isinstance(obj, dict):
                props = obj.get("properties")
                if isinstance(props, dict) and "effects" in props:
                    types = _trigger_types(props)
                    if any(t in CONSUME_TYPES for t in types):
                        key = (obj.get("id"), tuple(types))
                        if key not in seen:
                            seen.add(key)
                            yield path, obj.get("id"), types, props.get("effects") or []
                for value in obj.values():
                    yield from walk(value, seen)
            elif isinstance(obj, list):
                for value in obj:
                    yield from walk(value, seen)

        yield from walk(data, set())


def _consume_triggers_in_library():
    """Yield (file, trigger_type, effects) for library item triggers."""
    for path in sorted((DATA / "library" / "items").glob("*.json")):
        try:
            item = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            continue
        for trigger in item.get("triggers") or []:
            types = _trigger_types(trigger)
            if any(t in CONSUME_TYPES for t in types):
                yield path, types, trigger.get("effects") or []


def test_no_consume_trigger_hand_spends_uses():
    offenders = []
    for path, trig_id, types, effects in _consume_triggers_in_scenarios():
        spend = [e.get("type") for e in effects
                 if isinstance(e, dict) and e.get("type") in SPEND_EFFECTS]
        if spend:
            offenders.append(f"{path}: {trig_id} {types} -> {spend}")

    for path, types, effects in _consume_triggers_in_library():
        spend = [e.get("type") for e in effects
                 if isinstance(e, dict) and e.get("type") in SPEND_EFFECTS]
        if spend:
            offenders.append(f"{path}: {types} -> {spend}")

    assert not offenders, (
        "consume triggers must not spend `uses` themselves (task-508); the "
        "engine decrements on eat/drink. Offenders:\n  " + "\n  ".join(offenders)
    )
