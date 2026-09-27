---
type: task
status: review
area: world
priority: high
---

# task-561: Building-type taxonomy: pick a kind for a cell

**Filed:** 2026-09-27
**Related:** task-497 task-560 task-562 task-566

## Goal

The author wants to select a *building type* per cell — residential, religious,
shopping mall, market, fast food, mansion, castle — and have it be the cell's
identity, so a painted town is more than a column of coordinates. Extend the
taxonomy with a settlement vocabulary, so a cell painted `inn` compiles with the
right tags, prose and distribution. Pairs with task-560: a type without a name is
`Building 3,4`, and a name without a type is a label with no behaviour.

## Acceptance

- [x] **Building types are biomes, not features.** A building is a *place* — a
      cell with an identity and prose — so it belongs in `biomes`. The file already
      had `town`, `village`, `building`, `ruin` and `gate` as **features**, which
      meant painting "building" put a cell the compiler read as a *road*: it merged
      with the street and described itself as a thoroughfare. Those feature entries
      are left alone (removing them is a separate decision) and the real vocabulary
      is added as biomes.
- [x] **31 types across 9 categories** — residential, religious, commercial,
      civic, craft, industrial, military, rural, transport — from the Millbrook map
      and the author's own list: cottage, tenement, inn, tavern, brothel, shrine,
      temple, chapel, shop, market, fast_food, mall, bank, warehouse, smithy,
      workshop, mill, town_hall, watch_house, infirmary, school, library, stable,
      barn, orchard, cemetery, ferry_landing, and the coarse picks `residential`,
      `castle`, `mansion`, `ruin`.
- [x] **Three tag families, so a later task can ask the question an author has**:
      `building`+`settlement` (it is a made place), a category (the coarse pick),
      and purposes — `sleeps`, `food`, `drink`, `hygiene`, `trade`, `craft`,
      `worship`, `medical`, `storage`, `transport` (what a character might want it
      for; task-566).
- [x] **A building is exempt from the wild-country contract, deliberately.** The
      validator demanded a forage tag and resource/hostile distribution for every
      biome; nobody forages berries off a smithy's wall and no wildlife spawns in a
      bank, so `biomes.validate` now skips those checks for a record tagged
      `building`. Written as a documented exemption, not an omission.
- [x] **The palette is pickable.** 47 biomes in one column is unusable, and the
      question when painting a settlement is "which *building*", so the vocabulary
      endpoint now ships `tags` and the editor groups the biome list into a
      Buildings section sorted by category (disabled separator options, since
      `select` cannot nest and a header must not be paintable).
- [x] **`terrain: "urban"`, which is currently a no-op on purpose.** The prose
      classifier has classes for forest/rock/water/farm and falls through to
      `open`; giving buildings a new class would apply to wilderness cells too.
      A building reads as `open` until a settlement register is designed.
- [x] **Tests.** `tests/test_biomes.py` now states the contract as it actually
      is: *every wild* biome is forageable and has distribution rules, and a
      building is exempt. A building is still a biome — the exemption is not a
      way to smuggle in a record with no name or no surface.

## Verified

`biomes.validate()` is clean on the shipped 47-biome taxonomy, and a tavern cell
compiles to an area tagged `['building', 'settlement', 'commercial', 'food',
'drink']` (see task-560's verification) — the hook task-566 needs is already
carried on the node.

## Not here

- **A type does not yet change what a place *does*** — no entering a building
  (task-563), no generated interior (task-567), no `urban` prose register.
- **The stale feature entries are still there**, so `building` and `town` are
  paintable in two senses. Worth a decision: drop them, or keep them as paintable
  *districts* (a `town` cell being a knot of streets is a reasonable thing).
