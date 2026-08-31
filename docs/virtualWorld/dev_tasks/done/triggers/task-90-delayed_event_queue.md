---
group: Agent AI & Behavior
wiki: "[[AI & Narration/Agent Engine]]"
---
# Delayed Event Queue — Schedule Trigger Effects N Ticks Later

**Filed**: 2026-07-21
**Priority**: Medium
**Status**: Done — implemented 2026-08-16. `engine/event_queue.py` (`DelayedEventQueue`); `schedule_trigger` effect handler (`engine/effects.py:handle_schedule_trigger`); `on_delayed` trigger type + `schedule_trigger` effect type in engine and frontend (`trigger-system.py`, `trigger-types.js`) with editor param fields; processing in `TickManager.tick_turn()` after clock advance; serialized via `to_dict()`/`load_from_dict()` (stripped from `to_scenario_dict()`). Tests: `tests/test_delayed_events.py` (8 passed); full suite 959 passed. Moved to review/.

---

## Summary

Add the ability to schedule a trigger effect to fire N ticks in the future. This is the single biggest missing causality mechanism — it enables curses, poisons, timed puzzles, summoned creature durations, and any "X happens Y turns from now" scenario. Currently every effect is immediate; the world can't remember to do something later.

## Why the Engine Must Do It

The LLM handles character minds — but it cannot reliably fire an effect 5 turns later across context windows and turns. Only the engine can guarantee delayed causality. This is world-physics, not narrative.

## Design

### Data model

A queue on the engine:

```python
self.delayed_events = []  # list of {fire_tick, trigger_source, params, label}
```

Each entry:
- `fire_tick` — absolute `time_ticks` value when this fires
- `target_node_id` — the item/node to fire triggers on  
- `trigger_type` — e.g. `"on_delayed"` (a new trigger type added to TRIGGER_TYPES)
- `label` — human-readable summary shown in event logs

### Processing

In `tick_turn()`, after existing per-tick processing:

```python
due = [e for e in self.delayed_events if e.fire_tick <= self.time_ticks]
self.delayed_events = [e for e in self.delayed_events if e.fire_tick > self.time_ticks]
for event in due:
    node = self.graph.get_node(event.target_node_id)
    if node:
        outputs = self._execute_triggers(node, event.trigger_type)
        self.record_turn_event('__system__', 'delayed', event.label)
```

### New trigger effect: `schedule_trigger`

Params:
- `delay_ticks` — int, ticks from now to wait
- `target` — item/node name or ID (defaults to the current trigger's parent item)

Usage in trigger JSON:

```json
{
  "trigger_type": "on_take",
  "effects": [{"type": "schedule_trigger", "params": {"delay_ticks": 5, "target": "cursed_ring"}}]
}
```

The target item then needs a corresponding trigger:

```json
{
  "trigger_type": "on_delayed",
  "effects": [
    {"type": "message", "params": {"message": "The cursed ring pulses with dark energy!"}},
    {"type": "damage", "params": {"amount": 5}}
  ]
}
```

This separation keeps `schedule_trigger` as pure scheduling — it just queues a trigger fire. What actually happens is defined by the target item's `on_delayed` trigger, reusing all existing effect types.

### New TRIGGER_TYPE: `on_delayed`

Added to `TRIGGER_TYPES` in `virtual_world_engine.py`. Fired by the delayed event queue. Any item can have `on_delayed` triggers.

### Serialization

Add `delayed_events` to `to_dict()` and `load_from_dict()` so scheduled events survive save/load.

## Use Cases This Enables

| Scenario | How |
|----------|-----|
| Cursed item | Pick up → 5 ticks later → take damage + message |
| Poisoned food | Eat → 3 ticks later → `sick` (or `poisoned`) instance with `source: <food>` and a `periodic` override — see the condition reference examples in [[review/characters/task-trait-condition-system-v2\|task: Trait & Condition System v2]] |
| Timed door | Pull lever → 10 ticks later → door slams shut |
| Summon duration | Summon creature → 20 ticks later → creature vanishes |
| Time bomb | Activate → 8 ticks later → explosion (area damage + environment change) |
| Ritual completion | Place 3 items on altar → after all placed, 2 ticks → ritual fires |
| Patrol timing | NPC reaches checkpoint → 15 ticks later → next patrol cycle |

## Files Affected

- `virtual_world_engine.py` — `delayed_events` queue, processing in `tick_turn()`, `schedule_trigger` effect handler, `on_delayed` in TRIGGER_TYPES, serialization
- `static/js/item-library.js` — show `schedule_trigger` in effect type list if needed

## Not In Scope

- Visual countdown UI (could be added later)
- Recurring/delayed intervals (use existing `on_tick` for that)
- Cancel/remove scheduled event (can be added later)

**Deferred**: Post-merge feature branch. This branch is refactoring/testing only.


## Refactoring Impact (July 2026)

TickManager (engine/tick_manager.py) processes per-tick logic. Create engine/event_queue.py — delayed event queue. Wire into TickManager.tick_turn(). Event data: {tick_trigger, effect_type, effect_params, target_node_id}. Follow existing trigger effect patterns from engine/effects.py.
