---
type: task
status: todo
area: gameplay
priority: medium
wiki: "[[World Building/Movement]]"
---

# task-467: Belief-based travel: heading + budget, maps and hearsay

**Filed:** 2026-09-22
**Related:** task-464, task-466, task-403, task-398, task-9
**Design:** `docs/design/worldpainter-knowledge-and-fog.md` - grids, belief
travel and fog of war as one substrate (ties task-495/496/499).

## What

Travel to a destination held as a belief rather than a known node: heading plus time budget ('go west 2h') moves the character through the world, resolves whatever lies that way (including generated content, task-398/task-9) and validates the belief on arrival. Maps and directions gained from dialogue or items write knowledge (task-403) that upgrades a belief into a known route/area. Shares the heading + frontier primitive with Explore, and interrupts via task-466 (hazard, vital, interesting find).

Once WorldPainter fills the world grid (task-495/496), moving by heading means
**selecting grid cells/edges**: a trigger can attach a target location or a path
to an item or character (a map, a note, a rumour), the walk follows the lattice,
and each entered cell **reveals fog of war** for that character (task-499). The
grid is the shared model for authoring, movement and knowledge.

## Acceptance

- [x] A known route's duration is derived from hop count (`route_hops()` x
      `per_hop_minutes()`), and the timeskip route derives its span from the
      route when `minutes` is omitted.
- [x] A heading moves the character through an exit whose label matches the
      heading (`_move_heading()`), trying every matching exit before the way is
      called shut.
- [ ] A believed destination is resolved from the character's own knowledge
      rather than from world truth, and the arrival outcome (found /
      found-not-there) is recorded against that belief.
- [ ] A heading plus a time budget spends no more than the requested budget, in
      flat per-area steps, and stops at the first refusal rather than continuing
      past it.
- [ ] Reading a map or being told a direction writes into the character's
      existing `known` store and upgrades only the belief it supports.
- [ ] Each area entered on a heading walk reveals fog for that character only.
- [ ] Entering an unmade frontier cell generates content for that character
      (task-398/task-9).

## Progress 2026-09-22 - partial (route duration + heading step)

- [x] `engine/timeskip.route_hops()` / `travel_minutes()` - a known route's
  duration from hop count × `TASK_MINUTES["travel"]`, so travel is a real span
  rather than an arbitrary turn count. The HTTP route derives the span from the
  route when `minutes` is omitted (`POST /api/world/timeskip {intent:"travel",
  target:"..."}`).
- [x] Heading step (`_move_heading`) - "go west" moves through an exit whose
  label matches the heading.
- [ ] Belief destination: resolve a described/unknown target (task-403 knowledge)
  and validate it on arrival (found / found-not-there).
- [ ] Maps and hearsay writing knowledge that upgrades a belief to a known route.
- [ ] Generation-on-discovery at the frontier (task-398/task-9).

## Steps to verify

1. Known route duration
   - expected: `route_hops()` returns the fewest way-steps between two areas,
     `travel_minutes()` multiplies that by the flat per-area cost, and the
     timeskip route derives its span from the route when `minutes` is omitted.
   - observed: PASS 2026-10-20 - `python -m pytest
     tests/test_timeskip.py::test_route_helpers_report_hop_duration
     tests/test_timeskip.py::test_timeskip_route_runs_a_long_span_in_chunks`
     passed (39 passed across the four targeted files in the same run). This
     half is already recorded as done in the progress section.
2. Heading step
   - expected: a heading moves the character through an exit whose label matches
     the heading, and every matching exit is tried before the way is called shut.
   - observed: implemented but NOT exercised live. Measured 2026-10-20:
     `engine/timeskip.py:602` `_move_heading()` exists and does the matching,
     but the HTTP route (`routes/timeskip_ops.py:79`) accepts `minutes`,
     `hours` and `turns` and no `heading` field, so the path is reachable only
     from a soak order (`engine/soak.py:34`, `:55`, `:133`).
3. Belief destination
   - expected: a described destination is resolved from the character's own
     knowledge rather than world truth, and the outcome (found /
     found-not-there) is recorded when the character arrives.
   - observed: NOT run live. Measured 2026-10-20: no belief resolver exists in
     `engine/timeskip.py`; there is no `engine/knowledge.py` module in the repo;
     `timeskip.INTENTS` is still `("idle", "leisure", "search", "explore",
     "travel")`.
4. Map and hearsay teach knowledge
   - expected: reading a map reveals the areas it charts into the character's
     `known` list, and a direction given in dialogue reveals one area the same
     way, so a belief becomes a known route.
   - observed: NOT run live. Measured 2026-10-20: `engine/fog.py:232`
     `teach_from_map()` exists and writes `player.known`, but `rg` for
     `teach_from_map|reveal_area|reveal_sightline|only_known` outside
     `engine/fog.py` returns 0 hits - the module has no importer at all.
5. Generation on discovery at the frontier
   - expected: entering an unmade frontier cell generates content and reveals
     it for that character only.
   - observed: NOT run live. Measured 2026-10-20: `engine/timeskip.py` consumes
     no frontier primitive; the same gap blocks task-482's explore-frontier
     item.

## Why

A map, a rumour or a half-remembered direction is knowledge a character holds
but cannot act on. The engine can already turn a *known* route into a real
duration and step one heading, but a destination the character only *believes*
in has no resolver and no validator, so the belief never becomes a trip and
never turns out to be wrong. That is the difference between a world that
answers to what a character was told and one where the telling changes
nothing. Closing this gap is also what gives the three pieces that already
landed - the heading step, the route duration, the task-466 interrupt path - a
reason to exist as one feature instead of three loose verbs.

## How

Four mechanisms already exist and should be reused, not rebuilt:

- `engine/timeskip.py:route_hops()` (:653) and `travel_minutes()` (:686) already
  turn a known route into a duration; `per_hop_minutes()` (:634) is the flat
  per-area cost.
- `engine/timeskip.py:_move_heading()` (:602) already steps through an exit
  whose label matches a heading, and `_policy_step()` (:493) already dispatches
  it for the `travel` intent when no `target` is given (:543).
- `engine/fog.py:teach_from_map()` (:232) already implements "a map teaches the
  areas it charts" and writes into `player.known` - the same list
  `AgentMind.know_area()` (engine/agent_memory.py:103) writes - and
  `fog.only_known()` (:298) is the honesty filter for prompts.
- `engine/memory_dynamics.py` defines `BELIEF = "belief"` (:42) as the memory
  category for "a conclusion the character holds; may be wrong".

The gap is **wiring, not authoring**. Measured 2026-10-20: `engine/fog.py`
has zero importers anywhere in `engine/` or `routes/` - `reveal_area`,
`reveal_sightline`, `reveal_examined`, `teach_from_map` and `only_known` are
all uncalled. So the remaining work is:

1. **Wire the map teach path.** A map's read or use should call
   `fog.teach_from_map(player, map_item)` and report what it taught. This is
   the "maps and hearsay writing knowledge" half, and it is one call site, not
   a new subsystem.
2. **Add the hearsay path beside it.** A direction given in dialogue is the
   same operation without a map item: resolve the named area and
   `Known.reveal()` it. Both write to `player.known`; there is one store.
3. **Add a belief-destination resolver** in `engine/timeskip.py`, next to
   `_areas_holding()` (:557). It looks the described destination up in the
   character's own knowledge (`AgentMind.knows_area()`, `known_areas`) and
   returns a *believed* target. It must be allowed to return a target that
   does not exist, because a belief may be wrong.
4. **Give a heading a time budget.** `timeskip.INTENTS` (:37) has no
   heading-budget intent and `POST /api/world/timeskip`
   (routes/timeskip_ops.py:79) accepts `minutes`/`hours`/`turns` but no
   heading. Add a heading-plus-budget request form and spend it as repeated
   `_move_heading()` steps at the same flat per-area cost `per_hop_minutes()`
   defines, stopping at the first refusal. The task-466 interrupt path is
   already inside the timeskip loop, so a hazard during the walk interrupts for
   free.
5. **Validate the belief on arrival.** When the walk ends, compare the area
   actually reached with the believed target and record found /
   found-not-there into the character's memory under the `BELIEF` category.
   That record is what turns a wrong belief into a corrected one, and it
   belongs in `AgentMind.remember()` (engine/agent_memory.py:95), not in world
   state.
6. **Reveal fog for the character as each cell is entered.**
   `fog.reveal_area(player, area_node)` (:169) is the call, in the same
   unwired module.

Generation-on-discovery at the frontier (task-398/task-9) is the last piece and
needs the same frontier primitive task-482 is blocked on, so 467 and 482 should
land against one shared primitive rather than two.

## Files

- `engine/timeskip.py` - `INTENTS` (:37), `_policy_step()` (:493),
  `_explore_step()` (:584), `_move_heading()` (:602), `per_hop_minutes()`
  (:634), `route_hops()` (:653), `travel_minutes()` (:686)
- `engine/fog.py` - `Known.reveal()` (:110), `reveal_area()` (:169),
  `teach_from_map()` (:232), `only_known()` (:298); implemented, zero
  importers
- `engine/agent_memory.py` - `remember()` (:95), `know_area()` (:103),
  `knows_area()` (:113), `knows_way()` (:116)
- `engine/memory_dynamics.py` - `BELIEF` memory category (:42)
- `engine/spatial_memory.py` - `build_known_routes()` (:19), `find_route()`
  (:76)
- `engine/soak.py` - the only current carrier of a `heading` order (:34, :55,
  :133)
- `engine/movement.py` - the heading of travel stamped on the connection edge
  (:767)
- `routes/timeskip_ops.py` - `handle_timeskip()` (:79),
  `_requested_minutes()` (:52)
- `player.py` - the `known` list (:378) both teach paths write
- `engine/world_compile.py` - the grid cells a frontier primitive would read
- `tests/test_timeskip.py` - route and heading regression

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

## Reconnaissance (2026-10-20) - still valid

Re-checked the cited code on 2026-10-20. Newer tasks (464 timeskip actions, 466 interrupt evaluator, 499 fog of war, 398 scoped generation, 403 knowledge) landed, but the belief-based travel pieces this card still asks for are not implemented:

- `engine/timeskip.py` still exposes `route_hops()` / `travel_minutes()` and `_move_heading()` (heading step) - those two progress boxes remain accurate.
- No belief-destination resolver, no map/hearsay knowledge writer, and no generation-on-discovery at the frontier exists in `engine/timeskip.py` or `engine/knowledge.py`. `engine/timeskip.INTENTS` = ("idle", "leisure", "search", "explore", "travel") - no "belief" or "heading-budget" intent.
- Note on the word "belief": it does occur in `engine/`, 11 times in `engine/memory_dynamics.py`, but as a *memory category* (`BELIEF = "belief"`, a conclusion the character holds) and in the reflection docs. That is the memory system's taxonomy, not a travel resolver; none of those sites are reachable from `engine/timeskip.py`.

Verdict: PARTLY_DONE is already recorded; the two checked boxes stand, the three unchecked boxes remain open. Card kept in todo.
