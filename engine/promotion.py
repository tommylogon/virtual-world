"""Promotion/demotion handoff between fidelity tiers (task-399).

A character is either **attended** (the normal agent/simple-NPC loop asks them
for decisions) or **background** (``engine/background_simulation.py`` runs them
deterministically). Switching between the two is the promote/demote seam
described in ``docs/design/reversibility-contract.md``: the same ``Player``, the
same graph, the same clock — only the decision source changes.

This module owns the *memory* half of that seam:

* :func:`offload` demotes a character and stamps the boundary tick. Nothing is
  banked, so a long span cannot become a burst when it lifts.
* :func:`promote` hands them back and turns the trace written while they were
  background into **one bounded subjective memory** (``source="background"``).
  The trace is the objective record (``engine/trace.py``); the memory is the
  bounded read of it.

Everything here is deterministic and templated — **no LLM call is made** (v1;
task-412 non-goals). Code writes the trace and the summary; a later LLM pass may
only *read* the trace.

Idempotence is the point. Activation is a tick boundary that can be crossed
twice (a re-render, a save reload, a scope opened again), and it must never
duplicate what the character remembers:

* :func:`promote` is a no-op unless the character is currently background.
* The span is ``t > max(last_offload_tick, background_consolidated_through)``,
  so foreground actions between two background spans are never summarized, and
  a second promotion of the same span finds no new entries and writes nothing.
* Both marks serialize with the save (``player.py`` / ``engine/serialization.py``).
"""

from __future__ import annotations

import logging
from collections import Counter
from typing import Any, Dict, List, Optional

from engine import trace as trace_mod

logger = logging.getLogger(__name__)

#: A promoted character must not wake up with an essay. The template truncates
#: to this many characters, matching the timeskip resume memory (task-481).
MEMORY_CHAR_LIMIT = 300

#: Tag put on every consolidated memory so the inspector and retrieval can tell
#: a background span from an authored or live observation.
BACKGROUND_TAG = "background"


def offload(gs, player, *, tick: Optional[int] = None,
            reason: str = "offload") -> bool:
    """Demote *player* to the deterministic background runner.

    Stamps the boundary tick so promotion can summarize exactly this span, and
    writes one ``demote`` trace entry. Idempotent: a character already in
    background mode is left alone and ``False`` is returned.

    Returns ``True`` when the character actually changed tier.
    """
    if player is None:
        return False
    if getattr(player, "simulation_mode", "active") == "background":
        return False
    now = _tick(gs, tick)
    player.simulation_mode = "background"
    player.last_offload_tick = int(now)
    # Entries at or before this tick are foreground history; only what happens
    # *after* the demotion belongs to the background span.
    player.background_consolidated_through = max(
        int(getattr(player, "background_consolidated_through", 0) or 0), int(now))
    _record(player, now, "demote", f"went to the background ({reason})",
            why=f"fidelity:{reason}")
    return True


def promote(gs, player, *, tick: Optional[int] = None,
            reason: str = "activate") -> Optional[str]:
    """Hand *player* back to attended play, consolidating the span into memory.

    Returns the memory text written, or ``None`` when there was nothing to do
    (the character was already attended) or nothing to remember.

    The character is marked attended and its consolidation mark advances even
    when the span was empty, so repeated activation is a no-op.
    """
    if player is None:
        return None
    if getattr(player, "simulation_mode", "active") != "background":
        return None  # already attended — promotion is not a foreground rewrite
    now = _tick(gs, tick)
    since = max(int(getattr(player, "last_offload_tick", 0) or 0),
                int(getattr(player, "background_consolidated_through", 0) or 0))
    entries = _span(player, since)

    player.simulation_mode = "active"
    player.background_consolidated_through = max(since, now)

    text = None
    if entries:
        text = summarize(gs, entries, since_tick=since, end_tick=now)
        try:
            player.add_memory(
                text, tick=now, importance=_importance(entries),
                memory_type="observation", tags=[BACKGROUND_TAG],
                source=BACKGROUND_TAG,
                location=getattr(player, "current_area", "") or "",
            )
        except Exception as e:  # never let memory block control hand-back
            logger.warning("[promotion] memory for %s: %s",
                           getattr(player, "name", "?"), e)

    # Written *after* the span is read so it is not part of its own summary; the
    # advanced mark excludes it from the next one as well.
    _record(player, now, "promote", f"came back into focus ({reason})",
            why=f"fidelity:{reason}")
    return text


def pending_span(player, since_tick: Optional[int] = None) -> List[Dict[str, Any]]:
    """The trace entries a promotion would currently summarize.

    Read-only; lets the boundary decide whether an activation is worth a memory.
    """
    if since_tick is None:
        since_tick = max(int(getattr(player, "last_offload_tick", 0) or 0),
                         int(getattr(player, "background_consolidated_through", 0) or 0))
    return _span(player, int(since_tick))


def summarize(gs, entries: List[Dict[str, Any]], *, since_tick: int = 0,
              end_tick: int = 0) -> str:
    """A deterministic, bounded sentence over a background span's trace facts.

    No LLM. The phrasing is stable for a given span so a replayed span reads
    identically (task-412 determinism acceptance). The result is truncated to
    :data:`MEMORY_CHAR_LIMIT`.
    """
    kinds = Counter(str(e.get("kind", "")) for e in entries)
    needs = _why_labels(entries, "needs:")
    routine = _why_labels(entries, "schedule:")
    moves = kinds.get("move", 0)
    notable = [str(e.get("what", "")) for e in entries if e.get("salient")]

    clauses: List[str] = []
    if needs:
        clauses.append("saw to " + _join(sorted(needs)))
    if routine:
        clauses.append("kept to your routine (" + _join(sorted(routine)) + ")")
    if moves:
        clauses.append(f"moved around ({moves} step{'s' if moves != 1 else ''})")
    if not clauses:
        clauses.append("passed the time")

    minutes = _elapsed_minutes(gs, since_tick, end_tick)
    text = (f"While you were on your own for about {minutes} min, you "
            + "; ".join(clauses) + ".")
    if notable:
        text += " Noted: " + "; ".join(notable[:2]) + "."
    return text[:MEMORY_CHAR_LIMIT]


# ───────────────────────────── internals ──────────────────────────────────


def _tick(gs, tick: Optional[int]) -> int:
    if tick is not None:
        return int(tick)
    return int(getattr(gs, "time_ticks", 0) or 0)


def _span(player, since_exclusive: int) -> List[Dict[str, Any]]:
    """Trace entries strictly after *since_exclusive* (the background span)."""
    return [e for e in trace_mod.ensure(player)
            if int(e.get("t", 0) or 0) > int(since_exclusive)]


def _why_labels(entries, prefix: str) -> set:
    out = set()
    for e in entries:
        why = str(e.get("why", "") or "")
        if why.startswith(prefix) and ":" in why:
            out.add(why.split(":", 1)[1])
    return out


def _join(items: List[str], limit: int = 3) -> str:
    items = [str(i) for i in items[:limit]]
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]


def _elapsed_minutes(gs, start: int, end: int) -> int:
    ticks = max(0, int(end) - int(start))
    try:
        per_tick = float(getattr(gs, "time_per_tick_minutes", 1) or 1)
    except (TypeError, ValueError):
        per_tick = 1.0
    return int(round(ticks * per_tick))


def _importance(entries) -> int:
    """Routine spans are forgettable; a span with salient events is not."""
    salient = sum(1 for e in entries if e.get("salient"))
    return max(2, min(8, 3 + salient))


def _record(player, tick: int, kind: str, what: str, why: str) -> None:
    try:
        trace_mod.record(player, tick, kind, what, why=why,
                         area=getattr(player, "current_area", "") or "",
                         tags=["fidelity"])
    except Exception as e:
        logger.warning("[promotion] %s trace for %s: %s", kind,
                       getattr(player, "name", "?"), e)
