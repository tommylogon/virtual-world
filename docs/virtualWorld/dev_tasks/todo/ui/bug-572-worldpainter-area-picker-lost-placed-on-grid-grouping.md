---
type: bug
status: todo
area: ui
priority: medium
wiki: "[[World Building/World Painter & Scope Editor]]"
related: [task-541]
---

# bug-572: WorldPainter area picker lost placed on grid and not placed grouping

**Filed:** 2026-11-09
**Related:** task-541

<!-- deps:start -->
**Related:** [[task-541-worldpainter-area-picker-show-what-is-placed-here-and-what-belongs-to-this-scope-only]]
<!-- deps:end -->

## What

When placing areas on a grid in WorldPainter, the area selector dropdown (`data-role="wp-area"`) renders a single flat list of area names. It has lost the visual and structural distinction between areas that are already "placed on grid" vs "not placed" (or belonging to another scope).

In `static/js/worldpainter/grid-model.ts`, `areaGroups(payload, selectedId)` correctly segments candidate areas into up to three groups:
1. `On this grid (${onGrid.length})` - areas already parked on the active grid with coordinates `placedHere: { x, y }`.
2. `This scope, not placed (${mine.length})` - areas belonging to the scope that have not yet been placed on a cell.
3. `Elsewhere in the world` - areas belonging to other scopes.

However, `static/js/worldpainter/editor-palette.ts: _areaBar()` calls `ctx.GM().placeableAreas(p)`, which flattens all groups into a single array with `.reduce()`, discarding the groups. Furthermore, `editor-palette.ts` checks `${a.name}${a.placed ? ' (placed)' : ''}`, but the property in `grid-model.ts` is `a.placedHere`, not `a.placed` (which is `undefined`). As a result, the `<select>` element renders no `<optgroup>`s and no placed indicators, leaving the author unable to tell at a glance which areas are already placed on the grid.

## Why

An author mapping out a scenario (such as The Valerious Case outdoor map or Millwood High) needs to see which rooms/areas are already placed on the map and which remaining rooms still need cell placement. A flat list creates authoring friction, duplicate placements, or accidental moving of already-positioned areas.

## How

1. In `static/js/worldpainter/editor-palette.ts` (`_areaBar`):
   - Call `ctx.GM().areaGroups(p, ctx.state.selectedArea)` instead of discarding structure with `placeableAreas(p)`.
   - Render `<optgroup>` elements for each group (`On this grid`, `This scope, not placed`, and `Elsewhere in the world`).
   - For placed areas, render the cell coordinates or `(on (${a.x},${a.y}))` / `(placed)` in the option label.
2. Recompile TypeScript: `python tools/ts_convert.py build`.

## Browser UI and intended live verification

Intended UI home: WorldPainter editor toolbar -> Area dropdown (`[data-role="wp-area"]`).

Current availability: Present and reproducible in WorldPainter on `localhost:4444` (verified on The Valerious Case and Millwood scenarios). The dropdown currently renders a single flat list without optgroups or placed tags.

Live steps when available:
1. Open WorldPainter for a scenario with multiple areas (e.g. `valerious_case` outdoor map or `millwood_high_1f`).
   - expected: WorldPainter canvas and top toolbar load with reference image and grid.
2. Click the Area dropdown (`data-role="wp-area"`).
   - expected: The dropdown displays distinct `<optgroup>` sections: "On this grid", "This scope, not placed", and "Elsewhere in the world".
3. Inspect the options under "On this grid".
   - expected: Each already-placed area clearly indicates its placed status or cell coordinates (e.g. `Frozen Stream Crossing (44,14)` or `(placed)`).
4. Inspect the options under "This scope, not placed".
   - expected: Unplaced areas are grouped together so the author can immediately pick the next room to place.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Open WorldPainter on a scenario with placed and unplaced areas and click the Area select element.
   - expected: The select contains `<optgroup>` elements separating placed areas from unplaced areas.
   - observed: Flat `<select>` with 0 `<optgroup>` elements; `a.placed` check evaluates to undefined so all options display bare names.
2. Select an already-placed area and verify coordinates appear in the option label and the toolbar readout.
   - expected: Coordinates or `(placed)` appear in the option text.
3. Run the targeted tests for `grid-model`: `npm test` or `node tools/unit/run.cjs`.
   - expected: All tests pass.

## Acceptance

- [ ] WorldPainter `Area:` selector groups candidate areas into distinct `<optgroup>` elements ("On this grid", "This scope, not placed", "Elsewhere in the world").
- [ ] Placed areas display their placed status or cell coordinates in the dropdown option label.
- [ ] Unplaced areas for the current scope are clearly distinguished from placed areas and external scope areas.
- [ ] No regression in area selection, placement click, or unplacing.

## Files

- `static/js/worldpainter/editor-palette.ts`
- `static/js/worldpainter/grid-model.ts`
- `tools/unit/test_worldpainter_grid.js`
