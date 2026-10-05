---
type: doc
tags: [system/world]
---

# World Scopes

A **world scope** is a named, addressable region of the world with a parent. It is
the unit of loading, of projection, of generation and — later — of eviction.
`Millbrook Falls > Downtown District > The Pines Apartment Complex > Floor 2` is
a path a system can name and a person can navigate.

Source of truth: `engine/world_scopes.py` (manifest + projection) and
`engine/generation_recipes.py` / `engine/generation.py` (making a place).
Task-397 is the originating task; task-398 added generation.

Part of [[_Index]].

## Why a scope, and not "a range of the map"

A region could be described three ways, and two of them are wrong:

- as **coordinates** — then every system that wants to know "is the well inside
  the mill?" needs geometry, and the answer changes when a map is re-painted;
- as a **name** — then a duplicate name silently merges two places, which is
  exactly the hazard task-581 has to fix for `current_area`;
- as a **node with a parent** — a scope. Addressing a place becomes a graph walk
  up to a common ancestor, not a geometry problem.

So a scope is a node. Its `area_ids` say what it contains, its `parent_id` says
where it sits, and its `kind` says what it is (`settlement`, `district`,
`building`, `floor`, …).

## The manifest

`world_scopes` on the app world, keyed by scope id:

```json
{
  "millbrook_falls": { "id": "millbrook_falls", "name": "Millbrook Falls",
                       "kind": "settlement",
                       "children": ["downtown", "the_pines"] },
  "downtown":        { "id": "downtown", "name": "Downtown District",
                       "kind": "district", "parent_id": "millbrook_falls",
                       "area_ids": ["area_town_square", "area_street", "…"] }
}
```

An area belongs to a scope through the `world_scope_id` property **on the area
node**. The manifest's `area_ids` is a mirror of that, kept in step by
`assign_area_membership()` (task-539) — so the node is the fact and a manifest
that has drifted still resolves correctly on read, because `area_ids_in_scope()`
unions both sources.

`normalise_manifest()` is called on every read, so a hand-edited scenario gets a
consistent shape rather than a crash at first use.

### A scope may also own a grid (2026-10-01)

This was missing here, which made the grid read like a *separate* system layered beside scopes
rather than a field on the same record. A scope record can also carry:

```json
{
  "mode": "world",                                  // world | town | interior
  "grid": { "w": 20, "h": 40, "cell_scale": 1.0 },  // absent = this scope has no grid
  "layers": { "biome": {"10,14": "sparse_forest"},  // painted cells, keyed "x,y"
              "road":  {"11,22": "road"},
              "floor": {} },                        // storey index: 0 ground, ±n, unbounded
  "placements": { "child_scope_id": { "x": 10, "y": 4 } },        // a child scope at a cell
  "area_placements": { "area_animal_pens": { "x": 11, "y": 7 } }, // a hand-written area at a cell
  "area_ids": ["…"]                                  // mirror; the node property is the fact
}
```

A scope with no `grid` costs nothing and older saves load unchanged. Coordinates are integer
`(x, y)` from the top-left with `y` down, and a cell's stable identity is `cell_id` =
`"<scope_id>:<x>,<y>"`.

**A painted cell compiles to an area node** — the id is minted from the cell
(`area_<scope_id>_<x>_<y>`) and the node carries `properties.cell`, so the grid is an *authoring*
surface over the same areas the graph holds, not a second model. Full statement, with the three
deliberate exceptions (region merging, hand-placed cells, never-compiled grids):
[[Rooms & Areas]] → "A compiled cell IS an area".

Two membership questions have different answers on purpose:
`area_ids_in_scope()` includes descendants, while `own_area_ids()` returns only
this scope's own areas. The graph view uses the second, so a parent shows a placed
child as a single feature cell rather than spilling its whole interior.

## Projection, not the whole graph

`project()` returns one scope's subtree — the areas, the ways between them, the
boundary ways that leave the scope, and the counts a UI needs. The rule that
matters: **the default view does not reveal what a scope merely contains.**
Opening a scope into a projection is a deliberate act, not a default.

`project_subgraph()` is the graph-only variant, and it is what the editor's scope
requests use. Several editor surfaces still fetch all nodes and edges and filter
client-side (see [[Rooms & Areas]]); once chunks exist (task-401) that has to go
through this path.

`flat_scopes()` is the whole manifest flattened for a tree or breadcrumb, and
`scope_summary()` is the per-scope rollup (areas, items, characters, generation
state). Deleting a scope is refused while it has children unless `cascade=True`,
and it removes only **generated** nodes — hand-authored nodes are left alone
rather than guessed at, while a hand-*placed* area keeps its area and loses the
cell.

## Unmade scopes

A scope with a grid but no materialised areas is **unmade**: declared, addressable,
and empty. This is the state that makes the rest of the roadmap possible —
generation needs a target, and chunking needs something to load.

An unmade scope may carry a `recipe`. That is the whole contract for
[making a place](#making-a-place).

## Making a place

`POST /api/world/scopes/<scope_id>/grid/generate` runs the scope's recipe and
applies the resulting patch. The contract is in `engine/generation.py`:

- `GenerationPatch(nodes, edges, area_scope_assignments, generated_manifest_updates, report)`
- same **seed + recipe version + clean fixture → same patch** (determinism);
- applying it twice creates **no duplicate** nodes, ways or items;
- everything it makes carries **provenance** (`is_generated()`), so the UI can
  tell generated from authored;
- the `report` lists **missing tag candidates**, so a thin library is visible
  rather than silently producing an empty room.

The first recipe is **`apartment.v1`** (`apartment_v1()`): a three-area interior
with real ways, its items placed through the ordinary spatial edges so they can be
looked at, taken and used. It is proven by `tests/test_apartment_recipe.py`.

The rule that keeps generation from becoming a second authoring system:

> **Generated is a provenance flag, not an ownership claim.**

Once a person edits a generated item, that edit outranks the recipe. A later
generation cannot erase it — a second run is a no-op on anything already made.
`ungenerate_scope()` is the explicit, separate way to take a scope back to unmade.

Not built yet: the `Generate` button and the preview surface (**task-580**). The
backend endpoint is there; nothing in the UI calls it yet.

## API

| Route | Does |
|---|---|
| `GET /api/world/scopes/<id>/grid` | grid + layers + breadcrumb + summary |
| `POST /api/world/scopes` | create a scope |
| `POST /api/world/scopes/<id>/grid/paint`, `/name`, `/place`, `/place_area`, `/unplace_area` | edit the grid and its membership |
| `POST /api/world/scopes/<id>/areas` | membership query for a scope |
| `POST /api/world/promote` | promote a graph selection into a child scope with a gateway |
| `POST /api/world/scopes/<id>/grid/generate` | run the recipe (see above) |
| `POST /api/world/scopes/<id>/grid/ungenerate` | revert to unmade |
| `POST /api/world/scopes/<id>/rename`, `/offset`, `/delete` | identity and placement |

Registrars: `routes/world_grid.py` (URLs only) and `routes/world_grid_ops.py`
(the logic). Editor side: `static/js/graph/scope-tree.js`.

## Not done

- **Chunking.** A scope is not yet independently loadable and evictable. That is
  task-401, split into [task-581](../dev_tasks/todo/refactor/task-581-stable-area-ids-and-one-authoritative-location-for-characters-and-items.md)
  (one authoritative location), [task-582](../dev_tasks/todo/world/task-582-chunk-load-unload-and-merge-apis-on-worldgraph.md)
  (load/unload/merge), [task-583](../dev_tasks/todo/world/task-583-global-scope-index-gateway-ways-and-load-before-you-move.md)
  (global index, gateways, load-before-you-move) and
  [task-584](../dev_tasks/todo/world/task-584-cross-chunk-ownership-rules-for-carried-items-triggers-and-delayed-events.md)
  (cross-chunk ownership).
- **Performance.** task-402 measures whether a scope projection is actually cheap
  at scale. Nothing here claims a million-node world yet.

## Related

- [[Simulation Model]] — where a character is, and what a turn is.
- [[Gameplay/Character Spatial Position]] — one `at` per character.
- [[Rooms & Areas]] — what a scope contains.
- [[Graph System]] — nodes, ways, and the projection over them.
- [[Millbrook Falls Town Map]] — the first authored scope hierarchy.

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply` — relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Features** — [[scopes|Scopes]] (#49)

**Neighbouring notes** — [[Doors & Connections]], [[Generated Scenario Review (2026-08)]], [[Graph System]], [[Grid to Graph]], [[Millbrook Falls Town Map]], [[Rooms & Areas]]

<!-- connected:end -->
