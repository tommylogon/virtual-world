---
type: task
status: inprogress
area: graph
priority: high
---

# task-394: graph-search-freeze-and-cluster

**Filed**: 2026-09-07
**Status**: In Progress — freeze + cluster + restore + keep-in-place landed 2026-09-07; manual browser pass pending.

## Source

Conversation 2026-09-07 (graph search UX). When searching (e.g. "food"), matching
nodes stay spread out on the graph even though everything else is hidden, because
hidden nodes **keep their mass in the physics simulation** — they're invisible but
still repel. Expected behavior per user: on search-enter, matches should be
centered in the middle of the viewport.

## Problem

Two distinct bugs:

1. **Hidden nodes still participate in physics.** Search-hiding sets visibility,
   but the hidden nodes' springs/masses keep the matches wedged in place.
2. **No clustering.** Even with ghosts gone, force-directed relaxation from a
   spread-out start is slow and arbitrary — matches need an explicit compact
   layout, not "just fit the view".

## Design

### A. Freeze the hidden set during search
- While `searchQuery` is active, mark non-matching nodes (that are currently
  hidden) with `physics: false` / `mass`-neutral so they stop influencing the
  simulation. Restore their original physics flags when the query clears.
- Matches + their one-hop neighbors (the current visible set) keep physics.

### B. Cluster results on query-enter
- On search activation (after the debounce in `graph/focus.js`), **save** the
  current positions + viewport (same pattern `loadGraphData` already uses —
  `savedPositions` / `savedView`).
- Lay out the visible set compactly around the viewport center:
  - `_fitToSearchMatches()` already exists — keep it for initial framing.
  - Add a short force-directed settle (reuse `_kickClusterPhysics()`) seeded at
    the center so matches gather into a tight cluster rather than spreading.
- On clearing the query: restore `savedPositions` + `savedView` so the world
  snaps back exactly where the user had it.

### C. Keep-in-place toggle
- A small checkbox under the search box: **"Keep in place"**.
  - Default (off): cluster mode above — best for *finding* things.
  - On: freeze hidden nodes from physics but do NOT move the matches (for spatial
    reasoning — "where does food live in this house?").

## Implementation notes

- Files: `static/js/graph/focus.js` (search entry/settle/clear + layout seed),
  `static/js/graph/projector.js` (visible-set computation — the hidden set is
  derivable), `static/js/graph/network-manager.js` (physics toggling per node +
  position save/restore already present in `loadGraphData`; reuse those helpers).
- Save/restore should be scoped per search session (not a global structural
  reload), so a clear always returns the user to the pre-search state.
- Debounce already exists in `filterNodes` — cluster kicks in after it settles.

## Verification

- `node --check` on touched files.
- Manual: mansion → search "food" → food nodes gather near center; hidden nodes
  don't affect placement; Esc/clear → exact prior viewport restored.
- Manual: toggle "Keep in place" → matches stay geographically where they are,
  hidden set still frozen.

- **Keep-in-place**: checkbox `#search-keep-in-place` next to the search box in
  `templates/index.html:201`, persisted via localStorage; toggling ON during an
  active cluster un-clusters (restores layout), toggling OFF re-clusters.

## Files changed

- `static/js/graph/focus.js` — reworked search settle flow:
  - `_parkHiddenSet()`: while a query is active, every node outside the visible
    set gets `physics:false` (excluded from the sim so hidden nodes stop
    repelling the matches); freshly-revealed nodes restore their config physics.
  - `_clusterResults()`: saves `getPositions(visible)` + `getViewPosition`/
    `getScale`, then lays the visible set into a compact grid (≤6 cols, spacing
    scaled by `1/scale`) centered on the viewport via `moveNode`, fits, and runs
    a bounded `stabilize(60)`.
  - `_applyFilter` restore path: clearing the query runs `_unCluster()` (move
    nodes back + `moveTo` saved viewport) and `_restoreParkedPhysics()`.
  - `_fitToSearchMatches()` retained as the keep-in-place path (fit + kick, no
    repositioning). `init()` syncs checkbox + manager flag from localStorage.
- `templates/index.html` — KEEP checkbox next to the graph search input.

## Verification

- `node --check static/js/graph/focus.js` — pass.
- Manual browser pass still TODO: search "food" → matches gather center;
  Esc/clear → exact prior viewport restored; KEEP mode leaves matches
  geographically in place while hidden set stays frozen.