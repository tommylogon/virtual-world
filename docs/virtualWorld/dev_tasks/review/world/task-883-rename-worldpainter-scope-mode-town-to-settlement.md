---
type: task
status: review
area: world
priority: low
wiki: "[[World Building/WorldPainter]]"
---

# task-883: Rename WorldPainter scope mode 'town' to 'settlement'

**Filed:** 2026-10-19
**Related:** task-882, task-650, task-495

## What

Rename the second WorldPainter scope mode from `'town'` to `'settlement'`. The three modes become `('world', 'settlement', 'interior')`.

The rename better reflects the range of exterior habitations that can be authored at this tier (camps, hamlets, villages, outposts, goblin war-camps, cities).

### Backward Compatibility Invariant
Existing scenarios (`kraktooth_goblin_camp.json`, `Millwood.json`) and saved scope records carry `"mode": "town"`. The backend loader and schema normalizer MUST alias `"town"` to `"settlement"` transparently on load so that older scenarios and saved files do not fail schema validation or mode assertions.

## Implementation Points

1. **`engine/world_grid.py`**:
   - `MODES = ("world", "settlement", "interior")`
   - Normalize incoming mode: if `mode == "town"`, return `"settlement"`.
2. **`routes/world_grid_ops.py`**:
   - Update API validation to accept `"settlement"` (with `"town"` accepted as legacy alias).
3. **`static/js/worldpainter/grid-model.ts`**:
   - `const MODES = ['world', 'settlement', 'interior'];`
   - Update `paletteForMode`, `MODE_HIDDEN_SECTIONS`, `MODE_KEPT_SECTIONS`, `nextMode`.
4. **`static/js/worldpainter/editor.ts`**:
   - Update `_checklistIntro` and `_checklistSteps` to handle `'settlement'`.
5. **`tools/unit/test_worldpainter.js` & `tests/test_world_grid.py`**:
   - Update unit test assertions.

## Acceptance

- [x] `engine/world_grid.py` declares `MODES = ("world", "settlement", "interior")`.
- [x] Existing `"mode": "town"` scopes normalize to `"settlement"` without schema or runtime failure.
- [x] `grid-model.ts` and `editor.ts` recognize and use `'settlement'`.
- [x] Palette filtering and checklist progress work cleanly for `'settlement'`.
- [x] Tests in `test_worldpainter.js` and `test_world_grid.py` pass.

## Evidence

- `tests/test_world_grid.py`: 37 passed in 0.55s, verifying `test_normalise_grid_is_tolerant` normalizes `mode: "town"` -> `mode: "settlement"`.
- `tools/unit/test_worldpainter.js`: 768 unit tests passed, verifying `nextMode` walks `world -> settlement -> interior` (with `town -> interior` backwards compatibility) and `paletteForMode` filters for both `'settlement'` and legacy `'town'`.
- Compiled `grid-model.js` and `editor.js` via `tools/ts_convert.py build-one`.

## Files

- `engine/world_grid.py`
- `routes/world_grid_ops.py`
- `static/js/worldpainter/grid-model.ts`
- `static/js/worldpainter/grid-model.js`
- `static/js/worldpainter/editor.ts`
- `static/js/worldpainter/editor.js`
- `tools/unit/test_worldpainter.js`
- `tests/test_world_grid.py`
