"""Delayed event queue — schedule trigger fires N ticks in the future.

Task-90: the world must be able to remember to do something later on its own
(curses, poisons, timed doors, summon durations). The LLM handles character
minds, but only the engine can guarantee delayed causality across turns, so
the scheduling lives here as world-physics rather than narrative.

The queue is deliberately dumb: ``schedule()`` just records a fire time and a
target node + trigger type. When the tick fires, whoever owns the queue (the
TickManager) executes the target node's triggers for that trigger type
(``on_delayed`` by default), reusing the normal trigger/effect pipeline.
"""


class DelayedEventQueue:
    """Holds scheduled future trigger fires.

    Each event is a dict::

        {
            "fire_tick": int,        # absolute time_ticks when this fires
            "target_node_id": str,   # node whose triggers will execute
            "trigger_type": str,     # e.g. "on_delayed"
            "label": str,            # human-readable summary for event logs
        }
    """

    def __init__(self, events=None):
        self.events = list(events) if events else []

    # ─────────────────── Scheduling ───────────────────

    def schedule(self, fire_tick, target_node_id, trigger_type="on_delayed", label=""):
        """Queue a trigger fire at *fire_tick* on *target_node_id*."""
        self.events.append({
            "fire_tick": int(fire_tick),
            "target_node_id": target_node_id,
            "trigger_type": trigger_type,
            "label": label or f"{trigger_type} on {target_node_id}",
        })

    def pop_due(self, current_tick):
        """Return and remove all events due at or before *current_tick*."""
        due = []
        remaining = []
        for event in self.events:
            if event["fire_tick"] <= current_tick:
                due.append(event)
            else:
                remaining.append(event)
        self.events = remaining
        return due

    # ─────────────────── Inspection ───────────────────

    def __len__(self):
        return len(self.events)

    def __bool__(self):
        return bool(self.events)

    # ─────────────────── Serialization ───────────────────

    def to_dict(self):
        return [dict(e) for e in self.events]

    @classmethod
    def from_dict(cls, data):
        events = list(data) if isinstance(data, list) else []
        return cls(events)