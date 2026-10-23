# Agent navigation knowledge: what an author can seed today

Recon, 2026-10-22. Updated 2026-10-23 after the fog, sightline and hearsay
wiring landed.
Scope: how an author gives an agent knowledge of a closed space, using the
mansion as the worked case. Measured against the code, not the task prose.

Companion reading:
`docs/design/worldpainter-knowledge-and-fog.md`,
`docs/virtualWorld/Gameplay/Per-Agent Knowledge (Fog of War).md`,
`docs/virtualWorld/dev_tasks/inprogress/gameplay/task-467-belief-based-travel-heading-budget-maps-and-hearsay.md`.

## Summary

Three authored levers exist, and two of them now feed navigation directly.

- `known` / `known_areas` / `known_ways` is the perception registry *and*,
  since 2026-10-23, a route source: `known_route_areas` unions it with the
  walked areas for the prompt's route block and `recall path`.
- `visited_areas` is the legacy bootstrap. It is migrated into observation
  memories at load and still feeds routes, but task-430 wants it retired.
- `memories` are prose. They reach the LLM and nothing else.

Walking, examining and reading a charted map now write `known` through
`engine/fog.py`, so authored knowledge is a head start rather than the whole of
it.

## Surfaces and what reads them

| Surface | Read path | Authored today? |
|---|---|---|
| Mind panel `Knowledge` (Manage modal) | writes `player.known` | yes, live |
| Prompt block `=== KNOWN ROUTES FROM HERE ===` | `memory-context.ts:173-184` calls `GET /api/players/<n>/memories/spatial` -> `known_route_areas` -> `build_known_routes` | yes, via `known`/`known_areas` or `visited_areas` |
| `recall path to X` | `routes/action_handlers.py:1049-1076` -> `known_route_areas` -> `SpatialMemory.find_route` | yes, same union |
| `recall` (mental-map count) | `routes/action_handlers.py:1035-1048` -> `visited_area_names()` + `charted_cells` | only via `visited_areas` |
| Surveyed cell readout (mental map) | `routes/player_ops.py:1750-1778` -> `charted_cells` | no |
| Exit list, hidden ways and hidden items | `engine/room_perception.py:56` `way_visible_to` reads `player.known` | yes |
| LLM memory context | recall-scored `player.memories` | yes, prose only |

## Lever 1: `known` (perception and now route knowledge)

`player.known` (default `[]`, `player.py:378`) is the fog-of-war list of areas,
ways and items a character knows. Three write paths:

- the character data `known` list, seeded in `Player.__init__` (`player.py:229-234`);
- a `preconceived_knowledge` block on the player data, loaded at
  `engine/serialization.py:648-651` through `AgentMind.load_preconceived`
  (`engine/agent_memory.py:149-182`), which accepts `memories`, `known_areas`,
  `known_items` and `known_ways`;
- the mind panel: `mind-view.ts:697-705` renders
  `Knowledge - known from the start (N)` with a Manage button that opens
  `KnownBySection` (`static/js/inspector/known-by.ts`), which edits `player.known`
  directly through `routes/player_ops.py:650-651`.

What it does:

- `room_perception.way_visible_to` and `visible_area_items` use it to decide
  whether a hidden way, a hidden item or a hidden exit is visible to that one
  character, and the prompt builder uses it to decide whether a person is named
  or left as a stranger.
- `engine/spatial_memory.known_route_areas(player, graph)` resolves each entry
  to an area node and unions the names with `visited_area_names`. The prompt
  route block and `recall path` read that union. An entry that resolves to a
  way or an item is a known thing, not a place, and does not widen a route.
- Walking (`engine/movement.py`), examining (`engine/items/examine_actions.py`)
  and using or reading a charted map (`engine/items/use_actions.py`,
  `examine_actions.py`) now write here through `engine/fog.py`.

What it still does not do: it does not seed `charted_cells`, so it does not draw
on the minimap.

`known_areas` and `player.known` are the same store: `load_preconceived` writes
areas through `AgentMind.know_area` (`engine/agent_memory.py:103-111`), which
appends to `player.known`.

## Lever 2: `visited_areas` (the legacy route bootstrap)

A plain list of area names on the player data. At load,
`engine/serialization.py:656-679` migrates it into observation memories:

```python
p.record_observation(aid, f"You have been to {aname_disp}.", 0,
                     kind="area", location=aname_disp)
```

`visited_area_names()` (`player.py:1211-1226`) reads exactly those memories
(`kind == "area"` with a `location`), plus any area node in `memory_index`. That
is the walked half of the route union, and it still backs the `recall`
mental-map count.

It is honest, idempotent (`has_seen` guard) and tolerant of an id or a display
name, but task-430 labels it a legacy migration and wants it retired. Treat it
as a bootstrap, not the design. Prefer `known`/`known_areas` for new content.

## Lever 3: `memories` (prose)

An authored memory (`source: manual`, `type: location`) goes into the character's
memory store and is scored into the LLM context like any other memory. It is a
briefing note. It does not make anything visible and does not build a route. The
existing butcher seed memory in `data/library/characters/the_butcher.json` is
this case: a full estate layout written by hand.

## What has no authored path today

- **Minimap / surveyed cells.** `charted_cells` (`player.py:372`) is written by
  observation/survey at runtime (`engine/observation.py:210`) and read by
  `routes/player_ops.py:1750-1778`. No authored field seeds it.
- **Prompt honesty filter.** `fog.only_known` has no caller. The route block and
  the exit list are already known-filtered, but the shared filter itself is not
  used elsewhere.
- **Fog on the map.** `fog.fog_view` has no caller. The map endpoint draws
  visited cells; painting fog for painted-but-unvisited cells is task-677's
  surface.

## Near future

- **task-467 (inprogress, gameplay)** is the remaining hinge. The map teach path,
  the fog reveal on a heading walk, the route union, the HTTP heading form and
  spoken directions teaching `known` now land. Still open: the belief-destination
  resolver, the found / found-not-there record, "upgrades only the belief it
  supports", and generation-on-discovery at the frontier (task-398/task-9).
- **task-499 (inprogress)** owns the fog wiring. The reveal, teach and sightline
  call sites landed 2026-10-23. `only_known` and `fog_view` remain unwired, which
  is why it is in progress rather than done.
- **bug-553 (review, fixed 2026-10-23)**: the minimap now opens on the scope of
  the current area, with the first server-sorted scope only as a fallback.
- **task-430 (review)** still wants `visited_areas` retired. That is the reason
  not to build new content on it.
- **task-677 (todo, ui)** is the player-facing fog surface, including
  `fog_view`.
- **task-736 (todo, characters)** is the per-character cognitive map in the mind
  panel. That is the longer-term home for this knowledge, not a new store.

## Mansion worked example

Measured: `data/scenarios/mansion.json` holds 27 way nodes, 5 of them with
`current_state: hidden`. Those five match the five secret routes listed in the
butcher's seed memory (slaughterhouse to kitchen, slaughterhouse to foyer, cellar
to crypt, attic to servant's quarters, library to secret study).

Recommended authored seed today:

- `known` / `known_areas`: the estate rooms the butcher should already know.
  This fills the prompt's route block and `recall path` without the legacy list.
- `known_ways`: the five hidden ways, so they appear in his exit list and he is
  not left hunting a door he can never see.
- A map item with `charted_areas` if the knowledge should be discoverable in
  play rather than innate. The teach path fires on `examine`/`read` and on
  `use`.
- `memories`: one short line of intent, if any. The hand-written layout is doing
  the LLM's job and none of the engine's.
- `visited_areas`: only as a fallback. Task-430 wants it gone.

## Caveats

- `visited_areas` is legacy-shaped. It is honored today, but the intended future
  is task-467 where `known_areas` drives travel. Authoring it now means
  re-authoring later.
- `teach_from_map` with **no** `charted_areas` key hands out every area in the
  world. Only pass it a map that declares a chart. The call sites added on
  2026-10-23 gate on `"charted_areas" in properties` for exactly this reason.
- `known_ways` gates visibility but does not by itself build a route to the far
  side, because `known_route_areas` counts only entries that resolve to an area
  node. Add the far room to `known`/`known_areas` if the agent should be able to
  route to it.
- Hidden-way traversal was not fully checked. Movement matches way names and
  slugs (`engine/movement.py:339-340`), so a hidden way may still resolve if the
  LLM guesses its name from prose even while it is absent from the exit list. The
  gate is on the listing, not confirmed on the step. That fragility is the reason
  to seed `known` rather than rely on a memory.
