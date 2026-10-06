"""Phrase meaningful lived_log entries into first-person memories (task-727).

The lived log (``engine/lived_log.py``) is the objective record; memories are
the subjective read the character Mind panel shows. ``engine/promotion.py``
bridges a background *span* into one aggregate memory. This module bridges
*individual* entries whose facts have no other memory writer, so a death, a
relationship shift, or a pursuit reads back as a first-person memory instead of
being lost.

Kinds already covered elsewhere and deliberately NOT re-phrased here:

- ``social``  -> ``engine/social_text.py`` (background_social writes the memory)
- ``threat``  -> ``background_social`` writes a memory at the same site
- ``need``    -> ``engine/agent_memory._surface_need_recall``
- ``act`` / ``move`` / ``traversal`` -> ``record_observation`` area/item memories

Deterministic, no LLM (v1) -- same rule as promotion (task-412). Idempotent per
entry: ``player.lived_log_memorized_through`` marks the newest tick already
phrased, so re-running a turn never duplicates a memory.

@module lived_log_memory
@contributes the per-entry lived_log -> first-person memory bridge
@docs docs/design/lived-log-format.md
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

#: Kinds with no other memory writer. See the module docstring for the kinds
#: that ARE covered elsewhere, so this list must not repeat them.
MEMORIZABLE_KINDS = ("death", "relationship", "pursuit")


def _closeness_text(entry) -> str:
    delta = entry.get("delta") or {}
    other = str(delta.get("with") or "them")
    try:
        amount = int(delta.get("closeness", 0) or 0)
    except (TypeError, ValueError):
        amount = 0
    cause = str(delta.get("cause") or "").strip()
    if amount > 0:
        base = f"I feel a little closer to {other} now."
    elif amount < 0:
        base = f"Something about {other} has me wary."
    else:
        base = f"Something involving {other} stayed with me."
    return f"{base} ({cause})" if cause else base


def _capitalize(text: str) -> str:
    text = text.strip()
    return (text[:1].upper() + text[1:]) if text else text


def phrase(entry) -> str:
    """First-person memory text for a lived entry, or ``''`` when none."""
    kind = str(entry.get("kind") or "")
    what = str(entry.get("what") or "")
    if kind == "relationship":
        return _closeness_text(entry)
    if kind == "death":
        cause = what[len("died of "):] if what.startswith("died of ") else what
        cause = cause.strip()
        return f"I died \u2014 {cause}." if cause else "I died."
    if kind == "pursuit":
        text = _capitalize(what)
        return text + ("." if text and not text.endswith(".") else "")
    return ""


def _importance(entry) -> int:
    if entry.get("salient"):
        return 8
    return 5 if str(entry.get("kind") or "") == "death" else 4


def bridge(player, gs=None) -> int:
    """Write a first-person memory for each un-phrased meaningful lived entry.

    Returns the number of memories written. Never raises.
    """
    log = getattr(player, "lived_log", []) or []
    if not log:
        return 0
    mark = int(getattr(player, "lived_log_memorized_through", 0) or 0)
    newest = mark
    written = 0
    for entry in log:
        try:
            tick = int(entry.get("tick", 0) or 0)
        except (TypeError, ValueError):
            tick = 0
        if tick <= mark:
            continue
        if tick > newest:
            newest = tick
        kind = str(entry.get("kind") or "")
        if kind not in MEMORIZABLE_KINDS:
            continue
        text = phrase(entry)
        if not text:
            continue
        tags = [kind]
        if kind == "relationship":
            other = str((entry.get("delta") or {}).get("with") or "").strip()
            if other:
                tags.append("rel:" + other)
        try:
            player.add_memory(
                text, tick=tick, importance=_importance(entry),
                memory_type="reaction", tags=tags, source="lived_log",
                location=str(entry.get("area") or ""),
            )
            written += 1
        except Exception as exc:  # a memory write must never break a turn
            logger.warning("[lived_log_memory] %s: %s",
                           getattr(player, "name", "?"), exc)
    if newest > mark:
        player.lived_log_memorized_through = newest
    return written


def bridge_all(gs) -> int:
    """Bridge every player's un-phrased lived entries. Safe to call per turn."""
    players = getattr(gs, "players", None)
    if not players:
        return 0
    total = 0
    for player in list(players.values()):
        total += bridge(player, gs)
    return total
