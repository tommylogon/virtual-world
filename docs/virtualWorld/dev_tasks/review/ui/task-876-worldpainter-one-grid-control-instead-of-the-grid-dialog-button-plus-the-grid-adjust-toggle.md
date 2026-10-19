---
type: task
status: review
area: ui
priority: medium
wiki: "[[World Building/WorldPainter]]"
---

# task-876: WorldPainter: one grid control instead of the Grid dialog button plus the grid adjust toggle

**Filed:** 2026-10-19
**Related:** task-597, task-717, task-776

<!-- deps:start -->
**Related:** [[task-597-worldpainter-grid-sizing-by-cell-size-not-a-cell-count]], [[task-717-worldpainter-grid-resize-numbered-w-h-fields-are-buried-at-the-modal-bottom-while-the-promoted-adjust-affordance-is-imprecise-drag-handles]], [[task-776-worldpainter-polish-and-performance-soft-render-konva-offscreen-paint-palette-side-dock-and-the-cheap-workflow-wins]]
<!-- deps:end -->

## What

The toolbar carries two adjacent grid buttons: '▦ Grid…' opens a dialog for exact numbers and '✥ grid' toggles on-canvas drag handles. Merge them into one 'Grid' control that offers both.

## Why

Reported by the author as odd, and confirmed in _toolbar (editor.ts lines 1539 and 1542): two buttons appended back to back, one calling _openGridDialog and one toggling state.gridEdit. task-717 and task-597 built both on purpose (exact numbers vs direct manipulation), so this is a presentation merge, not a removal of either mode. A toolbar with 14+ controls pays for every redundant one.

## How

Replace the two buttons with a single 'Grid' button that opens a small popover holding the current size, an 'Exact size...' action that opens the existing dialog, and an 'Adjust on canvas' toggle bound to state.gridEdit. Keep the data-role wp-grid-adjust hook so existing tests and help coach cards still find the toggle. Reuse _openGridDialog unchanged.

## Browser UI and intended live verification

Intended UI home: WorldPainter, top toolbar next to the value picker

Current availability: Both buttons exist today; the merged control is not built.

Live steps when available:
1. Open WorldPainter on a scope with a grid and count the grid buttons in the top toolbar. expected after fix: one.
2. Open it, use Exact size to resize, then toggle Adjust on canvas and drag the E handle. expected: both work.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Follow the intended live path in Browser UI and intended live verification when that surface is available.
   - expected: TODO
   - observed: TODO
2. Record the browser surface and interaction actually used (for example: navigate, click, hover, type, expand, or scroll to the bottom).
   - expected: TODO
   - observed: TODO
3. Run the targeted regression test for the mechanism.
   - expected: TODO
   - observed: TODO

## Acceptance

- [ ] The toolbar shows one grid control where it showed two.
- [ ] Both exact-number resize and on-canvas handle adjust remain reachable from it.
- [ ] Grid adjust mode still shows the green cell-size handle and the E/S/SE frame handles.
- [ ] tools/unit/test_worldpainter.js still passes.

## Files

- `static/js/worldpainter/editor.ts`
- `tools/unit/test_worldpainter.js`
