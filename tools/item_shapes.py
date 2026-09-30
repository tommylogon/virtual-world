"""Item authoring shapes, shared by the content passes.

Four shapes, and the linter (`tools/lint_library.py`) has an opinion about each:

- **food**   `food` tag or `eat` action -> needs `on_eat` with a *negative*
  `adjust_vital` on Hunger. A drive fills upward, so relief is negative; getting
  that backwards is what made 64 shipped items look authored when they were not.
- **drink**  the same, on Thirst.
- **pool**   a `resource_pool`: `uses: -1`, a `quantity`, and a `harvest` naming
  another library item (never itself) with a positive `size`.
- **thing**  anything else: no trigger, no harvest.

Two rules this module exists to enforce, both learned by breaking them:

1. **A row's *shape* decides what it is, not a flag in a fixed column.** A 4-tuple
   with a number in the third slot is consumable; a 3-tuple is a plain thing.
   Hand-unpacking the columns instead transposed `tags` and `weight` against each
   other four separate times in one session, and each transposition failed
   differently: a `food` tag on a fishing tool, a `str` where an `int` was
   expected, a float where a list belonged.
2. **A claim that is not backed must be dropped, not half-written.** A row tagged
   `food` that gets no relief number is a bug or a fixture, and writing it as a
   thing that still claims to be food is exactly the "a tag alone makes an item
   edible" problem task-506 retired. The linter names every one; `emit()` refuses
   instead.
"""
from __future__ import annotations

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB = os.path.join(ROOT, "data", "library", "items")


# ── row normalisation ─────────────────────────────────────────────────────

def row(item):
    """Normalise a table row to ``(id, description, tags, relief_or_weight)``.

    Both shapes occur in the authored tables and both are legible. A numeric third
    element is a **consumable relief**; anything else is a **weight** and the row is
    a plain item. The fourth element, when present and boolean, is the old `edible`
    flag and is ignored — a `food` tag on a non-consumable is stripped, which is
    stricter and is why the flag is redundant.
    """
    item_id, desc = item[0], item[1]
    if len(item) >= 4 and isinstance(item[2], (int, float)):
        tags = list(item[3]) if isinstance(item[3], list) else []
        return item_id, desc, tags, item[2]
    tags = list(item[2]) if len(item) >= 3 and isinstance(item[2], list) else []
    weight = item[3] if len(item) >= 4 and isinstance(item[3], (int, float)) else None
    return item_id, desc, tags, weight


# ── record shapes ─────────────────────────────────────────────────────────

def _base(item_id, description, tags, weight=0.3, **extra):
    item = {
        "name": item_id,
        "description": description,
        "actions": "examine,take,drop",
        "uses": 1,
        "weight": weight,
        "current_state": "normal",
        "light_level": "dim",
        "equip_slots": [],
        "defense": 0,
        "damage": 0,
        "tags": list(tags),
        "triggers": [],
        "contents": [],
    }
    item.update(extra)
    return item


def _relief(trigger_type, stat, amount, message):
    return {
        "trigger_type": [trigger_type],
        "effects": [
            {"type": "message",
             "params": {"message": "", "success_message": message}},
            {"type": "adjust_vital",
             "params": {"stat": stat, "amount": amount, "target": "self"}},
        ],
        "conditions": {},
        "target_name": "",
        "target_state": "",
        "success_message": message,
        "fail_message": "",
    }


def food(item_id, description, hunger, tags, uses=3, weight=0.2, message=None):
    """Something you eat. `hunger` is how far it pushes Hunger DOWN."""
    message = message or "You eat it. It is not much, but it is food."
    return _base(item_id, description, ["food"] + list(tags), weight,
                 actions="examine,take,use,eat,drop", uses=uses,
                 triggers=[_relief("on_eat", "Hunger", -abs(hunger), message)])


def drink(item_id, description, thirst, tags, uses=3, weight=0.4, message=None):
    """Something you drink."""
    message = message or "You drink it down. It helps."
    return _base(item_id, description, ["drink"] + list(tags), weight,
                 actions="examine,take,use,drink,drop", uses=uses,
                 triggers=[_relief("on_drink", "Thirst", -abs(thirst), message)])


def both(item_id, description, hunger, thirst, tags, uses=3, weight=0.4):
    """Food that is also worth drinking — a stew, a broth, a fruit you squeeze."""
    return _base(item_id, description, ["food", "drink"] + list(tags), weight,
                 actions="examine,take,use,eat,drink,drop", uses=uses,
                 triggers=[_relief("on_eat", "Hunger", -abs(hunger),
                                   "You eat your fill of it."),
                           _relief("on_drink", "Thirst", -abs(thirst),
                                   "You drink it down.")])


def pool(item_id, description, yields, size, dc, tags, quantity=3, weight=1.0,
         skill="Survival"):
    """A standing resource: one node standing for many of a kind in the world."""
    # `pool()` contributes the resource-pool tags and a row may repeat one of them
    # (a hay bale is a `plant` twice). De-duplicated here because a repeated tag in
    # a shipped file looks like a copy-paste error even when it is not.
    seen, merged = set(), []
    for tag in ["plant", "organic", "outdoor", "resource_pool"] + list(tags):
        if tag not in seen:
            seen.add(tag)
            merged.append(tag)
    return _base(item_id, description, merged, weight,
                 actions="examine,take,drop", uses=-1, quantity=quantity,
                 harvest={"item": yields, "size": size, "skill": skill, "dc": dc},
                 insulation=0)


def thing(item_id, description, tags, weight=1.0, **extra):
    return _base(item_id, description, tags, weight, **extra)


def tool(item_id, description, tags, weight=1.5, **extra):
    return _base(item_id, description, ["tool"] + list(tags), weight, **extra)


def worn(item_id, description, tags, slot, weight=0.3, insulation=0, **extra):
    """Something put **on**. `slot` is required, not decorative: the linter
    refuses a `clothing` or `armor` tag with no slot, and it is right to — a
    wearable that cannot be worn is a label on nothing."""
    return _base(item_id, description, ["clothing"] + list(tags), weight,
                 equip_slots=[slot], insulation=insulation, **extra)


def emit(records, item_id, description, tags, relief, weight=0.4, message=None):
    """Route one row by what it *claims*, dropping a claim it cannot back.

    Returns the record to add. The rules, in order:

    - no relief number, or a non-positive one -> a plain item, and any
      `food`/`drink` tag is **stripped**. A honeypot with a `food` tag and no
      effect is the bug task-506 exists to prevent, and writing it is worse than
      not writing it;
    - `drink` and not `food` -> a drink, needing positive thirst relief;
    - otherwise -> a food, needing positive hunger relief.
    """
    tags = list(tags)
    if relief is None or relief <= 0:
        return thing(item_id, description,
                     [t for t in tags if t not in ("food", "drink")]
                     or ["material"], weight=weight)
    if "drink" in tags and "food" not in tags:
        return drink(item_id, description, relief, tags, weight=weight)
    return food(item_id, description, relief, tags, weight=weight, message=message)


# ── writing and auditing ──────────────────────────────────────────────────

def existing():
    """The ids already on disk, so a content pass never overwrites shipped work."""
    return {name[:-5] for name in os.listdir(LIB) if name.endswith(".json")}


def write(records, label="", force=False):
    """Write `records` to the library. Returns ``(written, skipped)`` ids.

    An id already on disk is **skipped, never overwritten**: these passes are
    content additions, and silently replacing a shipped item because a table
    mentioned the same id is how you lose work you did not mean to touch. `force`
    is how you do it deliberately.
    """
    have = existing()
    written, skipped = [], []
    for item_id, item in sorted(records.items()):
        if item_id in have and not force:
            skipped.append(item_id)
            continue
        with open(os.path.join(LIB, item_id + ".json"), "w",
                  encoding="utf-8", newline="\n") as handle:
            json.dump(item, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        written.append(item_id)
    if label:
        print("%s: wrote %d, skipped %d already on disk"
              % (label, len(written), len(skipped)))
    return written, skipped


def audit(records_by_pass, verbose=True):
    """Every authored id present on disk? Returns the missing ids per pass.

    This is the check that was **skipped** on 2026-09-30, when 545 authored items
    were absent from disk and the pass was reported as written. Counting what a
    generator *wrote* is not the same as counting what is *there*; this is the
    difference, and it is a test (`tests/test_library_content_pass.py`) as well as
    a script.
    """
    have = existing()
    missing = {}
    for label, records in records_by_pass.items():
        gone = sorted(set(records) - have)
        if gone:
            missing[label] = gone
    if verbose:
        total = sum(len(v) for v in missing.values())
        for label, records in records_by_pass.items():
            print("  %-8s authors %4d  missing %d"
                  % (label, len(records), len(missing.get(label, []))))
        print("total authored %d, missing from disk: %d"
              % (sum(len(r) for r in records_by_pass.values()), total))
        for label, gone in missing.items():
            print("  %s: %s%s" % (label, ", ".join(gone[:10]),
                                   " …" if len(gone) > 10 else ""))
    return missing
