---
type: task
status: todo
area: ui
priority: high
---

# task-776: WorldPainter polish and performance: soft render, Konva/offscreen paint, palette side-dock, and the cheap workflow wins

**Filed:** 2026-10-11
**Related:** task-597, task-774, bug-545, task-536, task-540

## What

A bundle of independent, grounded WorldPainter improvements: the render /
performance rework and the layout / workflow wins visible in the current editor.
Every item is small and independently shippable, so any can land alone. Sourced
from a multi-model review and **filtered to what is grounded in `editor.ts` and
the repo** — see the rejected list below.

May be split into sub-tasks when picked up; one umbrella keeps the inventory in
one place.

## Why

The editor is "a form wrapped around a canvas": every action rebuilds the whole
panel (`render()` → `_renderShell()`), the palette hides the map, and feedback
lands off-screen. The performance half is the same latency as **bug-545** from
the client side; the layout half is the single most visible UX complaint.

## How — workstreams

**A. Performance (highest value)**

- **Soft render.** Split `render()` so a status change, a paint commit, a nudge
  or a name change refreshes only the Konva layers + estimate + status + open
  inspector; reserve the full shell rebuild for payload-shape changes (scope
  load, resize, generate). This also removes the scroll-jump / lost-focus that
  the rAF scroll-capture band-aids. (The backend half of the same latency is
  bug-545.)
- **Keep the Konva stage mounted.** Per-layer shapes already exist
  (`bgShape`/`paintShape`/…, `editor.ts:2190-2196`); stop recreating the stage
  and shapes per render — rebuild only the paint layer's children.
- **Offscreen paint cache.** Render the paint layer to a 1px/cell offscreen
  canvas; write only changed pixels on a paint edit; in `sceneFunc`,
  `drawImage` it scaled with `imageSmoothingEnabled = false`. Zoom / pan / alpha
  become O(1) composites, and the reference image stops being re-rasterised.
- **rAF-throttle pointermove** (brush hover, marquee, grid-drag) to one tick.
- **Memoize `paletteSections` / `_layerOptions`** per `(layer, vocab)`.

**B. Layout**

- **Palette as a side dock** (right column with its own scroll) instead of a
  full-width block above the canvas. Reconcile with **task-759** (tile grid
  shipped) and **task-774** (filter filed) — one palette, not a third.
- **Toolbar wrap** — a two-row grid with the Generate cluster pinned
  never-scrolling; stop the value-detail sentence truncating.
- **Painted-cell readability** — outline the tile and drop the gaps so biomes
  read as regions, not confetti (keep the per-cell model; run-merging optional).

**C. Workflow (cheap wins)**

- **Actionable checklist** — `_checklistSteps` already returns `{title, how,
  done}` carrying tool/layer/value; wire each undone row to arm the tool.
- **Recents row** — pinned last ~6–8 `(layer, value)` from
  `state.strokeLayer` / `strokeValue`.
- **Per-scope UI persistence** — tool / layer / value / zoom / palette-open in
  `localStorage` keyed by scope id.
- **Fixed status bar** — move `_status` out of the scroll box so feedback is
  visible.
- **Drag-to-move placements** — click = select, drag = move, unplace only from
  the inspector (a misclick currently costs a confirm dialog).
- **Selection action bar** — surface what `state.selection` can do.

## Out of scope / rejected (recorded so they are not re-proposed)

- **Client-side undo stack** — the server undo stack (task-371, `/api/undo`) is
  the one source of truth; add a visible affordance, never a second stack.
- **Command palette Ctrl+K** — task-370, done.
- **Palette tile grid + category rail + detail panel** — task-759, done.
- **Design-token / stylesheet rewrite, SVG icon family replacing emoji,
  minimap, dockable hierarchy tree, contextual tool-settings bar, rulers** —
  taste / feature-adds, not defects; file separately if wanted.

## Steps to verify

1. Change a status line or commit a stroke.
   - expected: no full shell rebuild; measure input→paint latency (with bug-545).
   - observed: TODO
2. Open the palette.
   - expected: the canvas keeps its size; the map is not pushed down.
   - observed: TODO
3. Click a checklist row.
   - expected: it arms the right tool / layer / value.
   - observed: TODO
4. Reopen a scope after a refresh.
   - expected: tool / layer / zoom / palette state restored.
   - observed: TODO

## Acceptance

- [ ] Status / paint / select updates no longer rebuild the whole shell; the Konva stage is not recreated on paint.
- [ ] Paint renders from an offscreen cache; zoom / pan is O(1).
- [ ] The palette docks beside the canvas (one palette, reconciled with 759 / 774).
- [ ] The checklist arms the tool from its rows.
- [ ] Recents + per-scope UI persistence + a fixed status bar are in.
- [ ] No client-side undo stack and no command palette (both already exist).

## Files

- `static/js/worldpainter/editor.ts`
- `static/js/worldpainter/grid-model.ts` — memo helpers
- `tools/unit/test_worldpainter.js`
- a scoped CSS block for the painter
