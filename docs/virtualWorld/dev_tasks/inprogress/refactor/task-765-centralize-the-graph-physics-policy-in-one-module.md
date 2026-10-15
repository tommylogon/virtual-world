---
type: task
status: inprogress
area: refactor
priority: high
---

# task-765: Centralize the graph physics policy in one module

**Filed:** 2026-10-10
**Related:** 

## What

Physics enable/disable is written from graph-manager, network-manager (applyModePhysics plus scattered setOptions), graph-background (lock), layout-engine (cardinal) and focus (search). Replace the scattered writers with a single physics policy function (global lock, mode, per-node pin, painted) that every call site reads, so lock, map, per-node and search cannot fight each other.

## Why

"Should the solver run?" was decided in five files from six inputs, written into
one shared boolean by nine call sites, and pushed to vis through fourteen calls
plus two bypasses (a hardcoded block in `layout-engine.ts`, a bare `setOptions`
in `graph-background.ts`). Two toggles existed — the button's, which saved, and
`GraphNetwork.togglePhysics`, which did not — and the preference persisted to two
stores (on/off to the server, solver/limit to localStorage). That is why a saved
"physics off" was ignored on reload (it was read *after* the first load), why
bug-534's re-enable had no owner, and why Map kept its own physics config.

## How

One module owns it: `static/js/graph/physics.ts` (`window.GraphPhysics`).

- `readState()` snapshots the inputs from their single writers (graphManager's
  `_physicsEnabled`/`activeLayout`/`_viewMode`, the node-count valve, and this
  module's own lock/pause flags).
- `shouldRun(state)` is the ONE pure decision; `reason(state)`/`availability()`
  explain it for the toolbar.
- `nodePinned(node)` is the per-node level of the same decision.
- `apply()` is the ONE writer to `network.setOptions({physics})` + start.
- `applyModePhysics(enabled)` is a shim: false → `pause()`, true → `resume()`.
- The lock is fed in via `setLocked()`; a reload reads `graph.physics_enabled`
  before the first load (`graph-manager.init`), so the toggle is honoured.

## Progress (2026-10-10)

Landed (gates green — build:ts, typecheck, lint, module:check, unit 661/0):

- New `static/js/graph/physics.ts` + `tools/unit/test_graph_physics.js` (15
  tests), with the script tag in `templates/index.html`, the load line in
  `tools/unit/run.cjs`, and `GraphPhysics` declared in `globals.d.ts` and
  `eslint.config.js`.
- `applyModePhysics` delegates to the policy; `buildOptions` and
  `applyGraphSettings` read `GraphPhysics.shouldRun()` (kills the `= !levelsOn`
  stomp); `loadGraphData` pauses/resumes through the policy (no hardcoded
  `_physicsEnabled = true`); `graph-manager.togglePhysics` → `toggleUserEnabled`;
  the view-switch/overlay calls go through `apply()`; the graph-background lock
  feeds `setLocked()`; `layout-engine`/`focus` route through `pause()`/`apply()`.
- `graph-manager.init` reads the engine config before `GraphNetwork.init()`.

Deferred (still open):

- `layout-engine.ts` `_applyGridLayout` keeps its own hardcoded barnesHut physics
  block (the map-settling params) — route it through `GraphPhysics` too, so the
  option params are one set as well as the decision.
- One persistence store for the whole policy (on/off → server; solver/limit →
  localStorage).
- Live verification.

## Browser UI and intended live verification

Intended UI home: Graph editor toolbar → Physics toggle and graph layout/settings controls.

Current availability: The centralized policy and toolbar wiring are in place; first-load live behavior and the deferred map-settling option remain open.

Live steps when available:

1. Turn Physics off, hard-refresh, and inspect button state and graph motion.
   - expected: The saved preference is honored on first load and the button matches actual solver state.

2. Switch layouts, pin a node, and change overlays while observing Physics.
   - expected: All controls agree with one physics policy; pin/overlay changes do not unexpectedly restart physics.

This section defines the intended access point and acceptance path. It is not a claim that the UI or complete behavior exists or works today; Current availability records the present state, and these steps describe how to verify the intended behavior when it is available.
## Steps to verify

1. Hard-refresh; toggle the toolbar Physics button off, hard-refresh again —
   physics must come up OFF and the button unpressed.
   - expected: the saved preference is honoured on the first load.
   - observed: wiring in place (init reads config before load); not driven live.
2. Graph / Map / Hierarchical, Lock nodes, an overlay, and a search — the solver
   state must match `GraphPhysics.availability()`, no writer fighting another.
   - expected: one decision, one writer.
   - observed: routed; live pass pending.
3. `node tools/unit/run.cjs` — the policy tests pass.
   - expected: `test_graph_physics.js` green.
   - observed: green (661 passed, 0 failed).

## Acceptance

- [x] Every `physics.enabled` write goes through one function.
- [x] Lock, mode, per-node pin and overlay cannot disagree (one `shouldRun`).
- [ ] The map-settling option block is folded in (deferred).
- [ ] Verified live on a running server (deferred — this 2763-node world blocks
      browser eval for ~1 min, so the live probe timed out).

## Files

- `static/js/graph/physics.ts` (new — the policy; emitted `physics.js`)
- `tools/unit/test_graph_physics.js` (new)
- `static/js/graph/network-manager.ts` (`applyModePhysics`, `buildOptions`,
  `applyGraphSettings`, `loadGraphData`, `applyOverlay`, `_clearOverlay`,
  `isNodePinned`, `togglePhysics`)
- `static/js/graph-manager.ts` (`init`, `_applyEngineConfigDefaults`,
  `togglePhysics`, `setViewMode`)
- `static/js/graph/graph-background.ts` (`_applyLockState`)
- `static/js/graph/layout-engine.ts` (deferred block still here),
  `static/js/graph/focus.ts`
- `static/js/types/globals.d.ts`, `eslint.config.js`, `templates/index.html`,
  `tools/unit/run.cjs`

