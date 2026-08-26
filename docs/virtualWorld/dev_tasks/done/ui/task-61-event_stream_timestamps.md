# Event Stream: Show Real Time Instead of Tick

**Status**: Done — verified 2026-08-03. tickToTime (static/js/event-stream.js:97) renders HH:MM from time_per_tick_minutes + clock start, applied to all bubble types.

**Priority**: Medium

## Summary

Event stream currently shows `[T123]` — the raw tick number. Replace this with a human-readable date/time so you can see when each action happened in game-world time rather than an abstract counter.

## Current State

In `event-stream.js`, bubble rendering uses `tick` from world state data:

```js
html += `<span class="bubble-tick">[T${tick}]</span>`;
```

Tick is an incrementing integer (starts at 0). No game-time tracking is displayed.

## Requirements

- Show game date/time instead of `[T123]` in event bubbles
- Format: `[Day X, HH:MM]` or similar readable format
- Calculate from `time_ticks` — each tick = some amount of game time (e.g., 5 minutes, or whatever the action cost represents)
- Fall back to tick if game time can't be computed
- Update all bubble types: action, thought, speech, system, raw LLM

## Backend

- The `/api/state` response may already have a `game_time` field — check `worldState.gameTime`
- If not, add a computed `game_time` string to the state endpoint based on `time_ticks * seconds_per_tick`
- Or compute purely on frontend from `time_ticks`

## Implementation Options

**Option A — Frontend only:**
```js
const SECONDS_PER_TICK = 60; // configurable
function tickToTime(tick) {
    const totalSeconds = tick * SECONDS_PER_TICK;
    const days = Math.floor(totalSeconds / 86400);
    const hours = Math.floor((totalSeconds % 86400) / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    return `Day ${days + 1}, ${String(hours).padStart(2,'0')}:${String(minutes).padStart(2,'0')}`;
}
```

**Option B — Backend computed:**
Add `game_time` to the `/api/state` response using a configurable `seconds_per_tick` in the engine.

## Files Changed

- `static/js/event-stream.js` — replace `[T${tick}]` with time string, add formatting helper
- Optional: `virtual_world_engine.py` or `app.py` — add `game_time` to API response
