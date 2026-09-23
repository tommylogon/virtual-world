"""Relevance / interrupt evaluator (task-466).

One deterministic answer to "does this character need to stop and react?".
It is shared, by design, between:

* **timeskip actions** (task-464) — the interrupt that hands control back to the
  human mid-skip;
* **attention / fidelity tiers** (task-411 / task-418) — what draws a character
  into the attended set;
* **background soak deferral** (task-399) — events too unsafe to resolve
  silently;
* **memory salience** (task-403) — what is worth remembering.

The evaluator is pure: it compares two :func:`snapshot` dicts plus the events
recorded this tick and returns structured :class:`Interrupt` reasons. It never
mutates state and never calls an LLM, so a skip that stops on an interrupt leaves
the world in an ordinary state at that tick (no half-applied special case).
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: Drives rise toward 100 and hurt at the top.
DRIVE_DANGER = {"Hunger": 90, "Thirst": 90, "Bladder": 90}
#: Resources sit at 100 and hurt at the bottom.
RESOURCE_DANGER = {
    "Energy": 10, "Hygiene": 10, "Sanity": 15,
    "Social": 5, "Entertainment": 5,
}
#: Below this, HP itself is the emergency.
HP_DANGER = 30
#: Bladder crossing here is "you are about to lose control" — the involuntary
#: action the human should decide about, not something a skip resolves for them.
INVOLUNTARY_BLADDER = 95

#: Conditions that mean someone else is doing something to you, or you are down.
HOSTILE_CONDITIONS = frozenset({
    "grappled", "restrained", "stunned", "paralysed", "unconscious", "dead",
    "bleeding", "poisoned", "frightened", "petrified", "suffocating",
})

#: Turn-event action labels that are inherently hostile to the receiver.
HOSTILE_ACTIONS = frozenset({"attack", "steal", "grapple", "stab", "hit", "kill"})

#: Turn-event action the background social approach writes (engine/background_social).
SOCIAL_APPROACH_ACTION = "social_approach"

#: Markers in the log / turn events that mean a hostile act happened to us.
#: The theft path (`engine/items/transfer_actions.py`) logs "[Steal] ..." and a
#: "notices" line, so both are covered without special-casing that module.
THREAT_MARKERS = (
    "steal", "stole", "pickpocket", "attacks you", "attack you", "stabs",
    "hits you", "grabs you", "grappling you", "notices", "draws a",
)

#: Snapshot keys that are lists of spatial entries.
_SPATIAL_RELATIONS = ("in", "on", "under", "behind", "beside", "at")


@dataclass(frozen=True)
class Interrupt:
    """One reason to stop a skip / attend to a character."""

    kind: str          # threat | vital | condition | involuntary | discovery | arrival | death
    why: str           # stable reason tag, e.g. "vital:thirst"
    detail: str        # human-readable line
    salient: bool = True

    def to_dict(self) -> dict:
        return {"kind": self.kind, "why": self.why,
                "detail": self.detail, "salient": self.salient}


def snapshot(gs, player) -> dict:
    """Capture the state the evaluator compares across one tick.

    ``visible`` is the set of ``(type, id, name, tags)`` the character's area
    holds by a spatial relation — the substrate for discovery interrupts. It is
    built from edges into the area, not a full-graph scan.
    """
    vitals = dict(getattr(player, "vitals", {}) or {})
    conditions = set(getattr(player, "conditions", {}) or {})
    visible = _visible_here(gs, getattr(player, "current_area", None))

    logger = getattr(gs, "game_logger", None)
    log_len = len(getattr(logger, "game_log", []) or []) if logger else 0
    te_len = len(getattr(logger, "turn_events", []) or []) if logger else 0

    return {
        "name": getattr(player, "name", ""),
        "vitals": vitals,
        "conditions": conditions,
        "hp": vitals.get("HP"),
        "state": getattr(player, "state", None),
        "area": getattr(player, "current_area", None),
        "visible": visible,
        "log_len": log_len,
        "te_len": te_len,
    }


def events_since(gs, before: dict) -> list:
    """The log + turn events recorded since *before* was snapshotted."""
    logger = getattr(gs, "game_logger", None)
    if logger is None:
        return []
    out = []
    log = getattr(logger, "game_log", []) or []
    for text in log[int(before.get("log_len", 0)):]:
        out.append({"description": str(text)})
    events = getattr(logger, "turn_events", []) or []
    for event in events[int(before.get("te_len", 0)):]:
        if isinstance(event, dict):
            out.append(event)
    return out


def evaluate(before: dict, after: dict, *, events=(), watch_tags=(),
             target=None, intent=None) -> list:
    """Return the interrupts triggered between two snapshots.

    Ordering is intentional: death, then threat, then a new hostile condition,
    then bodily/vital danger, then discovery. Callers stop on the first one, so
    the most consequential reason is the one reported.
    """
    reasons = []

    if after.get("state") == "dead" and before.get("state") != "dead":
        reasons.append(Interrupt("death", "death", "You died.", True))
        return reasons

    if _threat(after, events):
        detail = _threat_detail(after, events) or "Someone turns on you."
        reasons.append(Interrupt("threat", "threat:attack", detail, True))

    new_conditions = after.get("conditions", set()) - before.get("conditions", set())
    hostile = sorted(c for c in new_conditions if c in HOSTILE_CONDITIONS)
    if hostile:
        reasons.append(Interrupt(
            "threat" if not reasons else "condition",
            f"condition:{hostile[0]}",
            f"You are {hostile[0].replace('_', ' ')}.",
            True,
        ))

    reasons.extend(_vital_danger(before, after))
    reasons.extend(_involuntary(before, after))

    approached = _social(after, events)
    if approached:
        reasons.append(Interrupt("social", "social:approach", approached, True))

    discovery = _discovery(before, after, watch_tags=watch_tags, target=target,
                           intent=intent)
    reasons.extend(discovery)

    return reasons


# ───────────────────────────── checks ─────────────────────────────────────

def _relevant_events(after, events):
    """Events that actually concern *this* character.

    Turn events carry an area and actor, so another room's fight is filtered
    out. Global log lines have neither, so they only count when they name the
    character (e.g. the theft line "... steal X from <name>").
    """
    name = str(after.get("name", "") or "").lower()
    area = after.get("area")
    out = []
    for event in events or []:
        if not isinstance(event, dict):
            continue
        actor = event.get("actor")
        event_area = event.get("area")
        if actor is not None or event_area is not None:
            if event_area and area and event_area != area:
                continue
            if name and str(actor or "").lower() == name:
                continue
            out.append(event)
            continue
        text = str(event.get("description", "")).lower()
        if name and name not in text:
            continue
        out.append(event)
    return out


def _threat(after, events) -> bool:
    if after.get("conditions", set()) & HOSTILE_CONDITIONS:
        return True
    for event in _relevant_events(after, events):
        if str(event.get("action", "")).lower() in HOSTILE_ACTIONS:
            return True
        low = str(event.get("description", "")).lower()
        if any(marker in low for marker in THREAT_MARKERS):
            return True
    return False


def _threat_detail(after, events) -> str:
    for event in _relevant_events(after, events):
        text = str(event.get("description", ""))
        low = text.lower()
        if str(event.get("action", "")).lower() in HOSTILE_ACTIONS or \
                any(marker in low for marker in THREAT_MARKERS):
            return text.strip()
    return ""


def _social(after, events) -> str:
    """Someone deliberately addressing the character (background social approach)."""
    for event in _relevant_events(after, events):
        if str(event.get("action", "")).lower() == SOCIAL_APPROACH_ACTION:
            return str(event.get("description", "")).strip() or "Someone approaches you."
    return ""


def _vital_danger(before, after) -> list:
    reasons = []
    bv = before.get("vitals", {})
    av = after.get("vitals", {})
    for stat, band in DRIVE_DANGER.items():
        if stat not in av:
            continue
        if bv.get(stat, 0) < band <= av.get(stat, 0):
            reasons.append(Interrupt("vital", f"vital:{stat.lower()}",
                                     f"Your {stat.lower()} is critical.", True))
    for stat, band in RESOURCE_DANGER.items():
        if stat not in av:
            continue
        if bv.get(stat, 100) > band >= av.get(stat, 100):
            reasons.append(Interrupt("vital", f"vital:{stat.lower()}",
                                     f"Your {stat.lower()} is dangerously low.", True))
    bhp = before.get("hp")
    ahp = after.get("hp")
    if isinstance(bhp, (int, float)) and isinstance(ahp, (int, float)):
        if bhp > HP_DANGER >= ahp:
            reasons.append(Interrupt("vital", "vital:hp",
                                     "You are badly hurt.", True))
    return reasons


def _involuntary(before, after) -> list:
    bv = before.get("vitals", {})
    av = after.get("vitals", {})
    reasons = []
    if "Bladder" in av and bv.get("Bladder", 0) < INVOLUNTARY_BLADDER <= av.get("Bladder", 0):
        reasons.append(Interrupt(
            "involuntary", "involuntary:bladder",
            "You can't hold it much longer.", True))
    return reasons


def _discovery(before, after, *, watch_tags=(), target=None, intent=None) -> list:
    reasons = []
    new_entries = after.get("visible", set()) - before.get("visible", set())
    watch = {str(t).lower() for t in (watch_tags or [])}
    target_low = str(target).lower() if target else None

    for entry in sorted(new_entries):
        ntype, _node_id, name, tags = entry
        name_low = str(name).lower()
        matched = False
        if target_low and (target_low == name_low or target_low in name_low):
            matched = True
        if watch and (watch & {str(t).lower() for t in tags}):
            matched = True
        if matched:
            reasons.append(Interrupt("discovery", "discovery:interest",
                                     f"You notice {name}.", True))

    area_changed = before.get("area") and after.get("area") != before.get("area")
    # Explore treats every new area as its point; travel only stops on the
    # destination (intermediate hops are the journey, not an event) so a
    # long route is not cut short at the first doorway.
    if area_changed and intent == "explore":
        reasons.append(Interrupt("discovery", "discovery:area",
                                 f"You reach {after.get('area')}.", True))
    if (area_changed and intent == "travel" and target_low
            and str(after.get("area")).lower() == target_low):
        reasons.append(Interrupt("arrival", "arrival",
                                 f"You arrive at {after.get('area')}.", True))
    return reasons


# ───────────────────────────── spatial ────────────────────────────────────

def _visible_here(gs, area_name):
    """Spatial entries in *area_name* for discovery comparison."""
    if not area_name:
        return set()
    graph = getattr(gs, "graph", None)
    area_id = None
    try:
        area_id = gs.area_node_id(area_name)
    except Exception:
        area_id = None
    if graph is None or not area_id:
        return set()

    out = set()
    for rel in _SPATIAL_RELATIONS:
        for edge in graph.get_edges_for_target(area_id, rel):
            node = graph.get_node(edge.source)
            if node is None:
                continue
            props = getattr(node, "properties", {}) or {}
            if props.get("current_state") == "hidden":
                continue
            tags = tuple(str(t) for t in (props.get("tags") or []))
            out.add((getattr(node, "type", ""), getattr(node, "id", ""),
                     getattr(node, "name", ""), tags))
    return out
