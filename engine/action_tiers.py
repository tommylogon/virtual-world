"""Action tiers - the free / minor / major / activity classification (task-352).

One verb, one tier, fixed slots. The tier table is shared vocabulary - the
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
gates free actions: `open` is free only for something you are *at* - reaching it
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

#: A dash is a two-hop **burst** (task-784): the initiate and the finish. The
#: initiate costs the major and needs a minor free to finish; the finish hop the
#: actor picks costs the minor. While a burst is armed the ONLY valid action is a
#: finish hop (or an explicit abort), so a dash cannot be abandoned into an
#: unrelated action with the major already spent. Enforced by
#: `routes/action_handlers.py:_slot_gate`, which every budgeted actor shares
#: (humans and LLM agents); NPC paths that keep no budget dash as a plain hop.
BURST_INITIATE = "dash"
#: The verbs a dash's finish hop accepts - a movement across a way. `approach`
#: is deliberately absent: it stops short of crossing, so it cannot complete a
#: dash - and `wait` is the abort, not a finish.
BURST_FINISH_VERBS = frozenset({"go", "dash", "climb", "crawl", "jump"})
#: Verbs that abandon an unfinished dash: the character stops. Clears the armed
#: burst without spending the minor, so a dead-end dash is never a soft-lock.
BURST_ABORT_VERBS = frozenset({"wait", "nothing", "stop"})


def can_initiate_dash(slots: dict) -> bool:
    """A dash needs BOTH its major (the first hop) and a minor (the finish)."""
    return slots.get(MAJOR, 0) > 0 and slots.get(MINOR, 0) > 0


def apply_action_gate(slots: dict, verb: str, burst_pending: int = 0):
    """Spend the slots *verb* costs, honouring the dash burst (task-784).

    The one implementation of the action-economy rule, shared by every budgeted
    actor. Returns ``(error, burst)``: *error* is a message to refuse the action
    (``None`` when it may proceed), and *burst* says what the caller does with the
    character's burst flag:

      ``"clear"``  a finish hop or a wait abandoned the armed dash;
      ``"arm"``    a dash was initiated - arm the burst once the hop **succeeds**;
      ``"none"``   leave the flag alone.

    *slots* is mutated in place. The caller arms on success only, so a dash that
    is blocked (winded/encumbered/locked) is not left able to finish.
    """
    verb = (verb or "").strip().lower()
    if burst_pending:
        if verb in BURST_FINISH_VERBS:
            if spend_slot(slots, MINOR) is None:
                return "You have no minor action left to finish the dash.", "none"
            return None, "clear"
        if verb in BURST_ABORT_VERBS:
            return None, "clear"
        return ("Finish your dash first - go, dash, climb, crawl or jump - or wait.",
                "none")
    if verb == BURST_INITIATE:
        if not can_initiate_dash(slots):
            return ("A dash takes a major and a minor action; you are short.",
                    "none")
        spend_slot(slots, MAJOR)
        return None, "arm"
    tier = tier_of(verb)
    if spend_slot(slots, tier) is None:
        return f"You have no {tier} action left this turn.", "none"
    return None, "none"

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
    "text": FREE,
    "message": FREE,
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
    "goal": FREE,     # task-809: set, complete or drop a goal in the character's mind
    "obligation": FREE,   # task-813: answer an obligation - accept, refuse or forget
    "schedule": FREE,     # task-814: edit your own routine - add or remove a step
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
    "eat": MINOR,
    "drink": MINOR,
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
      1. `item.properties.action_costs[verb].tier` - the declared override.
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
    if verb in VERB_TIERS:
        return VERB_TIERS[verb]
    try:
        from engine import action_verbs
        spec = action_verbs.get_verb(verb)
        if spec and spec.cost_key in VALID_TIERS:
            return spec.cost_key
    except Exception:
        pass
    return MAJOR


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
