---
type: task
status: inprogress
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
- [ ] Biomes in `data/worldpainter/biomes.json` can declare an optional `hazard_id` property, and new water/river archetypes are registered.
- [ ] Flow direction and strength auto-derive from the `floor` storey layer gradient across adjacent water cells when no manual current layer override is painted.
- [ ] River flow assistant / linting tool checks water runs for uphill flow, abrupt jumps, and dead ends.
- [ ] Compiler (task-747) stamps derived or painted hazards onto generated ways/areas.

## Progress (2026-10-09)

The **registry half (2)** is done; the **paint layer (1)** and the compiler pass
(task-747) remain. Moved to `inprogress`.

- `data/worldpainter/hazards.json` - 7 hazards. Policy fields: `ability`, a
  `dc` ladder keyed by strength threshold, `on_fail {conditions, tags, damage}`,
  and `message_success`/`message_fail`.
- `engine/hazards.py` - `hazards()`, `hazard()`, `ladder()`, `dc_for()`,
  `validate()`, `clear_cache()`.
- `tools/hazard_index.py` - `--check` (gate) and `--report`.
- `tests/test_hazards.py` - 8 tests; `python tools/hazard_index.py --check` ->
  "hazard registry OK (7 hazards)".

**Deviation, recorded:** the card said `{skill, ...}`; the six engine
**abilities** (`engine/abilities.ABILITIES` = STR/DEX/CON/INT/WIS/CHA) are the
vocabulary that exists, so a hazard names an `ability`, not a skill. No skill
vocabulary was invented to match the card's wording.

**Remaining:** the paint layer (UI-bound; needs live verification) and task-747.

**Integration (2026-10-09):** the registry is authorable now - it was added as a
sixth type in the library **Vocabulary tab** (task-589), file-backed on
`worldpainter/hazards.json`, validated by `engine/hazards.hazard_problems`, with
the route test `test_hazard_registry_is_file_backed_and_validates`.

## Why

Environmental hazards (rapids, sheer cliffs, briars, pits) were either absent or represented as ad-hoc, hardcoded DC checks without a unified data-driven vocabulary or authoring support. Creating a `hazards.json` category registry and a dedicated `current` strength/direction paint layer gives world authors a consistent, declarative way to author terrain risks and water flow. The compiler and movement system can translate painted flow and hazard rungs directly into ability checks, traversal costs, and failure consequences (damage, conditions) without code changes for every new obstacle.

## How

1. Define hazard registry in `data/worldpainter/hazards.json` with schema `{ability, dc_ladder, on_fail, message_success, message_fail}`.
2. In `engine/hazards.py`, implement validation, category lookup, and `dc_for(hazard_id, strength)` resolution.
3. Expose validation CLI in `tools/hazard_index.py --check` and register vocabulary in the Library Vocabulary tab (`static/js/library/`).
4. Add `current` layer to `engine/world_grid.PAINT_LAYERS` storing flow direction (0-7 compass / angle) and strength (1-20).
5. In WorldPainter UI (`static/js/worldpainter/`), add tools to paint flow vectors and strength on water/cliff cells.
6. Feed painted hazard and current data into `engine/world_compile.py` to stamp hazard attributes on generated ways and areas.

## Browser UI and intended live verification

Intended UI home: Build -> WorldPainter -> current/strength paint layer and cell Inspector; game traversal for the resulting hazard.

Current availability: The hazard registry and engine reader are present; the current paint layer and authored current behavior remain open.

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
2. Run targeted pytest suite `python -m pytest tests/test_hazards.py`.
   - expected: All hazard registry unit tests pass (ladder selection, bounds checking, ability validation).
   - observed: 8 passed.
3. Verify Library Vocabulary tab exposes hazard editing.
   - expected: Hazards category is visible and editable under WorldPainter vocabulary tab.
   - observed: Verified via `test_hazard_registry_is_file_backed_and_validates`.
4. Paint flow and strength on water cells in WorldPainter editor.
   - expected: Cell inspector reflects authored flow direction and 1-20 strength on current layer.
   - observed: Pending completion of current paint layer UI.

## Files

- `data/worldpainter/hazards.json`
- `engine/hazards.py`
- `tools/hazard_index.py`
- `tests/test_hazards.py`
- `engine/world_grid.py`
- `static/js/worldpainter/editor.ts`
- `static/js/worldpainter/layers.ts`


## Blocker Note (2026-10-19)
- Registry half (data/worldpainter/hazards.json, engine/hazards.py, hazard_index.py, and 8 pytest unit tests) is 100% complete and passing.
- Blocked on implementing the current paint layer (vector flow & 1-20 strength) in the WorldPainter Konva UI editor and connecting it to compiler consumer task-747.
