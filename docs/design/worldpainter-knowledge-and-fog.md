# WorldPainter grids, belief-based travel, and fog of war

**Status:** design note (target architecture; pieces land across task-495/496/
498/499/500, task-467, task-403, task-411/418)
**Related:** `docs/design/world-environment-taxonomy.md` (the tile vocabulary),
`docs/design/long-horizon-simulation-progress.md` (fidelity tiers),
`docs/design/reversibility-contract.md`

## The insight

Once WorldPainter has **filled the world grid**, the grid is not just an
authoring surface — it is the spatial substrate the runtime reasons over:

1. A **target location** or a **path** can be attached to an item or a character
   by a **trigger** (a map names a place; a note names a road; a rumour names a
   direction).
2. The character **moves by selecting grid cells/edges**, so its route is a walk
   over the painted lattice rather than a hand-authored chain of rooms.
3. As the character walks, it **reveals fog of war** — the known set grows cell
   by cell, and that known set is what the map view draws and what the agent's
   prompt is allowed to contain.

So the grid is simultaneously the authoring model (task-495/496), the movement
model (task-467), and the knowledge/perception model (task-499). That is the
unifying claim this note fixes.

## Pipeline

```
WorldPainter painted grid (task-495)          engine/world_grid.py
        │  compile cells → areas + ways
        ▼
grid→graph compiler (task-496)                engine/world_compile.py
        │  emits GenerationPatch via task-398 contract  engine/generation.py
        │
        ├── areas carry: biome tags (engine/biomes.py, task-497), environment,
        │   floor, world_scope_id, grid cell coordinate (stable frame)
        │
        ▼
runtime graph
        ├── movement: a target/path from an item/character trigger resolves to
        │   grid cells/edges and the character walks them (task-467)
        ├── travel duration: hop count × TASK_MINUTES["travel"] (already done)
        └── reveal: each visited cell is added to the character's known set
                (task-499), reusing player.known + the existing teach path
```

## Contract details

- **Stable frames.** A cell's identity survives feature moves (task-495
  acceptance). The compiler must map a cell to a stable area id so a save made
  before a feature moved still resolves; moves never silently reassign a cell to
  a different biome.
- **Grid-canonical vs baked-and-hand-edited.** **Decided 2026-09-24 (task-496):
  per-zone `paint_policy`, canonical by default, baked opt-in.** A canonical
  zone may be re-compiled through `apply_patch(allow_regenerate=True)`, but a
  re-run is rejected by default so an edit made after baking is never silently
  overwritten; a baked zone compiles once and is hand-authored thereafter. The
  clobber trap (task-289/290/317) applies: a manual edit made after baking must
  not be silently overwritten by a re-compile.
- **Belief, not omniscience (task-467).** A destination held as a *belief* is
  `heading + budget` ("go west 2h"), not a node id. Arrival validates the belief
  (found / found-not-there). A map or directions teach a *known* entry through
  the existing teach path, which upgrades a belief into a known route. Generation
  at the frontier (task-398/task-9) resolves whatever lies that way.
- **Perception stays honest (task-499).** Unknown cells/zones are fog on the map
  view; an unaware agent is not told about unknown areas. This reuses the
  viewer-aware room perception already in `engine/room_perception.py` and
  `player.known` (tests/test_known.py); `EDGE_KNOWN` remains abilities-only.
- **Fidelity tiers (task-411/418).** Attendance is not a hop-count fiction: the
  attended set derives from awareness channels (sound, co-presence, recency,
  hooks). Fog of war is the *knowledge* dimension; attendance is the *simulation*
  dimension — both read the same grid but neither is the other.

## Scope hierarchy: root then zone

A scope with no `parent_id` **is** a root (`engine/world_scopes.root_scope_ids`);
there is no special root record. The literal id `"root"` is only a projection
alias meaning "list the top-level scopes" (`world_scopes.project`), so it must
never be stored as a scope id.

The authoring sequence is therefore:

1. Create the world **root** scope with no parent
   (`POST /api/world/scopes {name, w, h, mode:"world"}`).
2. Create a **zone** with `parent_id` set to an **existing** scope
   (`{name, w, h, parent_id:"<root id>", mode:"town"}`). `handle_create_scope`
   rejects an unknown parent (`Parent scope '<id>' not found`); the child id is
   appended to the parent's `children`. The **id** is disambiguated on collision,
   the **display name** is never renamed.
3. Paint/place on either grid. Placing a feature records `child_scope_id` on the
   parent cell (`world_compile`), and drilling in opens the child's own grid in
   the next mode (`grid-model.nextMode`: world → town → interior).

**Generation is per scope.** Generating a parent compiles only the parent's own
painted grid; the child's grid is **not** compiled as a side effect, so generate
the zone separately. Keep the root coarse — at world scale a town is a single
cell — and put the detail in the child grid, so no level mints thousands of area
nodes at once (the node-count blow-up that freezes the graph view, task-400).

**Linking a zone to its cell (task-496).** Once *both* a parent and a placed
child are materialized, the compiler emits one gateway `way`
(`way_gateway_<parent>_<child>`) between the parent's compiled cell area and the
child's entry area. Entering uses the `in` direction, leaving uses `out`, so the
two levels are one continuous walk without cascading generation. The gateway is
emitted by whichever scope compiles second, so either authoring order links
exactly once; a placement on an unpainted cell links nothing.

## Why not a second state model

The same `world_scopes` hierarchy (task-397) backs the editor grid, the runtime
projection, and the known set. A cell is a scope at the finest painted
resolution; a zone is a scope grouping cells. Movement, reveal, and generation
all address scopes, so there is one addressing model, not three.

One consequence worth stating: because a scope is the load boundary, the graph
view can load **one scope's subgraph** (`world_scopes.project_subgraph`, giving
the areas, interior ways, and present characters/items of that scope only)
instead of the whole world. That is what keeps a densely painted world from
freezing the canvas — the browser is never sent nodes outside the selected
scope, so the node count is per zone, not per world.

## Open decisions

- ~~Grid-canonical vs baked (task-496) — blocking; must be decided before the
  compiler is written.~~ **Decided 2026-09-24: per-zone `paint_policy`
  (`canonical` default, `baked` opt-in); see above.**
- Whether fog is tracked per cell, per area, or per scope (start at area/scope,
  refine to cell only if a painted wilderness is ever walked at cell scale).
- How a path-from-item is authored: a trigger naming a target scope/cell, or a
  map item whose `use` writes the known set directly. task-499 prefers the second
  (reuse the teach path); task-467 needs the first for beliefs with no map.
