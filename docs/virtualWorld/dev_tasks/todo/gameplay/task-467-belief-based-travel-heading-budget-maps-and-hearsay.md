---
type: task
status: todo
area: gameplay
priority: medium
---

# task-467: Belief-based travel: heading + budget, maps and hearsay

**Filed:** 2026-09-22
**Related:** task-464, task-466, task-403, task-398, task-9
**Design:** `docs/design/worldpainter-knowledge-and-fog.md` — grids, belief
travel and fog of war as one substrate (ties task-495/496/499).

## Goal

Travel to a destination held as a belief rather than a known node: heading plus time budget ('go west 2h') moves the character through the world, resolves whatever lies that way (including generated content, task-398/task-9) and validates the belief on arrival. Maps and directions gained from dialogue or items write knowledge (task-403) that upgrades a belief into a known route/area. Shares the heading + frontier primitive with Explore, and interrupts via task-466 (hazard, vital, interesting find).

Once WorldPainter fills the world grid (task-495/496), moving by heading means
**selecting grid cells/edges**: a trigger can attach a target location or a path
to an item or character (a map, a note, a rumour), the walk follows the lattice,
and each entered cell **reveals fog of war** for that character (task-499). The
grid is the shared model for authoring, movement and knowledge.

## Acceptance

- TODO

## Progress 2026-09-22 — partial (route duration + heading step)

- [x] `engine/timeskip.route_hops()` / `travel_minutes()` — a known route's
  duration from hop count × `TASK_MINUTES["travel"]`, so travel is a real span
  rather than an arbitrary turn count. The HTTP route derives the span from the
  route when `minutes` is omitted (`POST /api/world/timeskip {intent:"travel",
  target:"..."}`).
- [x] Heading step (`_move_heading`) — "go west" moves through an exit whose
  label matches the heading.
- [ ] Belief destination: resolve a described/unknown target (task-403 knowledge)
  and validate it on arrival (found / found-not-there).
- [ ] Maps and hearsay writing knowledge that upgrades a belief to a known route.
- [ ] Generation-on-discovery at the frontier (task-398/task-9).

## Verification

`python -m pytest tests/test_timeskip.py::test_route_helpers_report_hop_duration -q` → passed.
