---
type: task
status: todo
area: library
priority: high
related: [task-694, task-2, task-409]
---

# task-701: Plan template library: generic plan/schedule templates as versioned library entries

**Filed:** 2026-10-04
**Related:** task-694,task-2,task-409

## Goal

A library entry type for plan templates - generic like items, bound at selection time. Schema: goal; requirements (items with quantities and consumed flag, equipment, area-function, persons, knowledge, ownership, time window); steps as primitive vocabulary; duration in game minutes; success/fail outcome items; skill check with quality tiers. No authored reactions to other characters (actor sovereignty). Registry, versioning, tags and sync reuse the existing library machinery. First templates authored in the HTC fixture world (task-694): sleep, cook_breakfast (the egg), fish-until-quota, scout, trade run.

## Acceptance
- [ ] A `plans` registry exists under data/library/ with the template schema
      (goal, requirements, steps, duration-minutes, success/fail outcomes,
      skill check with tiers) and reuses registry load/save, versioning, tags
      and sync - no bespoke storage.
- [ ] Templates are character-agnostic: every character-specific value is a
      bound parameter; a template file contains no proper names.
- [ ] Requirements reference the condition leaves (task-705); unknown leaves
      fail closed at load.
- [ ] The fixture world (task-694) ships the first five: sleep, cook_breakfast
      (the egg, duration 10 game-minutes, fail: burned_egg, skill Cooking vs 7),
      fish-until-quota, scout-with-water-math, trade-run.
- [ ] A template round-trips save/load byte-stable and validates like other
      library entries.
- [ ] The library browser (fixed in bug-520) lists and edits them.
