---
type: doc
tags: [system/graph]
---

# Grid to Graph

**Task:** [[dev_tasks/review/world/task-496-worldpainter-grid-to-graph-compiler-cells-to-areas-and-ways|task-496]] (the compiler) · [[dev_tasks/review/world/task-400-pines-world-scale-vertical-slice|task-400]] (the recipe sibling path)

`engine/world_compile.py` turns one painted scope grid into normal `area` and `way` nodes.
The compiled world loads through **the same area/way conventions as hand-authored data** —
the engine is unchanged, and nothing downstream knows whether a room was typed or painted.
Output is a `GenerationPatch` (`engine/generation.py`), the same contract the apartment and
item-plan recipes emit, applied by `generation.apply_patch`.

**Size, verified.** 2660 lines — the largest non-test Python file in the repo. (The Feature
Map's "largest file in the repo" is close but not exact: `tests/test_trigger_system.py` is
2851 lines. `routes/graph_ops.py` is next at 1837.)

---

## The pipeline

```
paint (WorldPainter)  ──POST──▶  scope record["layers"]     engine/world_grid.py
                                        │
                                 compile_grid()
                                        ▼
   GenerationPatch{nodes, edges, area_scope_assignments, generated_manifest_updates, report}
                                        │
                            generation.apply_patch(graph, manifest, patch)
                                        ▼
                  area nodes + way nodes + gateways, in the live [[Graph System|graph]]
```

`compile_grid(manifest, scope_id, *, region_merge, link_islands, recipe_id, seed, tick, graph)`
— `world_compile.py:1506`.

**Determinism is absolute:** no `random`, no clock. The same manifest + scope + options give
identical nodes and edges; description fragments are chosen by a stable hash of `seed:cell`
(`stable_digest`, `world_compile.py:169`; the rule is in the module docstring, `:66-68`).

### 1. Cells → regions

The compile set is `set(biome_of) | set(road_of)` — **every painted cell is a place**,
roads included (`world_compile.py:1595`). A road does not add a second node; it *replaces*
the biome as that cell's identity:

```python
def identity(cell):                      # world_compile.py:1667
    road = road_of.get(cell)
    kind = f"road:{road}" if road else f"biome:{biome_of.get(cell)}"
    return f"{kind}|floor:{wg.floor_at(record, *cell)}"
```

`_regions()` flood-fills 8-neighbour cells of the same identity into ordered regions
(`world_compile.py:1058`), so a run of road merges into one road area while a road cell
beside forest stays its own place. The **storey is part of the identity** — otherwise a
classroom merges diagonally with the classroom one floor above it. `default_merge` is the
scope's merge switch; `always_merge` / `never_merge` are per-kind overrides
(`_merge_always_cells` / `_merge_never_cells`, `:1154`/`:1161`).

Two cells are removed from the compile set before regions form:
- **structure** (`:1607`) — a wall, void, window or door occupies its cell and says how it
  connects but never becomes a place; the vocabulary decides via `biomes.cell_kind`.
- **hand-placed areas** (`:1640`) — a cell holding an area you already wrote belongs to that
  area, so Generate can never mint a second place on top.

### 2. Regions → area nodes

One `area` node per region (`:1978`). Its properties (`:1908-1976`) carry what the engine
and the prose both read:

| Property | From |
|----------|------|
| `floor` | the cell's storey index (0 ground, ±1 up/down, unbounded) |
| `surface` | `biomes.ground_surface(road, biome)` — what you stand on, a different fact from the storey |
| `biome` / `road` | both kept, so "a road in the woods" can be described |
| `environment` | the biome's own env dict, or `DEFAULT_ENVIRONMENT` (`:127`) |
| `base_temperature` | the region's aggregated climate — **world scopes only** (`:1950-1961`) |
| `description` | `_area_description()` + `classify_company()` — the place's character from its neighbours' terrain and storey steps |
| `x` / `y` / `cell` | `anchor × CELL_CANVAS_UNITS` (40), so a compiled scope lays out in the shape it was painted |
| `building` | set when the biome `is_building` |
| `windows` | windows facing this place (`:1974`) |
| `child_scope_id`, `tags`, `generated` | scope membership, `outdoor` when world mode, provenance |

### 3. Adjacency → ways

`emit_passage()` (`:1991`) is the single emitter; one `way` node plus two connection edges
(`_way_edges`, `:697`). The adjacency scan uses a **south-half direction subset**
(`_SCAN_DIRECTIONS`, `:107`) so each 8-neighbour pair is visited once from the cell that
owns its southern or eastern end — a hand-placed area's boundary scan uses all eight
(`_BOUNDARY_SCAN`, `:118`) because it does not start from every cell.

Every way records `direction`, `kind` (`open` / `door` / `stairs`), `floor_step`, `floor`
(the **lower** of the two storeys, so it does not depend on which side emitted first),
`surface`, `pass_message`, a `cell` midpoint, and `generated`. Way ids come from the two
area ids in sorted order (`_way_id`, `:651`), which is why a pair scanned from both ends is
still one way.

Passages come from four passes:
- **region boundaries** (`:2117`) — one per adjacent region pair;
- **painted doorways** (`:2149`) — a passable structure cell between two places mints the
  route it stands for, or a `stairs` way when the storey steps;
- **hand-placed area boundaries** (`:2201`) — gives a placed area a way to each painted cell
  touching it; `boundary_overrides` records an author-suppressed seam so a regenerate does
  not resurrect it;
- **island links** (`:2312`) — each disconnected component is joined to the main landmass by
  a **single** way between the closest pair of cells, so a lone outpost is reachable.

`_apply_way_blocking()` (`:352`, called at `:2534`) then closes a deterministic subset of
**outdoor `open` ways only** — never a door or a stairway, which would be closing a
building's own front door.

### 4. Buildings — you go *in*, you do not walk on

A building cell gets an `in` way from **every cardinal side that already has a way**
(`:2241`). Which sides qualify is read from `emitted_pairs`, not guessed from adjacency, so
a side walled off gets no door and a side reached through a painted doorway does.
`_enter_way()` (`:967`) makes it:

- **one-way** where the building owns a child scope, so `out` inside is unambiguous and
  means the doorstep;
- **shut** where it has no interior yet — `current_state: closed` plus a
  `refusal_message` drawn from the building's category (`building_refusal`, `:937`), which
  is the *same string* the palette shows the author.

Diagonals get no door: a door is on a wall, not on a corner (`_CARDINAL_STEPS`, `:123`).

### 5. Gateways between scopes

`_gateway()` (`:828`) mints `way_gateway_<parent>_<child>` between the parent's compiled
cell area and the child's entry area, with `in`/`out` rather than compass opposites
(`GATEWAY_IN`/`GATEWAY_OUT`, `:136`), `see_through: False`, and an `entry_phrase`
("enter the inn", "climb down into the cave") from `_entry_phrases()` (`:720`) — the storey
step comes off `entry_floor`, which each scope records when *it* compiles, so **whichever
scope compiles second emits identical content** (`:2412-2508`, and the parent-first mirror
at `:2484`).

A placement sharing a cell with a hand-placed area is *hand-gated* — reported, never minted,
because the author's own way is the seam (`:2454`).

---

## How it is invoked

| Caller | Where |
|--------|-------|
| `POST /api/world/scopes/<id>/grid/generate` | `routes/world_grid_ops.py:1062` — the production path. Compiles, checks `max_nodes` (default 20 000, `:1077`), **snapshots**, then `apply_patch` (`:1084-1090`). A second call is 409 unless `allow_regenerate` (`:1048`). |
| `ZoneManager.materialise()` | `engine/zones.py:298` — lazy materialisation when somebody approaches or a schedule fires. Refuses a `baked` zone (`:276`) and uses a `seed` derived from the release, not a fresh one. |
| `preflight()` | `routes/world_grid_ops.py:253` — the same conditions as advice, shipped in the grid payload so the editor can show blockers before the click. |

A scope carrying a **`recipe`** takes a different branch of the same endpoint
(`_generate_from_recipe`, `:1097`) — a declared recipe instead of a painted grid, emitted
through the same `apply_patch` contract. That is the path
`tests/test_pines_slice.py::TestGenerationEndToEnd` exercises; the *painted-grid* path is
covered by `tests/test_world_compile.py`.

---

## Constraints worth knowing

- **`floor` is a storey index, not a material** (`world_compile.py:54-62`). An earlier
  revision put the material on `floor` and heights on a separate `elevation`; both were
  wrong and are gone. What you stand on is `surface`.
- **`paint_policy`**: `canonical` by default (may be regenerated on request), `baked`
  opt-in (compiled once, then hand-authored). A `baked` scope **does** compile — it holds
  hand-authored areas *and* it can hold paint, and the two live side by side
  (`:1526-1534`).
- **Only world scopes get cliffs and climate.** `outdoor = mode == "world"` (`:1552`) gates
  cliff phrasing and `base_temperature`; a hall is not −8 °C because someone painted arctic
  on it.
- **Floors inform prose; they gate movement later.** A storey step makes a `stairs` way and
  a cliff phrase today; `climb_required` is recorded for task-525 to decide
  (`_climb_step`, `:1202`).
- **Determinism is testable.** `tests/test_way_blocking.py:352` compiles the same manifest
  twice and asserts the patches are equal.
- **The report says what went wrong, not just the counts** (`:2544-2634`): structure cells
  dropped, thresholds joined, gates with a place on one side only, unknown taxonomy ids,
  unknown climates, mixed-climate regions, islands linked, areas with no exits, placed areas
  nothing reaches, gated climbs, and blocked ways with their blocker counts.

---

## Design note

`docs/design/worldpainter-knowledge-and-fog.md` — "WorldPainter grids, belief-based travel,
and fog of war". It is the target architecture this
compiler is one step of: the grid as the spatial substrate, belief-based travel over it,
and fog of war as the known set. Its `Related:` header points at
`docs/design/world-environment-taxonomy.md` (the tile vocabulary) and
`docs/design/reversibility-contract.md`.

---

## Code map

| Module | Role |
|--------|------|
| `engine/world_compile.py` | the compiler — regions, areas, ways, gateways, buildings, blocking, preflight |
| `engine/world_grid.py` | the painted record: `PAINT_LAYERS`, cell keys, `floor_at`, placements |
| `engine/biomes.py` | `cell_kind`, `is_building`, `is_stair`, `merge_rule`, `ground_surface` |
| `engine/generation.py` | `GenerationPatch` / `apply_patch` — provenance and the once-only guard |
| `engine/zones.py` | lazy materialisation caller |
| `routes/world_grid_ops.py` | the Generate endpoint and `_grid_payload` |
| `tests/test_world_compile.py` | the mapping (112 tests) |
| `tests/test_zones.py`, `tests/test_way_blocking.py`, `tests/test_open_sky.py` | the zone, blocking and determinism paths |

---

## Related docs

- [[WorldPainter]] — the authoring surface that produces the grid
- [[World Scopes]] — placements, promotion, `baked` scopes
- [[Rooms & Areas]] · [[Doors & Connections]] · [[Way Properties]] — what the compiled nodes are
- [[Graph System]] · [[World Scopes]] — where they land

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply` — relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Read next** — [[WorldPainter#Known constraints]]

**Features** — [[grid-to-graph|Grid to graph]] (#48)

**Neighbouring notes** — [[Doors & Connections]], [[Generated Scenario Review (2026-08)]], [[Graph System]], [[Millbrook Falls Town Map]], [[Rooms & Areas]], [[Way Properties]]

<!-- connected:end -->
