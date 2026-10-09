---
type: task
status: review
area: world
priority: medium
related: [task-497, task-557, task-569, task-718, task-745, task-759]
---

# task-758: Biome records: add the climate and neighbour fields the palette needs

**Filed:** 2026-10-09
**Related:** task-497, task-557, task-569, task-718, task-745
**Blocks:** task-759 (the palette detail panel renders these fields)

**Design:** `docs/design/world-environment-taxonomy.md` §"Record shape (target
schema per entry)". The record converges on *some* of that schema — not all of
it, because the rest belongs in separate registries (see "Deliberately not here").

## What

Extend `data/worldpainter/biomes.json` records with the two field groups that are
genuinely **biome data**: `climate` (`temperature`, `rainfall`, `elevation`) and
the adjacency sets (`natural_neighbors`, `unlikely_neighbors`,
`transition_biomes`), plus explicit `engine_tags` / `forage_skills`. Fields are
additive; absent = unknown, never guessed. Add the matching validation to
`engine/biomes.py`.

## Deliberately not here (and why)

The mockup's **Resources / Creatures / Hazards** panels must **not** become biome
fields. The design tasks already sent those elsewhere:

- **Resources** → `data/library/resource_distribution/` (task-718 splits the
  loot tables out of `biomes.json`; task-569 wires the runtime consumer). A
  resource is a tag-intersection against library items, not a per-biome list.
- **Creatures** → `data/library/hostile_distribution/` (same split, task-718).
- **Hazards** → `data/worldpainter/hazards.json`, a category registry
  (task-745), not a biome field.

The palette (task-759) renders those three by reading the **registries** for the
biome's tags — it does not copy them onto the biome record. Baking them in here
would re-centralise exactly what task-718 is trying to decentralise, and create a
second source of truth for spawns.

## Why

`biomes.json` records today are `{name, terrain, tags, surface, descriptions}` —
no climate, no neighbours. The improved palette (task-759) and the adjacency
generator rule — *"a pine forest next to a mountain stream is normal; a tropical
rainforest beside an arctic tundra is bizarre"* — have no data to render or
check. task-497 authored the taxonomy prose; the records never gained the
per-entry fields. (`world-environment-taxonomy.md` §"Gap analysis" records this.)

## How

- **Data** (`data/worldpainter/biomes.json`): add `climate {temperature,
  rainfall, elevation}` and `natural_neighbors` / `unlikely_neighbors` /
  `transition_biomes` per record, drawn from the taxonomy doc. Neighbours and
  transitions are **biome ids** where they resolve; where the doc uses a prose
  noun, prefer an existing id and record any soft noun in an alias map rather
  than inventing a second vocabulary.
- **Engine** (`engine/biomes.py`): extend `validate()` (the one owner) to fail a
  record whose `natural_neighbors` / `transition_biomes` ids do not resolve.
  Expose the new fields through the derivation `handle_painter_vocabulary`
  (`routes/world_grid_ops.py:287`) already uses, so task-759 needs no new read
  path. `clear_cache()` exists and has zero callers — the save/reload story is
  task-589's, not this.
- **Climate vs the paint layer:** the `climate` field here is **per-biome
  descriptive ranges** for the panel. It is not the painted `climate` layer,
  which is a 5-value enum (arctic/alpine/temperate/arid/tropical) with a base °C
  (task-557) and must stay an enum "not a float". Do not couple them.
- **No compiler behaviour change.** Additive data + validation only; existing
  compiled scopes and scenarios stay unaffected.

## Steps to verify

1. Read a populated record from `data/worldpainter/biomes.json`.
   - expected: it carries `climate` and neighbour sets; no `resources`,
     `creatures` or `hazards` key (those live in the registries).
   - observed:
2. `engine/biomes.validate()` with an unresolvable neighbour id.
   - expected: fails loudly with the bad id.
   - observed:
3. `GET /api/world/painter/vocabulary` (or the painter's derived route).
   - expected: the new fields are present per biome entry.
   - observed:

## Acceptance

- [ ] Records carry authored `climate` + neighbour values, from the taxonomy
      doc. **Deferred to the authoring surface (task-589)** — the doc's 170
      entries are wilderness ecotypes that mostly are not shipped ids, and the
      doc gives no numbers, so authoring here would be invention. The schema and
      validation are the deliverable of this task (below); 589 is the right home
      for the values.
- [x] No `resources` / `creatures` / `hazards` key is added to a biome record;
      those stay in the task-718 / task-745 registries.
- [x] `engine/biomes.validate()` checks the shape of `climate` and the neighbour
      lists when present; a regression test proves a malformed climate and a
      non-list neighbour are rejected, and well-formed data passes.
- [x] The painter vocabulary derivation serves the new fields; no new read path.
- [x] Existing taxonomy/compiler output unchanged; targeted tests stay green.

## Resolution (2026-10-09)

Recon changed the picture: the records live in **`data/library/biomes/*.json`**
(106 one-file entries), and the loaders already prefer those dirs — the bundled
`biomes.json` no longer carries `resource_distribution`/`hostile_distribution`.
So the split task-718 describes is **already done at the data+loader level**; this
task did not re-add any distribution key.

Shipped:

- `engine/biomes.py` — `_climate_problems` and `_neighbour_problems`, called from
  the per-biome loop in `validate()`. Present `climate` must be an object whose
  `temperature`/`rainfall`/`elevation` are `[min, max]` numbers with `min <= max`;
  present neighbour lists must be lists of non-empty strings. **Absent stays
  valid** (unknown, never guessed). Neighbour names are *not* forced to resolve to
  a biome id — the doc uses soft nouns ("meadow"), and a resolution rule without a
  shipped wilderness vocabulary would be a second taxonomy.
- `routes/world_grid_ops.py` — `handle_painter_vocabulary` passes `climate`,
  `natural_neighbors`, `unlikely_neighbors`, `transition_biomes` (and `terrain`)
  through the one derivation.
- `static/js/worldpainter/grid-model.ts` — `detailRows` renders authored climate
  ranges and neighbour lists, and invents no row when the field is absent.

**Verified:** `pytest tests/test_biomes.py` → 20 passed;
`node tools/unit/run.cjs` → 645 passed; `build:ts` + `typecheck` clean.

**Named deferral:** the values (which biomes carry which climate/neighbours) are
authored via task-589's vocabulary tab, not fabricated here.

## Files

- `engine/biomes.py` — `_climate_problems`, `_neighbour_problems`
- `routes/world_grid_ops.py` — `handle_painter_vocabulary` field passthrough
- `static/js/worldpainter/grid-model.ts` — `detailRows` climate/neighbour rows
- `tests/test_biomes.py` — 3 validation tests
- `tools/unit/test_worldpainter.js` — detail-rows test

