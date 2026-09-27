---
type: task
status: todo
area: characters
priority: high
---

# task-549: Species on characters: an animal is not a goblin

**Filed:** 2026-09-27
**Related:** task-545,task-547

## Goal

Characters have no species or faction field at all, so an animal, a goblin and a human are the same kind of thing to the simulation. Add a species/faction identity that the need layer can read.

## Measured (2026-09-27) — there is no species anywhere

- `player.py` has **no** species, faction, or race field. `rg species engine/
  player.py` returns one hit, and it is a comment in `engine/traits.py` about
  temperature thresholds. No file in `data/library/characters/` mentions species.
- Need servicing is a **pure tag intersection**. `engine/background_simulation.py`
  `_has_tag(node, tags)` does `set(tags) & node_tags` and nothing else. The
  vocabularies are `DRINK_TAGS = ("drink", "water", "beverage")` and
  `RELIEF_TAGS = ("latrine", "toilet", "privy", "restroom", "bathroom")`.
- So the question "would an animal use a latrine?" **cannot be answered in either
  direction by the engine.** The goblin camp is tagged `latrine` and a human city
  would be tagged `bathroom`, and that distinction is authored by hand and
  invisible to the simulation. An animal, a goblin and a human all draw from the
  same list.
- The world *already* models the split — but only for narration. 31 of 272 areas
  in the Kraktooth scenario carry `goblin_description`, `human_description` and
  `goblin_knowledge` properties, so a goblin and a human in the same room already
  get different text. What is missing is the same distinction in the
  **simulation** layer, where it would decide who may use what.

## Open decisions

1. **Field or tag?** A `species` field on the character, or a `species` tag the
   existing tag machinery already reads. A tag needs no serializer change and no
   migration, and the world already uses tags this way.
2. **What granularity?** `goblin` / `human` / `animal` is probably too coarse to
   be useful; the goblin camp has a chief, a shaman, prisoners and a farmhand.
3. **What does it gate?** Minimum: need servicing. Then movement (can a goblin
   enter the village?), and narration (replacing the per-faction description
   keys, or complementing them).

## Acceptance

- A character carries a species identity readable by the need layer.
- A test asserts a species can be excluded from a service, so the answer to
  "would an animal use a latrine" is a property of the data and not of the
  author's tag choices.
- Existing characters and scenarios load unchanged.

## Related

- task-550 — faction and ownership, which is the same idea applied to areas
- task-551 — relief anywhere but indoors, which makes the species question matter



- TODO
