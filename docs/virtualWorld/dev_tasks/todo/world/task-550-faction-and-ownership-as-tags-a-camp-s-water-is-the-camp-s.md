---
type: task
status: todo
area: world
priority: high
---

# task-550: Faction and ownership as tags: a camp's water is the camp's

**Filed:** 2026-09-27
**Related:** task-549

## Goal

Areas carry tags but no owner, so the goblin camp's single water source and waste disposal are a shared resource with no claimant. Make faction and ownership tag-based so using someone else's resource is an event.

## Measured (2026-09-27) — nobody owns anything

Areas carry `tags`, `cell`, `x`/`y`, `description`, `world_scope_id` and
per-faction description keys, but **no owner and no faction**. `goblin_camp` is a
*tag on a node*, not a claim on it.

That has a measured consequence. In the Kraktooth goblin camp:

- 84 areas, of which **one** carries a `RELIEF_TAGS` tag (`Waste Disposal`) and
  four carry a `DRINK_TAGS` tag (`Murk Lake`, `Raven River`, `Water Source`,
  `item_water_skin`).
- 23 goblins and 5 humans share that one `Water Source` and that one
  `Waste Disposal`.
- **4 of the 5 humans start in Eldenford** (the farmer starts at the neighbouring
  Abandoned Farm, the road guard on the Human Road) and **all 5 end up living in
  the goblin camp** after a 3-day run. That is emergent, not authored — and it is
  the clearest available evidence that resources have no claimant, because the
  only place that satisfies survival wins outright regardless of who is there.
- When a human drinks from the camp's water, **nothing is recorded at all**. There
  is no state for "someone took mine" and no event, so the situation is silent.

## Tag-based, as the author intends

Faction and ownership are both expressible as tags, which needs no new field and
no migration: a character carries its faction, an area carries the faction that
holds it, and "mine" is a comparison. A `civilization` tag already exists on
Eldenford and is currently doing nothing.

## Open decisions

1. Is ownership a tag on the area, or derived from the area's *scope*? The goblin
   camp is a WorldPainter scope (`deep_woods_2`, 21 `area_placements`), so
   ownership may be free — the scope already is a claim.
2. Is a road or a border area owned by nobody, or by both?
3. What happens on a contested use — an event, a vital, a relationship delta, or
   all three?

## Acceptance

- An area can name who holds it, and a character can tell whether a place is
  theirs.
- A non-owner using a held need-resource produces a recorded event, not silence.
- A test asserts the whole-cast ownership map, so an unowned shared resource is
  visible in a test failure rather than only in a dashboard.

## Related

- task-549 — the same tag idea applied to characters
- task-552 — fear, which is the reaction this is supposed to produce



- TODO
