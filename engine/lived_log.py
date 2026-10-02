"""Objective, code-written per-character record of what was lived.

See docs/design/lived-log-format.md. This is the mechanical record of what
happened (and why) that the LLM later summarizes into subjective memory, and
that makes a backgrounded character's history recoverable on promotion.

Named ``lived_log`` rather than ``trace`` because of what it is *not* (task-542).
A trace sounds like instrumentation — an auditable objective record you would
debug a long run with — and that reading is what invites merging it with soak
telemetry. They are not the same system and cannot be: this one is
salience-filtered, capped at 200 entries, rolled up, and stored **in the save on
the player**, because the question it answers is "would a person remember this?".
Soak telemetry is complete, per-run, and thrown away with the run, because its
question is "measure exactly this". The rollup that makes this store good for
memory is precisely what destroys it for measurement. **Telemetry is never
written here, and this is never the dashboard's data source.**

Nothing here calls an LLM or mutates world state beyond the character's own
``lived_log``. Entries are plain dicts so they serialize with the save.

@module lived_log
@contributes the bounded per-character record of what was experienced
@docs docs/virtualWorld/Characters/Background Simulation.md
"""

from __future__ import annotations

MAX_ENTRIES = 200

# Bounded, documented kinds (see the format doc).
KINDS = (
    "move", "act", "need", "condition", "encounter",
    "observe", "plan", "death", "promote", "demote",
)


def ensure(player) -> list:
    """Guarantee ``player.lived_log`` exists (older saves won't have it)."""
    log = getattr(player, "lived_log", None)
    if log is None:
        log = []
        player.lived_log = log
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
        "tick": int(tick),
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
    _tap(character=getattr(player, "name", ""), tick=tick, kind=kind,
         what=entry["what"], why=entry["why"], area=entry["area"])
    return entry


def _tap(character, tick, kind, what, why, area) -> None:
    """Fan this decision out to an active soak telemetry recorder, if any.

    One-way and one reason: a background decision needs the same tuple written
    twice — lossy here for memory, lossless there for measurement — and
    duplicating ~20 call sites guarantees they drift. The tap fires at write
    time, *before* any rollup can collapse the entry, so a lossy store can never
    become the source of a lossless one.

    This never writes to a lived log and never reads one. Outside a soak the
    active recorder is ``None`` and this costs one identity check.
    """
    try:
        from engine.soak_telemetry import active_recorder
    except Exception:  # noqa: BLE001 - telemetry must never break a game turn
        return
    recorder = active_recorder()
    if recorder is None:
        return
    try:
        recorder.action(character, tick, kind, what, why, area)
    except Exception:  # noqa: BLE001 - a measurement failure is not a game failure
        pass


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
        kept.sort(key=lambda e: _tick_of(e))
    player.lived_log[:] = kept


def _tick_of(entry) -> int:
    """Read an entry's tick, accepting the pre-task-542 ``t`` key.

    ``load()`` normalises ``t`` to ``tick`` on the way in, so this is belt and
    braces — but a missing fallback here would read every legacy entry as tick 0,
    which scrambles ``_trim``'s sort and makes ``since()`` find nothing. That is
    silent corruption rather than a load error, so the fallback stays.
    """
    value = entry.get("tick", entry.get("t"))
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def recent(player, n=20) -> list:
    return ensure(player)[-n:]


def since(player, tick) -> list:
    return [e for e in ensure(player) if _tick_of(e) >= tick]


def to_list(player) -> list:
    return [dict(e) for e in ensure(player)]


def load(player, data) -> None:
    """Restore from a serialized list; tolerate missing/garbage.

    Old saves carry the tick under ``t`` and entries under ``trace_log``.
    ``load()`` copies entries verbatim, so without the rewrite below a legacy
    entry would keep its old key and every reader would see tick 0 — silent
    corruption, not a load error. The rename is therefore only safe while this
    function normalises both keys in the same change.
    """
    entries = []
    for raw in (data or []):
        if not isinstance(raw, dict):
            continue
        entry = dict(raw)
        if "tick" not in entry and "t" in entry:
            entry["tick"] = entry["t"]
        entry.pop("t", None)
        entries.append(entry)
    player.lived_log = entries


def summarize_window(player, since_tick=0, limit=40) -> list:
    """Compact text lines for an LLM catch-up prompt over a lived window."""
    lines = []
    for e in since(player, since_tick)[-limit:]:
        why = f" ({e['why']})" if e.get("why") else ""
        area = f" @ {e['area']}" if e.get("area") else ""
        lines.append(f"t={_tick_of(e)} {e.get('what')}{why}{area}")
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
                "tick": _tick_of(e), "kind": "plan",
                "what": f"{e.get('what')} (x{run})",
                "why": e.get("why", ""), "area": e.get("area", ""),
                "tags": e.get("tags", []), "salient": False, "rolled": run,
            })
        else:
            out.extend(log[i:j])
        i = j
    player.lived_log[:] = out
    return before - len(out)
