---
type: task
status: review
area: world
priority: medium
---

# task-499: Per-agent fog of war and map knowledge transfer

**Filed:** 2026-09-24
**Related:** task-495, task-403
**Design:** `docs/design/worldpainter-knowledge-and-fog.md` - fog is the
knowledge dimension of the painted grid (movement + reveal + belief travel,
task-467).

## What

Add an area/scope-level known set per character. player.known already gates hidden ways and items through viewer-aware perception (engine/room_perception.py; tests/test_known.py), and EDGE_KNOWN is abilities-only. Unknown cells/zones are fog on the map; walking, examining, or finding a map item reveals them - a map's use/read teaches known entries (reuse the existing teach path). Rendering: the map view shows only known cells/zones. Keep perception honest in agent prompts (an unaware agent is not told about unknown areas).

## Acceptance

- [x] Areas/scopes can be marked known per character. The reveal verbs and the
      perception gate are wired. Rendering unknown cells as fog is task-677.
- [x] Walking and examining reveal them; a charted map's use/read teaches the
      entries it lists, through the same `known` registry.
- [x] Agent prompts never disclose unknown areas. The route block and the exit
      list are known-filtered, `only_known` is wired into `known_route_areas`
      (`engine/spatial_memory.py`), and `fog_view` is wired into
      `GET /api/players/<name>/map` (`routes/player_ops.py`).
- [x] Tests cover the reveal, map-item knowledge transfer and the authored route
      bridge.

## Progress - 2026-09-28 (in `review`)

### The gate existed and had no key

`player.known` was already a list, and `engine/room_perception.py:way_visible_to`
already gated on it - *"Authored knowledge: a way, or its area, listed in the
viewer's `known` registry is visible from the start (the butcher's passage, a
scout's map)."* **Nothing anywhere wrote to it.** Every test passed because every
fixture hand-populated the list. The gate was sound and had no key, which is the
whole of this task's delta.

`engine/fog.py` (new) supplies the three halves.

### Reveal - three verbs, one registry

`reveal_area` (walking in), `reveal_examined` (examining a way teaches where it
goes, examining a place teaches the place), and `reveal_sightline` (seeing down a
corridor, **reusing `engine/beyond_visibility.sightline_run`** rather than
re-deciding what is visible - one place that knows how far you can see, so the
map and the prose cannot disagree).

**Ids and names both matter, and the set stores both.** The gate matches on
`way.id`, `area_name`, or a lossy name-derived id guess, because hand-authored
ways predate the id convention. A set holding one form leaks through the other
two, so a reveal writes every form it can derive. The derived guess is never
needed in the set: a reveal writes the real id and the real name, so the guess is
always redundant.

### Teach - a map goes into the *same* registry

`teach_from_map` writes `player.known`, which is the existing teach path. Two
paths would mean two places to look and one of them would be forgotten; a test
asserts a walk and a map end up in one list.

**A chart entry that is a display name resolves to its area**, so a map that
charts `"Room 1"` and a walk that reaches `area_1` teach the same forms rather
than two half-entries. The report counts **places** and **entries** separately,
because those are different numbers and conflating them makes "a map of two rooms"
look like it taught five things.

### Fog - present but marked, never omitted

`fog_view` returns `{known, fog, known_count, fog_count}`, and unknown cells are
**in `fog`, not missing from the payload**. An omitted cell is indistinguishable
from one that was never painted, so the map could not tell "you have not been
there" from "there is nothing there" - and fog of war that looks like empty space
is fog of war nobody explores. It also de-duplicates: a map that lists a cell
twice is a map with a bug in it, and a caller counting `known_count` to draw a
legend would be off.

### Honesty - a filter on a list, not a string

`only_known(player, names)` is **the** boundary the task's third acceptance line
asks for, and it filters a **list**, deliberately. A filter on a rendered prompt
string is unauditable; a list filter is a call a reviewer can see, and a prompt
that forgot to call it is the actual failure mode this guards against. A test
pins the degradation direction: a filter that cannot decide returns **nothing**,
never the input - returning the input would be an omniscient agent with extra
steps.

`unknown_are_hidden` exists as a named predicate so the call sites read as a
decision rather than an `if not in known(...)`, and so there is exactly one place
to change if the rule ever becomes "a rough bearing is allowed".

### Three bugs the tests caught, all in this task's own new code

1. **An explicit empty chart taught the whole world.** `props.get("charted_areas")`
   is falsy for `[]`, so `charted_areas: []` fell through to the "no list, so a map
   of wherever you are" branch. Now `"charted_areas" in props`. The difference is
   a blank prop and an absent one, and a truthiness test reads both the same.
2. **`fog_view` listed a duplicated cell twice** and inflated `known_count`, which
   a legend-drawing caller would be off by.
3. **A chart of two rooms reported five things taught**, because `count` was
   counting registry entries rather than places.

### New tests - `tests/test_fog.py` (24)

The missing key: a fresh agent knows nothing, a reveal teaches both forms,
re-revealing adds nothing, **two agents never share a set** (fog of war is per
agent; a shared set is omniscience), a `Known` is re-readable without clearing
anything, `reveal` covers id/name/props, and `forget` on a node removes every form
while a bare string removes only itself.

The verbs: walking in, examining a way (teaches the far side), examining an area,
a sightline, and every empty-input case.

The map: a chart teaches exactly its chart, a chartless map teaches where you are,
an explicit empty chart teaches nothing, and a map and a walk share one registry.

Honesty: the filter, names as well as ids, degrading to nothing, the named
predicate, and **two agents getting different prompt answers from one world**.

The view: fog present-but-marked, stable with no input, de-duplicated, zones
optional.

And the payoff test: a revealed hidden way is visible to the agent that revealed
it and still hidden from another, through the real
`room_perception.way_visible_to`. `tests/test_known.py` still passes.

### Wired 2026-10-23 (follow-up)

The follow-up named below has landed. The call sites are:

- **Walk:** `engine/movement.py` calls `reveal_area` for the acting player at the
  arrival point, right after `_set_player_area`. Best-effort: a reveal failure
  never breaks a move.
- **Examine:** `engine/items/examine_actions.py` calls `reveal_area` for the room
  and `reveal_examined` for the target. A way reveals the far side, and
  `reveal_examined` now takes `from_area_id` so a two-ended way resolves the room
  the viewer is not standing in. That bug was invisible while nothing called the
  verb.
- **Map:** a charted item (`"charted_areas" in properties`) teaches through
  `teach_from_map` on `examine`/`read` and on `use`. Uncharted map props are not
  passed to `teach_from_map`, because its no-chart fallback hands out every area
  in the world.
- **Sightline:** `engine/area_description.py` calls `reveal_sightline` for each
  open or see-through exit in the room description, using
  `beyond_visibility.sightline_run`. Looking down a corridor therefore teaches
  every room the line of sight reaches, and the prose and the map read the same
  run instead of two visibility rules. A shut door stops the run.
- **Tests:** `tests/test_fog_wiring.py` (13) pins the walk, room examine, way
  examine, item examine, mapped and unmapped reads, looking down a corridor, a
  shut door stopping the sightline, idempotence, and the authored route bridge.
  `tests/test_fog.py` and `tests/test_known.py` still pass.

`known_route_areas` in `engine/spatial_memory.py` unions the walked areas with
authored `known`/`known_areas`, and the prompt route block plus `recall path`
now use it. That is the task-467 half that makes authored knowledge navigable
without a second store.

Wired:

- only_known is wired into engine/spatial_memory.py.
- og_view is wired into GET /api/players/<name>/map (
outes/player_ops.py), returning {fog: fog_view(player, all_area_ids)}.
- Canvas rendering of unknown cells as fog on the player-facing map is tracked in 	ask-677.

### Not wired at filing (historical)

Nothing called `reveal_*` on movement or examine. The verbs existed, were tested
and were the right shape; the call sites were `engine/movement.py` and the
examine handler.

## Why

`player.known` gates hidden ways, hidden items and exit visibility, but nothing
in the runtime wrote to it. Per-agent knowledge therefore only worked for
authored starting knowledge: a character who walked into a room still did not
know it, and an agent could not route to a place it had been told about. The
gate was sound and had no key.

## How

- `engine/fog.py` supplies the verbs: `reveal_area`, `reveal_examined` (a way
  teaches the far side; `graph` and `from_area_id` make a two-ended way resolve
  the room the viewer is not in), `teach_from_map`, `only_known` and `fog_view`.
- `engine/movement.py` calls `reveal_area` at the arrival point.
- `engine/items/examine_actions.py` reveals the room, the item and the far side
  of a way; `engine/items/use_actions.py` does the same for a used map.
- A map is only taught when it declares `charted_areas`. The no-chart fallback
  in `teach_from_map` hands out every area, so an uncharted map prop must not
  reach it.
- `engine/spatial_memory.known_route_areas` unions the walked areas with the area
  entries in `known`/`known_areas`; the prompt route block (`routes/memories.py`)
  and `recall path` (`routes/action_handlers.py`) read the union.

## Steps to verify

1. `python -m pytest tests/test_fog_wiring.py tests/test_fog.py tests/test_known.py`
   - expected: all pass
   - observed: 40 passed on 2026-10-23
2. Walk a two-room world and examine the joining way.
   - expected: the destination room's id and name are both in `player.known`
   - observed: `test_walking_into_an_area_teaches_it` and
     `test_examining_a_way_teaches_the_far_side` pass
3. Read a charted map and an uncharted map prop.
   - expected: the charted map teaches its chart; the uncharted prop teaches only
     the room the reader is in
   - observed: `test_reading_a_charted_map_teaches_its_chart` and
     `test_reading_an_uncharted_map_does_not_teach_the_world` pass
4. Seed `known` with an area id and ask for a route.
   - expected: `find_route` returns the path even with no walked memory
   - observed: `test_authored_known_area_makes_a_path_findable` passes
5. Live browser check of the fog reveal.
   - expected: a walked area appears in known in GET /api/players/<name>
   - observed: PASS 2026-10-25. GET /api/players/<name>/map returns {fog: fog_view(player, all_area_ids)}; walked areas appear in player.known in player payload. 42 tests pass across tests/test_fog_wiring.py, tests/test_fog.py, and tests/test_known.py.

## Files

- `engine/fog.py`
- `engine/movement.py`
- `engine/items/examine_actions.py`
- `engine/items/use_actions.py`
- `engine/spatial_memory.py`
- `routes/memories.py`
- `routes/action_handlers.py`
- `tests/test_fog_wiring.py`
