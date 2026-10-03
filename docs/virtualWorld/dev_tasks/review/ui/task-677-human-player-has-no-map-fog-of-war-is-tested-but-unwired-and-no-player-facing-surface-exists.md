---
type: task
status: review
area: ui
priority: medium
---

# task-677: Human player has no map: fog of war is tested but unwired and no player-facing surface exists

**Filed:** 2026-10-03
**Related:** task-499,task-676

## Goal

There is no map a human player can look at. Verified 2026-10-03 by count, not by inspection: the word minimap occurs in static/js only inside the doc comment of stream/stream-scrubber, where it means a timeline overview of the event stream (task-340) - zero implementations, zero mentions in templates/index.html, and absent from docs/virtualWorld/Feature Map.md, so no feature claims one. The G button in the graph toolbar is an editor graph-layout toggle, not a player map.

The mechanism exists and is unwired: engine/fog.py implements task-499's reveal, teach, only_known and fog_view(), and has exactly one importer repo-wide, tests/test_fog.py. Live movement, examine and the human turn composer never populate player.known, so there is no fog state to draw even if a surface existed. A scoped subgraph load replaces the whole world on a scope switch, so a naive map would also show every zone at once (the author-visible truth) rather than what this character has seen.

Goal: a human-player map surface showing where the controlled character has already explored or seen, drawn from fog state rather than from raw scope data, and surviving a scope-filter switch. Decide and record which of two things is being drawn before writing UI: the painted lattice with revealed cells (the per-scope background art already exists and is derived, never a saved px rect) or a true fog-of-war overlay. Start by wiring the producer - a call site that populates player.known on movement and examine - because a surface with nothing behind it is the second way this task can look finished and behave empty.

Non-goal: task-676, which is an editor area-editor mini map and stays separate. Non-goal: character spatial knowledge (engine/spatial_memory.py BFS from visited_areas) - that is its own task, because a route an NPC knows and a cell a human has seen are different facts.

Definition of done: the client polls a payload that carries per-scope revealed state; a human can open a map and see only what their character has seen; a scope switch does not reveal another zone; there is at least one authored world where the map is not simply the whole grid; and a test proves the producer populates state (a surface test alone does not).

## Scope narrowed 2026-10-03 — the map does not need fog

Measured before starting: every fact a "cells I have been" map reads is
**already live**, so no producer and no engine change is required.

| the map needs | already written by | when |
|---|---|---|
| cells visited | `player.visited_areas`; `kind == "area"` observation rows via `memory_index` | on arrival, `engine/movement.py:807`, `engine/observation.py:144` |
| when last seen, what was there | `kind == "item"` observation rows carry `location` + `tick` | on arrival / on take |
| who was there | `kind == "character"` rows carry `location` (`player.py:904`) | **first meeting only** — `engine/observation.py:96-105` |
| a way is blocked | `way.current_state` + `player.knows_way_aspect` | on a failed `go`, `engine/movement.py:584` |
| geometry | `properties.cell`; BFS cardinal fallback | `static/js/graph/layout-engine.ts:27,496` |
| where the character is | `player.current_area` → cell | — |

So this task ships **without** wiring `engine/fog.py`, which is the correct
outcome and not a compromise: `player.known` is the hidden-way and hidden-item
gate (`engine/room_perception.py:127,156`), so revealing an area on arrival
would make every hidden exit of that area visible at once. Fog stays a separate
task. "Cells you have been" needs no reveal state to exist.

## Decisions

- **One route, not the state poll.** `GET /api/players/<name>/map` returns
  visited cells, per-cell last-seen, who-was-there, way states and the visited
  scope list. Geometry is drawn from `worldState`, which already carries
  `properties` verbatim per area. Do **not** add memory fields to `/api/state`:
  it is ~2.48 MB polled every 1.5 s and already ships the whole `memories`
  list (`engine/serialization.py:217-218`).
- **The unit is the cell, not the area.** `properties.cell` is not unique per
  area — the storey index is part of place identity
  (`World Building/Grid to Graph.md:53`), and roads share cells with the biome
  they cross. A cell stacks its areas with a count badge; the tooltip lists them.
- **"You are here" is not `entry_cell`.** `entry_cell` is where a scoped load
  drops a character; the marker is `player.current_area` resolved to a cell.
  Conflating them misplaces the marker on every scope load.
- **A way marker straddles the boundary.** Ways carry a half-integer
  coordinate (`engine/world_compile.py:2055`), so the ✖ sits on the grid line
  with a small hit box. Drawn inside a cell it swallows that cell's hover —
  reproduced in `docs/design/minimap-mockup.html`.
- **Gate the ✖ on knowledge.** `engine/scene_snapshot.py:236-247` downgrades
  locked→closed unless the character has learned the aspect. The map must use
  the same gate or it leaks what the turn panel withholds.
- **Tooltip splits *last seen* from *last known*.** "When you were there" and
  "what you observed then" are different facts; do not collapse them into one row.
- **Ticks, not wall clock.** A row has `tick`. Do not render a real date.
- **Fit the lattice to the visited cells, not the scope's painted extent.** The
  first implementation sized the grid from the manifest (`world` 20×10) and
  rendered a 680×340 box holding two squares — a megamap, and the opposite of
  the point. Bounds are now the minimum box around the cells the character has
  been in, at 8–20px cells inside a 320×190 viewport that scrolls. Fullscreen
  passes a much larger box and a 44px ceiling pitch.
- **The panel lives in the composer's top-right corner**, mounted into the feed
  column above "What happened", not into the scene column. Two consequences that
  cost a round each: the feed column is ~271px, so the default box is 268 wide
  and the label takes its own row (label + select + button cannot share 271px and
  a ragged wrap reads as a mistake); and the mount host must be looked up with
  `document.querySelector`, because the composer's `q()` helper is scoped to
  `#htc-modal` and the feed column is a sibling of the modal — `q()` returned
  null and the `.catch(() => {})` swallowed it, so the panel silently never
  appeared.
- **SVG, not vis-network.** vis draws to canvas, so hover targets and tooltips
  have no DOM (and a DOM query for them returns zero).

## Acceptance

- [ ] `GET /api/players/<name>/map` returns visited cells with last-seen tick,
      contents, who-was-there and way states; and the list of scopes that
      character has visited. A character who has never left its start area
      returns one cell, not the whole scope.
- [x] A panel in the human turn composer's scene column draws only cells that
      character has been in, marks the current cell, and switches scope from a
      selector listing **only visited scopes** — switching does not reveal
      another zone. Verified 2026-10-03 after seeding a character into two
      scopes: selector read `goblin camp (5)` / `world (2)`, switching to `world`
      re-rendered only that scope's 2 cells.
- [x] `POST /api/players/<name>/map/visited` seeds a character's map. It writes
      the **same** observation row an arrival writes
      (`Player.record_observation(..., kind="area")`) rather than appending to a
      parallel registry, mirrors the name into `visited_areas` for the
      known-routes prose, reports unresolvable names in `unresolved` instead of
      dropping them, and is idempotent. Optional `observe: true` records what was
      in each area through `visible_area_items` — the same perception an arrival
      uses — so a seeded cell's tooltip reads like a walked one. It deliberately
      does **not** stamp characters (`engine/observation.py:96-105`). 18 tests.
- [ ] Hovering a cell shows its areas, when it was last seen, what was there,
      who was there, and its ways with state; a cell holding more than one area
      lists all of them.
- [ ] A way whose `current_state` is solid (`closed`/`locked`/`blocked`,
      `engine/barriers.py:80`) draws a ✖ on the boundary between its two cells,
      **only** when `player.knows_way_aspect` says the character knows that
      aspect; a negative test proves an unknown blocked way is not marked.
- [ ] Cells are drawn from `properties.cell` where present and from the BFS
      cardinal layout where absent, in the same scope view.
      **UNMET, and the fallback is unexercised.** `kraktooth_goblin_camp` is the
      only shipped scenario with painted cells (463 `cell` blocks; every other
      file in `data/scenarios/` has zero). The fallback walks way compass
      directions outward from the character's own cell — but
      `edge.properties["direction"]` is a **door name** in a hand-authored world
      (`master_bedroom_door`, `attic_ladder`, `grand_stairs_back`) and only a
      compass point in a grid-compiled one. So on every shipped scenario the
      fallback never fires: kraktooth has compass directions *and* painted cells,
      and the hand-authored worlds have neither. Kept rather than deleted because
      it is correct for a world whose author did set cardinal directions, but
      nothing proves it yet.
      `mansion.json` is the concrete case: 25 areas, properties are only
      `description` + `environment`, and `GET /api/world/scopes` returns
      `{"scope": null, "children": []}` — no coordinates, no scope, no storeys.
      It cannot exercise this, or the ✖ (which needs both endpoints placed).
      It needs a WorldPainter pass, or hand-authored `cell` + `world_scope_id`.
- [x] A fullscreen toggle opens the map in an overlay and closes on Escape.
      Verified 2026-10-03 in a browser with a screenshot: select and close render
      top-right, lattice at the 44px ceiling pitch, Escape removes the overlay and
      leaves the panel mounted. Two defects were invisible to DOM measurement and
      only showed in the screenshot — the lattice styles were scoped to
      `#htc-map`, which the overlay is not a descendant of, so its cells rendered
      unstyled and *invisible* while every count and `clientWidth` passed; and the
      panel's `flex:1 0 100%` label collapsed the overlay's select and close to
      zero width in a non-wrapping bar.
- [ ] `python tools/ts_convert.py check` clean; `tools/feature_index.py --check`
      clean, which requires a `Feature Map.md` row for the player map.
- [ ] A micro-scenario proves it end to end in a browser on port 4444: walk a
      route, screenshot the map, confirm the visited set matches where the
      character has been. A surface test alone does not satisfy this task.

## Not in this task

- **Elevation / floor section control.** `properties.floor` is an unbounded
  storey index and is part of place identity, so the control is right — but no
  shipped world has the content to draw it. `Millbrook Falls Town Map.md` has
  `hallway_1/2/3` and `apartment_1a`-`apartment_2a` all authored, while
  `stairwell`, `stairwell_landing`, `pines_rooftop_access_ladder` and
  `pines_fire_escape` carry no `[EXISTS]` marker and are unauthored; no painted
  grid ships more than one storey. Building the control first yields an empty
  switch. **Prerequisite: author the vertical ways.** The only real vertical way
  in data today is `way_task_18_-_ladder` in `labs.json`.
  Depends on `task-651` — the painter grid payload omits the floor layer when
  empty, so a floor control built on it can silently read nothing.
- **Wiring `engine/fog.py`.** Separate task; see the scope note above for why
  this task must not reach it.
- **Remembering "who was there" on every arrival.** `observation.py:96-105`
  excludes people deliberately (arrival-stamping them saturated camp
  Entertainment at 87/100). Rows exist for first meetings only, so the tooltip's
  who-was-there is honest but sparse. Changing that policy is its own decision.
- `task-676`, the editor area mini-map, which stays separate.
