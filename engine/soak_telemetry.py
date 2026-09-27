"""Soak telemetry — the measurement store for a soak run (task-543).

This is deliberately **not** the lived log. The two look alike and answer
opposite questions, so the boundary is load-bearing and worth restating:

======================  ==========================================  =========================================
                        ``lived_log`` (engine/lived_log.py)        telemetry (this module)
======================  ==========================================  =========================================
scope                   per **character**                          per **run**
stored                  **in the save**, on the player             **out of the save**, on the run
grain                   salience-filtered, runs collapsed          complete, every move
test applied            "would a person remember this"              "measure exactly this"
lifetime                ~200 entries, rolled up                    the whole run, then archived
consumer                LLM summarisation on promote/demote        dashboard, export, benchmark
if it leaks             an LLM "remembers" a life it never lived   the benchmark becomes fiction
======================  ==========================================  =========================================

The rollup that makes the lived log *good* for memory is exactly what destroys it
for measurement, so the two cannot be one store. See
``docs/design/lived-log-format.md``.

**How the two writers stay separate while sharing one decision.** Background
decisions are recorded through :func:`engine.lived_log.record`, and every soak
action needs the same ``(character, tick, kind, what, why, area)`` tuple. Rather
than duplicate ~20 call sites and risk the copies drifting, ``record()`` fans out
to an *active* recorder through :func:`active_recorder` — a one-way tap, the same
pattern as a logging handler. Three properties keep the boundary honest, and all
three are asserted by tests rather than trusted:

1. **One way.** Nothing here ever writes to a ``lived_log``, and no lived-log
   reader is used to serve the dashboard. Telemetry is *pushed* at write time,
   before any rollup can touch it, so a lossy store cannot leak into a lossless
   one.
2. **Off by default.** ``active_recorder()`` is ``None`` outside a soak, so the
   normal game pays one identity check per record and nothing else.
3. **Refuses the wrong vocabulary.** See ``WHY_PREFIXES``.

## Why presence intervals, not per-tick samples

Occupancy is knowable only if you record *where a character was between two
moves*. One line per area change, not one line per tick:

.. code-block:: json

    {"character": "Jake", "area": "Kraktooth Camp, Storehouse",
     "from_tick": 41200, "to_tick": 41480}

The cost is therefore bounded by **moves**, not ticks, and the same records render
at any zoom — a swimlane at one-minute resolution and a whole week at hourly
resolution are the same data. Per-tick sampling cannot do that: a 7-day soak at
1 min/tick is 10,080 samples per character on the tick axis, and any stored
subsample is a permanent loss of resolution. A character sitting in a room for
six hours produces **one** interval and no further events, which is the whole
point: presence is *state*, and only a state change is worth writing down.

For calibration, a ``lived_log`` entry is 189 B as JSON but ~1,106 B as a Python
object — a ~5.8x object-graph overhead that makes raw volume the thing people
intuit wrongly. At 120 moves/day/char x 7 days x 20 characters that is 16,800
intervals, roughly 1.9 MB: the same order as a 30-day lived log, and ~11,000x
smaller than the "record everything every tick" proposal. **Memory is not the
constraint here; resolution is.**
"""

from __future__ import annotations

import json
import os
import threading
from typing import Any, Dict, Iterable, List, Optional

#: The closed set of ``why`` prefixes telemetry accepts, as the code actually
#: writes them. Measured 2026-09-27 with ``tools/why_vocabulary.py`` against a
#: 240-tick Kraktooth goblin camp run, not copied from a design doc — the first
#: draft of this list came from task-543's prose and was wrong within one run,
#: missing ``traversal:``/``forage:``/``schedule:`` entirely. The rejection
#: counter is what surfaced it, which is the argument for keeping the counter.
#:
#: A strict subset of the lived log's vocabulary, so there is one writer and no
#: drift: telemetry reuses tags, it does not invent them.
#:
#: ``llm:`` is excluded **structurally**, not by frequency. A soak makes no LLM
#: calls by construction — ``engine/soak_runner.py`` says so in its own
#: docstring and ``background_all`` forces every character to
#: ``simulation_mode = "background"`` — so an LLM reason is impossible, not merely
#: rare. Carrying the prefix would leave a permanently empty category that invites
#: "why is this always zero?" every time someone reads the breakdown.
WHY_PREFIXES = (
    "needs:",        # a pressing vital drove it
    "goal:",         # serving a chosen goal
    "plan:",         # executing a standing plan
    "social:",       # another character prompted it
    "threat:",       # reactive to danger
    "order:",        # following an instruction
    "env:",          # forced by environment/area status
    "schedule:",     # the character's daily schedule
    "agenda:",       # a background agenda (task-468)
    "search:",       # looking for something (foraging)
    "forage:",       # a forage attempt and its outcome (task-470)
    "traversal:",    # a movement gate and its outcome (task-475)
    "timeskip:",     # a compressed offline span
    "fidelity:",     # the promote/demote boundary
    "cause:",        # a death, named by cause
    "react:",        # a reaction to a stimulus
    "sense:",        # a percept
    "sim:",          # the simulation/fidelity layer
)

#: Prefixes that are valid in a lived log but must never appear in telemetry.
EXCLUDED_PREFIXES = ("llm:",)

#: A record with no ``why`` at all. Common and not an error — plenty of
#: bookkeeping records are not a decision — but it must be *counted*, because a
#: breakdown that silently drops the unattributed share reports a distribution
#: that does not add up to the run. Counted as its own group rather than
#: rejected, so the numbers stay honest without failing the run.
UNATTRIBUTED = "unattributed"

#: Set while a soak run is recording. ``engine.lived_log.record`` fans out here.
_ACTIVE: Optional["TelemetryRecorder"] = None
_ACTIVE_LOCK = threading.RLock()


def is_valid_why(why: str) -> bool:
    """True when *why* is in telemetry's closed vocabulary.

    A bare prefix (``"plan:"``) is rejected as well as a missing one: a breakdown
    that groups ``plan:`` separately from ``plan:patrol`` is a category with no
    meaning, and it is almost always an unfinished tag rather than an intent.
    """
    text = str(why or "")
    if not text:
        return False
    if text.startswith(EXCLUDED_PREFIXES):
        return False
    for prefix in WHY_PREFIXES:
        if text.startswith(prefix):
            return len(text) > len(prefix)
    return False


def why_group(why: str) -> str:
    """The prefix a ``why`` ranks under (``plan:patrol`` -> ``plan``).

    Unrecognised values group under ``other`` rather than raising: telemetry is
    measurement, and a bad tag should be visible in the breakdown, not fatal to
    the run that produced it.
    """
    text = str(why or "")
    if not text:
        return UNATTRIBUTED
    for prefix in WHY_PREFIXES:
        if text.startswith(prefix):
            return prefix[:-1]
    return "other"


def active_recorder() -> Optional["TelemetryRecorder"]:
    """The recorder currently fanned out to, or ``None`` outside a soak."""
    return _ACTIVE


class _ActiveScope:
    """Context manager installing *recorder* as the active fan-out target."""

    def __init__(self, recorder: "TelemetryRecorder"):
        self._recorder = recorder
        self._previous: Optional[TelemetryRecorder] = None

    def __enter__(self) -> "TelemetryRecorder":
        global _ACTIVE
        with _ACTIVE_LOCK:
            self._previous = _ACTIVE
            _ACTIVE = self._recorder
        return self._recorder

    def __exit__(self, *exc) -> bool:
        global _ACTIVE
        with _ACTIVE_LOCK:
            _ACTIVE = self._previous
        return False


def recording(recorder: "TelemetryRecorder") -> _ActiveScope:
    """Install *recorder* for the duration of a ``with`` block."""
    return _ActiveScope(recorder)


#: Conditions that describe a character's *baseline* state rather than an
#: incident, and are therefore excluded from the space-time ribbons.
#:
#: This is a judgement about meaning, not about frequency. `awake` and `busy` are
#: on a character for most of a run and describe nothing — "conscious and alert"
#: is not a finding. Ribbons that mark them turn the chart into a solid orange
#: field, which is worse than no ribbons: it looks like everybody is perpetually
#: unwell, and a real illness loses its contrast against the background.
#:
#: Excluded here rather than in the renderer so the exclusion is part of the data
#: contract — the counts stay reconcilable, and a caller cannot accidentally
#: re-introduce the noise by forgetting a filter.
AMBIENT_CONDITIONS = frozenset({"awake", "busy"})


def is_ambient(condition: str) -> bool:
    """True when *condition* is a baseline lifecycle state, not an incident."""
    return str(condition or "") in AMBIENT_CONDITIONS


class TelemetryRecorder:
    """Run-owned measurement store. Thread-safe: a run writes from its own
    thread while the dashboard reads from the request threads."""

    def __init__(self, run_id: str, jsonl_path: Optional[str] = None,
                 hot_window: int = 20000):
        self.run_id = run_id
        self.jsonl_path = jsonl_path
        self.hot_window = max(0, int(hot_window))
        self._lock = threading.RLock()

        # presence intervals, keyed by character
        self._intervals: Dict[str, List[Dict[str, Any]]] = {}
        self._open_area: Dict[str, str] = {}
        self._open_from: Dict[str, int] = {}

        self._events: List[Dict[str, Any]] = []
        self._truncated_events = 0
        #: ``why`` values rejected by the vocabulary check, with counts. Surfaced
        #: in the payload rather than raised: a soak that dies because a new
        #: background rule used a new tag is worse than one that reports it.
        self.rejected_why: Dict[str, int] = {}
        self.rejected_events = 0

        self._fp = None
        if jsonl_path:
            os.makedirs(os.path.dirname(jsonl_path) or ".", exist_ok=True)
            self._fp = open(jsonl_path, "a", encoding="utf-8")

    # ── presence ──────────────────────────────────────────────────────────

    def observe_area(self, character: str, area: Optional[str], tick: int) -> None:
        """Note where *character* is at *tick*. Emits an interval on change.

        Called once per character per tick, which is O(cast) — the same order as
        the runner's existing death sweep. Only a *change* writes a record, so the
        interval count scales with moves and not with run length.
        """
        area_name = str(area or "")
        with self._lock:
            previous = self._open_area.get(character)
            if previous == area_name:
                return
            if previous is not None:
                self._close_interval(character, previous, self._open_from[character], tick)
            self._open_area[character] = area_name
            self._open_from[character] = int(tick)

    def close_character(self, character: str, tick: int) -> None:
        """Close a character's open interval (a death, or end of run)."""
        with self._lock:
            area = self._open_area.pop(character, None)
            from_tick = self._open_from.pop(character, None)
            if area is not None and from_tick is not None:
                self._close_interval(character, area, from_tick, tick)

    def close_all(self, tick: int) -> None:
        for character in list(self._open_area):
            self.close_character(character, tick)

    def _close_interval(self, character: str, area: str,
                        from_tick: int, to_tick: int) -> None:
        interval = {
            "character": character,
            "area": area,
            "from_tick": int(from_tick),
            "to_tick": int(to_tick),
        }
        self._intervals.setdefault(character, []).append(interval)
        self._write_line({"type": "presence", **interval})

    def presence_intervals(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [dict(iv) for group in self._intervals.values() for iv in group]

    def presence_for(self, character: str) -> List[Dict[str, Any]]:
        with self._lock:
            return [dict(iv) for iv in self._intervals.get(character, [])]

    # ── events ────────────────────────────────────────────────────────────

    def action(self, character: str, tick: int, kind: str, what: str,
               why: str = "", area: str = "") -> Optional[Dict[str, Any]]:
        """Record one thing a character did, and why. Fanned out from
        ``engine.lived_log.record``; see the module docstring for why these share
        a decision without sharing a store.

        An *empty* ``why`` is kept and bucketed as ``unattributed`` — many
        bookkeeping records are not decisions, and dropping them would make the
        breakdown's shares not add up to the run. A *wrong* ``why`` is rejected
        and counted, because silently accepting an unknown tag is how a
        vocabulary rots.
        """
        if why and not is_valid_why(why):
            key = str(why)
            with self._lock:
                self.rejected_why[key] = self.rejected_why.get(key, 0) + 1
                self.rejected_events += 1
            return None
        return self._push({
            "type": "action",
            "character": character,
            "tick": int(tick),
            "kind": kind,
            "what": str(what),
            "why": str(why or ""),
            "why_group": why_group(why),
            "area": str(area or ""),
        })

    def condition(self, character: str, tick: int, condition: str,
                  gained: bool, area: str = "") -> Dict[str, Any]:
        """Record a condition gained or lost — a state crossing, so it is
        event-driven rather than sampled."""
        return self._push({
            "type": "condition",
            "character": character,
            "tick": int(tick),
            "kind": "condition_gained" if gained else "condition_lost",
            "what": condition,
            "why": "",
            "why_group": "",
            "area": str(area or ""),
        })

    def death(self, character: str, tick: int, cause: str,
              area: str = "") -> Dict[str, Any]:
        return self._push({
            "type": "death",
            "character": character,
            "tick": int(tick),
            "kind": "death",
            "what": cause,
            "why": f"cause:{cause}" if cause else "",
            "why_group": "cause" if cause else "",
            "area": str(area or ""),
        })

    def _push(self, event: Dict[str, Any]) -> Dict[str, Any]:
        with self._lock:
            self._events.append(event)
            if self.hot_window and len(self._events) > self.hot_window:
                del self._events[:len(self._events) - self.hot_window]
                self._truncated_events += 1
        self._write_line(event)
        return event

    def events(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [dict(e) for e in self._events]

    # ── aggregation for the dashboard ─────────────────────────────────────

    def why_breakdown(self) -> List[Dict[str, Any]]:
        """Ranked ``why`` distribution, grouped by prefix.

        This is the panel the whole view exists to serve: *who did what, why,
        where.* Without it a run can only say "Jake moved 47 times", which is not
        a finding. Grouped by prefix so the background rules compete on one axis
        (``plan:provision`` and ``plan:patrol`` both count as ``plan``).

        **Only decided records are ranked.** A record with no ``why`` — the
        mechanical cost-application entry ``apply_action`` writes for every verb,
        or a condition crossing — has no deciding rule, and counting it as one
        would drag every real rule's share down and make the distribution answer a
        question nobody asked. Those are reported separately as
        :attr:`unattributed_count`, so the panel's shares still add up to the
        decided total and the omitted volume is still visible.
        """
        counts: Dict[str, int] = {}
        decided = 0
        for event in self._events:
            group = event.get("why_group") or ""
            if not group or group == UNATTRIBUTED:
                continue
            counts[group] = counts.get(group, 0) + 1
            decided += 1
        total = decided or 1
        return [
            {"group": group, "count": count, "share": round(count / total, 4)}
            for group, count in sorted(counts.items(), key=lambda kv: -kv[1])
        ]

    @property
    def unattributed_count(self) -> int:
        """Events recorded with no deciding rule. Reported, not ranked."""
        with self._lock:
            return sum(1 for e in self._events
                       if not e.get("why_group") or e.get("why_group") == UNATTRIBUTED)

    def kind_breakdown(self) -> List[Dict[str, Any]]:
        """``kind`` distribution — *what* they spent time on. Coarser than
        ``why``; the two are not interchangeable. Unlike :meth:`why_breakdown`
        this counts every event, because "what" is a fair question to ask of a
        condition crossing."""
        counts: Dict[str, int] = {}
        for event in self._events:
            kind = event.get("kind") or "unknown"
            counts[kind] = counts.get(kind, 0) + 1
        return [{"kind": k, "count": v}
                for k, v in sorted(counts.items(), key=lambda kv: -kv[1])]

    def condition_spans(self, end_tick: Optional[int] = None) -> List[Dict[str, Any]]:
        """Pair condition crossings into spans a ribbon can draw.

        A ribbon wants ``(from, to)`` pairs, and the crossings are two separate
        events. Pairing them server-side keeps the client from re-deriving state
        and keeps the pairing next to the state it comes from. An unmatched gain
        (still active at the end of the run) is closed at *end_tick* rather than
        dropped — "they were ill from here to the end" is a real reading, and
        dropping it would understate a long illness.
        """
        with self._lock:
            events = [dict(e) for e in self._events]
        open_spans: Dict[tuple, Dict[str, Any]] = {}
        spans: List[Dict[str, Any]] = []
        for event in sorted(events, key=lambda e: e.get("tick", 0)):
            if event.get("kind") not in ("condition_gained", "condition_lost"):
                continue
            if is_ambient(event.get("what")):
                continue
            key = (event.get("character"), event.get("what"))
            if event["kind"] == "condition_gained":
                open_spans[key] = {
                    "character": event.get("character"),
                    "condition": event.get("what"),
                    "from_tick": int(event.get("tick", 0)),
                    "to_tick": None,
                }
            elif key in open_spans:
                span = open_spans.pop(key)
                span["to_tick"] = int(event.get("tick", 0))
                spans.append(span)
        for span in open_spans.values():
            span["to_tick"] = int(end_tick if end_tick is not None else span["from_tick"])
            spans.append(span)
        return sorted(spans, key=lambda s: (s["character"] or "", s["from_tick"]))

    def conditions(self) -> List[str]:
        """Every condition seen, ambient ones included — this is the roster a
        reader may want to filter by. The *ribbons* exclude the ambient set; see
        :func:`is_ambient`."""
        with self._lock:
            return sorted({e.get("what") for e in self._events
                           if e.get("kind") in ("condition_gained", "condition_lost")
                           and e.get("what")})

    def characters(self) -> List[str]:
        with self._lock:
            return sorted(set(self._intervals) | {e.get("character") for e in self._events
                                                  if e.get("character")})

    def areas(self) -> List[str]:
        with self._lock:
            return sorted({iv["area"] for group in self._intervals.values()
                           for iv in group if iv.get("area")})

    def to_payload(self, include_events: bool = True,
                   end_tick: Optional[int] = None) -> Dict[str, Any]:
        """Everything the dashboard needs, in one response.

        Intervals are always included — they are the bounded half (one per move)
        and they are what the swimlane draws. Events are the unbounded half, so
        they are opt-in. Condition *spans* (not raw crossings) are included,
        because a ribbon draws durations and the pairing belongs next to the
        state it came from.
        """
        payload = {
            "run_id": self.run_id,
            "characters": self.characters(),
            "areas": self.areas(),
            "conditions": self.conditions(),
            "intervals": self.presence_intervals(),
            "condition_spans": self.condition_spans(end_tick),
            "why": self.why_breakdown(),
            "kinds": self.kind_breakdown(),
            "unattributed": self.unattributed_count,
            "rejected_why": dict(self.rejected_why),
            "rejected_events": self.rejected_events,
            "truncated_events": self._truncated_events,
            "jsonl_path": self.jsonl_path,
            "counts": {
                "intervals": sum(len(v) for v in self._intervals.values()),
                "events": len(self._events),
            },
        }
        if include_events:
            payload["events"] = self.events()
        return payload

    # ── disk ──────────────────────────────────────────────────────────────

    def _write_line(self, record: Dict[str, Any]) -> None:
        """Append one JSONL line. Best-effort: a telemetry write failure must not
        take down the run it is measuring."""
        fp = self._fp
        if fp is None:
            return
        try:
            fp.write(json.dumps(record, ensure_ascii=False) + "\n")
            fp.flush()
        except Exception:  # noqa: BLE001 - never fail a run over telemetry
            pass

    def close(self) -> None:
        fp, self._fp = self._fp, None
        if fp is not None:
            try:
                fp.close()
            except Exception:  # noqa: BLE001
                pass

    def __enter__(self) -> "TelemetryRecorder":
        return self

    def __exit__(self, *exc) -> bool:
        self.close()
        return False


def summarise(intervals: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Cheap integrity check over an interval set: gaps, overlaps, coverage.

    Exposed because "the intervals tile the run with no gaps" is a property worth
    asserting rather than assuming — a gap means presence is unknown for that
    window, and a swimlane that silently omits it reads as "nobody was here".
    """
    by_character: Dict[str, List[Dict[str, Any]]] = {}
    for interval in intervals:
        by_character.setdefault(interval["character"], []).append(interval)
    gaps = 0
    overlaps = 0
    for group in by_character.values():
        group.sort(key=lambda iv: iv["from_tick"])
        for prev, nxt in zip(group, group[1:]):
            if nxt["from_tick"] > prev["to_tick"]:
                gaps += 1
            elif nxt["from_tick"] < prev["to_tick"]:
                overlaps += 1
    return {
        "characters": len(by_character),
        "intervals": sum(len(v) for v in by_character.values()),
        "gaps": gaps,
        "overlaps": overlaps,
    }
