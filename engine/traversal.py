"""Soak-tier traversal checks (task-475).

Routine ground **takes 10 and never rolls**: a character crossing an ordinary
area keeps the soak tier free of dice, exactly like routine maintenance (eat,
drink, sleep, wash) already does. Risky ground rolls:

* a way that needs a verb (``crawl`` / ``climb`` / ``jump``) is used with that
  verb instead of stalling on "you need to climb through the north";
* entering a hazard-tagged area is a skill check — Survival for wild country,
  Athletics for climb/swim ground, Acrobatics for balance and squeeze, Stealth
  for watched ground;
* a failure costs the turn (never more), may leave **one** minor condition, and
  is remembered for a while so the character routes around it rather than
  walking into the same wall every turn.

Nothing here can starve anyone: eating, drinking and sleeping are the need
policy's job and stay automatic, and a refusal only ever costs time.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from engine import checks

logger = logging.getLogger(__name__)

#: Routine attempts take 10 — the number a passive check uses. Only used for
#: display: a routine hop does not roll at all.
ROUTINE = 10

#: Area tag -> the skill that carries a character *into* that ground.
HAZARD_SKILLS = {
    # Wild country: read the trail, find the ford, pick the safe line.
    "swamp": "Survival", "marsh": "Survival", "bog": "Survival",
    "wasteland": "Survival", "snow": "Survival", "desert": "Survival",
    "jungle": "Survival", "woods": "Survival", "forest": "Survival",
    # Height, water and rubble are body work.
    "cliff": "Athletics", "crag": "Athletics", "steep": "Athletics",
    "ledge": "Athletics", "river": "Athletics", "rapids": "Athletics",
    "ford": "Athletics", "flooded": "Athletics",
    # Balance and squeeze.
    "narrow": "Acrobatics", "rubble": "Acrobatics", "debris": "Acrobatics",
    "unsteady": "Acrobatics",
    # Ground that is being watched.
    "guarded": "Stealth", "patrolled": "Stealth", "watched": "Stealth",
}

#: Soak action -> the skill that carries it, per task-475.
#: ``SOAK_ACTIONS`` is the full mapping; the ones the soak policy can reach
#: today are the traversal verbs (`climb`/`jump`/`crawl`) and ground hazards.
#: The rest are the mapping for actions that need a policy hook first —
#: calm/ride (task-476 roles), treat/diagnose, read_mood and identify_plant
#: (task-478 tables), investigate (task-468 agendas).
SOAK_ACTIONS = {
    "travel_hazard": "Survival",
    "climb": "Athletics", "jump": "Athletics", "swim": "Athletics",
    "force": "Athletics",
    "balance": "Acrobatics", "squeeze": "Acrobatics",
    "sneak": "Stealth", "avoid_notice": "Stealth",
    "calm_beast": "Animal Handling", "ride": "Animal Handling",
    "treat": "Medicine", "diagnose": "Medicine",
    "read_mood": "Insight",
    "identify_plant": "Nature",
    "investigate": "Investigation",
}

#: Actions that are routine maintenance: they take 10 and never roll.
ROUTINE_ACTIONS = frozenset({
    "walk", "eat", "drink", "sleep", "wash", "rest", "relieve",
})


def skill_for(action) -> str:
    """The skill a soak action uses, or ``""`` for routine maintenance."""
    return SOAK_ACTIONS.get(action, "")


def is_routine(action) -> bool:
    """True when an action takes 10 and never rolls."""
    return action in ROUTINE_ACTIONS


#: The DC a hazardous crossing is made against.
HAZARD_DC = 12

#: The minor condition a failure can leave behind — never anything that spirals.
HAZARD_CONDITION = {
    "river": "wet", "rapids": "wet", "ford": "wet", "flooded": "wet",
    "swamp": "wet", "marsh": "wet", "bog": "wet",
    "cliff": "injured", "crag": "injured", "steep": "injured",
    "rubble": "injured", "debris": "injured", "unsteady": "injured",
}

#: Ways that need a movement verb rather than a plain walk.
WAY_VERBS = ("crawl", "climb", "jump")

#: How long a refused hop is routed around, in game minutes.
AVOID_MINUTES = 30


@dataclass
class HopResult:
    """What happened when a character tried to cross one way."""

    ok: bool
    kind: str = "go"
    dest: str = ""
    skill: str = ""
    dc: object = None
    total: int = 0
    tier: str = "routine"
    detail: str = ""
    condition: str = ""
    blocked: bool = False
    checked: bool = False
    result: object = None
    modifiers: list = field(default_factory=list)

    @property
    def why(self) -> str:
        """Trace/log why-tag for this hop."""
        if self.ok:
            return "traversal:routine" if not self.checked else "traversal:ok"
        return "traversal:blocked" if self.blocked else "traversal:fail"


def way_kind(gs, way_id) -> str:
    """The movement verb a way requires, or ``"go"`` for an ordinary walk."""
    if not way_id:
        return "go"
    try:
        node = gs.graph.get_node(way_id)
    except Exception:
        return "go"
    if node is None:
        return "go"
    requires = str((node.properties or {}).get("requires", "") or "").strip().lower()
    if requires in ("", "none"):
        return "go"
    return requires if requires in WAY_VERBS else "go"


def _area_tags(gs, area_name) -> set:
    if not area_name:
        return set()
    try:
        area_id = gs.area_node_id(area_name) or area_name
        node = gs.graph.get_node(area_id)
    except Exception:
        node = None
    if node is None:
        return set()
    return {str(t).lower() for t in ((node.properties or {}).get("tags") or [])}


def hazard(gs, area_name):
    """``(tag, skill, dc)`` when entering *area_name* is risky ground, else None.

    Deterministic: the first matching tag in sorted order, so a run does not
    depend on set iteration.
    """
    tags = _area_tags(gs, area_name)
    for tag in sorted(tags):
        skill = HAZARD_SKILLS.get(tag)
        if skill:
            return (tag, skill, HAZARD_DC)
    return None


def attempt(gs, player, *, kind: str = "go", dest: str = "",
            roll_fn=None) -> HopResult:
    """Roll for a risky crossing. A routine hop takes 10 and never rolls."""
    spec = hazard(gs, dest)
    if not spec:
        return HopResult(ok=True, kind=kind, dest=dest, tier="routine",
                         detail="takes 10")
    tag, skill, dc = spec
    check = checks.resolve(player, kind=skill, dc=dc, roll_fn=roll_fn,
                           context=f"traversal:{tag}")
    if check.success:
        return HopResult(ok=True, kind=kind, dest=dest, skill=skill, dc=dc,
                         total=check.total, tier=check.tier, checked=True,
                         result=check, modifiers=list(check.modifiers),
                         detail=f"{skill} beats the {tag}")
    return HopResult(ok=False, kind=kind, dest=dest, skill=skill, dc=dc,
                     total=check.total, tier=check.tier, checked=True,
                     result=check, modifiers=list(check.modifiers),
                     condition=HAZARD_CONDITION.get(tag, ""),
                     detail=f"the {tag} turns you back")


def hop(gs, player, direction, *, dest: str = "", kind=None,
        roll_fn=None) -> HopResult:
    """Cross one way, never raising for a blocked passage.

    Chooses the verb the way needs, runs the ground check, and moves the
    character. Returns a :class:`HopResult` whose ``ok`` says whether the
    character actually ended up on the other side.
    """
    if kind is None:
        kind = "go"
        try:
            exits = gs.build_exits_for_area(
                getattr(player, "current_area", None), include_hidden=True) or {}
            data = exits.get(direction) or {}
            if not dest:
                dest = data.get("target") or ""
            kind = way_kind(gs, data.get("way_id"))
        except Exception:
            pass

    result = attempt(gs, player, kind=kind, dest=dest, roll_fn=roll_fn)
    if not result.ok:
        return result

    old_active = getattr(gs, "active_player", None)
    gs.active_player = player.name
    try:
        gs.movement.move_to_area(direction, kind=kind)
    except Exception as e:
        result.ok = False
        result.blocked = True
        result.detail = str(e) or "the way is blocked"
        if result.condition:
            # A blocked way is not a hazard injury — the check never happened.
            result.condition = ""
    finally:
        gs.active_player = old_active
    return result


# ───────────────────────── refusal memory ─────────────────────────────────

def avoid_key(area, label):
    return (str(area or "").lower(), str(label or "").lower())


def note_refusal(gs, player, area, label, *, minutes: float = AVOID_MINUTES):
    """Remember that *label* out of *area* is not worth retrying for a while."""
    store = getattr(player, "traversal_avoid", None)
    if store is None:
        store = {}
        try:
            player.traversal_avoid = store
        except Exception:
            return
    try:
        now = float(gs.total_game_minutes())
    except Exception:
        now = 0.0
    store[avoid_key(area, label)] = now + float(minutes)


def avoid(gs, player) -> set:
    """The (area, label) pairs still being routed around, expiring as time passes."""
    store = getattr(player, "traversal_avoid", None)
    if not store:
        return set()
    try:
        now = float(gs.total_game_minutes())
    except Exception:
        now = 0.0
    live = {key for key, until in store.items() if float(until) > now}
    for key in [k for k in store if k not in live]:
        store.pop(key, None)
    return live
