---
type: task
status: review
area: gameplay
priority: medium
---

# task-427: Creature spawners, population caps, and a death path

**Filed:** 2026-09-21  
**Depends on:** task-410 (source/fixture pattern, and slice 2 for active sources).  
**Relates:** `spawn_character` (`engine/effect_handlers/spawn.py:195`), combat.

## Gap

task-410 covers **item** sources (plants) and, in slice 2, active item sources
(fishing spot, snare). It records character sources as slice 4 without a task of
their own — and they need three things item sources do not.

A rabbit hole should either breed rabbits or be snared; a deer trail should
produce a deer you can hunt. Those are **character** spawns, and:

1. **Nothing caps them.** `contains_count` counts items *inside* a node, but a
   rabbit hole's rabbits are loose in the world. Without a live count of tagged
   entities an `on_tick` spawner floods the map in a week.
2. **Nothing kills them.** A cap only works if creatures also leave: hunted,
   starved, eaten, old. Without a death path the fourth rabbit ends the
   population forever.
3. **Killing has to yield something.** A carcass is what a dead creature *drops*.
   Do **not** shortcut a trail to "survival check → carcass" — that is a meat
   dispenser the moment the player watches it, which is the background/foreground
   seam we have been careful about all along.

## Design

- **`tagged_count` condition** — count tagged entities in an area (or the world):
  `{"type":"tagged_count","target_has_tag":"rabbit","area":"current","value":4,"op":"lt"}`.
  Generic beyond creatures: "how many goblins are in this room". Register in
  `CONDITION_TYPES` and document with the other conditions.
- **Creature templates** — a library character per species (`rabbit`, `deer`) with
  species tags, vitals, and the behaviour needed to wander/graze. Spawned with
  `spawn_character {character_id, area}`.
- **Spawners are sources, not characters**: an untagged standing fixture with the
  growth-counter pattern (`parameter_reached` + `tagged_count` + `spawn_character`),
  so a burrow is not edible and cannot be hunted.
- **Death yields a carcass** — a loot/drop-on-death hook in the combat/death path,
  producing a food item. Audit `engine/combat.py` first: it is not confirmed today
  that death drops anything.
- **Lifetime** — creatures age/die, and starvation via task-409's needs so the
  population self-limits rather than needing a cull.

## Acceptance

- A burrow spawns a rabbit only while the area holds fewer than N tagged rabbits.
- Killing a creature yields a carcass item that then behaves as ordinary food
  (consumption via task-424's path).
- Population reaches a stable band over a week rather than 0 or unbounded.
- A creature spawner is never itself edible or huntable.
- Deterministic under a fixed seed.

## Resolution (2026-09-24)

Engine pieces:

- **`tagged_count` condition** (`engine/triggers/condition_tree.py`, registered in
  `engine/trigger_validator.py`) — counts live characters/items carrying a tag,
  scoped to `"world"`, `"current"` (the anchoring item's area, else the active
  actor's area) or a named area. `_count_tagged` / `_area_of_node` helpers.
- **`spawn_character` defaults to the triggering item's area**
  (`engine/effect_handlers/spawn.py`) — a burrow spawns rabbits where the burrow
  is, not where the player happens to be. This was the missing piece that made a
  fixture spawner usable.
- **Death yields a carcass** (`engine/ghost.py`): a character whose template
  declares `carcass` (new `Player.carcass_item`, serialized) drops a fresh
  library-spawned food item instead of the human `body_<name>` item. The carcass
  carries the library's authored `on_eat` trigger, so it depletes through
  task-424's path rather than being infinite. `_hydrate_character`
  (`engine/effects.py`) copies `carcass` from the template.

Data (no code change to add a species):

- `data/library/characters/rabbit.json` — creature template, tags
  `animal/rabbit/small/prey`, `carcass: "carcass"`.
- `data/library/items/carcass.json` — ordinary food (`food/meat/carcass`), uses 1,
  authored `on_eat` (Hunger −30, `adjust_uses -1`).
- `data/library/items/rabbit_burrow.json` — untagged spawner: growth counter →
  `spawn_character` gated by `tagged_count rabbit < 4`.

Tests: `tests/test_creature_spawners.py` (14) cover the count/scope/op matrix,
the fifth-rabbit cap, spawn-into-the-burrows-area, the spawner not being edible,
template hydration, creature-vs-human death, the depleting authored eat trigger,
and two separate carcasses from two deaths. `tools/lint_library.py` gains no new
errors; the 24 remaining are pre-existing.

Still open: the week-scale **population band** soak (a scenario that places a
burrow and runs multi-day) — the cap + death mechanics it depends on are done and
tested, but no scenario authors a burrow yet.

## Files

- `engine/triggers/condition_tree.py`, `engine/trigger_validator.py` — `tagged_count`
- `engine/effect_handlers/spawn.py` — spawn into the triggering item's area
- `engine/ghost.py`, `engine/effects.py`, `player.py`, `engine/serialization.py`
  — carcass-on-death + `carcass_item`
- `data/library/characters/rabbit.json`, `data/library/items/carcass.json`,
  `data/library/items/rabbit_burrow.json`
- `tests/test_creature_spawners.py`

## Non-goals

- Ecology, predator/prey modelling, breeding genetics, or taming.
- Multi-species food webs.
- Generated creature lineages (task-404 is life *experiences*, not species).
