---
type: task
status: review
area: graph
priority: medium
---

# task-564: Per-kind merge rules: hallways and classrooms merge, buildings do not

**Filed:** 2026-09-27
**Related:** task-561 task-562 task-496

## Goal

Region merging is one global switch per scope, but a high-school plan needs different rules per kind in the same grid: a run of hallway cells merges into one corridor, 4 classroom cells merge into one room, and adjacent building cells never merge (a terrace of houses is several buildings, not one). The machinery already exists (world_compile._regions with an identity function); it needs the identity to carry a per-kind merge rule instead of the whole scope sharing one toggle. Also decide what the 'merge' control means once this lands - a default per mode, with the toggle as an override.

## Acceptance

## Acceptance

- [x] **A run of `hallway` is one corridor, whatever the merge switch says.**
      `merge: always` is declared on the record (`hallway`, `corridor`) and
      overrides the scope's `merge same-biome` checkbox. A ten-cell corridor
      painted with merging off is still one corridor, not ten anonymous rooms.
- [x] **A terrace of cottages is three cottages.** Every `building` record is
      `merge: never` without 31 records having to say so —
      `biomes_mod.merge_rule` reports a building as never-merge from the `building`
      tag. Adjacent `cottage` cells stay three areas with the merge switch **on**.
- [x] **Everything else follows the switch**, unchanged from before: two
      `dining_hall` cells are two rooms with merging off and one with it on. A
      wilderness scope compiles identically to how it did before this task, so no
      existing map changes shape.
- [x] The rules are **per kind, resolved in one place** (`_regions`, via
      `always_merge` / `never_merge` / `default_merge`), so a half-merge — a run
      broken in the middle — is impossible.
- [x] The rule is **vocabulary, not code**: a modder adding a `cellar` or a
      `subway` writes `merge: always` on the record and gets the behaviour.

## Notes

- The earlier draft of this called for 4 classroom cells to merge into one room.
  That is the *scope switch's* job, not a per-kind rule: a room's footprint is
  what the author paints, and making rooms merge unconditionally would make it
  impossible to have a study next to a bedroom. Rooms follow the switch; only
  circulation (shape, not count) and buildings (a plot, not a run) are per-kind.
