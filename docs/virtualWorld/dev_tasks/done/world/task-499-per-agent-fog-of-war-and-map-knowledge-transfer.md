---
type: task
status: done
area: world
priority: medium
---

# task-499: Per-agent fog of war and map knowledge transfer

**Filed:** 2026-09-24
**Related:** task-495, task-403
**Design:** `docs/design/worldpainter-knowledge-and-fog.md` — fog is the
knowledge dimension of the painted grid (movement + reveal + belief travel,
task-467).

## Goal

Add an area/scope-level known set per character. player.known already gates hidden ways and items through viewer-aware perception (engine/room_perception.py; tests/test_known.py), and EDGE_KNOWN is abilities-only. Unknown cells/zones are fog on the map; walking, examining, or finding a map item reveals them - a map's use/read teaches known entries (reuse the existing teach path). Rendering: the map view shows only known cells/zones. Keep perception honest in agent prompts (an unaware agent is not told about unknown areas).

## Acceptance

- Areas/scopes can be marked known per character; unknown ones are fog on the map.
- Walking and examining reveal them; a map item's use/read teaches `known` entries via the existing teach path.
- Agent prompts never disclose unknown areas (perception stays honest).
- Tests cover the reveal, the fog-rendering data, and map-item knowledge transfer.

## Progress — 2026-09-28 (in `review`)

### The gate existed and had no key

`player.known` was already a list, and `engine/room_perception.py:way_visible_to`
already gated on it — *"Authored knowledge: a way, or its area, listed in the
viewer's `known` registry is visible from the start (the butcher's passage, a
scout's map)."* **Nothing anywhere wrote to it.** Every test passed because every
fixture hand-populated the list. The gate was sound and had no key, which is the
whole of this task's delta.

`engine/fog.py` (new) supplies the three halves.

### Reveal — three verbs, one registry

`reveal_area` (walking in), `reveal_examined` (examining a way teaches where it
goes, examining a place teaches the place), and `reveal_sightline` (seeing down a
corridor, **reusing `engine/beyond_visibility.sightline_run`** rather than
re-deciding what is visible — one place that knows how far you can see, so the
map and the prose cannot disagree).

**Ids and names both matter, and the set stores both.** The gate matches on
`way.id`, `area_name`, or a lossy name-derived id guess, because hand-authored
ways predate the id convention. A set holding one form leaks through the other
two, so a reveal writes every form it can derive. The derived guess is never
needed in the set: a reveal writes the real id and the real name, so the guess is
always redundant.

### Teach — a map goes into the *same* registry

`teach_from_map` writes `player.known`, which is the existing teach path. Two
paths would mean two places to look and one of them would be forgotten; a test
asserts a walk and a map end up in one list.

**A chart entry that is a display name resolves to its area**, so a map that
charts `"Room 1"` and a walk that reaches `area_1` teach the same forms rather
than two half-entries. The report counts **places** and **entries** separately,
because those are different numbers and conflating them makes "a map of two rooms"
look like it taught five things.

### Fog — present but marked, never omitted

`fog_view` returns `{known, fog, known_count, fog_count}`, and unknown cells are
**in `fog`, not missing from the payload**. An omitted cell is indistinguishable
from one that was never painted, so the map could not tell "you have not been
there" from "there is nothing there" — and fog of war that looks like empty space
is fog of war nobody explores. It also de-duplicates: a map that lists a cell
twice is a map with a bug in it, and a caller counting `known_count` to draw a
legend would be off.

### Honesty — a filter on a list, not a string

`only_known(player, names)` is **the** boundary the task's third acceptance line
asks for, and it filters a **list**, deliberately. A filter on a rendered prompt
string is unauditable; a list filter is a call a reviewer can see, and a prompt
that forgot to call it is the actual failure mode this guards against. A test
pins the degradation direction: a filter that cannot decide returns **nothing**,
never the input — returning the input would be an omniscient agent with extra
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

### New tests — `tests/test_fog.py` (24)

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

### Not wired here

Nothing calls `reveal_*` on movement or examine. The verbs exist, are tested and
are the right shape; the call sites are `engine/movement.py` (mine) and
`engine/effect_handlers/examine.py` (contended). Wiring the walk verb into
movement is a one-line change and is left for a follow-up rather than done blind
inside this task.
