---
type: task
status: review
area: ui
priority: high
---

# task-465: Turn mode dial: fold Simultaneous into the mode dropdown + add Simultaneous per room

**Filed:** 2026-09-22
**Related:** task-101, task-437

## Goal

Remove the separate Simultaneous Mode toggle and make the turn mode dropdown the single dial (Sequential / Random / Initiative / Simultaneous / Simultaneous per room). Add the frontend per-room variant: rooms resolve independently while characters inside a room act in order. Engine-level intent/effect and the per-room sync barrier stay with task-437/task-101.

## Acceptance

- [x] The separate 🌊 Simultaneous Mode checkbox is gone; `#agent-turn-order`
      is the single turn-mode dial with Sequential / Random / Initiative /
      Simultaneous / Simultaneous per room, always visible (no longer hidden
      under the Turn-Based toggle).
- [x] `config.turnOrder` stores the dial value; `config.simultaneousMode` is a
      derived getter (legacy boolean setting folded in). Picking a simultaneous
      variant forces Turn-Based Mode off; enabling Turn-Based while a
      simultaneous variant is selected switches back to Sequential.
- [x] New pure module `static/js/agent/simultaneous.js` (`VWSimultaneous`):
      mode vocabulary, `cooldownFor`, `groupByRoom`, `roomCooldown`,
      `firstReadyRoom`, `tickCountdowns`.
- [x] `agent-engine.js` `_simultaneousRoomStep`: per-room countdowns; the first
      ready room runs its autonomous, living characters sequentially, then the
      room's cadence (its fastest member's) restarts. `_simultaneousStep` uses
      the shared cooldown helper.
- [x] Help text and the settings sync updated.
- [x] Tests: `tools/unit/test_simultaneous.js` (11 tests); JS unit/lint/typecheck green.

## Not in scope

- The engine-level intent/effect model and the cross-room sync barrier remain
  task-101 / task-437. This is the frontend dial + the per-room experiment.

