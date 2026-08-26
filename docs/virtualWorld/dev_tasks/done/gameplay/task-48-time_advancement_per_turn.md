---
group: Environment & Climate
wiki: "[[Environment/Time & Weather]]"
---

# Time Advancement Per Turn

**Filed**: 2026-07-19
**Priority**: High
**Status**: In Review — implemented (code-verified 2026-08-11). Time advances once per full turn: `advance_clock(1)` inside `tick_turn()` at `engine/tick_manager.py:446`; per-request `_action_time_consumed` flag (`tick_manager.py:59`, reset at `routes/action.py:141`) suppresses per-action advances.

## Summary

Every `POST /api/action` and `GET /api/room/description` advances the clock by 5 minutes (1 tick) by default, even for actions that shouldn't consume meaningful time (speech, examine, etc.). An agent step can advance time by 15–20 minutes when it should only advance by 1 tick when the full turn cycle completes.

## Current State

Time advances in 4 places per agent step:

| Source | File | Line | Advance |
|--------|------|------|---------|
| Observe phase: `ApiClient.getAreaDescription()` → `get_area_description()` calls `apply_action("look")` | `virtual_world_engine.py` | 827 | 5 min |
| Decision speech: `ApiClient.action("speak ...")` — no `apply_action` called → default fallback fires | `app.py` | 505 | 5 min |
| Decision action: `ApiClient.action("examine ...")` — same, no `apply_action` → default fallsback | `app.py` | 505 | 5 min |
| Reaction speech: `ApiClient.action("speak ...")` — same pattern | `app.py` | 505 | 5 min |

The default fallback at `app.py:505` is:
```python
if not getattr(world, '_action_time_consumed', False):
    world.advance_clock(1)
```

This runs for **every** `POST /api/action` that doesn't explicitly set `_action_time_consumed = True` via `apply_action()`. Speech, examine, inventory, and fumble all fall through to this default.

## Desired Behavior

- Actions within a turn happen in a "burst" — time only advances when the full turn cycle completes
- 1 tick (5 min) per turn, not per action
- `tick_turn()` (called at turn change via `/api/turn/apply`) already handles vitals decay — time advance should be coupled with it

## What Needs to Change

### Option A: Remove default advance, add explicit advance only at turn change

Remove `advance_clock(1)` from `app.py:505` and instead call `advance_clock(1)` inside `tick_turn()` or `/api/turn/apply`.

**Risks**: Human players typing commands one-at-a time would never see the clock advance until they click "End Turn" (or equivalent). Currently every `look` or `go` bumps time.

### Option B: Selective default — skip for speech/examine

```python
# In app.py, after the try block:
if cmd.startswith(("speak ", "say ")):
    pass  # speech doesn't consume meaningful time
elif not getattr(world, '_action_time_consumed', False):
    world.advance_clock(1)
```

This is the minimal fix but doesn't address the conceptual issue that examine/take/look shouldn't each consume 5 min when an agent does them back-to-back within one turn.

### Option C: Track per-turn consumed flag

Add a `_turn_time_consumed` flag that prevents the default advance from firing more than once per turn cycle:

```python
# In app.py:
if not getattr(world, '_turn_time_consumed', False) and not getattr(world, '_action_time_consumed', False):
    world.advance_clock(1)
    world._turn_time_consumed = True
# In tick_turn() or at turn boundary:
world._turn_time_consumed = False
```

This way, during a full turn cycle (multiple agent steps), time only advances once. But human players typing one command at a time still see the clock move.

## Edge Cases

| Case | Current | Desired |
|------|---------|---------|
| Agent: observe + speak + act + react-speak | 20 min | 5 min (once per turn) |
| Human: look | 5 min | 5 min (still works) |
| Human: go + look | 10 min | 10 min (still works) |
| Rest command | already consumes its own time via `apply_action` | unchanged |
| Combat: attack several times in one turn | 5 min per attack | 5 min total |

## Files

- `app.py:505` — default `advance_clock(1)`, needs gating or removal
- `virtual_world_engine.py:2911` — `tick_turn()`, candidate for explicit time advance
- `agent-engine.js:254` — `getAreaDescription()` in observe phase (triggers extra `apply_action("look")`)