"""One relationship mutation path (task-420, extended multi-axis in task-972).

Relationship state is a per-pair multi-axis record:

    player.relationships[other] = {
        "closeness": -100..100,    # default 0
        "trust": -100..100,        # default 0
        "attraction": 0..100,      # default 0
        "fear": 0..100,            # default 0
        "resentment": 0..100,      # default 0
        "last_interaction_tick": int,
        "interaction_count": int,
        "label": str,              # authored declaration ("my brother")
        "first_sighting": bool,    # identity still hidden this turn
    }

Legacy records that only contain `closeness` remain 100% valid; missing axes
default to 0 on read and normalization.

Every gameplay writer used to touch that dict itself - combat, the foreground
loop, first-meeting registration, the `label` command - so two things were true:

1. **No cause was recorded.** A delta from a beating looked identical to one
   from a shared meal, so nothing downstream (trace, memory, reflection) could
   explain why two characters feel the way they do.
2. **The fidelity tiers could diverge.** Foreground outcomes and background
   relationship drift wrote the same scalar through different code, so at a
   promotion/demotion the value could jump: the two paths never agreed on how it
   evolves.

`apply_relationship_delta` and `apply_relationship_axes_delta` are the writers
of relationship axes. They clamp in one place, stamp the interaction, and
record the cause on the trace. A deserializer replacing the whole store from a
payload is not a mutation of a relationship and does not go through here (see
`routes/player_ops.py`).

`closeness_band` also lives here: the band ladder was inline in
`Player.get_relationship_nl`, and task-423's outcome table needs the same bands,
so it is defined once.

@module relationships
@contributes clamp_closeness, clamp_axis, RELATIONSHIP_AXES, closeness_band, band_at_least, resolve_key, display_name, get_relationship, get_relationship_axis, get_relationship_axes, normalize_relationship, normalize_relationships, apply_relationship_delta, apply_relationship_axes_delta
@docs docs/virtualWorld/Rules Engine/Combat System.md
"""

from __future__ import annotations

import math
from typing import Optional

CLOSENESS_MIN = -100
CLOSENESS_MAX = 100
TRUST_MIN = -100
TRUST_MAX = 100
ATTRACTION_MIN = 0
ATTRACTION_MAX = 100
FEAR_MIN = 0
FEAR_MAX = 100
RESENTMENT_MIN = 0
RESENTMENT_MAX = 100

#: Canonical relationship axes and their inclusive (min, max) bounds.
RELATIONSHIP_AXES: dict[str, tuple[int, int]] = {
    "closeness": (CLOSENESS_MIN, CLOSENESS_MAX),
    "trust": (TRUST_MIN, TRUST_MAX),
    "attraction": (ATTRACTION_MIN, ATTRACTION_MAX),
    "fear": (FEAR_MIN, FEAR_MAX),
    "resentment": (RESENTMENT_MIN, RESENTMENT_MAX),
}

#: Band -> the words the prompt uses. Keys are what game systems match on, so
#: they never change; the values are prose and can.
BAND_LABELS = {
    "mortal_enemy": "mortal enemy",
    "enemy": "enemy",
    "rival": "rival",
    "unfriendly": "unfriendly",
    "neutral": "neutral",
    "acquaintance": "acquaintance",
    "friend": "friend",
    "close_friend": "close friend",
    "inseparable": "inseparable",
}

#: Ordered worst-to-best for callers that want a position, not a name.
BAND_ORDER = (
    "mortal_enemy", "enemy", "rival", "unfriendly", "neutral",
    "acquaintance", "friend", "close_friend", "inseparable",
)


def clamp_axis(axis: str, value) -> int:
    """Clamp a value to the bounds of ``axis``. Returns 0 on invalid input."""
    bounds = RELATIONSHIP_AXES.get(axis)
    if bounds is None:
        raise ValueError(f"Unknown relationship axis: {axis!r}")
    lo, hi = bounds
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0
    if math.isnan(number):
        return 0
    return int(max(lo, min(hi, number)))


def clamp_closeness(value) -> int:
    """Clamp to the closeness store's range. The one place the bounds are enforced."""
    return clamp_axis("closeness", value)


def closeness_band(closeness) -> str:
    """The band a closeness value falls in.

    Mirrors the ladder that used to live inline in `Player.get_relationship_nl`
    (which now calls this), so the prompt's wording and any band-gated game rule
    can never disagree about where the boundaries are.
    """
    try:
        value = float(closeness or 0)
    except (TypeError, ValueError):
        value = 0.0
    if value <= -75:
        return "mortal_enemy"
    if value <= -50:
        return "enemy"
    if value <= -25:
        return "rival"
    if value < 0:
        return "unfriendly"
    if value == 0:
        return "neutral"
    if value <= 25:
        return "acquaintance"
    if value <= 50:
        return "friend"
    if value <= 75:
        return "close_friend"
    return "inseparable"


def band_at_least(closeness, minimum: str) -> bool:
    """True when ``closeness`` sits at or above the ``minimum`` band.

    The gate task-423 needs for `flirt`/`confide` (the Diary's
    ``has_relationship: {min_quality}``): a comparison by band position rather
    than by inventing another threshold.
    """
    try:
        return BAND_ORDER.index(closeness_band(closeness)) >= BAND_ORDER.index(minimum)
    except ValueError:
        return False


def resolve_key(player, other) -> str:
    """The identity key a relationship with ``other`` is stored under (task-446).

    When the actor is registered, its manager resolves a name/uid/Player to the
    unique registry key; for a unique name that key IS the name, so existing data
    and tests are unaffected. Without a manager (unit-test Players) the ref is
    used verbatim.
    """
    manager = getattr(player, "player_manager", None)
    if manager is not None and hasattr(manager, "relationship_key"):
        return manager.relationship_key(other)
    if hasattr(other, "name"):
        return getattr(other, "name", "") or ""
    return str(other or "")


def display_name(player, other, key: str) -> str:
    """Human-readable label for the other party, for prose and prompts."""
    if hasattr(other, "name"):
        return getattr(other, "name", "") or key
    manager = getattr(player, "player_manager", None)
    if manager is not None and hasattr(manager, "display_name_of"):
        return manager.display_name_of(key)
    return key


def get_relationship(player, other) -> Optional[dict]:
    """Read the relationship record for ``other``, resolving its identity."""
    store = getattr(player, "relationships", None) or {}
    return store.get(resolve_key(player, other))


def get_relationship_axis(player, other, axis: str) -> int:
    """Read a single relationship axis for ``other``, defaulting to 0."""
    rel = get_relationship(player, other)
    if not isinstance(rel, dict):
        clamp_axis(axis, 0)  # validate axis name
        return 0
    return clamp_axis(axis, rel.get(axis, 0))


def get_relationship_axes(player, other) -> dict[str, int]:
    """Read all relationship axes for ``other``, defaulting missing axes to 0."""
    rel = get_relationship(player, other)
    if not isinstance(rel, dict):
        return {axis: 0 for axis in RELATIONSHIP_AXES}
    return {axis: clamp_axis(axis, rel.get(axis, 0)) for axis in RELATIONSHIP_AXES}


def normalize_relationship(record: dict) -> dict:
    """Return a copy of ``record`` with all relationship axes present and clamped."""
    out = dict(record) if isinstance(record, dict) else {}
    for axis in RELATIONSHIP_AXES:
        out[axis] = clamp_axis(axis, out.get(axis, 0))
    return out


def normalize_relationships(rel_data) -> dict[str, dict]:
    """Normalize a player's relationship map for serialization or deserialization."""
    if not isinstance(rel_data, dict):
        return {}
    return {
        str(key): normalize_relationship(rec)
        for key, rec in rel_data.items()
        if isinstance(rec, dict)
    }


def rekey_relationship(player, old_key: str, new_key: str, new_name: str = "") -> bool:
    """Re-key a relationship on ``player`` from ``old_key`` to ``new_key`` (task-619).

    Preserves closeness, last interaction tick, interaction count and labels.
    """
    rels = getattr(player, "relationships", None)
    if not isinstance(rels, dict) or old_key not in rels or old_key == new_key:
        return False
    record = rels.pop(old_key)
    if isinstance(record, dict) and new_name:
        record["name"] = new_name
    rels[new_key] = record
    return True


def ensure_relationship(player, other_name: str, tick: int = 0,
                       label: str = "") -> tuple[dict, bool]:
    """The record for ``other_name``, created if absent. Returns (record, created).

    Creating a record is not the same as *feeling* something: this grants no
    novelty and moves no axes, so callers that do care (first meeting,
    a landed insult) apply their own delta afterwards.
    """
    if player is None or not other_name:
        return {}, False
    key = resolve_key(player, other_name)
    if not key:
        return {}, False
    existing = player.relationships.get(key)
    if existing is not None:
        if not existing.get("name"):
            existing["name"] = display_name(player, other_name, key)
        for axis in RELATIONSHIP_AXES:
            existing.setdefault(axis, 0)
        return existing, False
    record = {
        "closeness": 0,
        "trust": 0,
        "attraction": 0,
        "fear": 0,
        "resentment": 0,
        "last_interaction_tick": int(tick or 0),
        "interaction_count": 0,
        "label": label or "",
        "name": display_name(player, other_name, key),
    }
    player.relationships[key] = record
    return record, True


def apply_relationship_axes_delta(player, other_name: str, deltas: dict,
                                  cause: str, tick: Optional[int] = None,
                                  area_id: str = "", trace: bool = True) -> dict:
    """Apply deltas to one or more relationship axes. Returns the updated record.

    ``deltas`` maps axis names (``closeness``, ``trust``, ``attraction``,
    ``fear``, ``resentment``) to integer deltas. Each axis is clamped to its
    defined bounds, interaction metadata is stamped, and any non-zero changes
    are recorded on the lived log with ``cause``.
    """
    record, _ = ensure_relationship(player, other_name, tick or 0)
    if not record:
        return {}
    label = display_name(player, other_name, resolve_key(player, other_name))
    applied: dict[str, int] = {}
    if isinstance(deltas, dict):
        for axis, raw_delta in deltas.items():
            if axis not in RELATIONSHIP_AXES:
                continue
            try:
                amount = int(raw_delta or 0)
            except (TypeError, ValueError):
                amount = 0
            if amount:
                record[axis] = clamp_axis(axis, record.get(axis, 0) + amount)
                applied[axis] = amount

    if tick is not None:
        record["last_interaction_tick"] = int(tick)
    record.setdefault("interaction_count", 0)
    if applied or tick is not None:
        record["interaction_count"] = int(record.get("interaction_count", 0)) + 1

    if trace and applied:
        try:
            from engine.lived_log import record as lived_record
            if list(applied.keys()) == ["closeness"]:
                summary = f"closeness toward {label} {applied['closeness']:+d}"
            else:
                parts = ", ".join(f"{ax} {amt:+d}" for ax, amt in applied.items())
                summary = f"{parts} toward {label}"
            lived_record(
                player, int(tick or 0), "relationship",
                summary,
                why=f"social:{cause}",
                area=area_id or (getattr(player, "current_area", "") or ""),
                tags=["rel:" + str(label), str(cause)],
                delta={"cause": str(cause), "with": str(label), **applied},
            )
        except Exception:
            pass
    return record


def apply_relationship_delta(player, other_name: str, delta, cause: str,
                             tick: Optional[int] = None, area_id: str = "",
                             trace: bool = True) -> dict:
    """Writer of `closeness` (delegating to `apply_relationship_axes_delta`).

    ``cause`` is a short token naming the deciding layer (`combat`, `dialogue`,
    `meeting`, `gift`, `derive`) and is recorded on the trace with the amount and
    the area, so a relationship change can be located and explained after the
    fact. Every caller must supply one - an unexplained relationship change is
    the thing this function exists to prevent.
    """
    try:
        amount = int(delta or 0)
    except (TypeError, ValueError):
        amount = 0
    return apply_relationship_axes_delta(
        player,
        other_name,
        {"closeness": amount},
        cause,
        tick=tick,
        area_id=area_id,
        trace=trace,
    )


def apply_symmetric_delta(first, second, delta, cause: str,
                          tick: Optional[int] = None, area_id: str = "") -> None:
    """Apply the same delta to both sides of a pair.

    A meeting is one event with two participants, so symmetry is a property of
    the *call*, not something a caller has to remember to do twice. Each side
    still gets its own trace entry, because each side's history is its own.
    """
    apply_relationship_delta(first, second, delta, cause, tick=tick, area_id=area_id)
    apply_relationship_delta(second, first, delta, cause, tick=tick, area_id=area_id)


def describe(player, other_name: str) -> str:
    """One line of prose for a relationship, using the shared band ladder."""
    rel = get_relationship(player, other_name)
    name = getattr(player, "name", "They")
    other_label = (rel or {}).get("name") or display_name(player, other_name, resolve_key(player, other_name))
    if not rel:
        return f"{name} has never met {other_label}."
    closeness = rel.get("closeness", 0)
    label = (rel.get("label") or "").strip()
    if label:
        return (f"{name} considers {other_label} their {label} "
                f"(closeness: {closeness}/100).")
    return (f"{name} considers {other_label} a "
            f"{BAND_LABELS[closeness_band(closeness)]} "
            f"(closeness: {closeness}/100).")
