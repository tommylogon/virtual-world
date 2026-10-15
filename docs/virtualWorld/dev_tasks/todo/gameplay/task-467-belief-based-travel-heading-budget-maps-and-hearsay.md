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

## What

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

## Steps to verify

`python -m pytest tests/test_timeskip.py::test_route_helpers_report_hop_duration -q` → passed.

## Why

TODO

## How

TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: game view → enter a believed heading and time budget such as `go west 2h` → inspect the character's resulting area, event stream, and Mind/known-locations view.

Current availability: belief-based heading travel, generation-frontier resolution, and route knowledge learned from dialogue/items are planned. No heading-budget travel or belief upgrade is claimed as available today.

Live steps when available:
1. In a scratch world with a known westward frontier and a character who has not visited the destination, submit `go west 2h` and inspect the travel events.
   - expected: movement spends no more than the requested time budget, follows the chosen heading through the world, and resolves the area reached rather than teleporting to a guessed node.
2. Give the character a map or a direction through a dialogue/item interaction, then ask it to travel to that believed destination.
   - expected: the received information updates that character's existing knowledge and upgrades only the belief it supports into a known route/area.
3. Give the character a hazard, vital interruption, or interesting frontier find during travel.
   - expected: the trip interrupts through task-466's existing follow-up path and reports the actual event; it does not continue past the interruption.
4. Ask the character to recall the destination before and after receiving the map/direction.
   - expected: before learning it, the response represents a belief with uncertainty; after learning it, recall returns the known route without using world truth the character has not learned.

This section is not a claim that planned UI exists or works today.
