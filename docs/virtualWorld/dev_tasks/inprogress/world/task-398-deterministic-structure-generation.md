---
type: task
status: inprogress
area: world
priority: high
---

# task-398: Deterministic scoped structure generation

**Filed:** 2026-09-08  
**Depends on:** task-397; task-323 and task-324 for tag-validated library
population; task-9 for reusable item-population planning.
**Dependency reality (2026-09-24):** `task-397` is satisfied — the manifest,
helpers, serialization round-trip and projection routes all exist
(`engine/world_scopes.py`, `virtual_world_engine.py:138`,
`engine/serialization.py:252/556`, `routes/world_scopes*.py`). `task-9` is also
satisfied (`engine/population.py`), and 323/324 are done. **This task is the
front door for the world-generation cluster**: 400, 401, 402, 482 (explore
frontier), 495, 496 and 500 all wait on it. `task-496` explicitly overlaps it
("decide whether to fold it into 398 or keep it as the grid recipe"), and
`task-439` is *not* a prerequisite here.

## Goal

Generate an unmade world scope into normal VirtualWorld graph nodes: real
areas, real ways, relevant furniture/items, and optionally inhabitants. The
generator must be deterministic, reviewable, editable after generation, and
safe to invoke exactly once. AI assistance is optional and may enrich a plan;
it is never required for topology or baseline item placement.

## Generator contract

Each generation recipe returns a **graph patch**, not a parallel world format:

```python
GenerationPatch(
    nodes: list[Node],
    edges: list[Edge],
    area_scope_assignments: dict[str, str],
    generated_manifest_updates: dict,
    report: GenerationReport,
)
```

Applying the patch must use the existing graph node/edge conventions:

- areas use `type="area"`;
- passages use normal `way` nodes and four connection edges where bidirectional;
- items use normal library-spawned item nodes and spatial edges;
- triggers remain normal logic-trigger nodes/edges;
- generated node ids are stable, scoped, and collision checked, e.g.
  `area_pines_3b_bedroom` and `way_pines_hall_3_to_3b`.

Every generated node receives provenance:

```json
{
  "generated": {
    "scope_id": "pines_apartment_3b",
    "recipe_id": "apartment.v1",
    "seed": "pines:3b:v1",
    "generated_at_tick": 0
  }
}
```

Once applied, a scope changes from `unmade` to `materialized`. Re-running must
be rejected by default; an explicit future regenerate/variant flow must never
overwrite manual edits.

## First recipe: Pines Apartment 3B

Use one small, authored apartment recipe as the proof:

- entry/living-kitchen area, bedroom, bathroom;
- an external way from Hallway 3 and internal ways between rooms;
- a minimal domain-tagged furniture set;
- a tag-aware population pass for furniture contents and loose items;
- either `vacant` or one explicitly requested resident seed. Do not silently
  manufacture an LLM character.

The recipe should use the existing profile as authored context, but profile
text is input data, not executable instruction.

## Tag-aware population rules

Task-9 already owns the reusable area → furniture → item tag-chain engine.
This task must call a stable planning/apply API from that task rather than
duplicate library selection in a building generator. The engine must not call
route-private helpers such as `_spawn_library_item_node`; extract a public
library/graph materialization service usable by both the route and generator.

For this prototype, create a deliberately small approved tag vocabulary, for
example `residential`, `bedroom`, `bathroom`, `kitchen`, `storage`, and
`display`, and a matching fixture/template inventory. Candidate selection must
also use room archetype, furniture `placement_roles`, weights, exclusion tags,
and per-archetype budgets/capacities; raw tag intersection alone would put
plausible-but-wrong things in rooms. Pre-index library candidates by tag/role
instead of scanning the full library for every placement. Pines currently has no
area-domain tags, so demonstrating "relevant items" without this data would
be fake. The generator report must say when a requested tag has no eligible
library candidates; it may not substitute unrelated items silently.

## Editor workflow

1. Select an unmade scope.
2. Preview: recipe, seed, proposed area/way/item counts, unresolved tag pools,
   and boundary ways.
3. Apply after user confirmation.
4. Show a generation report and focus the new graph projection.

AI enrichment, if later enabled, produces a staged proposal using the existing
natural-language editor; deterministic validation and user apply remain the
authority.

## Acceptance

- Generating Apartment 3B creates a walkable three-area interior from Hallway
  3 using normal movement and way rules.
- Generated items are physically placed through normal spatial edges and can
  be looked at/taken/used.
- Same seed + recipe version + clean fixture yields the same patch.
- A second generation attempt makes no duplicate nodes/ways/items.
- Missing tag candidates are visible in the preview/report.
- Save/reload preserves generated nodes, provenance, and scope state.
- A later manual edit to a generated item survives reload and cannot be erased
  by a second generator invocation.

## Non-goals

- Generating all of Millbrook, district road layout, or wilderness grids.
- LLM-only generation or unreviewed mutation.
- Chunk unloading (task-401).

## Progress — 2026-09-24 (the patch contract)

The generation **contract** is implemented; the first concrete recipe
(Pines Apartment 3B, below) is still to build.

- **`engine/generation.py`** (new) — `GenerationPatch(nodes, edges,
  area_scope_assignments, generated_manifest_updates, report)` and
  `GenerationReport`; `provenance(scope_id, recipe_id, seed, tick)` and
  `is_generated(node)`; `apply_patch(graph, manifest, patch, *,
  allow_regenerate=False)`.
  - **Once-only guard**: the target scope flips `unmade → materialized`; a
    second apply raises unless `allow_regenerate=True`, so a re-run cannot
    duplicate nodes or erase a manual edit.
  - **Collision-safe**: all node-id collisions are checked *before* any
    mutation, so a rejected apply leaves the graph untouched. A hand-authored
    node at a generated id is refused; with `allow_regenerate`, generated ids
    are replaceable and hand-authored ones are preserved.
  - `area_scope_assignments` merge into each scope record's `area_ids`.
- **`tests/test_world_compile.py`** covers the contract: materialize-once,
  second-apply rejected with the manual edit intact, and refusal to clobber a
  hand-authored node.

The grid recipe that consumes this contract lives in `engine/world_compile.py`
(task-496) — see that task's progress note. The Pines Apartment 3B recipe
(three areas from Hallway 3, tag-aware furniture population) is the next slice
here, and it should call task-9's `engine/population.py` planner rather than
re-selecting from the library.
