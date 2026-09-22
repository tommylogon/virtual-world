---
type: task
status: review
area: graph
priority: medium
---

# task-451: Multiple background images per scenario with easy placement and layering

**Filed:** 2026-09-22
**Related:** bug-39 (the fix that had to survive this change), task-408 (scenario naming),
task-357 (structures, which will want to ship reference maps)

## Goal

Let a scenario carry **several** reference images at once - a regional map, a floor plan, a
hand-sketched thumbnail - and make them pleasant to arrange: select one, drag it, scale it,
rotate it, set its order and opacity, hide it, without fighting the graph.

## Implemented (2026-09-22, all four slices)

**Model + storage.** The world block `graph_background` is now
`{ layers: [{id, label, image, rect, rotation, crop, opacity, locked, visible}], positions,
layoutLocked }`. Array order is z-order. Images stay files under
`static/images/backgrounds/` referenced by path; only a failed upload falls back to a data
URL. A legacy single-image block migrates on read, with its `locked` becoming
`layoutLocked` (the node-layout freeze) because that was what it always meant.
`routes/graph_ops.py` accepts the list form and replaces the block; the old partial-merge
form is kept for compatibility.

**Architecture fix that made moving possible at all.** The images paint in a layer that is
the container's first child, beneath the transparent vis canvas - and the canvas owns pointer
events, so **nothing inside the paint layer can ever be clicked**. The previous build put its
handles and its drag target in there, which is why maps could not be dragged. Now the paint
layer is purely visual and an above-canvas interact layer carries one hit box per visible
layer plus the active layer's handles.

**Interaction.** Click a map to select it (topmost wins), drag to move, alt-click to cycle
down through overlapping layers, corner handles to scale (shift keeps the aspect ratio), the
purple dot to rotate (shift snaps to 15°), amber inner handles to crop, arrow keys to nudge
(shift = 10 units). Snapping pulls edges and centres onto the other layers and the node
bounds; alt/shift during a move bypasses it. Handles are counter-scaled to a constant
on-screen size (verified 10px and 14px at scale 0.112), so they stay usable zoomed out.

**Layer panel** (top right, while editing): select, visibility, lock, rename, send
back/bring forward, remove, remove all, add. Rows are drag-reorderable, and reordering is
applied on **drop** rather than live, because the panel is rewritten by `_render()`.

**Persistence.** World first, IndexedDB (`graph_assets`, keyed by scenario name) as
fallback, and an empty layer list clears the screen - bug-39's contract, now enforced for the
list form as well.

### Two bugs found and fixed while building this

1. Hit boxes were created but never given geometry (`_placeBox` was called only for the paint
   frame), so in the real UI they were zero-size and unclickable. The synthetic-event tests
   passed anyway, which is exactly why the geometry was checked against the frames
   afterwards (now 45x34 matching, offset 0,0).
2. Alt-click cycling used `network.DOMtoCanvas`, which does **not** invert the transform used
   to place the layers - it put the cursor ~2,500 graph units from the map under it. Replaced
   with `_clientToGraph()`, derived from the same transform `_syncView` applies.

## Acceptance

- [x] Several images in one scenario, each with its own transform, opacity, crop, order,
      visibility and label (verified: two layers restored with per-layer opacity 0.5/0.2,
      order and visibility intact).
- [x] Layer panel with select / reorder / visibility / rename / remove, handles only on the
      selected layer (verified live; opacity for the active layer is the 🎚 slider in the
      on-canvas hint rather than a panel slider).
- [x] On-canvas per-layer handles, unchanged feel from the single-image version (rotated to
      135°, resized, cropped to w=0.05 in the harness).
- [x] Selection with overlapping images, plus alt-click cycling (`l-over → l-under → l-over`).
- [x] Snapping to layers and node bounds (a layer 5 units off a node bound snapped exactly).
- [x] Images remain files on disk referenced by path.
- [x] World-first persistence with the per-scenario cache as fallback, and an empty list
      clearing the screen.
- [x] Migration from the legacy block without a visible jump (the live kraktooth block loaded
      as one layer).
- [x] A locked layer is selectable but not draggable, and shows no handles.
- [x] Backend contract tested: `tests/test_graph_background_layers.py` (5 tests) covers the
      list form, the empty list, malformed input, and the legacy merge.
- [x] Format and UX documented in the vault (`World Building/Graph System.md`).
- [x] JS unit coverage: `tools/unit/test_graph_background.js` (9 tests) covers the legacy
      migration, the bug-39 emptiness predicate, hit sorting, rotation-aware hit testing,
      snapping and the screen→graph conversion. The runner (`tools/unit/run.cjs`) existed but was
      wired to neither npm nor `AGENTS.md`, which is how two `test_describe_vital.js` expectations
      rotted for two weeks - both are now wired (`npm run unit`), documented, and green.
- [ ] **One-undo-step granularity is per settled change**, because the debounced save posts
      the whole block once. Node-layout saving still uses the batched endpoint.

## Converted to TypeScript

`static/js/graph/graph-background.ts` is now the source; `graph-background.js` is **generated**
by `npm run build:ts` and must not be hand-edited. `ApiClient` and `appEvents` were typed into
`static/js/types/globals.d.ts` for it. The unit runner loads the emitted `.js`, so the two tracks
stay compatible. See `docs/design/typescript-migration.md`.

## Notes and open questions

- **Restart required**: the new block shape needs the updated `handle_save_background` in
  `routes/graph_ops.py`; until the app is restarted, background saves take the legacy merge
  path and only the client copy holds the extra layers.
- `positions` still lives on the background block although it is not per-image. Splitting it
  into a scenario-level `graph_layout` would simplify the model and the migration.
- A layer cannot yet point at a **library asset** (reusable across scenarios) rather than a
  per-scenario uploaded file.
- Per-layer opacity is only reachable for the *active* layer (the hint slider); a slider per
  panel row would be a better fit for arranging several maps.
- The interact layer clips to the graph container (`overflow: hidden`) so a stray hit box
  cannot cover the inspector, which means handles very close to the container edge are
  clipped. Panning before editing an edge case handles it.
