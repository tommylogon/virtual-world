---
type: task
status: todo
area: world
priority: medium
blocked_by: [task-439]
related: [task-624, task-646]
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

## Triage 2026-10-02 (wt/graph-render) — blocked, not attempted

Checked the two things that would have to be true for a safe stored-name rename,
and neither holds yet, so this is left in `todo` with `blocked_by: [task-439]`
and `related: [task-646]` rather than migrated:

1. **The lookup layer is still name-keyed, and task-439 owns fixing that.**
   `engine/serialization.py` writes `rooms_serialized[node.name]`, and
   `Player.current_area` holds display names (23 distinct values in this
   scenario). Replacing coordinate names with shorter, reuse-prone nouns
   ("Bridge", "Road") before task-439 lands would make two areas collide in the
   save — exactly the failure 439 exists to prevent. 439 is still `todo`.
2. **The rename moves three stores together** — the area `name`, the 326
   `area_from`/`area_to` endpoint strings, and the 102 that already hold ids —
   plus the task-646 registry-id surface in the library cluster. That is the
   filer's own "do 638 and 646 as one change" and needs a coordinated session,
   not a unilateral edit from the graph lane.

**What is already true (so the user-visible half is not blocked):**

- The display half shipped with task-624: `display_area_name()`
  (`engine/matching.py:72`) strips a trailing `(world N,M)` / `(Eldenford
  interior N,M)` suffix, so narration reads "you are in Road", not "Road
  (world 10,4)".
- The WorldPainter picker that this note calls "the sidebar" **already
  disambiguates**: `_areaBar()` (`static/js/worldpainter/editor.js:1383-1433`)
  groups areas by scope, appends `(x,y)` to each placed area
  (`a.name + ' (' + x + ',' + y + ')'`), and renders placed areas as
  `📍 <name> (x,y)` chips. Graph/sidebar node lists render the raw node name,
  which for compiled areas already carries the coordinate suffix. So the
  "five indistinguishable Road entries" reading does not reproduce in the
  current UI; the surviving issue is the stored name itself, which is 439/646's.

No code or scenario data was changed by this lane.