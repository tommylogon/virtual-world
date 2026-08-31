---
group: Agent AI & Behavior
wiki: "[[Characters/NPC Behavior System]]"
---

# NPC Behaviors: Add "go" Command

**Filed**: 2026-07-15
**Priority**: Medium
**Status**: Done — `go` implemented with pathfinding in task-8 (2026-08-13). Behavior `go` uses `move_to_area()`; use `teleport` for instant relocation. `go` action type in `engine/trigger_system.py:1297` (`_execute_behavior_actions`), behavior editor entry with Target Area param in `static/js/inspector/behaviors-view.js:23/186/540`.

---

## Summary

NPC behaviors support conditional actions triggered by events, but there is no "go" (move to room) action type. Simple NPCs can trigger messages, damage, etc., but cannot autonomously navigate between areas.

## Current State

In `inspector.js:_showAgent()` (line 223-246), NPC behaviors are displayed with their triggers, conditions, and actions. The action types available for behaviors are the same as item actions (examine, take, use, etc.) — there's no movement action.

The behavior engine (in `virtual_world_engine.py`) processes NPC behavior actions but doesn't support a `go` / `move` / `go_to` action type that would move the NPC to a different room.

## Required Changes

### Backend (`virtual_world_engine.py`)

Add support for a `go` (or `move`) action type in the NPC behavior system. When triggered:
1. Parse the target room name from the action parameters
2. Move the NPC to the target room
3. Return a result message

The behavior action processing should handle:
```json
{ "type": "go", "params": { "room": "Kitchen" } }
```

### Frontend (`inspector.js` / behavior editor)

Add `go` to the available actions list when editing NPC behaviors. The behavior editor (in the agent inspector) needs a way to specify the target room.

## Issues to Consider

- What happens if the target room doesn't exist? Graceful error / no-op.
- Should there be conditional pathfinding (e.g., "go to room X only if door is open")? Out of scope for now.

## Audit

**Status**: Ready to test
**How to test**:
- Open the inspector for an NPC with behaviors. Add a behavior action — verify "go" is available as an action type with a "Target Area" text field.
- Set up a trigger (e.g. `on_tick`) with action type `go` targeting a room name. Advance time/steps. Verify the NPC moves to the target room.

## Files Affected

- `virtual_world_engine.py` — add `go` action handling in behavior processing
- `static/js/inspector.js` — add `go` action option in behavior editor