"""Action tiers — the free / minor / major / activity classification (task-352).

One verb, one tier, fixed slots. The tier table is shared vocabulary — the
composer, the agent turn, and the soak must all read the same data, and a second
copy would be the same "two homes" bug the rest of the tree is full of
(task-491, task-724).

Resolution: `tier_of()` honours a per-item override
(`item.properties.action_costs[verb].tier`), then the intrinsic-ability default
of `minor`, then the table. Budget and enforcement: `DEFAULT_BUDGET`,
`reset_slots`, `spend_slot` (a higher slot pays for a lower action); the runtime
budget is `Player.turn_slots`, charged by `routes/action_handlers.py:_slot_gate`.
The browser reads a generated mirror (`static/js/agent/action-tiers.ts`, emitted
by `tools/action_tiers_index.py`) so the turn prompt can hide what the budget
cannot pay for.

Task-352's fixed allowance is `major: 1, minor: 1, free: 3, activity: 1`. Position
gates free actions: `open` is free only for something you are *at* — reaching it
costs `approach` (minor) or `go` (major).

@module action_tiers
@contributes VERB_TIERS, VALID_TIERS, DEFAULT_BUDGET, tier_of, reset_slots, spend_slot
@docs docs/virtualWorld/Gameplay/Turn Queue & Human Turns.md
"""

from __future__ import annotations

from typing import Optional

from engine.equipment import INTRINSIC_ABILITY_TAGS

FREE = "free"
MINOR = "minor"
MAJOR = "major"
ACTIVITY = "activity"

VALID_TIERS = frozenset({FREE, MINOR, MAJOR, ACTIVITY})

#: Fixed per-turn slot allowance (task-352 decision, 2026-10-07).
DEFAULT_BUDGET = {MAJOR: 1, MINOR: 1, FREE: 3, ACTIVITY: 1}

#: The classification. Every verb dispatched by `routes/action_handlers.py` must
#: appear here; `tests/test_action_tiers.py` derives the dispatched set from the
#: source and fails when one is added without a tier.
VERB_TIERS: dict[str, str] = {
    # ---- free: the at-a-distance layer, what you can tell from where you stand
    "look": FREE,
    "listen": FREE,
    "open": FREE,
    "close": FREE,
    "drop": FREE,
    "speak": FREE,
    "say": FREE,
    "whisper": FREE,
    "shout": FREE,
    "scream": FREE,
    "sing": FREE,
    "do": FREE,
    "fear": FREE,
    "interest": FREE,
    "guess": FREE,
    "inventory": FREE,
    "i": FREE,
    "inv": FREE,
    "stats": FREE,
    "status": FREE,
    "recall": FREE,   # task-736: cheap self-query; an agent won't pay a turn to think
    "name": FREE,     # task-447 alias
    "label": FREE,    # relationship label
    "stop": FREE,
    # ---- minor: positioning and small manipulation
    "grab": MINOR,
    "lead": MINOR,
    "release": MINOR,
    "toggle": MINOR,  # task-352 listed toggle in both free and minor; chosen here
    "stow": MINOR,
    "put": MINOR,
    "place": MINOR,
    "wear": MINOR,
    "equip": MINOR,
    "remove": MINOR,
    "unequip": MINOR,
    "approach": MINOR,  # task-352 decision 2026-10-07
    "stand": MINOR,
    "wake": MINOR,
    "flee": MINOR,
    "disengage": MINOR,
    "withdraw": MINOR,
    "manifest": MINOR,
    "vanish": MINOR,
    # ---- major: the significant action, one per turn by default
    "go": MAJOR,
    "dash": MAJOR,
    "crawl": MAJOR,
    "climb": MAJOR,
    "jump": MAJOR,
    "examine": MAJOR,
    "take": MAJOR,
    "get": MAJOR,
    "pickup": MAJOR,
    "pick": MAJOR,
    "use": MAJOR,
    "eat": MAJOR,
    "drink": MAJOR,
    "attack": MAJOR,
    "search": MAJOR,
    "frisk": MAJOR,
    "find": MAJOR,
    "craft": MAJOR,
    "make": MAJOR,
    "combine": MAJOR,
    "split": MAJOR,
    "give": MAJOR,
    "steal": MAJOR,
    "fix": MAJOR,
    "treat": MAJOR,
    "relieve": MAJOR,
    "bind": MAJOR,
    "enchant": MAJOR,
    "teach": MAJOR,
    "escape": MAJOR,
    "struggle": MAJOR,
    # ---- activity: consumes the turn, mutually exclusive with other tiers
    "rest": ACTIVITY,
    "sleep": ACTIVITY,
    "wait": ACTIVITY,
    "meditate": ACTIVITY,
    "bathe": ACTIVITY,
    "bath": ACTIVITY,
    "sit": ACTIVITY,
    "lie": ACTIVITY,
    "lay": ACTIVITY,
    "dress": ACTIVITY,
    "undress": ACTIVITY,
    "strip": ACTIVITY,
}


def _is_ability(item_node) -> bool:
    """True when a node is tagged as an intrinsic ability (spell/talent)."""
    tags = (getattr(item_node, "properties", None) or {}).get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",")]
    return bool(INTRINSIC_ABILITY_TAGS.intersection(tags))


def tier_of(verb: str, item_node=None) -> str:
    """The tier a verb costs, honouring a per-item override and ability default.

    Resolution order (task-352):
      1. `item.properties.action_costs[verb].tier` — the declared override.
      2. intrinsic ability (spell/ability/innate/intrinsic/power) → ``minor``.
      3. the verb table.
      4. ``major`` for an unknown verb (the coverage test should make this dead).
    """
    verb = (verb or "").strip().lower()
    if item_node is not None:
        props = getattr(item_node, "properties", None) or {}
        override = (props.get("action_costs") or {}).get(verb) or {}
        declared = override.get("tier")
        if declared in VALID_TIERS:
            return declared
        if _is_ability(item_node):
            return MINOR
    return VERB_TIERS.get(verb, MAJOR)


def all_verbs() -> list[str]:
    """Every classified verb, for the coverage test and future registries."""
    return sorted(VERB_TIERS)


#: Ascending by value: a higher tier may pay for a lower action (task-352).
_TIER_ORDER = [FREE, MINOR, MAJOR]


def reset_slots(slots: dict, budget: Optional[dict] = None) -> dict:
    """Fill *slots* with a fresh per-turn allowance, in place."""
    slots.clear()
    slots.update(budget or DEFAULT_BUDGET)
    return slots


def spend_slot(slots: dict, tier: str) -> Optional[str]:
    """Spend a slot for an action of *tier*. Returns the tier spent, or None.

    A higher slot pays for a lower action when the exact tier is exhausted (the
    major slot pays for `approach`); the cheapest sufficient slot is used first.
    `activity` is its own single slot and does not downgrade.
    """
    if tier not in VALID_TIERS:
        tier = MAJOR
    if tier == ACTIVITY:
        if slots.get(ACTIVITY, 0) > 0:
            slots[ACTIVITY] -= 1
            return ACTIVITY
        return None
    for candidate in _TIER_ORDER[_TIER_ORDER.index(tier):]:
        if slots.get(candidate, 0) > 0:
            slots[candidate] -= 1
            return candidate
    return None
