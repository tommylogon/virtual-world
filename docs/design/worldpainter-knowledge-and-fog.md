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
WorldPainter painted grid (task-495)
        │  compile cells → areas + ways
        ▼
grid→graph compiler (task-496)  ── emits GenerationPatch via task-398 contract
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
- **Grid-canonical vs baked-and-hand-edited.** task-496 must decide this and
  enforce it. The clobber trap (task-289/290/317) applies: a manual edit made
  after baking must not be silently overwritten by a re-compile.
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

## Why not a second state model

The same `world_scopes` hierarchy (task-397) backs the editor grid, the runtime
projection, and the known set. A cell is a scope at the finest painted
resolution; a zone is a scope grouping cells. Movement, reveal, and generation
all address scopes, so there is one addressing model, not three.

## Open decisions

- Grid-canonical vs baked (task-496) — blocking; must be decided before the
  compiler is written.
- Whether fog is tracked per cell, per area, or per scope (start at area/scope,
  refine to cell only if a painted wilderness is ever walked at cell scale).
- How a path-from-item is authored: a trigger naming a target scope/cell, or a
  map item whose `use` writes the known set directly. task-499 prefers the second
  (reuse the teach path); task-467 needs the first for beliefs with no map.
