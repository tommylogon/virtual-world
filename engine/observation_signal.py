"""Who saw whom, and whether it was public (task-547).

**Not** :mod:`engine.observation`. That module is task-403's *observation
memories* — "what has this character seen", a per-subject belief stored on the
character. This is the mirror image: "who has seen *this character*", a
social/audience fact about the target. They answer different questions and are
updated by different passes, so they live in different modules.

Before this, "someone was looking at you" existed nowhere in the engine. The only
thing close was ``NPCBehaviorSystem.process_bystander_reactions``, which is the
wrong shape for the question:

1. it returns **strings**, so no caller can learn *who* perceived anything;
2. it walks only ``simple_npc`` characters, so agent-driven and human characters —
   the ones a player most expects to be watching — are skipped;
3. ``max_reactions`` (default 1) breaks the loop, so the reaction cap was also a
   silent truncation of the observer set;
4. it conflates *noticed* with *emitted a line*, so an observer whose reaction
   trait resolves to ``ignore`` left no trace at all.

This module is the record the missing effects need (task-487 among them). It is
deliberately **derived, tick-stamped state, not serialized**: the perception pass
rebuilds it each turn, so persisting it would only store something the next pass
recomputes. The cost is that a page reload drops the recent window, which
self-heals on the next turn.

The public/covert distinction answers "was there an audience", which
``engine.body_parts.is_exposed`` cannot — that answers "is this body part
covered", and a covered body part in an empty room is nobody's business.
"""

from __future__ import annotations

from typing import Dict, List, Optional

#: How many turns a "someone saw that" fact stays readable by default. The
#: exposure and the reaction it causes usually land on different turns, so a
#: single-turn record would be too short to be usable (task-547, decision 3).
DEFAULT_MEMORY_TURNS = 3

#: Minimum ambient light (0-100) for an observation to count as *public*. Below
#: this the light penalty the perception DC already applies takes over and the
#: observation is recorded as covert: someone may have caught a shape, but nobody
#: was an onlooker to it.
PUBLIC_LIGHT_FLOOR = 20

#: Conditions that mean the observer is not watching. ``Player.state`` is derived
#: from a precedence hierarchy, so it cannot answer this on its own — a
#: character who is ``awake`` and asleep at once reads as ``awake``. The
#: conditions are the truth. ``sleeping`` is listed alongside the activities
#: because the codebase sets it both ways (``player.state = "sleeping"`` adds
#: the condition), and marking a sleeper's sighting covert is the safe direction.
OFF_WATCH_CONDITIONS = ("dead", "unconscious", "blind", "sleeping")

#: Activities during which a character is present but not watching. Kept tight:
#: someone sitting down is still looking around, someone asleep is not.
OFF_WATCH_ACTIVITIES = frozenset({"sleeping", "bathing"})


class ObservationSignalLog:
    """Tick-stamped, self-pruning store of *who observed whom*.

    Not thread-safe and not serialized — it is per-run derived state, rebuilt by
    the perception pass (see
    :meth:`engine.npc_behaviors.NPCBehaviorSystem.record_observations`).
    """

    def __init__(self, memory_turns: int = DEFAULT_MEMORY_TURNS):
        self.memory_turns = memory_turns
        # target name -> observer name -> observation record
        self._by_target: Dict[str, Dict[str, dict]] = {}

    # ── writing ──

    def record(self, observer_name: str, target_name: str, *, tick: int,
               public: bool, stimulus_type: str = "") -> dict:
        """Record that *observer_name* perceived *target_name* on *tick*.

        Re-recording refreshes the tick rather than adding a second entry, so a
        long scene does not grow one row per turn per pair.
        """
        entry = {
            "observer": str(observer_name),
            "target": str(target_name),
            "tick": int(tick or 0),
            "public": bool(public),
            "stimulus_type": stimulus_type or "",
        }
        self._by_target.setdefault(str(target_name), {})[str(observer_name)] = entry
        self.prune(tick)
        return entry

    def clear(self) -> None:
        self._by_target.clear()

    # ── reading ──

    def observations_of(self, target_name: str, *, tick: int,
                        max_age: Optional[int] = None) -> List[dict]:
        """Every live observation of *target_name*, oldest first.

        Reading never re-runs perception: the roll happened once, at record time.
        """
        return self._live(target_name, tick, max_age)

    def observers_of(self, target_name: str, *, tick: int,
                     public_only: bool = False,
                     max_age: Optional[int] = None) -> List[str]:
        """Names of who has seen *target_name* recently, oldest first."""
        return [o["observer"] for o in self._live(target_name, tick, max_age)
                if not public_only or o["public"]]

    def public_observers_of(self, target_name: str, *, tick: int,
                            max_age: Optional[int] = None) -> List[str]:
        """Observers for whom this was an open, onlooker-visible sighting."""
        return self.observers_of(target_name, tick=tick, public_only=True,
                                 max_age=max_age)

    def was_observed(self, target_name: str, *, tick: int,
                     max_age: Optional[int] = None) -> bool:
        """True when anyone has seen *target_name* inside the window."""
        return bool(self._live(target_name, tick, max_age))

    def was_observed_publicly(self, target_name: str, *, tick: int,
                              max_age: Optional[int] = None) -> bool:
        """True when at least one observer saw this openly rather than covertly."""
        return any(o["public"] for o in self._live(target_name, tick, max_age))

    def observed_by(self, target_name: str, observer_name: str, *, tick: int,
                    max_age: Optional[int] = None) -> Optional[dict]:
        """The record for one observer/target pair, or ``None``."""
        for entry in self._live(target_name, tick, max_age):
            if entry["observer"] == str(observer_name):
                return entry
        return None

    def last_observed_tick(self, target_name: str, *, tick: int,
                           max_age: Optional[int] = None) -> Optional[int]:
        """When *target_name* was last seen by anyone, or ``None``."""
        return max((o["tick"] for o in self._live(target_name, tick, max_age)),
                   default=None)

    # ── housekeeping ──

    def prune(self, tick: int) -> None:
        """Drop observations older than the memory window.

        Called on every write. Reads filter by window without mutating, so a
        scene that stops producing observations ages them out at the next write
        and costs nothing in the meantime. The store is bounded by *pairs* of
        characters, not by turns — see :meth:`record`.
        """
        window = self.memory_turns
        for target, observers in list(self._by_target.items()):
            for observer, entry in list(observers.items()):
                if window is not None and (int(tick or 0) - entry["tick"]) > window:
                    observers.pop(observer, None)
            if not observers:
                self._by_target.pop(target, None)

    def _live(self, target_name: str, tick: int,
              max_age: Optional[int]) -> List[dict]:
        entries = self._by_target.get(str(target_name)) or {}
        if not entries:
            return []
        now = int(tick or 0)
        window = self.memory_turns if max_age is None else max_age
        live = [e for e in entries.values()
                if window is None or (now - e["tick"]) <= window]
        return sorted(live, key=lambda e: (e["tick"], e["observer"]))


#: Process-wide log. The engine is a single world in a single process, and the
#: consumers (task-487) read it as ambient state rather than threading an argument
#: through every call site.
OBSERVATION_SIGNALS = ObservationSignalLog()


def get_observation_signals() -> ObservationSignalLog:
    """The process-wide observation-signal log."""
    return OBSERVATION_SIGNALS


def reset_observation_signals() -> None:
    """Drop every observation. Used when a world is loaded or restarted."""
    OBSERVATION_SIGNALS.clear()
