---
type: bug
status: review
area: graph
priority: high
---

# bug-542: Graph Physics button never reflects the node-layout lock, so a locked world reads as a dead toggle

**Filed:** 2026-10-10
**Related:** task-765 (the GraphPhysics policy), bug-538

## What

With the node-layout lock on (the scenario's background block carries
`layoutLocked: true`), the ⏸/▶ Physics toolbar button stays enabled, keeps the
`⏸ Physics` glyph and the "Pause the simulation…" tooltip, and flips
`graphManager._physicsEnabled` on click — but the solver never runs, so items and
characters never settle into their areas. The button promises a resume the
solver refuses, and gives no reason.

## Why

Two flags were meant to be the same input and were not:

- `GraphPhysics.shouldRun()` gates on `locked`, which is fed by
  `GraphBackground` → `GraphPhysics.setLocked(state.layoutLocked)`. This is the
  flag the solver actually reads.
- `GraphToolbar.state()` instead read `gm._mapLayoutLocked`, a graph-manager
  field that is **never assigned anywhere** (grep: one read, zero writes; the
  live instance has no such own property). So `physicsAvailability`'s `mapLocked`
  branch was dead code and the button never disabled for the lock.

Before the task-765 refactor (`95497e40^`) the toggle called
`applyModePhysics(_physicsEnabled)` and wrote `physics:{enabled:true}` directly,
overriding the lock's disable — so clicking could force the solver on despite the
lock. After the refactor, `GraphPhysics.apply()` runs
`shouldRun(readState())` and the `locked` gate wins, so the toggle can no longer
override the lock, and with no button feedback the world looks broken rather than
locked.

A second gap: `GraphPhysics.setLocked()` (unlike `setUserEnabled()`) did not
refresh the toolbar, and the lock is fed during load — after the toolbar's
initial paint — so even a correct `mapLocked` signal would not have repainted the
button.

## How

1. `static/js/graph/toolbar.ts` — `state().mapLocked` now reads the single source
   the solver reads, `window.GraphPhysics._locked` (the lock holds positions in
   every layout, so the `layout === 'map'` qualifier was also dropped).
2. `static/js/graph/physics.ts` — `setLocked()` now calls
   `GraphToolbar.syncAll()` after `apply()`, so a lock change repaints the
   affordance exactly as the user's own toggle does.

## Steps to verify

1. Open the world with `layoutLocked: true` (kraktooth_goblin_camp) and read the
   button.
   - expected: `#btn-physics` disabled, title "The node layout is locked — unlock
     it (🔒 in the background menu) to simulate."
   - observed: button enabled, `⏸ Physics`, title "Pause the simulation and freeze
     every node where it is" (`mapLocked: false`).
2. Release the lock and watch the canvas.
   - expected: solver runs; items/characters move toward their areas.
   - observed: `setLocked(false)` → `shouldRun` true, `physicsEnabled` true;
     121 of 142 nodes moved over 2.5 s (max 6327 px); re-lock → solver off,
     button disabled again.

## Acceptance

- [ ] With the lock on, the Physics button is disabled and explains the lock.
- [ ] With the lock off, toggling physics starts/stops the solver.
- [ ] `node tools/unit/run.cjs` passes; `python tools/ts_convert.py check` is green.

## Files

- `static/js/graph/toolbar.ts` — `state().mapLocked` reads `GraphPhysics._locked`
- `static/js/graph/physics.ts` — `setLocked()` refreshes the toolbar
- `static/js/graph/toolbar.js`, `static/js/graph/physics.js` — emitted
