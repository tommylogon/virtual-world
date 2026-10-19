---
type: task
status: todo
area: world
priority: medium
wiki: "[[World Building/WorldPainter]]"
---

# task-884: Child-scope procedural generators: Markov adjacency buffers, settlement/dungeon grammar, and reference-guided painting

**Filed:** 2026-10-19
**Related:** task-398, task-496, task-567, task-580, task-747, docs/design/procedural-generation-and-dungeon-biomes.md

## What

Believable procedural generation and painting assistants for **child scopes** (settlements, interiors, wilderness reaches, dungeons, caves, ruins). Rather than filling arbitrary noise or forcing tedious manual painting across hundreds of cells over a reference image:

1. **Believable Transition Gradients (Markov Adjacency Buffers):** Natural landscapes and settlements obey transition bands rather than jarring borders. E.g. `deep_river` -> `shallow_river` -> `banks` -> `clearing / fields / sparse_woods` -> `deep_woods`. A Markov transition matrix defines valid neighbor probabilities so auto-fill and smart brush strokes feather realistic edges.
2. **Reference-Guided Painting Assistance:** Authors provide a reference background art image. The assistant samples the luminance/color bands under the cursor or across a marquee selection to suggest/apply coherent biome and road placements matching the art.
3. **Child-Scope Structural Generators (Grammar + Layouts):**
   - *Settlement:* Central square/well -> arterial streets -> alleys -> zoned building lots with frontages.
   - *Wilderness / River Reaches:* Sinuous channel carving, bank buffers, elevation-conforming terrain.
   - *Dungeons / Caves / Ruins (see `docs/design/procedural-generation-and-dungeon-biomes.md`):* Graph-first spanning tree linking mandatory hand-placed landmarks (e.g. Grand Gate, Great Forge, Tombs, Deep Mines) with A* corridor/stair carving under a partitioned gold budget. Secondary WFC/Markov infill of functional chambers, followed by a catastrophe decay pass (cave-ins, chasm breaches, flooding, monster nesting). Multi-storey depth complexes are partitioned into child scopes per depth level to preserve 2.5D layer storage invariants.
4. **Natural Language Co-Pilot in WorldPainter:** Leverage the existing NL Editor engine to take author intent ("Add a fortified bandit camp with watchtowers and palisades overlooking the river bend") and materialize the corresponding painted cells and feature placements into the active child scope.

## Why

In WorldPainter, whole-world painting is guided by an authored reference image, but child scopes (towns, ruins, interior layouts) are high-density surfaces where hand-placing dozens of cells easily results in repetitive grids or abrupt, unnatural borders (e.g. deep woods touching a tavern wall with no path or yard). Authors need assistive tools that know what naturally sits between cells, feather transitions, and generate coherent child-scope layouts from high-level prompts and reference art.

## How

1. **Markov Adjacency Matrix (`data/worldpainter/adjacency.json`):**
   - Declare transition affinities and forbidden adjacencies between biomes.
   - Expose `engine/world_adjacencies.py` with `suggest_buffer(cell_a, cell_b)` to calculate the intermediate gradient.
2. **Smart Feather / Buffer Brush in `static/js/worldpainter/`:**
   - Tool mode that automatically inserts the logical intermediate tier when stroking between contrasting zones (e.g. automatically placing banks/reeds between water and forest).
3. **Child-Scope Generators (`engine/scope_generators/`):**
   - Specialized recipes for settlement, cave, ruin, and interior modes that compile structured templates into paint layers (`biome`, `road`, `floor`, `hazards`).
   - Landmark-first spanning tree ensuring reachability before spending construction budget on elective rooms.
   - Ruin catastrophe decay filters generating realistic structural failures, flooded lower tiers, and monster nests.
4. **Subterranean Biome Taxonomy (`data/library/biomes/`):**
   - Suite of 18 subterranean and dwarven biomes covering industrial, civic, sepulchral, mining, and structural portal roles.
5. **WorldPainter Storey Adjuster Rail (`static/js/worldpainter/`):**
   - Vertical rail on the canvas margin allowing switching active sibling floor scopes (`kind: "floor"`), with translucent ghost-layer onion-skinning of adjacent floors.
6. **Corner Door Compilation (`engine/world_compile.py`):**
   - Extend `door_pairs` opposite-pair scanning to include diagonal offsets `((1, 1), (1, -1))` guarded by solid wall flanking checks.
7. **NL Integration:**
   - Route WorldPainter generation prompts through `static/js/nl-editor/` to parse layout instructions into batch grid paint operations.

## Browser UI and intended live verification

Intended UI home: WorldPainter -> child scope view -> Generation / Assistant toolbar & Smart Feather brush.

Current availability: Planned; interior templates exist in `engine/interior_gen.py`, but Markov adjacency buffers, smart gradient brushes, and NL scope generation are not yet implemented.

Live steps when available:

1. Open a child scope (e.g. settlement or wilderness) over a reference image.
2. Use the Smart Buffer brush to stroke between a river cell and forest.
   - expected: The editor automatically places `shallow_river`, `banks`, and `sparse_woods` along the seam instead of a harsh single-cell transition.
3. Open the Scope Generator modal, pick "Settlement", and click Generate Preview.
   - expected: A coherent layout appears with roads, perimeter gates, and zoned building placements conforming to the chosen template.
4. Issue an NL instruction to add a palisade and clearings.
   - expected: The staging tray renders the proposed paint diff for author approval before committing to the scope.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Run unit tests on Markov adjacency solver `node tools/unit/run.cjs --filter adjacency`.
   - expected: Transition solver returns expected intermediate buffer tiles for test biome pairs.
2. Run generator tests `python -m pytest tests/test_scope_generators.py`.
   - expected: Deterministic settlement, cave, and wilderness generators produce valid, connected, and bounded child-scope grid layers.
3. Test reference image color sampling in WorldPainter canvas.
   - expected: Sampler correctly matches art tones to mapped biome palette archetypes.

## Acceptance

- [ ] Transition matrix in `data/worldpainter/adjacency.json` defines natural biome gradients and prohibited adjacencies.
- [ ] Smart Feather brush in WorldPainter places gradient buffers along painted seams.
- [ ] Child-scope procedural generators for settlements, caves, and ruins generate walkable, connected grids.
- [ ] Dungeon and ruin generator enforces landmark reachability via spanning tree and respects the partitioned gold budget.
- [ ] Ruin catastrophe pass applies structural collapse, chasm severance, or flooded tiers.
- [ ] 18 subterranean and dwarven biomes in `data/library/biomes/` compile into standard areas and way connections.
- [ ] WorldPainter Storey Adjuster rail enables stepping through sibling floor scopes with ghost-layer onion skinning.
- [ ] Doorway compiler opposite scan supports diagonal chamfered doors when flanked by solid wall cells.
- [ ] NL Editor can execute child-scope layout commands with diff staging.
- [ ] All generation outputs write standard paint layers (`biome`, `road`, `floor`, `hazards`) that compile cleanly through `engine/world_compile.py`.

## Files

- `data/worldpainter/adjacency.json`
- `data/library/biomes/`
- `engine/world_adjacencies.py`
- `engine/scope_generators/`
- `static/js/worldpainter/editor.ts`
- `static/js/worldpainter/brushes.ts`
- `static/js/nl-editor/`
- `docs/design/procedural-generation-and-dungeon-biomes.md`
