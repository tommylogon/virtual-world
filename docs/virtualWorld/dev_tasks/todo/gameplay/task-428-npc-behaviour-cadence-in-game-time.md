---
type: task
status: todo
area: gameplay
priority: low
---

# task-428: `npc_behaviors` cadence in game time (the last tick-quantised scheduler)

**Filed:** 2026-09-21  
**Relates:** task-389/390 (the newer behaviour phases), task-406 (standing-item
tick), `engine/npc_behaviors.py`.

## Problem

Everything else that measures time now scales with `time_per_tick_minutes`:
vital decay, condition durations and periodics, body-temperature drift, starvation
grace, background decision cadence (action credit), and plant growth
(`adjust_parameter` with `per: "minute"`).

Two schedulers in `engine/npc_behaviors.py` still don't:

```python
interval = behavior.get("interval", 1) or 1
if interval > 1 and self.gs.time_ticks % interval != 0:   # :70
    continue
...
interval = getattr(player, 'npc_action_interval', 3) or 3
if self.gs.time_ticks % interval != 0:                    # :90
    continue
```

`interval` is a count of **ticks**, so at 15 min/tick a behaviour authored as
"every 5 ticks" fires every 75 game minutes, and a legacy `wander` NPC moves
every 45 minutes instead of every 3.

It is inert in the goblin camp (`process_simple_npcs` skips anyone without
`simple_npc`, and the camp's characters are `simple_npc: false`), which is why it
has not surfaced — but it is a live divergence for any `simple_npc` character or
authored `behaviors[]` patrol.

## Design

Express both intervals in **game minutes** and convert at evaluation:
`due every max(1, round(interval_minutes / minutes_per_tick))` ticks, or reuse the
same action-credit idea as `background_simulation` if a behaviour should be able
to fire more than once in a long tick.

Keep the authored field's meaning documented either way — a data value whose unit
silently depends on a config setting is exactly the bug this task exists to
remove.

## Acceptance

- A behaviour authored as "every 10 minutes" fires every 10 game minutes at 1, 5
  and 15 min/tick.
- Legacy `wander` moves at the same rate per game hour at any tick length.
- No change at 1 min/tick (the authored values are unchanged in meaning there).
- `simple_npc` characters still defer to sleeping/busy states as today.

## Non-goals

- The newer behaviour phases (task-389/390).
- Deciding whether the legacy `npc_behavior` wander path should be retired —
  untested in practice, so it stays until someone exercises or removes it
  deliberately.
