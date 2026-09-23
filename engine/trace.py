"""Objective, code-written per-character trace.

See docs/design/trace-format.md. This is the mechanical record of what
happened (and why) that the LLM later summarizes into subjective memory, and
that makes a backgrounded character's history recoverable on promotion.

Nothing here calls an LLM or mutates world state beyond the character's own
``trace_log``. Entries are plain dicts so they serialize with the save.
"""

from __future__ import annotations

MAX_ENTRIES = 200

# Bounded, documented kinds (see the format doc).
KINDS = (
    "move", "act", "need", "condition", "encounter",
    "observe", "plan", "death", "promote", "demote",
)


def ensure(player) -> list:
    """Guarantee ``player.trace_log`` exists (older saves won't have it)."""
    log = getattr(player, "trace_log", None)
    if log is None:
        log = []
        player.trace_log = log
    return log


def record(player, tick, kind, what, why="", area="", tags=None,
           salient=False, delta=None) -> dict:
    """Append one objective fact. Returns the entry.

    ``why`` is a reason tag naming the deciding layer (e.g. ``needs:hunger``,
    ``goal:eat``, ``plan:patrol``, ``llm:novel``) so background activity stays
    explainable long after it happened.
    """
    log = ensure(player)
    entry = {
        "t": int(tick),
        "kind": kind,
        "what": str(what),
        "why": str(why or ""),
        "area": str(area or ""),
        "tags": list(tags or []),
        "salient": bool(salient),
    }
    if delta:
        entry["delta"] = dict(delta)
    log.append(entry)
    if len(log) > MAX_ENTRIES:
        _trim(player, MAX_ENTRIES)
    return entry


def _trim(player, max_entries):
    """Keep salient entries; fill the rest with the newest routine entries."""
    log = ensure(player)
    if len(log) <= max_entries:
        return
    salient = [e for e in log if e.get("salient")]
    plain = [e for e in log if not e.get("salient")]
    if len(salient) >= max_entries:
        kept = salient[-max_entries:]
    else:
        kept = plain[-(max_entries - len(salient)):] + salient
        kept.sort(key=lambda e: e.get("t", 0))
    player.trace_log[:] = kept


def recent(player, n=20) -> list:
    return ensure(player)[-n:]


def since(player, tick) -> list:
    return [e for e in ensure(player) if e.get("t", 0) >= tick]


def to_list(player) -> list:
    return [dict(e) for e in ensure(player)]


def load(player, data) -> None:
    """Restore from a serialized list; tolerate missing/garbage."""
    player.trace_log = [dict(e) for e in (data or []) if isinstance(e, dict)]


def summarize_window(player, since_tick=0, limit=40) -> list:
    """Compact text lines for an LLM catch-up prompt over a trace window."""
    lines = []
    for e in since(player, since_tick)[-limit:]:
        why = f" ({e['why']})" if e.get("why") else ""
        area = f" @ {e['area']}" if e.get("area") else ""
        lines.append(f"t={e.get('t')} {e.get('what')}{why}{area}")
    return lines


def rollup(player, min_run=5) -> int:
    """Collapse long runs of identical routine entries into one summary.

    Salient entries are never merged. Returns the number of entries removed.
    """
    log = ensure(player)
    before = len(log)
    out = []
    i = 0
    while i < len(log):
        e = log[i]
        if e.get("salient"):
            out.append(e)
            i += 1
            continue
        j = i + 1
        while (j < len(log) and not log[j].get("salient")
               and log[j].get("kind") == e.get("kind")
               and log[j].get("why") == e.get("why")
               and log[j].get("area") == e.get("area")):
            j += 1
        run = j - i
        if run >= min_run:
            out.append({
                "t": e.get("t"), "kind": "plan",
                "what": f"{e.get('what')} (x{run})",
                "why": e.get("why", ""), "area": e.get("area", ""),
                "tags": e.get("tags", []), "salient": False, "rolled": run,
            })
        else:
            out.extend(log[i:j])
        i = j
    player.trace_log[:] = out
    return before - len(out)
