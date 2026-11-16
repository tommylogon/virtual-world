---
type: bug
status: inprogress
area: ui
priority: high
wiki: "[[World Building/World Painter]]"
---

# bug-571: World Painter: inspect tool left-click does nothing (falls through to paint)

**Filed:** 2026-11-05
**Related:** 

## What

The inspect tool (shortcut I) is defined in TOOLS array but not handled in onCellClick in editor-canvas.ts. Left-click in inspect mode falls through to paintAt() which tries to paint on the cell. Right-click (contextmenu) correctly calls inspectCell().

## Why

User expects inspect tool to show cell details on click, but it paints instead. This is a regression - the tool exists in UI but the click handler is missing.

## How

Add an inspect case in onCellClick (editor-canvas.ts) before the paintAt fallback. The case should call inspectCell(p, x, y) to set state.inspected and trigger softRender which shows the cell panel.

## Browser UI and intended live verification

Intended UI home: World Painter editor (any scope with grid)

Current availability: Always

Live steps when available:
1. Open World Painter for a scope with has_grid=true
2. Select Inspect tool (I key or 🔍 Inspect button)
3. Left-click any cell on the grid
4. Observe: cell panel should open with cell details

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

1. Select inspect tool (I key or toolbar button)
2. Left-click a cell on the grid
3. Cell panel opens showing cell info (biome, road, floor, structure, area, sub-zone, exits, name)
4. Right-click on any tool still works as before

## Files

- `static/js/worldpainter/editor-canvas.ts`
