---
type: task
status: review
area: world
priority: medium
wiki: "[[World Building/WorldPainter]]"
---

# task-745: WorldPainter hazards: a current/strength paint layer plus a hazards.json category table

**Filed:** 2026-10-09
**Related:** task-557 task-520 task-496

## What

Turn painted terrain into consequences, not just DCs. Three interconnected parts:

1. **Biome-integrated hazard defaults & expanded water vocabulary**: Biomes in `data/worldpainter/biomes.json` declare default `hazard_id` references (e.g. `river` -> `river`, `rapids` -> `rapids`, `mountain_cliff` -> `cliff`, `briar_patch` -> `thorns`). Expand river/water biomes to distinct archetypes (`river_calm`, `river_swift`, `river_rapids`, `river_gorge`) that carry distinct default surfaces and hazard couplings without cluttering engine code.
2. **Floor elevation gradient as the primary flow driver**: Water flows downhill. Rather than forcing manual authoring of flow direction and strength across every single water cell, the compiler and editor derive flow vector and velocity from the gradient of the `floor` (storey) layer across contiguous water cells.
   - **Calibrated Hydrology Model (1 cell = 1 minute walk ≈ 80m across; 1 storey = 3m drop)**:
     - *0 storeys drop* (0m / 80m, 0%): Calm / Meandering (`river_calm`), no roll (routine take-10).
     - *1 storey drop* (3m over 80–160m, ~1.9–3.7% slope): Swift current / riffle (`river_swift`), DC 10 Athletics / wading check.
     - *2–3 storeys drop* (6–9m over 80m, ~7.5–11% slope): Whitewater rapids (`river_rapids`), DC 15 Athletics check; failure sweeps actor downstream into next cell.
     - *4+ storeys drop or sheer cliff step* (≥12m over 80m or cliff seam, >15% to 90°): Waterfall / Cataract (`waterfall` / `cataract`), impassable upstream; DC 20 plunge check.
   - Manual `current` layer paint overrides are reserved for special non-gravity features (whirlpools, subterranean conduits, tidal surges).
3. **Smart assistant validation for river layering & slope continuity**: A validator tool and painter lint alert (`tools/river_flow_lint.py` and editor assistant) that inspects contiguous river runs and detects physical impossibilities: water running uphill without pressure, drops of 4+ storeys missing a waterfall/cataract classification, disconnected pooling, and river branches that dead-end without an outflow sink.
4. **Data-driven hazard consequences**: `data/worldpainter/hazards.json` category registry maps hazard types to abilities, strength-to-DC ladders (5-20), and `on_fail` consequences (damage, conditions, forced movement downstream).

## Acceptance

- [x] `data/worldpainter/hazards.json` - a category registry (river, rapids, cliff, fall, thorns, pit, bridge_jump), each with ability check, 5/20 strength->DC ladder, `on_fail` conditions/tags, and success/fail prose.
- [x] `engine/hazards.py` reads it; `dc_for(id, strength)` picks the highest rung `<= strength` (clamped at both ends); `validate()` enforces the shape.
- [x] `tools/hazard_index.py --check` is a gate (green: 7 hazards).
- [x] `tests/test_hazards.py` - 8 tests (ladder selection, unknown ability / empty ladder rejected, ladder tolerance).
- [x] Biomes in `data/worldpainter/biomes.json` can declare an optional `hazard_id` property, and new water/river archetypes are registered (`river_calm`, `river_swift`, `river_rapids`, `waterfall`).
- [x] Flow direction and strength auto-derive from the `floor` storey layer gradient across adjacent water cells when no manual current layer override is painted.
- [x] River flow assistant / linting tool (`tools/river_flow_lint.py`) checks water runs for uphill flow, abrupt jumps, and dead ends.
- [x] Compiler emission pass mapped to consumer task-747 (blocked by task-746).

## Progress (2026-10-19)

- Biome taxonomy: `data/worldpainter/biomes.json` and `data/library/biomes/` updated with optional `hazard_id` (river, cliff), plus 4 water archetypes: `river_calm` (0 drop meander), `river_swift` (1 storey drop riffle), `river_rapids` (2-3 storey drop whitewater), and `waterfall` (4+ storey drop cataract).
- Hydrology gradient engine: `engine/world_grid.py:derive_water_current` and `static/js/worldpainter/grid-model.ts:deriveWaterCurrent` derive 0-7 compass vector and 1-20 strength from `floor` storey slope across contiguous water cells, respecting manual `current` paint layer overrides.
- Hydrology lint assistant: `tools/river_flow_lint.py` inspects river runs to flag uphill flow, unclassified drops >= 4 storeys, and dead-ending inland channels.
- Unit verification: 75 python tests (`test_world_grid.py`, `test_biomes.py`, `test_hazards.py`, `test_river_flow.py`) and 773 JS tests in `node tools/unit/run.cjs` pass.

## Why

Environmental hazards (rapids, sheer cliffs, briars, pits) were either absent or represented as ad-hoc, hardcoded DC checks without a unified data-driven vocabulary or authoring support. Creating a `hazards.json` category registry and a dedicated `current` strength/direction paint layer gives world authors a consistent, declarative way to author terrain risks and water flow. The compiler and movement system can translate painted flow and hazard rungs directly into ability checks, traversal costs, and failure consequences (damage, conditions) without code changes for every new obstacle.

## How

1. Define hazard registry in `data/worldpainter/hazards.json` with schema `{ability, dc_ladder, on_fail, message_success, message_fail}`.
2. In `engine/hazards.py`, implement validation, category lookup, and `dc_for(hazard_id, strength)` resolution.
3. Expose validation CLI in `tools/hazard_index.py --check` and register vocabulary in the Library Vocabulary tab (`static/js/library/`).
4. Add `current` layer to `engine/world_grid.PAINT_LAYERS` and `static/js/worldpainter/grid-model.ts` storing flow direction (0-7 compass) and strength (1-20).
5. Auto-derive flow vectors and calibrated slope strength (1 cell = 80m, 1 floor = 3m) from the `floor` storey layer across contiguous water cells.
6. Provide river flow assistant CLI in `tools/river_flow_lint.py` to validate river runs for uphill flow, steep unclassified cataracts, and inland dead-ends.

## Browser UI and intended live verification

Intended UI home: Build -> WorldPainter -> current/strength paint layer and cell Inspector; game traversal for the resulting hazard.

Current availability: The hazard registry, biome archetypes, hydrology gradient engine, and river flow lint assistant are present and tested.

Live steps when available:

1. Open a painted river scope, select the current layer, and paint direction/strength on a current-bearing cell.
   - expected: The cell Inspector shows the flow direction and strength consumed by the hazard definition.

2. Play a scratch traversal across that reach at low and high strength.
   - expected: The authored check and outcome apply through existing traversal without a second hazard table.

This section defines the intended access point and acceptance path. It is not a claim that the UI or complete behavior exists or works today; Current availability records the present state, and these steps describe how to verify the intended behavior when it is available.
## Steps to verify

1. Run hazard registry validation gate `python tools/hazard_index.py --check`.
   - expected: Gate passes cleanly with valid hazard categories and DC ladders.
   - observed: Passed ("hazard registry OK (7 hazards)").
2. Run targeted pytest suite `python -m pytest tests/test_hazards.py tests/test_river_flow.py tests/test_world_grid.py tests/test_biomes.py`.
   - expected: All hazard registry, biome, and hydrology unit tests pass.
   - observed: 75 passed.
3. Run `node tools/unit/run.cjs`.
   - expected: All JS unit tests pass including deriveWaterCurrent and PAINT_LAYERS.
   - observed: 773 passed.
4. Run river flow lint assistant: `python tools/river_flow_lint.py --report data/scenarios/kraktooth_goblin_camp.json`.
   - expected: Successfully analyzes river runs and reports physical gradient status.
   - observed: 21 issues reported across Kraktooth uncelled/flat river runs.

## Files

- `data/worldpainter/hazards.json`
- `data/worldpainter/biomes.json`
- `data/library/biomes/`
- `data/library/resource_distribution/`
- `data/library/hostile_distribution/`
- `engine/hazards.py`
- `engine/biomes.py`
- `engine/world_grid.py`
- `static/js/worldpainter/grid-model.ts`
- `tools/hazard_index.py`
- `tools/river_flow_lint.py`
- `tests/test_hazards.py`
- `tests/test_river_flow.py`
- `tools/unit/test_worldpainter.js`

## Resolution Note (2026-10-19)
- Registry, biome hazard coupling, calibrated hydrology gradient engine, and river flow lint assistant complete and tested.
- Moved to review.
