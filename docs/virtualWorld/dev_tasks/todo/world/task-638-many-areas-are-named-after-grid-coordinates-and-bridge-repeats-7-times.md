---
type: task
status: todo
area: world
priority: medium
---

# task-638: Many areas are named after grid coordinates and 'Bridge' repeats 7+ times

**Filed:** 2026-09-30
**Related:** 

## Goal

Names embed '(world N,M)' and reuse common nouns, so several areas are indistinguishable by name. Tommy has confirmed this is the wrong call.

## Acceptance

- TODO

## Measured 2026-09-30 — this is a data migration, and it is bigger than filed

In `kraktooth_goblin_camp`:

| | value |
|---|---|
| areas | 205 |
| name contains a coordinate | **51** — `Road (world 10,4)`, `Sparse Forest (world 10,5)`, `Bridge (world 10,6)` |
| area has a `display_name` property | **0** |
| **ways whose name carries a coordinate** | **326** — the interior scheme: `Sparse Forest (Eldenford interior 10,3)` |
| ways carrying both `area_from` and `area_from_id` | 326 |

Two things this changes:

1. **The display half is already done.** `display_area_name()` (task-624) uses an
   authored `display_name` when present and otherwise strips a trailing
   coordinate, so narration already reads "you're in Road". Verified live:
   seven movement commands, zero leaks. The remaining work here is purely the
   stored name.

2. **The `display_name` escape hatch is currently unused** — 0 of 205 areas set
   it. So the mechanism exists and nothing uses it, which is this audit's house
   pattern again (mechanic built, content absent).

**On the naming itself.** Tommy has already said coordinates in a name is the
wrong call, and the duplication is the sharper problem: `Road (world 10,4)` and
`Road (world 10,5)` are two distinct places called "Road", and the sidebar in the
painted world shows five separate `Road` entries with no way to tell them apart.
Renaming is not cosmetic -- `area_from` on 326 ways holds these strings as the
*resolved endpoint*, so a rename has to update those references too. That is the
same cross-registry coupling flagged in task-646, and it argues for doing 638 and
646 as one change rather than two.