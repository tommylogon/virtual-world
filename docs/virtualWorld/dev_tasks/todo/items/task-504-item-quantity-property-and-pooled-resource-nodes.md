---
type: task
status: todo
area: items
priority: medium
---

# task-504: Item quantity property and pooled resource nodes

**Filed:** 2026-09-24
**Related:** 419, 438, 155, 427, 410, 483, 495, 496, 500

## Goal

Introduce a per-node `quantity` property (default 1) so one item node can
represent *many of the same kind*. It is chiefly a presentation and data-model
win — **"1 giant tree"** or **"3 berries"** reads correctly and is far cheaper to
store than hundreds of nodes — but hidden underneath it is the **pooled
resource node**: a bush, plant, rock, thicket or tree that is one node described
plural and depletes by yielding real item copies.

## The distinction

Two different things have both been called "how much of this there is":

| | `uses` (task-155) | `quantity` (this task) |
|---|---|---|
| Attaches to | an individual item copy | the node's identity / the pool |
| Meaning | charges left on **this** copy (a lantern's fuel, a bread's bites) | how many **of this kind** the node stands for |
| Example | one full waterskin `uses: 3` | one thicket `quantity: 40` berries |
| Consumed by | `use` / `consume` (task-424 hook) | `take` / harvest (spawns copies) |
| Default | `-1` (untracked) | `1` |

`quantity` must **not** be folded into `uses`: a stack of 40 berries is not one
berry with 40 charges, and a tree standing in a forest is not something you can
carry at all.

## Model

- `quantity` is an item-node property, default **1**. Absent == 1, so every
  existing item and save is unchanged.
- Display is `"<qty> <name>, <description>"`, e.g. `1 giant tree, its lower
  branches heavy with fruit.` The quantity is shown even when it is 1 (the user's
  example, "you see 1 giant tree") so the prose stays uniform, but see
  *pluralisation* below.
- A **pooled resource node** is an item node whose `quantity` may be large and
  which does **not** move as a whole. On `take`/harvest it:
  1. spawns `k` real item copies (a bounded handful, e.g. `k = min(quantity,
     harvest_size)`) into the taker / area, using the existing
     `effects._hydrate_item(..., always_fresh=True)` path (task-483/410),
  2. decrements the pool's `quantity` by `k`,
  3. at `quantity == 0`, is removed (reuse the task-424 `on_depleted` empty-state
     hook rather than inventing a second teardown).
- Natural resources first: bushes, plants, rocks, thickets, trees, veins.
  Crafted/singular objects keep `quantity: 1` and behave exactly as today.

### Pluralisation and descriptions

- The stored `name` stays singular (`giant tree`); the renderer pluralises from
  `quantity` and the item's authored `plural` (optional property, default
  `name + "s"`). Irregular plurals are authored, not guessed.
- `description` may contain a `{qty}` / `{name}` token; when absent the renderer
  prefixes `<qty> `.

### Harvest yield and per-unit uses

Harvesting is **skill-gated**: a check (Survival / Nature / Medicine, per the
foraging tables) sets how many units the attempt yields, bounded by the pool's
remaining `quantity`. The spawned **unit** is a normal item copy with its own
`uses` — that is the per-unit shelf life, and it is *item-specific*:

- `berries` unit → `uses: 1` (a handful eaten once);
- `apple` unit → `uses: 3` (eats in three bites).

So a pooled `blueberry bush` node (`quantity: 3`, i.e. "3 blueberry bushes") on a
successful harvest might spawn `1–3` `berries` units into the harvester's
inventory and drop the pool to `3 − k`. The pool describes *how many bushes /
how much is out there*; the `uses` on each spawned unit describes *how long one
unit lasts*. The two never fold together.

### Biome and WorldPainter

Pooled resources are the natural output of the world generator: a biome
determines which pool *kinds* exist and their density (a berry thicket in
temperate forest, a gravel bank on a shore, an ore vein on a rocky slope), and
WorldPainter places them per cell / zone. Coordinate pool density with task-427
(population caps), task-410 (food renewal), task-419's anchor budget, and the
WorldPainter scope/zone work (task-495/496/500). The generator authors
**pools**, not individual plants.

### Interaction with existing systems

- **task-155 stacking** merges two carried *copies* (uses add). Pooled nodes are
  the other direction: many-in-one in the **world**, spawning copies on take.
  `stackable_twins` must not treat a pool and a single copy as twins.
- **task-196 `use N ... on`** already parses an amount; harvest reuses that
  parse so "take 3 berries" is natural.
- **Weight**: a pooled node has no carry weight until copies are taken; the
  carried copy's `weight` is the per-unit weight. `carry_weight.py` reconciles
  per-copy only.
- **foraging (task-483)**: `find_or_spawn` today spawns one fresh copy per find.
  It should be able to target an existing pool (find *into* the thicket) before
  falling back to spawning a standalone copy.
- **task-419 anchors / task-438 proxy resource nodes**: these are *related but
  not the same*.
  - **task-419's "pooled resource anchor"** is the closest overlap: the same
    behaviour (one node "described as a quantity", spawning a bounded handful on
    take/use, "same model as the berry thicket"), but framed as a *positioning/
    anchor-budget* device. It treats "quantity" as presentation only and adds no
    stored property. task-504 supplies the stored `quantity` model it assumes.
  - **task-438's "proxy resource node"** is a *different mechanism*: on region
    split it clones the existing **stateful producer** (the berry bush's
    `on_tick` grow → `spawn_item` into a container, capped by `contains_count
    berries < 10`) once per generated child so yield scales with child count,
    "described plural". It is producer-cloning for generation, not a counted
    pool; a stored `quantity` pool could *replace/simplify* it later, but they
    are not the same feature. Coordinate caps with task-427 (population) and
    task-410 (food renewal).
- **`apple_tree.json`** (`uses: 3`, `actions: examine,take,drop`) is the poster
  child for the bug this fixes: a whole tree should not be carryable. It becomes
  a pooled node (`quantity: 3` apples, tree itself not takeable).

## Acceptance

- An item with no `quantity` property behaves exactly as today (full suite
  baseline unchanged).
- An area renderer shows `1 giant tree` for `quantity: 1` and `40 berries` for a
  thicket, in **both** perception paths (`area_description.py` and
  `scene_snapshot.py`) — one shared helper, no re-implementation (room_perception
  charter).
- `take 3 berries` from a pool of 40 yields three real `berries` item nodes and
  leaves the pool at 37; taking the last unit removes the pool node.
- A pool is never picked up whole, and never merges with a carried copy.
- Save/load round-trips `quantity` and the plural override.
- Authored singular/irregular plurals are respected ("1 mouse" / "3 mice").

## Work plan

1. **Renderer + property (slice 1).** Add `quantity` (default 1) to
   `effects._hydrate_item` passthrough and library schema; add one shared
   `describe_item_quantity(node)` helper beside `room_perception` item listing;
   wire it into `area_description`, `scene_snapshot`, `narration`, `examine`,
   and the take-not-found list. Tests: default unchanged, singular/plural,
   capped.
2. **Harvest (slice 2).** Pooled-resource take/use: bounded spawn via
   `_hydrate_item(always_fresh=True)`, decrement, remove at zero via the
   task-424 depletion hook; reuse task-196 amount parsing. Tests: partial,
   exact, over-take, last-unit removal, weight.
3. **Authoring + data (slice 3).** Convert `apple_tree.json` and the camp berry
   thicket (currently an `on_tick` grow + `spawn_item {into: container}` capped
   by `contains_count berries < 10`, `kraktooth_goblin_camp.json`) to the pooled
   model; `lint_library` check for `quantity`; scenario tool + soak to confirm
   supply is unchanged and behaviour stays 23/23.
4. **Integration (slice 4).** `find_or_spawn` finds into an existing pool when
   one is present; align with task-419 anchor budget and task-438 proxy cloning.

## Non-goals

- Currency / abstract counters (a separate wallet concept if ever needed).
- Stacking carried copies — that stays task-155.
- Renaming display names on collision (ids only; project constraint).

## Verification

- `python -m pytest tests/test_item_quantity.py tests/test_item_actions.py tests/test_scene_snapshot.py tests/test_forage_tables.py -q`
- `python -m pytest -q` against the documented baseline (no new failures).
- Week soak on the camp: food supply and 23/23 outcome unchanged.
