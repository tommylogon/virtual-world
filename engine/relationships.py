"""One relationship mutation path (task-420).

Relationship state is a blunt per-pair scalar:

    player.relationships[other] = {
        "closeness": -100..100,
        "last_interaction_tick": int,
        "interaction_count": int,
        "label": str,              # authored declaration ("my brother")
        "first_sighting": bool,    # identity still hidden this turn
    }

Every gameplay writer used to touch that dict itself — combat, the foreground
loop, first-meeting registration, the `label` command — so two things were true:

1. **No cause was recorded.** A delta from a beating looked identical to one
   from a shared meal, so nothing downstream (trace, memory, reflection) could
   explain why two characters feel the way they do.
2. **The fidelity tiers could diverge.** Foreground outcomes and background
   relationship drift wrote the same scalar through different code, so at a
   promotion/demotion the value could jump: the two paths never agreed on how it
   evolves.

`apply_relationship_delta` is now the only writer of `closeness`. It clamps in
one place, stamps the interaction, and records the cause on the trace. A
deserializer replacing the whole store from a payload is not a mutation of a
relationship and does not go through here (see `routes/player_ops.py`).

`closeness_band` also lives here: the band ladder was inline in
`Player.get_relationship_nl`, and task-423's outcome table needs the same bands,
so it is defined once.
"""

from __future__ import annotations

from typing import Optional

CLOSENESS_MIN = -100
CLOSENESS_MAX = 100

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


def clamp_closeness(value) -> int:
    """Clamp to the store's range. The one place the bounds are enforced."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0
    return int(max(CLOSENESS_MIN, min(CLOSENESS_MAX, number)))


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


def ensure_relationship(player, other_name: str, tick: int = 0,
                       label: str = "") -> tuple[dict, bool]:
    """The record for ``other_name``, created if absent. Returns (record, created).

    Creating a record is not the same as *feeling* something: this grants no
    novelty and moves no closeness, so callers that do care (first meeting,
    a landed insult) apply their own delta afterwards.
    """
    if player is None or not other_name:
        return {}, False
    existing = player.relationships.get(other_name)
    if existing is not None:
        return existing, False
    record = {
        "closeness": 0,
        "last_interaction_tick": int(tick or 0),
        "interaction_count": 0,
        "label": label or "",
    }
    player.relationships[other_name] = record
    return record, True


def apply_relationship_delta(player, other_name: str, delta, cause: str,
                             tick: Optional[int] = None, area_id: str = "",
                             trace: bool = True) -> dict:
    """The only writer of `closeness`. Returns the updated record.

    ``cause`` is a short token naming the deciding layer (`combat`, `dialogue`,
    `meeting`, `gift`, `derive`) and is recorded on the trace with the amount and
    the area, so a relationship change can be located and explained after the
    fact. Every caller must supply one — an unexplained relationship change is
    the thing this function exists to prevent.
    """
    record, _ = ensure_relationship(player, other_name, tick or 0)
    if not record:
        return {}
    amount = int(delta or 0)
    if amount:
        record["closeness"] = clamp_closeness(record.get("closeness", 0) + amount)
    if tick is not None:
        record["last_interaction_tick"] = int(tick)
    record.setdefault("interaction_count", 0)
    if amount or tick is not None:
        record["interaction_count"] = int(record.get("interaction_count", 0)) + 1

    if trace and amount:
        try:
            from engine.trace import record as trace_record
            trace_record(
                player, int(tick or 0), "relationship",
                f"closeness toward {other_name} {amount:+d}",
                why=f"social:{cause}",
                area=area_id or (getattr(player, "current_area", "") or ""),
                tags=["rel:" + str(other_name), str(cause)],
                delta={"closeness": amount, "cause": str(cause),
                       "with": str(other_name)},
            )
        except Exception:
            pass
    return record


def apply_symmetric_delta(first, second, delta, cause: str,
                          tick: Optional[int] = None, area_id: str = "") -> None:
    """Apply the same delta to both sides of a pair.

    A meeting is one event with two participants, so symmetry is a property of
    the *call*, not something a caller has to remember to do twice. Each side
    still gets its own trace entry, because each side's history is its own.
    """
    apply_relationship_delta(first, getattr(second, "name", second), delta, cause,
                             tick=tick, area_id=area_id)
    apply_relationship_delta(second, getattr(first, "name", first), delta, cause,
                             tick=tick, area_id=area_id)


def describe(player, other_name: str) -> str:
    """One line of prose for a relationship, using the shared band ladder."""
    rel = (getattr(player, "relationships", None) or {}).get(other_name)
    name = getattr(player, "name", "They")
    if not rel:
        return f"{name} has never met {other_name}."
    closeness = rel.get("closeness", 0)
    label = (rel.get("label") or "").strip()
    if label:
        return (f"{name} considers {other_name} their {label} "
                f"(closeness: {closeness}/100).")
    return (f"{name} considers {other_name} a "
            f"{BAND_LABELS[closeness_band(closeness)]} "
            f"(closeness: {closeness}/100).")
