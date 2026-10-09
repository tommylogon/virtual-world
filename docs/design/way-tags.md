# Way Tags

Node tags are a generic, tag-driven seam: a system reads `properties.tags` off
whatever node it holds. A way is a node, so a tag on a way reaches every system
that already keys on tags — matching, plans, observation, hazards, fear,
foraging, triggers, search. This document is the design for what a compiled way
carries and who reads it.

Related: `docs/design/worldpainter-knowledge-and-fog.md`,
`engine/area_tags.py` (the open-sky predicate), `tools/way_properties.py`
(the authorable way-property set; `tags` is declared there).

## The one writer, the many readers

The WorldPainter compiler is the writer. `engine/area_tags.py` states the
doctrine plainly: an area's open-sky fact used to be decided four ways with two
spellings (`outdoor` vs `exterior`), and the fix is that the **compiler emits one
canonical tag** while readers accept both spellings.

Compiled **areas** already get a tag derivation
(`engine/world_compile.py`, the area props block): the road feature's tags, or
the biome's tags, plus `feature`, plus the canonical `outdoor` in world mode.
Compiled **ways** were skipped. This is the missing half.

## What the compiler knows per way

`emit_passage` holds both cells it joins, so every tag below is derived, not
invented:

| Input | Source | Feeds |
|---|---|---|
| `cell`, `nb` | the two painted cells | which cells to read |
| `cell_biome(cell)` / `cell_biome(nb)` | biome id per cell | ground tags |
| `cell_road(cell)` / `cell_road(nb)` | feature id per cell (`road`, `bridge`, `ford`, `tunnel`, `gate`) | route tags |
| `kind` | `open` / `door` / `stairs` | structure tags |
| `outdoor` | scope mode is `world` | open-sky tag |
| `storey_delta`, `climb` | floor layer / steep-step decision | `stairs`, `climb` |
| `surface` | `biomes.ground_surface` | ground material |
| blocked pass | `_apply_way_blocking` | `blocked` (a state, still written) |

The vocabulary itself already exists in `data/worldpainter/biomes.json` (106
biomes, 9 feature records). No new vocabulary is required to tag a way.

## The vocabulary

Three tiers. Only the first two are compiler output; the third is written by
triggers.

- **Route** (from the feature cell): `road`, `bridge`, `ford`, `tunnel`, `gate`,
  `underground`. The identity tier — what matching, plans and recall want.
- **Ground** (union of both cells' biome tags): `forest`, `woods`, `dense`,
  `marsh`, `river`, `stream`, `lake`, `rocky`, `cliff`, `ravine`, `hills`,
  `mountain`, `field`, `farmland`, `beach`, `shore`. The hazard / fear / forage
  tier.
- **Structure + sky**: `door`, `stairs` (from `kind`), `outdoor` (canonical,
  world mode).
- **Condition** (trigger-written, not compiler output): `flooded`, `broken`,
  `overgrown`, `snowbound`, `cleared` — mutable route state, written by
  `add_tag` / `remove_tag` effects (see below).

## How the systems read way tags

| System | Module / seam | Reads | Way tag it uses |
|---|---|---|---|
| Exit prose | `area_description.py` (exit list) | way tags | `outdoor` → "[path] **is clear**" |
| Open sky / weather / heat / light | `area_tags.is_open_sky`, `environment_propagation`, `lighting`, `tick_manager` | area tags | `outdoor` on a path |
| Hazard checks | `traversal.CROSSING_HAZARD_SKILLS`, `way_hazard` **and** `HAZARD_SKILLS` at the destination | the way's tags **and** the destination area's | `river`, `ford`, `flooded`, `cliff`, `rubble` on the crossing (`bridge` cancels) |
| Foraging | `foraging.AREA_SKILL_BONUS`, `biomes.forage_skill_bonus` | area tags | `forest` + `road` = a forageable corridor |
| Fear | `fear.character_tags` ∩ `fear_tags` | character / item / area tags | `dense`, `dark`, `cliff`, `underground` |
| NPC plans / schedules | `background_plans._areas_with`, `_travel_toward` | area tags | aim a step at a way: "patrol the road", "guard the gate" |
| Observation → memory → recall | `observation` (tags the observation with the subject's tags) | item tags | a `bridge` / `ford` observation is recallable by tag |
| Matching / aliases / autocomplete | `matching.resolve_exit` route tier (`ROUTE_WORDS`), `node_aliases`, `autocomplete` | way name/handle; route tags | `bridge`, `ford`, `gate`, `tunnel` as addressable exit names |
| Triggers / effects | `effect_handlers/equipment.handle_add_tag/remove_tag` (any `node_id`) | any node | `flooded`, `broken`, `overgrown`, `cleared` written live |
| Barriers / blocking | `barriers.WAY_STATES`, `blocked_by` | `current_state` | a reason tag distinct from the state |
| Sound | `sound.py` (`sound_absorbing`, `sound_source`) | item tags | a `quiet` / `noise` way |
| Search / selectors / NL editor | `_node_has_tags`, `/api/tags/search` | node tags | find ways by tag |

## Implemented

### Writer — `engine/world_compile.py::emit_passage`

A way's tags are the **union of both cells' feature tags and biome tags**, plus
`outdoor` when the scope is world mode, plus `door` / `stairs` from `kind`. This
mirrors the area writer exactly, so a road through forest reads as `road` +
`forest` and an open-sky path also carries `outdoor`.

### Reader — `engine/area_description.py`

The exit list's open-word test used the literal set `{"exterior", "natural"}`,
which never matched the canonical `outdoor`, so a compiled open-air path always
read "is open". It now uses `area_tags.is_open_sky`, the single predicate that
accepts both spellings.

### Crossing hazard — `engine/traversal.py`

`attempt` checks the **way's** tags before the destination area's ground
(`way_hazard(gs, way_id) or hazard(gs, dest)`). `CROSSING_HAZARD_SKILLS` is a
deliberately *narrower* set than `HAZARD_SKILLS`: only tags about the crossing
itself — `river`, `ford`, `flooded`, `cliff`, `rubble`, … The ambient ground
tags (`forest`, `swamp`, `snow`) stay the destination area's business, so a path
through woods does not turn every step into a Survival roll. A `bridge` on the
way cancels the check: a built crossing is answered, not rolled.

This is also the reader for **condition tags**: a trigger that writes `flooded`
onto a named way (via `add_tag`) makes that crossing an Athletics check with no
further code.

### Route-word exits — `engine/matching.py`

A way's physical route tag is an addressable name: a new tier matches `road` /
`bridge` / `ford` / `gate` / `tunnel` against a way's tags, so `go over the
bridge` resolves even when the handle is a place name. Only a **unique** match
resolves, so a road network does not swallow a plain `go road`.

## Follow-ups (planned, not in this change)

- **Plans toward a route** — let a plan step target a way (patrol the road). The
  plan engine moves toward *areas* (`current_area`), so this needs a "route via
  a tagged way" semantics and a path that prefers such ways, not just a new tag
  read.
- **Fear of the passage** — `fear` matches co-located character/item/area tags;
  a way is not co-located, so a `dense`/`dark`/`cliff` crossing needs a hook on
  the traversal path, not a tag read.

## Non-goals

- **No invented vocabulary.** A tag with no reader is dead weight; `muddy` and
  `dark` are evocative and stay unwritten until something reads them.
- **No directional tags yet.** A way joins two cells; a `from:`/`to:` split is
  added only when a consumer needs the asymmetry.
- **Not a second state model.** `blocked` remains `current_state`; a tag is a
  *reason*, never a substitute for movement's state machine.
