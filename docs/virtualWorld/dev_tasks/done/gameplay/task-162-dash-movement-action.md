---
id: 162
title: Dash Movement Action
status: done
priority: low
created: 2026-08-02
tags: [gameplay, movement, actions]
---

# Dash Movement Action

## Summary

Add a `dash` action: run into another area and immediately get the option to run again — no inner monologue or other actions allowed between the two moves.

## Problem

Movement is one area per action (engine/movement.py `move_to_area`), and each agent action costs a full turn. There's no way to cover ground quickly, which makes chases and escape attempts tedious.

## Implementation

### Command

- Add a `dash <direction>` command in routes/action.py that calls `move_to_area` twice in a row
- The intermediate step does NOT trigger agent decision/inner monologue — just a compact "You dash through the doorway." line
- Optionally a third+ move requires another dash command (player chooses to keep dashing)
- Apply double (or scaled) energy cost for the dash — ties into task-156 weight/energy

### Agent integration

- Add `dash <direction>` to the allowed actions list in the prompt
- The result reaction should treat the dash as a single turn (no decide phase between moves)

## Files to Modify

1. `routes/action.py` — `dash <direction>` command parsing ✅
2. `engine/movement.py` — `dash_to_area()` (two moves, chained, compact single action) ✅
3. `static/js/agent/prompt-builder.js` — dash added to allowed movement commands ✅

## Testing

- [x] `dash north` moves ONE area (single fast hop)
- [x] Agent immediately gets a second decision step to chain another `go`
- [x] Energy surcharge is applied for the sprint
- [x] Dash blocked by locked/closed doors as normal

**Implemented 2026-08-02 (v1)** — `MovementSystem.dash_to_area(direction)` ran two `move_to_area` hops back-to-back (single action, no decision between), stopped gracefully if the second hop found no exit, and applied an extra energy surcharge. Wired as `dash <direction>` in `routes/action.py` and exposed to agents in the prompt command table.

**Reworked 2026-08-06 (v2, chained sequential `go`s)** — dash is now a single fast hop (`engine/movement.py dash_to_area` = one `move_to_area` + sprint surcharge). The agent engine (`static/js/agent-engine.js`) detects a `dash` action, then runs `_runDashFollowUp`: an immediate second decision via `PromptBuilder.buildDashFollowUpPrompt` (new area context, pick one exit to `go` through or `wait`), validates and executes that move, and appends it to the action result before the reaction phase. The reaction context notes the player just sprinted into a new room. Backend tests in `tests/test_movement.py::TestDash` updated to single-hop expectations (5 tests).

**Status: DONE** — moved to `done/gameplay/`.

## Related

- [[todo/items/task-156-weight-affects-energy-decay|task-156: Weight affects energy decay]]
