---
group: Graph & Area UX
wiki: "[[Rules Engine/Triggers & Effects]]"
---
# Task 101: Simultaneous Turns Per Area (Parallel Processing with Sync)

**Status**: todo
**Priority**: Low
**Filed**: 2026-07-24

## Summary

Currently all characters are processed sequentially in a global initiative order. This task changes the game loop to process areas in parallel — all characters in a room act (sequentially within the room), then areas sync before the next tick. If one room finishes before another, it waits. Movement between areas during a tick is handled as a special case.

## What Already Exists

- `TickManager.tick_turn()` processes characters by global initiative order
- `PlayerManager` tracks which players are in which areas
- `process_simple_npcs()` groups NPCs by behavior type
- Turn queue in `TurnQueue` manages initiative order

## The New Flow

```
Tick N:
  Phase 1: Group all characters by room
  Phase 2: For each room (in parallel / concurrent):
    Process characters in that room sequentially
    Handle movement within room
    Collect events
  Phase 3: Sync barrier — wait for all areas
  Phase 4: Resolve cross-room movement
    - Character A moved from Area 1 to Area 2
    - Area 2 characters can *react* to A's arrival
    - Character A does NOT get a new action in Area 2
  Phase 5: Apply tick-level effects (vital decay, conditions)
  Phase 6: Next tick
```

### Key Rules

- All areas process the same tick at the same "time"
- Within a room, characters act in initiative order (sequentially)
- If Area A finishes before Area B, Area A waits at the sync barrier
- If Character C moves from Area B to Area A:
  - C finishes their action in Area B
  - After sync, C is now in Area A
  - Area A characters who haven't acted yet can *react* to C's arrival
  - C does NOT get a new turn in Area A this tick
- Dead/sleeping/unconscious characters are still processed (they just don't act)

## Implementation

### Engine Changes

- New grouping logic in `tick_manager.py` or new `engine/area_tick.py`
- Character actions within a room are sequential (maintains causality)
- Area processing can be parallelized via `concurrent.futures` or async
- Sync barrier implementation (simple counter + event flag)

### Edge Cases

- **Empty areas**: Rooms with no characters are skipped
- **Single-character areas**: Process immediately, wait at barrier
- **All characters in one room**: Falls back to sequential (same as current behavior)
- **All areas empty**: Tick advances without character processing

### Frontend Changes

- Event stream might need room labels ("Kitchen: Traveler looks around")
- Turn order display might need room grouping
- Step button advances one room-tick (all areas, all characters)

## Files Affected

- `engine/tick_manager.py` — restructure tick loop for room-based processing
- `engine/player_manager.py` — add `get_players_by_area()` grouping
- `engine/movement.py` — handle cross-room movement during tick
- `routes/action.py` — `/api/turn/apply` may need changes
- `static/js/agent/turn-queue.js` — turn order display

## Tests
- Two areas with characters — both process same tick
- Character moves between areas mid-tick
- Empty areas don't block processing
- All characters in one room = same behavior as before
- Sync barrier works (slow room doesn't lose events)