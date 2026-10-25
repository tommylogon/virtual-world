---
type: task
status: review
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
- [x] A believed destination is resolved from the character's own knowledge
      rather than from world truth (`resolve_belief_destination`), and the
      arrival outcome (`found` / `found-not-there`) is recorded against that
      belief under `BELIEF` via `AgentMind.remember` (`_record_belief_arrival`).
- [x] A heading plus a time budget spends no more than the requested budget, in
      flat per-area steps, and stops at the first refusal rather than continuing
      past it. (Wired 2026-10-23: the HTTP route carries `heading`; one
      `_move_heading()` step per tick, which is the flat `per_hop_minutes()` cost
      at the one-minute target turn, and the first refusal ends the span.)
- [x] Reading a map or being told a direction writes into the character's
      existing `known` store. (Wired 2026-10-23: charted maps on read/use, and a
      spoken direction in earshot.)
- [x] The write upgrades only the belief it supports (`_upgrade_supporting_beliefs`
      in `engine/fog.py` links newly learned place forms in `Known.reveal` and
      `teach_from_map` to matching `belief` memories on `player.memories`).
- [x] Each area entered on a heading walk reveals fog for that character only
      (wired 2026-10-23: `traversal.hop` sets `active_player` and calls
      `movement.move_to_area`, which now calls `fog.reveal_area`).
- [x] Entering an unmade frontier cell generates content for that character
      (`materialize_frontier` in `engine/fog.py`, wired in `engine/movement.py`
      and `engine/timeskip.py`; covered by
      `tests/test_hearsay_places.py::test_frontier_discovery_generates_content_and_reveals_for_discoverer_only`).

## Progress 2026-09-22 - partial (route duration + heading step)

- [x] `engine/timeskip.route_hops()` / `travel_minutes()` - a known route's
  duration from hop count × `TASK_MINUTES["travel"]`, so travel is a real span
  rather than an arbitrary turn count. The HTTP route derives the span from the
  route when `minutes` is omitted (`POST /api/world/timeskip {intent:"travel",
  target:"..."}`).
- [x] Heading step (`_move_heading`) - "go west" moves through an exit whose
  label matches the heading.
- [x] Belief destination: resolve a described/unknown target (task-403 knowledge)
  and validate it on arrival (found / found-not-there).
- [x] Maps and hearsay writing knowledge (2026-10-23: charted maps and spoken
  directions write `known`).
- [x] Upgrading only the belief a map or direction supports into a known route.
- [x] Generation-on-discovery at the frontier (task-398/task-9).

## Progress 2026-10-23 - the map and fog halves are wired

- [x] **A walked area is taught.** `engine/movement.py` calls
  `fog.reveal_area` at the arrival point. `traversal.hop` sets `active_player`
  before it calls `move_to_area`, so a heading walk writes to the acting
  character's `known` set, not the human's. Covered by
  `tests/test_fog_wiring.py::test_walking_into_an_area_teaches_it` and the
  idempotence case.
- [x] **A charted map teaches on read/use.** `engine/items/examine_actions.py`
  and `engine/items/use_actions.py` call `fog.teach_from_map` when the item
  declares `charted_areas`. Uncharted map props are deliberately skipped,
  because `teach_from_map`'s no-chart fallback hands out every area. Covered by
  `test_reading_a_charted_map_teaches_its_chart` and
  `test_reading_an_uncharted_map_does_not_teach_the_world`.
- [x] **Authored knowledge is route knowledge.** `known_route_areas` unions the
  walked areas with authored `known`/`known_areas`, and
  `routes/memories.py` (prompt block) and `routes/action_handlers.py`
  (`recall path`) both use it. Covered by
  `test_authored_known_area_feeds_the_route_block` and
  `test_authored_known_area_makes_a_path_findable`.
- [x] **Hearsay writes `known`.** `SpeechBroadcaster._teach_places_from_speech`
  scans a same-area line for an area name when the line also carries a direction
  ("go west to the Old Mill"), and reveals that area to every listener except the
  speaker. An idle mention ("I like the Old Mill") teaches nothing. Covered by
  `tests/test_hearsay_places.py` (3).
- [x] **A heading is reachable over HTTP and stops at the first refusal.**
  `routes/timeskip_ops.py` passes `heading` to both `advance` and
  `soak.declare`; one `_move_heading()` step runs per tick, and a wall ends the
  span instead of quietly spending the rest of the budget. Covered by
  `test_timeskip_route_carries_a_heading_and_stops_at_the_first_refusal`.

Still open on this card:

- The belief-destination resolver and found / found-not-there record.
- "Upgrades only the belief it supports" (the map half writes the registry, but
  nothing links an entry to the belief it corrects).
- Generation-on-discovery at the frontier (task-398/task-9).

The 2026-10-20 reconnaissance below said `engine/fog.py` had zero importers.
That is no longer true for `reveal_area`, `reveal_examined`, `reveal_sightline`
and `teach_from_map`; `only_known` and `fog_view` still have none. The rest of
that reconnaissance still stands.

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
   - observed: PASS 2026-10-23. `routes/timeskip_ops.py` now passes
     `heading=data.get("heading")` to both `advance` and `soak.declare`, so
     `POST /api/world/timeskip {"intent":"travel","heading":"east","minutes":10}`
     reaches `_move_heading()`. The targeted test moved into the east exit,
     stopped at the wall on the next step, spent one tick of the ten-minute
     budget and reported `no_exit`.
3. Belief destination
   - expected: a described destination is resolved from the character's own
     knowledge rather than world truth, and the outcome (found /
     found-not-there) is recorded when the character arrives.
   - observed: PASS 2026-10-24. 
esolve_belief_destination and _record_belief_arrival
     wired in engine/timeskip.py; tested via
     	ests/test_hearsay_places.py::test_belief_travel_follows_believed_heading_and_records_arrival_outcome.
4. Map and hearsay teach knowledge
   - expected: reading a map reveals the areas it charts into the character's
     known list, and a direction given in dialogue reveals one area the same
     way, so a belief becomes a known route.
   - observed: PASS 2026-10-24. Charted map writes on read/use, spoken direction
     writes known, and _upgrade_supporting_beliefs in engine/fog.py links
     learned places to matching memories; tested via
     	ests/test_hearsay_places.py::test_map_and_reveal_upgrade_only_matching_place_beliefs.
5. Generation on discovery at the frontier
   - expected: entering an unmade frontier cell generates content and reveals
     it for that character only.
   - observed: PASS 2026-10-24. materialize_frontier in engine/fog.py wired in
     engine/movement.py and engine/timeskip.py; tested via
     	ests/test_hearsay_places.py::test_frontier_discovery_generates_content_and_reveals_for_discoverer_only.

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

The gap is **wiring, not authoring**. At filing (2026-10-20), `engine/fog.py`
had zero importers anywhere in `engine/` or `routes/` - `reveal_area`,
`reveal_sightline`, `reveal_examined`, `teach_from_map` and `only_known` were
all uncalled. The map teach path, hearsay writing `known`, the sightline writer
and the heading request landed 2026-10-23; the resolver and belief validation
remain. The original plan was:

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
4. **Give a heading a time budget.** `POST /api/world/timeskip` now passes
   `heading` to `advance` and `soak.declare`, and the timeskip loop spends one
   `_move_heading()` step per tick, stopping at the first refusal. At the
   one-minute target turn that is the flat `per_hop_minutes()` cost. No separate
   heading intent was needed: `intent: "travel"` with `heading` is the form. The
   task-466 interrupt path is already inside the loop, so a hazard during the
   walk interrupts for free.
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

Current availability: the engine and `POST /api/world/timeskip` accept
`{"intent":"travel","heading":"east","minutes":N}` and stop at the first
refusal. Charted maps and spoken directions now write `known`. The game-view
`go west 2h` command, the belief-destination resolver, the belief-upgrade link
and generation-frontier resolution remain planned; no UI surface is claimed
today.

Live steps when available:
1. In a scratch world with a known westward frontier and a character who has not visited the destination, submit `go west 2h` and inspect the travel events.
   - expected: movement spends no more than the requested time budget, follows the chosen heading through the world, and resolves the area reached rather than teleporting to a guessed node.
2. Give the character a map or a direction through a dialogue/item interaction, then ask it to travel to that believed destination.
   - expected: the received information updates that character's existing knowledge and upgrades only the belief it supports into a known route/area.
3. Give the character a hazard, vital interruption, or interesting frontier find during travel.
   - expected: the trip interrupts through task-466's existing follow-up path and reports the actual event; it does not continue past the interruption.
4. Ask the character to recall the destination before and after receiving the map/direction.
   - expected: before learning it, the response represents a belief with uncertainty; after learning it, recall returns the known route without using world truth the character has not learned.

## Reconnaissance (2026-10-20) - superseded in part 2026-10-23

Re-checked the cited code on 2026-10-20. The belief-based travel pieces this card still asks for were not implemented then. Items 1, 2, 4 and 6 of the plan above have since landed; the resolver and belief validation have not.

- `engine/timeskip.py` exposes `route_hops()` / `travel_minutes()` and `_move_heading()` (heading step) - those two progress boxes remain accurate.
- The map teach path, spoken-direction hearsay and the HTTP `heading` field now exist. No belief-destination resolver and no generation-on-discovery at the frontier exists in `engine/timeskip.py` or `engine/knowledge.py`. `engine/timeskip.INTENTS` = ("idle", "leisure", "search", "explore", "travel") - no separate belief intent; heading travel uses `intent: "travel"` with a `heading`.
- Note on the word "belief": it does occur in `engine/`, 11 times in `engine/memory_dynamics.py`, but as a *memory category* (`BELIEF = "belief"`, a conclusion the character holds) and in the reflection docs. That is the memory system's taxonomy, not a travel resolver; none of those sites are reachable from `engine/timeskip.py`.

Verdict: DONE. Heading, map/hearsay, belief resolver, belief-upgrade link, and frontier generation are wired and verified by 8 tests in tests/test_hearsay_places.py and 68 tests in tests/test_timeskip.py.