---
type: task
status: review
area: ui
priority: medium
wiki: "[[World Building/WorldPainter]]"
---

# task-877: WorldPainter: import and export a greyscale heightmap for the floor layer

**Filed:** 2026-10-19
**Related:** task-525, task-776, task-651

## What

Let an author import a greyscale image onto a scope's floor layer and export the floor layer back out as a greyscale PNG, so regional elevation is a one-step operation instead of one cell at a time.

## Why

docs/design/notebook-notes.md line 49 already asks for it: "use a heightmap to import with standard black to white grayscale values to translate into the areas floor value". Today the floor layer is a sparse {"x,y": int} map painted one cell (or one brush) at a time.

Unit settled by the author (2026-10-19): one floor step is 3 metres. That is consistent with the engine, where floor is a whole-storey index (engine/world_grid.py docstring; a storey is about 3 m) and the climb gate is DEFAULT_MAX_STOREY_STEP = 3 (engine/world_compile_regions.py), so the default cliff is a 9 m step. No metres-per-storey constant exists anywhere in the engine today (searched engine/ and routes/), so this card introduces the first one and it needs one home, not a copy in the editor.

Not a height layer: the deleted `elevation` layer was a 0..1 fraction the author never agreed to, and world_grid.py warns that one word must not mean two things. Import must therefore convert metres to whole storeys and store only storeys; no metre value is ever persisted.

## How

Mapping: storeys = round(metres / 3). Define METRES_PER_STOREY = 3 once in engine/world_grid.py and hand it to the painter through the vocabulary route that already returns the modes list (routes/world_grid_ops.py), so the editor reads it instead of hardcoding 3.

Import: the author picks the metres that black and white stand for (for example 0 m to 765 m). Greyscale 0..255 is interpolated into that range, divided by 3 and rounded, so 8 bits give at most 256 distinct levels and a 765 m range uses all of them at exactly 3 m each. The image is resampled to the scope's w x h. A preview shows the metre range, the resulting storey min and max, and how many neighbouring cell pairs exceed the scope's climb threshold (record climb.max_storey_step, default 3 storeys = 9 m), since those become climb-gated ways when the scope is a world scope (task-525). Apply commits through the existing paint_batch route as one undo step; no second write path.

Export: floor storeys x 3 m mapped linearly to greyscale between a chosen min and max metre; the chosen range is written next to the file so a round trip is lossless. Cells with no painted floor export as the ground value (0 storeys), because an unpainted cell is ground by definition.

Browser decode and encode use canvas; add no library. The 0 storey ground level must be representable: import never writes 0 into unpainted cells that the image leaves out, but a black pixel inside the range that rounds to 0 is painted 0 storeys on purpose.

## Browser UI and intended live verification

Intended UI home: WorldPainter, layer set to floor, an Import / Export heightmap action

Current availability: Not built; no import or export of the floor layer exists today.

Live steps when available:
1. Select the floor layer, choose Import heightmap, pick a gradient PNG, set black = 0 m and white = 60 m. expected: a preview showing 0 to 60 m, storeys 0 to 20, and the count of climb-gated steps; Apply paints the floor layer in one undo step.
2. Choose Export heightmap. expected: a PNG whose brightness tracks the painted storeys.

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

- [ ] METRES_PER_STOREY = 3 exists once in engine/world_grid.py and reaches the editor through the painter vocabulary route; no literal 3 for this purpose in editor.ts.
- [ ] Importing a black-to-white gradient with black = 0 m and white = 60 m onto a 21-wide scope yields storeys 0 through 20 left to right, in one undo step.
- [ ] A pixel at 4.4 m imports as 1 storey and 4.6 m as 2 (round to nearest of 3 m steps: 1.5 m boundaries at 1.5, 4.5, 7.5).
- [ ] Exporting then re-importing with the same recorded metre range reproduces the original floor layer exactly.
- [ ] The import preview shows the metre range, the storey min and max, and the count of cell pairs that exceed the scope's climb threshold.
- [ ] Nothing in a saved scenario stores metres: the floor layer still holds integers only.
- [ ] Cells the image does not cover are left unpainted, not set to 0.
- [ ] Unit tests cover the metres-to-storeys quantisation and its rounding boundaries in grid-model, and the constant in a Python test.

## Files

- static/js/worldpainter/editor.ts
- static/js/worldpainter/grid-model.ts
- engine/world_grid.py (METRES_PER_STOREY)
- routes/world_grid_ops.py (vocabulary route carries it)
- tools/unit/test_worldpainter.js
- tests/test_world_grid.py
