---
type: task
status: todo
area: world
priority: high
---

# task-496: WorldPainter: grid-to-graph compiler (cells to areas and ways)

**Filed:** 2026-09-24
**Related:** task-495, task-398, task-400
**Design:** `docs/design/worldpainter-knowledge-and-fog.md`,
`docs/design/world-environment-taxonomy.md`

**Overlaps task-398.** task-398 already owns the deterministic generation contract (the `GenerationPatch` shape, provenance, apply-once, "a manual edit survives a second run"). This task is the *painted-grid recipe* — wilderness/road/biome tiles + region-merge — that should emit a `GenerationPatch` through 398's contract rather than a parallel generator. Decide whether to fold it into 398 or keep it as the grid recipe.

## Goal

Compile a painted scope grid into the existing area/way node+edge format: cells become areas (optionally region-merged by biome via flood-fill), adjacent cells get ways (direction, open/see_through, floor), and areas get tags, environment, floor and world_scope_id. Descriptions are deterministic templates over (own tile + 4 neighbours + exits/directions), reusing visible_in_direction (engine/area_description.py); no LLM at lattice scale. Emit into the scenario/library formats so the engine is unchanged. Decide grid-canonical vs baked-and-hand-edited per zone to avoid the task-289/290/317 clobber trap.

## Acceptance

- A painted grid compiles to areas + ways in the existing scenario/library formats, loadable with **no engine change**.
- Optional region-merge collapses contiguous same-biome cells into one area (flood-fill); a test shows fewer nodes with identical topology.
- Ways carry `direction`/open/`see_through`/`floor`; areas carry tags, `environment`, `floor`, `world_scope_id`.
- Descriptions are deterministic from (own tile + 4 neighbours + exits) with **no LLM call** — sample: "a road running east and west, sparse forest to the north".
- Grid-canonical vs baked-and-hand-edited is decided and enforced (edit-after-bake is not silently clobbered; see task-289/290/317).
