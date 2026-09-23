---
type: task
status: todo
area: graph
priority: high
---

# task-438: NL editor region decomposition — add child areas to, and split, a region node

**Filed:** 2026-09-21
**Depends on:** task-439 (canonical area identity in save + lookups — hard prerequisite),
task-387 (NL editor + staging), task-9 (`engine/population.py`)
**Related:** task-397 (world scopes), task-398 (deterministic structure generation),
task-393 (validator triage), task-324 (domain tags), task-427 (population caps),
task-410 (food renewal), task-411 (attention budget / fidelity tiers), task-422 (NL editor budget)

## Goal

Type this into the NL editor and get a reviewable staged graph patch:

> "Add a creek margin, a rocky rise, and a deeper interior to the Deep Forest."
>
> "Split the Deep Forest into: forest edge, undergrowth, deep interior, creek margin,
> rocky rise — instead of one node."

The LLM interprets the request and authors the **content** (names, descriptions,
features, tags, ambience). The **topology** — node creation, way minting, boundary
retargeting, id casing, contents migration — is deterministic code. This is task-398's
generator contract applied to an *existing* region instead of an unmade scope.

## Problem

`area_deep_forest` is one node with six outbound ways (Raven River, Old Dwarven Ruins,
Northern Hills, Human Road, Abandoned Farm, Murk Lake) and seven inbound
(`kraktooth_goblin_camp.json:2539+`). Six regions have this shape — `northern_hills`,
`murk_lake`, `blackmarsh`, `raven_river`, `eldenford`, `human_road` — and the library
`data/library/areas/eldenford.json` is 15 lines with `"exits": []`, its contents
("farms, houses, livestock, a smithy, an inn, a market, and guards") left as prose.

The camp interior, by contrast, is correctly decomposed: `area_chiefs_pit` is a hub with
`way_pit_to_*` passage nodes to ~20 leaf areas. The exterior was never decomposed.

The NL editor already has the mutation primitives — `create_node`, `connect_areas`,
`attach`, `spawn_library_item`, `link_to_library` (`static/js/nl-editor/tools.js:291-441`)
— and a staging buffer with deterministic minted IDs, so chains
*create → connect → attach* resolve before commit. What it does **not** have is a
*topology operation*: one intent → N areas + internal ways + boundary re-homing, planned
deterministically. Asking a small local model to hand-assemble six areas and ten ways
through 25 individual tool calls is how `Generated Scenario Review (2026-08).md` ended
with 9 broken scenarios out of 13.

## Two verbs, two phases

### slice 1 — `add_areas` (ships first; no retargeting)

Append N child areas to a region and connect them to it. The region node is **retained**
as the hub, so all six existing boundary ways keep pointing at it, unchanged. Nothing
dangles, no save key churns. The result mirrors `area_chiefs_pit` + `way_pit_to_*` —
the precedent already exists in the same scenario file.

### slice 2 — `split_area` (the hard half)

Decompose the region: create children, connect them internally, **re-home every boundary
way** to the correct child, then demote the region node to a grouping anchor. Requires a
gateway-assignment rule and a rollback-safe atomic create+update Apply.

## Non-negotiable properties (task-398 generator contract)

Deterministic · seedable · reviewable before Apply · idempotent (a second run must not
duplicate) · provenance on every generated node · never overwrite manual edits ·
**report** unresolved assignments, never silently substitute.

## Design

### Anchor rule (v1): never delete the region node

On `split_area`, retag the region node `region` and keep its id. Deleting it would dangle
every `way_*` edge and every spatial relation, and — given task-439 — would also churn the
save's area keys. The retained node becomes the grouping anchor, forward-compatible with
task-397's `properties.world_scope_id`.

### Children: authored inline or pulled from the library

```jsonc
"children": [
  { "name": "Creek Margin", "approach": "east",
    "description": "...", "tags": ["forest", "water_margin"],
    "features": ["creek", "reeds"] },
  { "library_area": "frozen_thicket", "name": "Thicket", "approach": "north" }
]
```

A library child imports `description` / `environment` / `tags` / `features` but **not its
`exits`** — the planner mints the ways, so `frozen_thicket`'s hardcoded exits to
`Snowbound Hollow` do not drag in a dead winter sub-graph. The library already holds the
right vocabulary (`weeping_willow_hollow`, `frozen_thicket`, `frozen_stream_crossing`,
`frozen_lake_clearing`, `marsh_trail`, `stream_bank`, `rocky_slope`, `willow_gap`), so
"a hollow / a thicket / a crossing / a rocky rise" can be reused rather than invented.

### Gateway assignment (slice 2)

Each child may declare `approach` / `cardinal`. A boundary way is re-homed to the child
whose `approach` matches the way's `cardinal` / `direction`. Anything unmatched is
**reported** as an unresolved pool in the preview (task-398: "may not substitute
unrelated items silently") — the author assigns it in the tray or re-declares `approach`.

### Connectivity modes

- `hub` — all children off the region node (slice 1 default, matches `area_chiefs_pit`).
- `linear` — a chain; right for a river as a sequence of banks.
- `mesh` — children adjacent per declared `approach`.

Bidirectional ways get four `connection` edges via `MovementSystem.connect_areas`
(`engine/movement.py:96`), matching the existing corpus.

### Boundary-way retarget + contents migration (slice 2)

- Every `way_*` connected to the region is patched (`update_node`) to target the assigned
  child. This is an update to an existing node, so it rides the existing staging buffer;
  Apply must be atomic across creates **and** updates, with rollback.
- Items and characters with an `in` edge to the region are re-homed to a child via
  `attach`, or stay if the anchor is retained.
- A character must never be left in an area that no longer exists; `at` stays 1:1.

### Proxy resource nodes (opt-in)

For each new child, optionally clone one representative stateful proxy — e.g. the existing
berry-bush node (`on_tick` grow, then `spawn_item {into: "container"} `capped by
`contains_count berries < 10`; `kraktooth_goblin_camp.json:1466-1531`). One node per child,
described **plural** ("berry bushes"), so resource yield scales with child count without
authoring individual plants. Co-ordinate caps with task-427 (population caps) and task-410
(food renewal).

### Interim region representation

`properties.region: "<region_id>"` on every child, plus `tags: ["region"]` on the anchor.
No engine change; superseded by task-397's `world_scopes` manifest when it lands.

## Tool contract

Add to `static/js/nl-editor/tools.js`, mirroring the existing schema shape (`tools.js:341-357`):

```jsonc
{ "name": "add_areas",
  "parameters": { "region_id": "string", "children": "array",
                  "connect": "hub|linear|mesh", "populate": "boolean",
                  "replicate_proxies": "array", "seed": "string" } }

{ "name": "split_area",
  "parameters": { "region_id": "string", "children": "array",
                  "connect": "hub|linear|mesh", "gateways": "object",
                  "populate": "boolean", "replicate_proxies": "array",
                  "preserve_region_node": "boolean (default true)", "seed": "string" } }
```

Planning lives in a pure, framework-free module — `engine/decompose.py`, modelled on
`engine/population.py`: `plan_*(...)` is pure and deterministic; `apply_*(plan, spawn,
relate, ...)` takes callables so the engine never imports Flask or a route-private helper.
The NL editor tool stages the returned patch; `tools/generate_scenario.py` may consume the
same planner offline.

## Work plan

1. **Phase 0 — prerequisites.** task-439 (`rooms_serialized[node.name]` →
   id-keyed, and name-based exit/`current_area` lookups made unambiguous). Split areas
   share names ("hollow", "clearing", "crossing") **by design**, so this is not optional.
2. **Phase 1 — `engine/decompose.py` (slice 1).**
   `plan_add_areas(graph, region_id, children, seed) -> DecompositionPatch`
   (nodes, edges, region assignments, unresolved, report, provenance). Deterministic,
   region-scoped id minting: `area_deep_forest_creek_margin`,
   `way_deep_forest_to_creek_margin`. Tests: same seed → same patch; re-run is a no-op.
3. **Phase 2 — `add_areas` tool + staging tray (slice 1).** Wire through
   `static/js/nl-editor/tools.js`, `staging.js`, `ghosts.js`; ghost preview of the new
   cluster; Apply.
4. **Phase 3 — `split_area` + gateway retarget (slice 2).** Boundary-way patching,
   contents migration, unresolved-gateway report, atomic create+update Apply, rollback.
5. **Phase 4 — population wiring.** Point the editor's `populate_area` at
   `engine/population.py`. **It currently is not:** `tools.js:344` describes nine
   hardcoded theme packs (`apothecary, kitchen, garden, study, smithy, warehouse, shrine,
   bedroom, generic`) with canned item lists and NPCs (`tools.js:552-660`); it never reads
   the area's tags, is not seedable, and has no forest/hollow/marsh vocabulary. No
   `populate` route exists in `routes/`. Without this the split produces empty areas.
   Gated on task-324 (23/58 areas tagged, none domain-flavoured; `eldenford.json` is
   `tags: []`).
6. **Phase 5 — validation gate.** Reuse the validator (task-393) before Apply: every edge
   endpoint exists, no duplicate area names, id casing, region coherence, every child
   reachable from the anchor. Refuse to split an already-split region unless `--variant`.

## Acceptance

- "Add a creek margin and a rocky rise to Deep Forest" stages exactly two areas and two
  ways with four connection edges each, ghosts visible, nothing applied until Apply.
- "Split Deep Forest into …" retargets all six boundary ways; the preview shows a table of
  old way → new child; unmatched gateways are listed, not guessed.
- Same seed + same children + clean graph yields an identical patch; a second run creates
  nothing.
- No character is orphaned; `look` resolves; movement to river / ruins / hills / road /
  farm / murk still works end-to-end.
- `python -m pytest tests/ -q -k "not mcp and not emote"`; new `tests/test_decompose.py`
  covers determinism, idempotency, retarget, unresolved gateway, contents migration.
- Reload preserves every generated node and its provenance; a later manual edit to a
  generated child survives a re-run.

## Non-goals

- Replacing task-397's `world_scopes` manifest (this is the interim `region` property).
- Generating wilderness *grids* or district road layouts (task-398's non-goal stands).
- Chunk unloading / projection endpoints (task-401, task-402).
- Re-filling way orientation prose for existing scenarios (task-395 / task-435).
- Unsupervised LLM topology — the LLM never mints ids or picks way endpoints.

## Risks

- **Name collisions** — why task-439 is a hard prerequisite and not a nice-to-have.
- **Travel depth** — `background_simulation._target_step` BFSes exits and returns one hop
  (`engine/background_simulation.py:735-742`), so decomposition needs no new travel code,
  but a region four hops deep costs four turns to reach food. Interacts with
  `minutes_in_turn` (task-436 / task-437). Verify a hungry goblin still eats.
- **Sanitized-id shim** — `background_simulation.py:703-706` documents ways referencing
  `area_chiefs_pit` while the node id keeps the apostrophe. Graph-level case resolution
  now exists (`graph.py:70-77`), but adding 30-40 areas multiplies the surface area for
  this class of mismatch.
- **Budget** — one child with furniture, items, an NPC and a way is a large slice of the
  NL editor's hard-coded 6000-token context (`static/js/nl-editor/agent-loop.js:23`;
  task-422 is still unstarted). Prefer several small `add_areas` calls over one giant
  `split_area`.
