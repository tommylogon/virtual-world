---
type: task
status: todo
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

## Non-goals

- Ecology, predator/prey modelling, breeding genetics, or taming.
- Multi-species food webs.
- Generated creature lineages (task-404 is life *experiences*, not species).
