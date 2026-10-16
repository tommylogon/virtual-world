---
type: bug
status: inprogress
area: world
priority: high
---

# bug-545: WorldPainter paint is seconds-per-cell: every single-cell paint serializes the whole world for undo, then rebuilds the full payload

**Filed:** 2026-10-11
**Related:** task-520, task-716

## What

Painting a single cell in WorldPainter takes **several seconds to appear**, and it
gets worse the larger the world (reported live in the kraktooth world scope,
2026-10-11). The single-cell paint path does far more work per cell than setting
one value:

- `static/js/worldpainter/editor.ts:2848` — a one-cell stroke sends
  `POST /api/world/scopes/<id>/grid/paint` (one cell per request), then awaits it
  before `render()` (pessimistic: nothing shows until the response lands).
- `routes/world_grid_ops.py:484` — `handle_paint_cell` calls
  `_snapshot(app, …)` **per cell**.
- `routes/saveload.py:22-33` — `_snapshot(world)` is `world.to_dict()`, i.e. a
  **full serialization of the entire world** (every node, edge, player, memory,
  history), pushed onto the undo stack on every paint.
- `routes/world_grid_ops.py:488` — `_commit` **clears the biomes taxonomy
  cache** on every paint, so the `blockers: world_compile.preflight(...)` in the
  payload rebuild re-reads the taxonomy per paint (see the `_commit` docstring:
  preflight is the expensive part; task-716 was a ~7-minute grid read).
- `routes/world_grid_ops.py:491` — the response then ships the **whole grid
  payload** back (`_grid_payload`), including `layers` copies, `placements`,
  `boundary_ways`, and `_unplaced_areas` (which scans **all** graph nodes).

Mechanism confirmed by reading the path; not yet measured. The `world.to_dict()`
per cell is the prime suspect because it scales with world size, which matches
"worse in a big world".

## Why

It makes painting unusably slow exactly when a world is worth painting (a large
scope). A 20-cell drag is 20 full-world serializations on the single-cell path.
The code already promises "one request, one undo" — that promise is being kept by
serializing the world, not by a cheap delta.

## How

Ranked; confirm dominance with a timing measurement before/after each.

1. **Do not full-snapshot the world per cell.** A grid paint's undo entry should
   be a delta — `{scope_id, cell, layer, previous_value}` — not `world.to_dict()`.
   Same for `paint_batch` (one snapshot per stroke, cheaply). Keep the undo stack
   semantics (task-371); only the *representation* of a paint entry changes.
2. **Stop clearing the biome taxonomy cache on a paint.** A paint changes the
   *grid*, not the biome *record* files. If preflight needs a grid-derived memo,
   that is a different cache from the 106-file record cache — clearing the record
   cache (`world_grid_ops.py:60`) on every paint is almost certainly wrong, and
   it re-heats it on the very next payload build.
3. **Compact ack + optimistic paint.** Return `{ok, version}` instead of the full
   grid manifest, apply the edit to the local layer map and redraw immediately,
   and reconcile only on error/version mismatch. This removes the round-trip and
   the full `render()` from the perceived latency (pairs with the render-split
   work).

## Browser UI and intended live verification

Intended UI home: Build → WorldPainter → paint a cell in a large scope; observe canvas feedback and undo.

Current availability: Single-cell paint latency is measured in seconds; delta-based undo and the cheaper payload path remain open.

Live steps when available:

1. In a scratch copy of the large Kraktooth scope, paint one cell and time until the canvas updates.
   - expected: The cell appears in under one second and only the intended cell changes.

2. Paint a 20-cell stroke and undo it once while measuring the operation.
   - expected: One stroke is one request/undo entry and undo restores all cells without a full-world snapshot per cell.

This section defines the intended access point and acceptance path. It is not a claim that the UI or complete behavior exists or works today; Current availability records the present state, and these steps describe how to verify the intended behavior when it is available.
## Steps to verify

1. Time one single-cell paint in a large scope (kraktooth world).
    - expected: the change appears in well under a second.
    - observed: 2026-10-16 LIVE on :4444 (world scope, 629 areas):
      paint `14 ms` (was `2016 ms` before the autosave skip),
      slim ack confirmed, undo `success`. ~144x end to end.
2. Measure the three costs separately: `world.to_dict()` time, `preflight` time,
   payload build/ship time.
    - expected: the snapshot and/or preflight dominates, not the paint itself.
    - observed: 2026-10-15 — `to_dict 0.20 s` dominated; `preflight`
      `0.02 s` cold / `0.00 s` warm; `_grid_payload` `0.02 s`. 2026-10-16
      live: autosave write `~1.7 s` dominated everything else combined.
      Final ranking: autosave write > undo snapshot > payload ≈ preflight.
3. Push a 20-cell stroke (one `paint_batch`) and compare to 20 single paints.
    - expected: one request, one snapshot, no linear blow-up.
    - observed: 2026-10-15 — one request, one *delta* entry
      (`test_paint_batch_is_one_undo_entry`); 20 singles are 20
      requests by design (each its own cell) but each is now bytes.

## Acceptance

- [x] A single-cell paint no longer serializes the whole world for undo.
  (Delta entries; `test_paint_pushes_a_delta_not_a_snapshot`.)
- [ ] A paint no longer invalidates the biome record cache (or the cache split is made explicit and the per-paint re-read is gone).
  (Measured `0.02 s`: kept deliberately for task-716 correctness —
  the re-read is cheap, not gone. Revisit only with a split cache.)
- [x] One stroke is one undo entry and one request; time-to-appear is sub-second on a large scope.
  (Batch: one delta. Single: `slim=1` ack + optimistic local patch,
  no full `render()`; backend `0.007 s`, live `14 ms` on the world
  scope with slim ack confirmed; live undo `success`.)
- [x] A timing measurement (before/after) is recorded on the card.
  (`to_dict 0.20 s` → delta bytes; paint `~0.25 s` → `0.007 s`
  route-level → `14 ms` live; the live path also caught and fixed
  the autosave write that cost `~1.7 s` per paint.)

## Files

- `routes/world_grid_ops.py` — `handle_paint_cell` / `handle_paint_batch`, `_commit`, `_snapshot`, `_grid_payload`.
- `routes/saveload.py` — `_snapshot` / `_push_undo_snapshot` (the paint delta path).
- `engine/world_compile.py` — `preflight` cost / cache split.
- `static/js/worldpainter/editor.ts` — `_commitStroke` (compact ack + optimistic).
