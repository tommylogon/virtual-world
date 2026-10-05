---
type: doc
tags: [system/gameplay]
---

# Per-Agent Knowledge (Fog of War)

`player.known` is a per-character list of the places, ways and items they have been
**told about**. `engine/fog.py` (346 lines) is the module that writes it: three reveal
verbs, a map-teach path, and the one filter that decides what a character may be told.
It is **unwired** — see "Unwired" below for the measurement.

Tasks: [[dev_tasks/done/world/task-499-per-agent-fog-of-war-and-map-knowledge-transfer|task-499]] ·
design: `docs/design/worldpainter-knowledge-and-fog.md`

---

## The gap this module fills

The gate existed before the key did. `engine/room_perception.py:56` already read
`player.known`:

```python
def way_visible_to(player, player_manager, viewer_name, way_node, area_name, direction):
    if way_node.properties.get("current_state") != "hidden":
        return True
    known = set(getattr(player, "known", None) or [])
    area_id_guess = "area_" + str(area_name or "").lower().replace(" ", "_")
    if way_node.id in known or area_name in known or area_id_guess in known:
        return True
```

and `visible_area_items` (`:82`) does the same for hidden items. Both are live and
both are called from real surfaces: `way_visible_to` from
`engine/area_description.py:259` (the exits list in prompts and `look`) and
`engine/scene_snapshot.py:198`; `visible_area_items` from `area_description.py:212`,
`engine/scene_snapshot.py:164`, `engine/observation.py:108`, `engine/movement.py:945`.

**Nothing in the runtime ever wrote to `known`.** Every test passed because every
fixture hand-populated the list. That is the whole of task-499's delta: the gate is
sound and has no key.

---

## `Known`: one set per character, holding ids *and* names

`Known` (`fog.py:62`) is constructed per character per call and holds no state of its
own, so two characters cannot share a set by accident — that is the property fog of
war actually is.

**Ids and names both matter and the registry stores both.** The perception gate matches
on `way.id`, `area_name`, *or* a lossy name-derived id guess, because hand-authored
ways predate the id convention. A known set holding one form leaks through the other
two, so `reveal` writes **every form it can derive** (`_forms`, `:142`: `id`, `name`,
and the `area_from_id` / `area_to_id` / `world_scope_id` connection props) and `has`
accepts any of them. The derived guess is never *needed* in the set — a reveal writes
the real id and the real name, so the guess is always redundant.

`player.known` stays a **plain list**, not a set: replacing it here would silently
change the save format (`fog.py:35-49`). It is de-duplicated on write instead, and it
serialises with the player — `engine/serialization.py:147` out, `:351` in.

`forget` (`:119`) has an asymmetry that is not cosmetic: a **string** drops exactly
that string, a **node** drops every form derived from it. Knowing the id and the name
are two entries; removing one leaves the gate still matching on the other.

**Unknown is not absent.** `Known.has` returning `False` means "not known", not "does
not exist" — so the prompt filter can only ever *withhold*, never assert.

---

## Reveal — three verbs

| Function | Verb in the world | Teaches |
|---|---|---|
| `reveal_area` (`:165`) | walking in | the area node |
| `reveal_examined` (`:172`) | examining | a **way** teaches the area on the far side, via `engine/beyond_visibility._area_across`; an area teaches itself |
| `reveal_sightline` (`:189`) | seeing down a corridor | every `area_id` / `area_name` in the sightline run |

`reveal_sightline` deliberately **reuses** `beyond_visibility.sightline_run` rather
than re-deciding what is visible. One place knows how far you can see, so the map and
the prose cannot disagree.

Each is total: a `None` area, a `None` target, or an empty run returns `[]` rather
than raising (`tests/test_fog.py:146`).

---

## Teach — a map goes into the *same* registry

`teach_from_map` (`:228`) writes `player.known`, which is the existing teach path.
**Two paths would mean two places to look, and one of them would be forgotten** — so
a walk and a map end up in one list, and a test asserts it
(`tests/test_fog.py:238`).

Three cases, and the difference between them is the difference between a blank prop
and an absent one:

| The item declares | Result |
|---|---|
| `charted_areas: ["area_0", "Room 1"]` | teaches exactly those entries |
| **no** `charted_areas` key at all | a map of wherever you are — every area in the world |
| `charted_areas: []` | teaches **nothing** |

The third is a bug the tests caught and it is worth stating as the rule: the test is
`"charted_areas" in props`, **not** a truthiness test. `[]` is falsy, so a
truthiness test reads "explicit empty chart" as "no chart" and hands out the whole
world (`fog.py:243-254`).

A chart entry that is a **display name** resolves to its area node (`:276-278`), so a
map that charts `"Room 1"` and a walk that reaches `area_1` teach the same forms
rather than two half-entries. The report counts **places** and **entries**
separately — `{taught, places, count, entries, total_known}` — because conflating them
makes "a map of two rooms" look like it taught five things.

No library item currently declares `charted_areas`
(`rg charted_areas` outside `engine/fog.py` returns only tests).

---

## Fog — present but marked

`fog_view` (`:306`) returns `{known, fog, known_count, fog_count}`, optionally with
`known_zones`. **Unknown entries are present in `fog`, not omitted from the payload.**
An omitted cell is indistinguishable from a cell that was never painted, so the map
could not tell "you have not been there" from "there is nothing there" — and fog of
war that looks like empty space is fog of war nobody explores. It also de-duplicates,
because a map that lists a cell twice is a map with a bug in it and a caller counting
`known_count` to draw a legend would be off.

---

## Honesty — a filter on a list, not a string

`only_known(player, names)` (`:294`) is the honesty boundary, and it filters a
**list**, deliberately. A filter on a rendered prompt string is unauditable; a list
filter is a call a reviewer can see, and a prompt that forgot to call it is the actual
failure mode this guards against.

Its degradation direction is pinned by a test (`tests/test_fog.py:268`): a filter that
**cannot decide returns nothing, never the input**. Returning the input would be an
omniscient agent with extra steps.

`unknown_are_hidden(player, area_name)` (`:339`) exists as a **named predicate** so
call sites read as a decision rather than an `if not in known(...)`, and so there is
exactly one place to change if the rule ever becomes "a rough bearing is allowed".

---

## Unwired — verified

> [!warning] The module is complete, tested (24), and unreachable
> Nothing in `engine/`, `routes/` or `static/js/` imports this file. A player
> cannot see per-agent knowledge today, and no amount of soak will change that —
> the honest reading is "not wired", not "low event rate". The evidence is below.

**`engine/fog.py` has zero runtime callers.** The only importer anywhere is
`tests/test_fog.py:21`.

```
rg -n "reveal_area|reveal_examined|reveal_sightline|teach_from_map|only_known|fog_view|unknown_are_hidden" \
   --glob '!.kilo/worktrees/**' -g '!docs/**' -g '!*.md'
→ engine/fog.py  (definitions only)
   tests/test_fog.py:21-31, 72-353  (the 24 tests)
→ nothing in engine/ other than fog.py itself, nothing in routes/, nothing in static/js/
```

(The four `fog.`-shaped hits in `engine/world_grid.py`, `engine/zones.py` and two
`static/js/worldpainter/` files are `@docs` pointer comments to
`docs/design/worldpainter-knowledge-and-fog.md`, not imports.)

Nothing calls `reveal_*` on movement or on examine. task-499 says so itself:

> *Nothing calls `reveal_*` on movement or examine. The verbs exist, are tested and
> are the right shape; the call sites are `engine/movement.py` (mine) and
> `engine/effect_handlers/examine.py` (contended).*

### What *is* live today: the authored half

`player.known` is not an inert field — it is **authored**, and it round-trips:

| Path | Line | What happens |
|---|---|---|
| `Player.__init__` | `player.py:229-234` | `self.known = []` — *"AUTHORED knowledge (not runtime discovery)"*, seeded from the character data's `known` list |
| save / load | `engine/serialization.py:147`, `:351` | list out and back |
| task-403 preconceived | `engine/serialization.py:433-438` → `agent_memory.load_preconceived` | `known_areas` / `known_items` / `known_ways` seed starting knowledge, idempotent by memory text |
| id repair | `engine/character_identity.py:228` `rewrite_known` | a `known` list naming a retired character id is remapped to the survivor |
| inspector | the "Known by" control | edits it (per the `player.py` comment) |

So a **hidden way an author put in a character's `known` list is genuinely visible to
that character today** — through the real `area_description` / `scene_snapshot` path.
That is the gate working with an authored key.

The **runtime** half is missing. Nothing in the live world ever *adds* to the list,
except `AgentMind.know_area` (`engine/agent_memory.py:96`), which is called from
exactly one place — `load_preconceived` at `:143` — i.e. scenario load, and nowhere
else (`rg know_area` outside tests returns two hits, both in `agent_memory.py`).

### How much authored knowledge exists

Measured across the shipped scenarios: **1 of 23 players** in
`kraktooth_goblin_camp.json` has a non-empty `known` list (Arix — 15 names and ids of
camp residents), and `mansion.json` (9 players) and `world_template.json` (3) have
**none**. So in practice the gate fires for one character in one scenario, and the
fog-of-war model is authored-only.

---

## What would make it reachable

Two call sites, and the module already says where they are:

1. **`reveal_area` on arrival** — `engine/movement.py`, where a character's
   `current_area` is set. One line.
2. **`reveal_examined` on examine** — `engine/effect_handlers/examine.py`. A way
   teaches where it goes; a place teaches itself.

Plus, for the map to actually teach, `teach_from_map` needs a hook on `use` / `read`
of an item carrying `charted_areas`.

And for the fog to be *visible*, `fog_view` needs a caller — the task's own acceptance
line ("the map view shows only known cells/zones") has no implementation surface yet.
The design doc records the same open question
(`docs/design/worldpainter-knowledge-and-fog.md`, §Still open): whether fog is tracked
per cell, per area, or per scope — task-499 starts at area/scope.

---

## Tests — `tests/test_fog.py` (24)

| Group | Count | What it pins |
|---|---|---|
| The missing key | 8 | a fresh agent knows nothing; a reveal teaches both forms; re-revealing adds nothing; **two agents never share a set**; `forget` on a node vs a string; empty inputs are not crashes |
| The verbs | 4 | walking in; a way teaches where it goes; an area teaches itself; a sightline teaches its rooms |
| The map | 4 | a chart teaches exactly its chart; a chartless map teaches where you are; an **explicit empty chart teaches nothing**; a map and a walk share one registry |
| Honesty | 4 | the filter, names as well as ids, **degrading to nothing**, the named predicate, two agents getting different prompt answers from one world |
| The view | 3 | fog present-but-marked; stable with no input; de-duplicated; zones optional |
| The payoff | 1 | a revealed hidden way is visible to the agent that revealed it and still hidden from another, through the real `room_perception.way_visible_to` |

`tests/test_known.py` covers the gate itself and still passes.

---

## Related docs

- [[Rooms & Areas]] — what a reveal is teaching
- [[Doors & Connections]] — `way_visible_to` and hidden exits
- [[Character Spatial Position]] — the other half of hidden-node perception
- [[Memory System]] — `agent_memory` and the authored-knowledge path
- [[Items Overview]] — the "Known by" control and authored item ids

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply` — relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Read next** — [[Background Simulation#Wiring]]

**Features** — [[per-agent-knowledge-fog-of-war|Per-agent knowledge (fog of war)]] (#29)

**Neighbouring notes** — [[Character Spatial Position]], [[Search & Forage]], [[Turn Queue & Human Turns]]

<!-- connected:end -->
