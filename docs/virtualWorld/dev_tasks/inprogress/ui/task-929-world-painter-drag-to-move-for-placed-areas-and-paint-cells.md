---
type: task
status: inprogress
area: ui
priority: high
wiki: "[[World Building/World Painter]]"
---

# task-929: World Painter: drag-to-move for placed areas and paint cells

**Filed:** 2026-11-05
**Related:** 

## What

Moving placed areas or cells in World Painter is cumbersome. For paint cells: there's a 'move' tool that nudges selected cells one at a time via arrow buttons (up/down/left/right). For placed areas: you must unplace the area (click in area tool) then re-place it at the new cell. There's no drag-to-move for areas, and the move tool only works on paint layers, not placed areas/features.

## Why

User wants to easily reposition placed areas (like rooms in millwood__public_school scope) and painted cells. Current workflow requires multiple clicks and tool switches. The cell panel has a 'Move [area name]' button but it just switches to area tool - you still have to click the new cell.

## How

Two possible improvements:
1. For areas: Add drag-to-move in area tool - click and drag an already-placed area to a new cell (like moving a token).
2. For paint cells: The move tool already exists but only nudges 1 cell at a time via buttons. Could add drag-to-move for selected cells.
3. Consider a unified 'move' tool that works on both selected paint cells AND placed areas/features.

## Browser UI and intended live verification

Intended UI home: World Painter editor (scopes with grid and placed areas)

Current availability: Always

Live steps when available:
1. Open World Painter for millwood__public_school scope
2. Place an area on the grid (area tool)
3. Switch to move tool or stay in area tool
4. Click and drag the placed area to a new cell
5. Release - area moves to new cell in one undo step

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

1. In area tool: click and drag an already-placed area to move it to a new cell (with visual feedback)
2. In move tool: drag selected cells to new position (not just nudge buttons)
3. Both operations are single undo steps
4. Visual preview during drag

## Files

- `static/js/worldpainter/editor.ts`
- `static/js/worldpainter/editor-canvas.ts`
- `static/js/worldpainter/editor-palette.ts`
