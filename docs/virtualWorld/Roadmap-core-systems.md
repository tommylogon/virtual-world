# Core Systems Roadmap

What must be built for the virtual world to be a living, populated, procedurally
populated world — and in what order, because the order is forced by three
verified dependencies.

*Audited 2026-09-27 against the code, not the task tree. Every claim below cites
`file:line`. Companion to [[Roadmap]], which covers the WorldPainter authoring
epic; this file covers the simulation substrate.*

## The short version

**Livesim is done. Do not spend another session on it.** The population
lifecycle, three-tier fidelity model, background simulation, promotion/demotion,
soak orders and timeskip controller-swap are all implemented, seeded, tested and
persisted. The instinct to build livesim next is the most expensive mistake
available right now.

**The actual missing core is the biome→resource consumer.** ~375 lines of
authored, validated, per-biome weighted resource data exist at
`data/worldpainter/biomes.json:1818` and **no code in the engine ever reads
it.** The declaration end is 100% built; the consumer end is 0% built. That is
the single cheapest large win in the repository.

**Order matters because three things block it**, and they block each other in a
fixed sequence: name-keyed serialization silently destroys data at scale →
non-determinism makes "procedural" meaningless → the compiler has a superlinear
path that dies on exactly the noisy paint a generator produces.

## Where the work actually is

270 open tasks. **`review` (164) is larger than `todo` (97)**, so the queue
overstates the backlog and understates the done-ness. The `review` pile is
mostly UI polish; the architectural risk is concentrated in a handful of ids.

| Area | Open | Shape |
|---|---|---|
| ui | 47 | 50 in review, mostly polish — not where the risk is |
| gameplay | 45 | 29 done of 74; genuinely half-built |
| world | 34 | **only 4 done of 39** — the least-finished area |
| characters | 32 | 48 done of 81; healthy |
| graph | 26 | scope fetch + signature dedup landed; virtualisation missing |
| items | 25 | model mature, *content* and *biome wiring* missing |
| triggers | 15 | feature-complete, O(n) scans |
| environment | 9 | nearly done |
| library | 5 | 8 tasks total — the "unified registry" is 3/8 built |

## Layer 0 — Identity (blocks every world-scale task)

`task-446` is ~60% done. The good half is real: opaque `Player.id`
(`player.py:97`), both player indices and `reindex()` (`player_manager.py:24-43`),
`relationship_key()` (`player_manager.py:65-94`), `NodeIDHelper` prefixes
(`node_ids.py:16-52`). The bad half is still open:

- **Serialization keys areas by display name** — `serialization.py:216`
  `rooms_serialized[node.name] = {...}`. Two "kitchen" areas in different scopes
  **silently overwrite each other in the save file**. This is data loss, not a
  performance issue, and it gets worse the more scopes exist.
- **`Player.current_area` is a display name** — `player.py:219`, serialised
  as-is at `player.py:724`, with **47+ references across 10 files**
  (`tick_manager.py:466`, `npc_behaviors.py`, `movement.py`, `lighting.py`,
  `sound.py`, `proximity.py`, `combat.py`, `area_description.py`,
  `player_ops.py`) resolving it back to an id each time.
- **`WorldGraph.load_from_dict` is clear-and-replace** — `graph.py:261-268`.
  No merge API exists, so chunk loading (task-401) cannot be written.

8 of the 9 claims in `dev_tasks/critical-review-scale-2026-09-08.md` are
**still true 19 days later**. Only the editor's scope-scoped fetch was partly
addressed (`static/js/graph/network-manager.js:359-376`, with a full-graph
fallback still present).

**Do:** `current_area` → `current_area_id`; serialise `areas` by `node.id`; add
`WorldGraph.merge_chunk()`.

**Exit test:** two areas with the same name in different scopes survive a
save/load round trip intact, and a character can cross a chunk boundary.

## Layer 1 — Determinism (prerequisite for the word "procedural")

There is a central dice path — `engine/checks.py:87` `roll_dice` — and most
subsystems correctly seed themselves. But **17+ call sites use the bare
`random` module with no seed**, which makes a session unreplayable:

`combat.py:326` (stun) · `npc_behaviors.py:189,216,369,398,475` (wander, dialog,
direction) · `area_statuses.py:245` · `body_parts.py:329` (injury location) ·
`crafting.py:185` · `environment_propagation.py:233,235` · `narration.py:305` ·
`items/transfer_actions.py:151-152` · `tick_manager.py:896,911` ·
`triggers/condition_tree.py:160` · and two *time-based* trigger-id generators
(`trigger_system.py:89`, `serialization_template.py:189,237`).

This matters beyond tidiness. Layer 3 generates a world procedurally, Layer 2
benchmarks it, and the soak telemetry (`engine/soak_telemetry.py:101-106`)
measures it. **If the NPCs roll unseeded dice, none of those measurements mean
anything.** `engine/soak_runner.py:496-501` already demonstrates the correct
save/restore pattern; it is only used for soak tests.

**Do:** one `random.Random(seed)` created at world init, threaded to every
subsystem; replace the bare calls; seed trigger ids.

**Exit test:** the same seed produces a byte-identical trace over N ticks.

## Layer 2 — Compiler scale (the thing that dies first)

The grid compiler `engine/world_compile.py:1087 compile_grid` is linear apart
from one path: `_nearest_cells` (`:1036-1062`) runs a **full-grid BFS per
disconnected component**, driven from `:1862-1866`. That is **O(C × W × H)**.
With `region_merge=False` on a noisy biome paint — precisely the shape a
procedural generator produces, since each differently-painted cell becomes its
own region — C approaches the cell count. A 200×200 checkerboard is ~20,000
components × 40,000 cells.

The only shipped evidence is **1,350 cells** (`data/scenarios/kraktooth_goblin_camp.json:29171`),
and `routes/world_grid_ops.py:1038-1044` carries a hard `max_nodes = 20000`
choke with a comment admitting the problem. **No benchmark exists.** `task-402`
asks for one and is still `todo`.

**Do:** index the component→cell adjacency instead of re-BFS; add the task-402
benchmark; only then raise or remove `max_nodes`.

**Exit test:** a 200×200 procedurally painted region compiles in bounded time,
with a committed measurement.

## Layer 3 — Biome resources: the actual missing core

This is the thing worth doing next, and the reason is unusually favourable.

**What exists.** `data/worldpainter/biomes.json:1818-2194` is ~375 lines of
authored, per-biome weighted resource data, e.g.:

```json
"sparse_forest": [
  { "tags": ["berry","fruit"], "weight": 4 },
  { "tags": ["herb","medicinal"], "weight": 3 },
  { "tags": ["root","food"], "weight": 2 }
]
```

`hostile_distribution` (`:2195+`) is the same shape with `base_chance`,
`per_area_from_settlement`, `max_chance`.

Both are loaded (`engine/biomes.py:131-136`) and both are **fully validated**
(`engine/biomes.py:397-439`, covered by `tests/test_biomes.py`).

**What does not exist: any consumer.** A repo-wide grep for
`resource_distribution` returns the data file, the loader, the validator, the
tests, and one mention in a task writeup. Nothing else. `HOSTILE_KINDS`
(`engine/biomes.py:41`) appears nowhere outside that file and its tests.

**Why the chain is broken in the middle, precisely:**

| Link | State |
|---|---|
| biome → area node tags | **REAL** — `world_compile.py:1451-1459` |
| area tags → foraging chance/flavour | **REAL** — `foraging.py:424-427, 360-375` |
| area tags → population engine | **REAL but inert** — `population_ops.py:65,88` reads tags, but only an explicit HTTP call reaches it, and it returns `{"status":"empty"}` for wilderness |
| **biome distribution → items** | **DOES NOT EXIST** |

That last row is the whole gap. Supporting evidence:

- **`compile_grid` emits zero item nodes.** Its area property set
  (`:1463-1484`) is `tags, floor, surface, environment, description, x, y, cell`
  — no items key, and no call to `population.py` anywhere in the function.
- **No paint layer for items.** `PAINT_LAYERS = ("biome","road","floor","climate")`
  (`world_grid.py:102`); the vocabulary endpoint serves only those four
  (`world_grid_ops.py:266-294`) and does not even expose the distribution tables.
- **The two vocabularies never meet.** I grepped every file in
  `data/library/items/` for the wilderness biome tags — `forest`, `woods`,
  `rocky`, `farmland`, `shore`, `ruin`, `road`, `dense` → **zero matches**. The
  only bridges are `storage`, `trade`, `religious`, all from *building* biomes.
  So a compiled forest yields an empty plan.
- **Every wilderness library area is empty.** 89 areas, 51 with authored items,
  38 with `"items": []` — and the empties are `deep_forest.json:16`,
  `northern_hills.json:16`, `blackmarsh.json:17`, `human_road.json:16`,
  `old_dwarven_ruins.json:17`. Only interiors are stocked.
- **No loot table, spawn weight, drop chance, or rarity exists anywhere.**
  Repo-wide grep for `loot_table|drop_chance|spawn_weight|rarity` → three prose
  hits, zero code. The only weighted tables are skill-keyed
  (`data/library/foraging.json`) and biome-keyed-and-dead.
- **No item↔biome affinity field.** No biome can say "this item belongs here".
- **`quantity` appears nowhere in `engine/`.** Without it (task-504) a thicket
  cannot yield copies and shrink.
- **The forage pool is 12 items** — only 12 library files carry the `forage` tag.
- **`GenerationReport.unresolved_tags`** (`generation.py:48`) is a field built
  precisely for "I asked the library for tag X and it offered nothing", and
  **no recipe ever populates it.** It is the hook this work needs.
- **`lint_library.py` never opens `biomes.json`.** Its only area-adjacent check
  is `area_tag_gaps` (`:223-229`), which asks whether an area has *any* tags —
  not whether the tag vocabulary meets the biomes.

**One warning about the task tree.** `task-497` is filed **done**, and its
acceptance criteria read as behaviour: *"Resource distribution rules exist
(biome → likely items)"*. Its own progress note is honest — *"Delivered as a
data file plus a generic loader/validator; no engine behaviour change"* — but
the closure is optimistic. **Any plan that reads task-497 as "biome resources
ship" is wrong.** Trust the code, not the folder.

**Do, in this order:**

1. Add a biome-affinity field to library items (the missing vocabulary bridge).
2. `task-504` — `quantity` and pooled resource nodes, so a thicket yields
   copies and shrinks. This is the data model everything else needs.
3. A spawner that reads `resource_distribution` and places items into compiled
   areas, populating `unresolved_tags` when a tag resolves to nothing.
4. Widen the forage pool beyond 12; make regrowth an engine model rather than a
   hand-authored trigger idiom (`bush_of_berries.json:18-69` does it by hand).
5. Extend `lint_library.py` to open `biomes.json` and report every biome with no
   reachable item.
6. Make the `population` route chain off generation so wilderness populates
   without a manual click.

**Exit test:** paint a forest, press Generate, and the forest contains berries
and herbs in the proportions `resource_distribution` specifies; the thicket
shrinks as it is harvested and regrows; two runs from one seed are identical.

## Layer 4 — Hostiles, and the wilderness vocabulary

Same shape as Layer 3, but it needs Layer 3's spawner first. Also blocked by
the vocabulary gap above: `plan_population` is correct code fed the wrong words,
which is why it returns empty for every non-interior area.

## Layer 5 — Time and turn order

The clock is a single source (`virtual_world_engine.py:1004-1015`; ticks ×
`time_per_tick_minutes` + clock start) and every action costs 1 minute
(`tick_manager.py:149-150`). That part is coherent.

Two gaps remain: there is **no turn-order source of truth** (`task-437`) —
ordering is an accident of dict insertion order — and no central action-duration
registry (`task-436`). Both block simultaneous mode (`task-533`) and any
multi-character fairness claim.

## Layer 6 — Trigger indexing (scale, not features)

The trigger system is the most complete subsystem in the repo: **23 trigger
types, 41 effect types, 58 conditions**, plus a real static validator
(`trigger_validator.py:165-832`). Do not rebuild it.

But `execution.py` resolves targets by scanning the whole graph —
`:29`, `:47`, `:198`, `:203`, `:228`, `:253` — and `get_edges_for_source` is a
linear scan (`graph.py:130-155`). Every `on_tick` trigger on every item walks
those. Fine at 1,350 cells; a showstopper at 100k. Blocked on graph indexes
(`task-407`).

## Orthogonal — drain the review pile

164 tasks in `review` against 97 in `todo`. Until review means something, every
count in this document is unreliable, and the Roadmap's own note is right that
"if it is not drained, done stops meaning done." Start with the ones the recent
sessions produced, whose acceptance nobody has re-read: task-496, 526, 528,
530, 531, 532, 539, 540, 541, 548, 559, 560, 561, 562, 563 and bug-49…54.

**Architectural risk in that pile is concentrated** in task-407 (edge
indexing), 440 (splitting the 1100-line `virtual_world_engine.py` god object),
442 (trigger blueprint runtime), 480 (skill growth), 495 (recursive scope
grids), 496 (grid→graph compiler) and 527 (graph steady-state perf). The other
~157 are editor polish and can be triaged cheaply.

## What not to do

- **Do not rebuild livesim.** It is implemented, seeded, tested
  (`test_promotion.py`, `test_background_simulation.py`, `test_soak_runner.py`)
  and persisted. Its real gaps are narrow and non-blocking: no test for
  `process_simple_npcs` (`npc_behaviors.py:284`) and none for
  `timeskip.run_policy_step` (`timeskip.py:141`).
- **Do not treat "proceed" as verification.** 3,239 tests, but **no integration
  or E2E layer at all** — no save/load round-trip test, no timeskip determinism
  test, no trigger fan-out test, and no perf baseline. The unit tests are
  strong; the seams between systems are untested, and the seams are where the
  remaining bugs are.
- **Do not trust `done`.** task-497 is the counter-example that matters.
- **Do not remove `max_nodes` before task-402 lands.** That cap is currently the
  only thing standing between a noisy paint and a hang.

## Sequence

```
0  identity (task-446 remainder)      ─┐
1  determinism (17 random calls)       ├─ everything below needs these
2  compiler index + benchmark (402)   ─┘
3  biome resource consumer  ◀── the cheapest large win in the repo
4  hostile distribution + wilderness vocabulary
5  time contract + turn order (436/437)
6  trigger indexing (407 -> 512, 527)
   └─ review drain throughout; integration test layer alongside
```
