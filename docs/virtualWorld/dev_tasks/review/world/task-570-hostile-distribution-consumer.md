---
type: task
status: todo
area: world
priority: medium
wiki: "[[Characters/Creature Spawners]]"
---

# task-570: Hostile distribution consumer

**Filed:** 2026-09-27
**Related:** 

## What

biomes.json hostile_distribution (line 2195) declares base_chance / per_area_from_settlement / max_chance per biome. It is loaded (engine/biomes.py:135) and validated (:418-439) but has no runtime consumer; HOSTILE_KINDS (engine/biomes.py:41) appears nowhere outside biomes.py and its tests. Needs task-569's spawner and the item-affinity vocabulary. Distance-from-settlement is already computable from the world grid.

## Acceptance

- [ ] `data/library/characters/` holds at least one usable hostile definition
      per kind `HOSTILE_KINDS` can roll, with the attributes the character
      loader expects. (Today: `shadow_pelt.json` is the only usable one, and it
      is a single worg.)
- [ ] A runtime consumer calls `roll_hostiles(...)` per area and registers each
      rolled kind as a `simple_npc` `Player` through the existing character
      spawn path, not as a bare graph node.
- [ ] The area's distance from the settlement reaches the consumer, from the
      grid `world_compile` already knows.
- [ ] A hostile appears in a high-chance biome area, does not appear in a
      zero-chance one, and the encounter appears in the event stream.
- [ ] The roll is seeded and the authored distribution, not an emergent side
      effect of walking around, is what decides whether a hostile appears.

## Progress / blocker (2026-10-02)

**Chance model landed and tested** (`engine/world/spawner.py`, task-569's
module): `hostile_chance(biome, distance)` evaluates
`min(max_chance, base_chance + per_area_from_settlement * distance)` clamped to
`[0,1]`; `roll_hostiles(...)` returns the kinds that appear for a seeded roll;
`hostile_character_node(kind, ...)` builds a tagged, generation-stamped
character node. `HOSTILE_KINDS` is now consumed. Covered by
`tests/test_biome_spawner.py` (chance rises with distance and caps; deterministic
roll; tagged node).

**Why it is not wired to a live spawn (blocking, per "never infer runtime from
existence"):** a hostile must become a live simple NPC (a `Player` in the
manager), not a bare graph node - and there is **no usable hostile character
content** to build one from. Re-measured 2026-10-20 across
`data/library/characters/`: exactly **2** entries carry a hostile-family tag, and
neither is usable as-is.

- `anne.json` - tags include `monster`, but it is also tagged `child` and
  `female`. It is a child, not a predator.
- `shadow_pelt.json` - tags include `predator`, and it is tagged `worg`,
  `animal`, `pack`. This is the only real candidate, and it is a single
  animal, so a distribution that rolls several `predator` kinds has one kind
  to roll.

The other two raw matches are not character definitions at all:
`shadow_pelt.json` also carries an item-level `"tag": "hostile"` (its pelt
item), and `the_butcher.json` carries a `"hostile": true` property rather than
a tag. Spawning generic hostiles from code would be inventing content the
taxonomy does not author, which is exactly what the resource path avoids by
reporting `unresolved_tags` instead of substituting.

**Needed to finish:** author hostile character definitions (predator / bandit /
monster) in `data/library/characters/`, then a runtime consumer that rolls at
area occupancy and registers a `simple_npc` `Player` via the existing character
spawn path. Distance-from-settlement from the grid is available (`world_compile`
knows the cells) and can be supplied per area.

Left in `todo`; not moved to review, because the behaviour is not demonstrated
live.

## Why

A biome declaring that the wilderness is dangerous is only half a feature. The
other half is that something actually shows up, and that the *shape* of the
danger is the author's to decide rather than the engine's. Right now
`hostile_distribution` is authored, validated, and then dropped: the chance
model computes the right number and the number goes nowhere.

The reason it goes nowhere is worth stating plainly, because it is a content
gap and not an engine gap. The machinery works. What is missing is the taxonomy
of hostile characters - and the repo's rule is that a mechanic with nothing
authored for it is not a mechanic. Authoring a handful of predator and bandit
definitions is the work; a runtime consumer is the smaller half.

## How

The chance model already exists and needs no change:
`engine/world/spawner.py` provides `hostile_chance(biome_id,
distance_from_settlement, ...)` (`:123`), `roll_hostiles(...)` (`:145`) and
`hostile_character_node(kind, ...)` (`:153`), all covered by
`tests/test_biome_spawner.py`. The distribution data is authored in
`data/worldpainter/biomes.json` under each biome's `hostile_distribution`
(`base_chance`, `per_area_from_settlement`, `max_chance`), and is validated on
load by `engine/biomes.py` (`:418-439`).

Two things have to happen, in this order:

1. **Author the content.** Add hostile character definitions to
   `data/library/characters/` - at least a predator and a bandit - tagged so
   `HOSTILE_KINDS` (`engine/biomes.py:41`) can select them, and with the
   attributes the existing character loader expects. `shadow_pelt.json` is the
   one existing definition close enough to use as a template for shape.
2. **Wire the consumer.** A runtime path that, per area and per occupancy
   check, computes the area's distance from the settlement, calls
   `roll_hostiles(...)` with the biome's distribution, and registers each rolled
   kind as a `simple_npc` `Player` through the existing character spawn path
   (not as a bare graph node). `world_compile` already knows the cells, so the
   distance term can be supplied per area.

The consumer must not fire in a way that inflates the soak baseline. The
roll is seeded (`roll_hostiles` is deterministic for a seed), so the
probability of a hostile appearing in a given area and tick has to be part of
the authored distribution rather than an emergent side effect of walking
around.

## Steps to verify

1. Confirm the chance model exists and is tested.
   - expected: `hostile_chance`, `roll_hostiles` and `hostile_character_node`
     exist in `engine/world/spawner.py` and are covered by a test file.
   - observed: CONFIRMED. `engine/world/spawner.py` exists with the three
     functions at lines 123, 145 and 153; `tests/test_biome_spawner.py` exists
     and covers chance rising with distance and capping, a deterministic roll,
     and a tagged node.
2. Confirm the distribution data is authored and validated.
   - expected: `data/worldpainter/biomes.json` declares `hostile_distribution`
     per biome and `engine/biomes.py` validates it.
   - observed: CONFIRMED. The file exists and `engine/biomes.py` loads the
     distribution (`:135`) and validates its shape (`:418-439`).
3. Confirm there is no runtime consumer.
   - expected: a caller outside the spawner module and its tests.
   - observed: FAILS. Searching `engine/` and `routes/` for
     `hostile_chance`, `roll_hostiles` and `hostile_character_node` returns
     matches only inside `engine/world/spawner.py` itself. No route or engine
     module calls them.
4. Confirm there is usable hostile character content.
   - expected: character definitions a spawner can instantiate.
   - observed: FAILS. Across `data/library/characters/`, exactly 2 entries carry
     a hostile-family tag: `anne.json` (tags include `monster`, but it is also
     `child` and `female`) and `shadow_pelt.json` (tags include `predator`,
     with `worg`, `animal`, `pack`). The only genuinely usable one is
     `shadow_pelt.json`, a single animal. Two further raw string matches are
     not character definitions: an item-level `"tag": "hostile"` in
     `shadow_pelt.json` and a `"hostile": true` property in `the_butcher.json`.
5. Author the content and wire the consumer, then re-run the live scenario.
   - expected: a hostile appears in a high-chance biome area, does not appear
     in a zero-chance one, and the event stream shows the encounter.
   - observed: not run. The content does not exist yet, so there is nothing to
     exercise.

## Files

- `engine/world/spawner.py` - `hostile_chance` (`:123`), `roll_hostiles`
  (`:145`), `hostile_character_node` (`:153`)
- `engine/biomes.py` - `HOSTILE_KINDS` (`:41`), distribution load (`:135`),
  validation (`:418-439`)
- `data/worldpainter/biomes.json` - the authored `hostile_distribution` blocks
- `data/library/characters/` - where the hostile definitions belong
  (`shadow_pelt.json` is the closest existing shape)
- `tests/test_biome_spawner.py` - the chance model's tests

## Browser UI and intended live verification

Intended UI home: load a scenario with a settlement and authored biomes → inspect the world map/area properties → run the hostile spawner or allow the scheduled simulation tick → inspect generated characters and encounter events.

Current availability: `biomes.json` declares and validates `hostile_distribution`, but this card records no runtime consumer; `HOSTILE_KINDS` is otherwise only referenced by its own module/tests. The distribution consumer is not claimed as implemented.

Live steps when available:
1. In a scratch world, choose two biome areas at different distances from a settlement and inspect their `hostile_distribution` values.
   - expected: the spawner reads the authored base chance, per-area settlement adjustment, and max chance for each biome.
2. Run the same seeded spawn pass in both areas and inspect generated hostile characters in the graph and `/api/state`.
   - expected: each spawned character uses a kind allowed by `HOSTILE_KINDS`; chance changes with biome and settlement distance and is capped at `max_chance`.
3. Repeat the same seed and fixture, then change only the settlement distance.
   - expected: the first run reproduces exactly; only the authored distance term changes the spawn decision in the second run.
4. Let a spawned hostile interact with a character and inspect the event stream.
   - expected: the spawned entity participates through the existing character behavior path; the distribution is not merely displayed as unused biome data.

## Reconnaissance (2026-10-20) - still valid, one count corrected

Re-checked on 2026-10-20. The chance model in `engine/world/spawner.py` remains and `HOSTILE_KINDS` is still only consumed there and in tests:

- `rg` for `hostile_chance|roll_hostiles|hostile_character_node` outside tests returned 0 hits.
- `rg` for `spawner.` (Python callers) outside tests returned 0 hits.

**Correction to the 2026-10-02 note above.** It said the character library holds
*"zero entries tagged predator/bandit/monster/hostile"*. Measured 2026-10-20 by
parsing every file in `data/library/characters/` and collecting `tags`/`tag`:
**2** entries carry a hostile-family tag.

- `anne.json` - tags include `monster`, but it is also tagged `child` and
  `female`. A child is not a predator.
- `shadow_pelt.json` - tags include `predator`, with `worg`, `animal`, `pack`.
  This is the only real candidate, and it is one animal, so a distribution that
  rolls several `predator` kinds has exactly one kind to roll.

Two further raw string matches are **not** character definitions and should not
be counted: an item-level `"tag": "hostile"` inside `shadow_pelt.json` (its pelt
item) and a `"hostile": true` property in `the_butcher.json` (a property, not a
tag).

The card's **conclusion** is unchanged - there is no usable hostile content to
build a live NPC from - but its **count** was wrong, and the 2 that do exist
are the starting point for the authoring work rather than nothing.

**Plan position (2026-10-20).** Newer work touches this card without
superseding it. task-571 (item biome affinity), task-573 (biome coverage
lint) and task-588 (investigate where WorldPainter vocabularies live) all name
task-570 as related. task-588 is an investigation whose stated constraint is
that *"the two consumers this is meant to unblock must keep working whichever
way it lands"* - so whatever task-588 concludes about the data layout, task-570
still stands as a consumer. task-569 (biome resource distribution consumer) is
the sibling: its chance model lives in the same `engine/world/spawner.py`
module, which is why that module exists at all.

Verdict: still valid, still a distinct piece of the plan. Kept in todo.
