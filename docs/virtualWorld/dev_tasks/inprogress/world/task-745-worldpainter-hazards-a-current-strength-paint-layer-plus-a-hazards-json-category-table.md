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

Turn painted terrain into consequences, not just DCs. Two halves. (1) A current paint layer beside biome/road/floor/climate: a per-cell flow direction and a strength 1-20, following task-557's precedent for adding a layer (whitelist in engine/world_grid.PAINT_LAYERS, editor tool, compiler read). Storey gradient may supply the direction/speed default when the author paints no current. (2) data/worldpainter/hazards.json, a category registry like biomes.json: river/rapids, cliff/fall, thorns, pit, bridge-jump, each {skill, dc ladder by strength, on_fail effects, success/fail message templates}. A --check gate validates it the way way_property_index does. Policy is data: the 5/20 ladder is author-tunable, not code.

## Acceptance

- [x] `data/worldpainter/hazards.json` - a category registry (river, rapids,
      cliff, fall, thorns, pit, bridge_jump), each with the ability check, a
      5/20 strength->DC ladder, `on_fail` conditions/tags, and success/fail prose.
- [x] `engine/hazards.py` reads it; `dc_for(id, strength)` picks the highest rung
      `<= strength` (clamped at both ends); `validate()` enforces the shape.
- [x] `tools/hazard_index.py --check` is a gate (green: 7 hazards).
- [x] `tests/test_hazards.py` - 8 tests (ladder selection, unknown ability /
      empty ladder rejected, ladder tolerance).
- [ ] The current/strength **paint layer** (`world_grid.PAINT_LAYERS` whitelist,
      editor tool, compiler read).
- [ ] The compiler attaches hazard ids to generated ways/areas - that is
      task-747, the consumer of this registry.

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
