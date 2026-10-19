---
type: task
status: review
area: world
priority: normal
wiki: "[[World Building/WorldPainter]]"
---

# task-887: WorldPainter Way Description and Visible-in-Direction Generator with Biome Narrative Pools

**Filed:** 2026-10-19

## Context and Problem

When WorldPainter compiles painted grid cells into areas and ways (`engine/world_compile.py`), generated ways currently lack:
1. `description` on the way node itself.
2. `visible_in_direction` on the connection edges (`area -> way`).

As a result:
- The World Validator reports over 4,000 `info` notices (`way_missing_description` and `way_missing_view_direction`).
- In-game narration for moving between painted cells falls back to bare room names ("You go north to Deep Woods (12, 14)") rather than rich, varied landscape transitions.
- Generating identical static text for every way in a biome makes large zones feel repetitive.

## Target Architecture

1. **Biome Narrative / View Direction Vocabulary:**
   - Author `data/worldpainter/way_narratives.json` with dedicated pools for structural kinds (door, stairs, entrance) and major biome/terrain transitions (roads, woods, water, rocks, cultivated fields, urban, grassland, and specific combinations).
   - Each entry provides 5 varied descriptions and 5 forward/reverse view cues.
2. **Compiler Generation Logic:**
   - In `engine/way_narratives.py` and `engine/world_compile.py` (`_way_edges`, `_gateway`, `_enter_way`, `emit_passage`, `sibling_seams`):
     - Inspect source and destination cell biomes, roads, and storey steps.
     - Deterministically select entries using `_stable_index` keyed on scope, way id, direction, and seed.
     - Populate `node.properties["description"]` and `edge.properties["visible_in_direction"]`.
3. **Validator Cleanup:**
   - Compiler-generated fields resolve `way_missing_description` and `way_missing_view_direction` on WorldPainter compiled scopes cleanly.

## Acceptance Criteria

- [x] Biome narrative phrase pools defined with at least 3-5 variations per major biome transition.
- [x] `engine/world_compile.py` assigns non-empty `description` to compiled way nodes and `visible_in_direction` to their connection edges.
- [x] Phrasing uses deterministic variation (no uniform repetition across every tile).
- [x] World Issues report for compiled scopes drops way description/direction notices.
- [x] Targeted tests verify compiled ways carry valid `description` and `visible_in_direction`.

## Verification Report

- `tests/test_way_narratives.py`: 5/5 passed in 0.43s.
- `tests/test_world_compile.py`: 119/119 passed in 1.75s.
- `tests/test_module_index_py.py`: 5/5 passed in 0.25s.
- `tests/test_trigger_validator.py`: 51/51 passed in 0.56s.
- `node tools/unit/run.cjs`: 778/778 frontend tests passed.
