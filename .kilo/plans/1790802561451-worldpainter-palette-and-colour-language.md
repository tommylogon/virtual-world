# WorldPainter: palette, one colour language, and the structure vocabulary

## Goal

Make the paint-time palette show what each entry **is** and **does it for gameplay**, give every
biome a colour that means something, and fix one place where the painted world's structure does
not match the engine's.

Satisfies `task-596` (its Acceptance is `- TODO` today; fill it in rather than filing a duplicate).

## Decisions

**Three families, no fourth.** Classify by what the cell belongs to:

| Family | Members | Count |
|---|---|---|
| World biomes | the 16 wild-terrain entries | 16 |
| Constructs | 31 buildings + `wall` + `void` | 33 |
| Interior | 53 rooms + `window` + `door` + `stairway` | 56 |

`door` and `stairway` placement is **derived by applying your window rule** (a threshold between
rooms belongs to the interior), not stated by you. A door also belongs to the building it sits
in, so this is the one ambiguous placement — confirm at review.

**Colour carries kind.** Hue is the only channel reliably discriminable at 22px per cell. Within
a family each subgroup gets its own hue; entries sharing a subgroup separate by lightness.

**Colour is authored, server-owned.** A `color` field per record in `data/worldpainter/biomes.json`,
served by `/api/world/painter/vocabulary`, consumed by both the palette swatch and
`grid-model.layerColor`. Precedent: task-557's "the server owns the values." The 16 wild colours
already in `grid-model.js:88-92` move into `biomes.json`.

**Structure colours stay reserved.** `wall` `#55525c`, `void` `#22222a`, `window` `#8fc4d8`,
`door` `#a8763f` read as fabric or threshold, not as places. Check them against every place hue
before finishing — door brown against storage brown is the obvious collision.

## Findings that changed this plan

### 1. Every painted door is currently a glass door

`_mint_way` hardcodes both properties at `world_compile.py:2016-2017`:

```python
"current_state": "open",
"see_through": True,
```

`movement.py:564` gates passage on `current_state`, so you **can** walk every one. But
`barriers.py:147-149` resolves `see_through` ahead of state for light and sound, and
`DEFAULT_LIGHT_TRANSMISSION` gives `see_through: 0.75` against `open: 1.0`. So every painted
way — doors, stairs, region boundaries, island links — passes ¾ light and rates worse for sound
than an open doorway. The same emitter serves every one of them (`world_compile.py:1998-2001`).

This is why the window branch at `:1777` refuses to mint a way: minting one would be
indistinguishable from a door, because all of them already are. The special case is the symptom.

### 2. The engine already models glass correctly — twice over

`movement.py` gates on `current_state`; `barriers.py` gates light/sound on `see_through`. They are
independent, so all four combinations exist:

| | opaque | see-through |
|---|---|---|
| **not walkable** | `closed` | `closed` + `see_through` → a window; add `needs_open` and it is breakable |
| **walkable** | `open` → a door | `open` + `see_through` → **a glass door, expressible today** |

`tests/test_beyond_visibility.py:145` covers the closed case. So the way layer needs nothing new.

### 3. The way layer already models this — three independent axes

From the Way inspector's Passage and Behavior tabs:

| axis | properties |
|---|---|
| passage | `current_state` (`open`/`closed`/`locked`/`blocked`/`broken`/`hidden`) + `requires` (none/crawl/climb/jump) |
| transparency | `see_through`, a single boolean |
| uncloseable | `prevent_close`; `requires: crawl/climb/jump` is always uncloseable |
| effort to open | `needs_open` `{skill, dc}` — auto-sets `current_state: "open"` on success |
| size | `max_size` (tiny…titanic) |
| per-side | `visible_in_direction`, command, cardinal, visible characters/items |

`movement.py` gates passage on `current_state` (`:564`); `barriers.py:148` gates light and sound on
`see_through`. So every combination asked for already exists:

- open door — `open`
- closable and opaque — `closed`
- closable and seen through — `closed` + `see_through: true`
- archway / forest trail / cave entrance — `open` + `prevent_close: true` + `see_through: true`
- door with a small window, broken through — `closed` + `see_through: true` + `needs_open`

**The gap is not the way model. It is `cell_kind`.** `CELL_KINDS = ("place", "solid",
"see_through", "passable")` (`biomes.py:64`) is single-axis — `passable` and `see_through` are
mutually exclusive values of one field — so a *painted* cell can be walkable or see-through but
never both. A glass wall is already expressible (today's `window`); a painted glass door is not.

Because `cell_kind` is the mechanic and records are the names, `window` and `glass_wall` can share
a kind and differ only in name and `descriptions` — one JSON record, no code.

### 4. The way library already holds the vocabulary

~87 way templates are selectable from the Way inspector (`data/library/ways/`), including
`frosted_archway`, `swinging_door`, `library_bookcase`, `ice_bridge`, `narrow_passage`,
`cellar_trapdoor`, `forest_trail_to_river`, `task_18_jump`, `task_18_ladder`.

No painted cell can express "a swinging door" however many `cell_kind` values are added, because
`cell_kind` says what a cell *is*, not which authored way it mints. **The palette should therefore
offer these templates as paintable entries**, not only cell kinds. That is the difference between
painting *glass* and painting *the library's glass door*.

### 6. Three climb systems — one of which the palette cannot see

| system | where | decided by |
|---|---|---|
| author-declared verb | way `requires: crawl/climb/jump` + `<requires>_dc` | the author; Athletics roll (`movement.py:542-546`), `on_fail_<requires>` triggers, own prose line and save effect |
| storey-delta gate | `DEFAULT_MAX_STOREY_STEP = 3`, per-scope via `_climb_threshold` | **the compiler, from the `floor` layer** — `_climb_step` (`world_compile.py:1202`), called at all four emission sites |
| prose-only cliff | `CLIFF_FLOOR_DELTA = 2` (`world_compile.py:237`) | entry phrasing only, no traversal effect |

`_climb_step`'s own report note (`:2614-2619`) says a gated climb is "a way the author cannot walk
until they paint a road over it." So **verticality is inferred, never declared** — a painted cell
cannot say "this is a climb," only produce a `floor` delta that reads as one. An interior opts out
of the gate entirely by being an interior (`:1191`).

Consequence for task 5: the palette's "what does this do" panel cannot be a per-entry constant for
anything whose behaviour depends on a neighbouring cell's storey. Either the panel computes it
(same payload problem as task 6), or it states the rule and names `floor` as the input. Note also
that `CLIFF_FLOOR_DELTA` and `DEFAULT_MAX_STOREY_STEP` are adjacent constants with different jobs —
a reader will conflate them.

The inspector's State dropdown offers `broken`. `WAY_STATES` (`barriers.py:36-38`) does not list
it, and the module documents that an unrecognised state resolves to `UNKNOWN_STATE_FALLBACK =
"open"` (`:69-71`). If that holds, a broken door is fully passable and passes 1.0 light — more open
than an open door. **Verify before asserting**; then either add `broken` to the ladder in both
tables (the module requires the two tables stay ordered along the same ladder) or remove it from
the dropdown.

### 4. What the palette must actually answer

task-596's own example is *"what is the difference between a bridge and a road?"* — a **gameplay**
question, not a colour one. The answer is in entry phrasing:
`world_compile.py:785-786` returns `("cross the bridge", "cross back over", ["in","out","bridge"])`.
Bridge, tunnel, ford, gate and road each get their own verb pair. That is the axis the detail
panel should speak to.

*(A previous draft of this plan claimed `road` and `bridge` were the same brown. Retracted — that
was read off two hex values without looking at the screen, and you can see the difference.)*

## Tasks

### 1. `see_through` means see-through, nothing else

Stop hardcoding it in `_mint_way`. Each minted way states what it is:

- `door` → `current_state: "open"`, no `see_through`
- `stairway` → as above plus `kind: "stairway"` and the existing `climbs` flag
- `window` → mints nothing; continues to record onto the place it faces
- region boundary, island link, road link → decide each; the recommendation is a plain open way,
  because nothing about a boundary is glazed

**Blast radius: every generated world's lighting and sound changes.** Painted rooms get brighter
and quieter through their doors, because a real opening is 1.0 light / 0.5 sound rather than
0.75 / 0.75. Expect `tests/test_light_barriers.py` and lighting fixtures to move. Compare failure
*names* against the 12-failure baseline, not counts — and do not get green by weakening assertions.

Decide whether the window branch keeps `props["windows"]` (nothing reads it — `area_description.py`
never mentions it) or is deleted. Recommend deleting once doors are correct, since a real window
way would reach prose through way metadata like any other.

### 2. Add glass to the structure vocabulary

- New `cell_kind` for walkable-and-see-through, wired in `biomes.cell_kind()` and the compiler's
  branch at `:1777-1813`. A `passable` cell with `see_through` must mint a way carrying both.
- New records, each one JSON with no code beyond the new kind:
  - `glass_door` — walkable, see-through
  - `glass_wall` — `cell_kind:see_through`, not walkable (may share the kind with `window`)
  - optionally `curtain` / `hedge` / `fence` to show the mechanism is general
- Breakable variant: `needs_open` already exists (`movement.py:584-600`), so a see-through wall
  you must break is a state change, not a new mechanic. Confirm it reads correctly for a
  *window* rather than only a door before relying on it.

### 3. Wall reaches the description

Walls mint no way, so prose is their only channel. Record facing walls onto the place they border
mirroring the shape `windows` used — `props["walls"] = [{"x","y","facing"}]`, and only when exactly
one side faces a place (the same `len(facing) == 1` rule, for the same ambiguity reason). Extend
`engine/area_description.py` to read it; the sibling mechanism is `visible_in_direction`.

**This changes compiled description prose** — the largest regression surface here.

### 4. Give every biome a colour, server-owned

- Add `"color"` to all 105 records. Move the 16 wild colours out of `grid-model.js`.
- Pick hues per subgroup: 9 building categories, 14 room purposes, the wild set, plus structure
  hues no room can take.
- Serve from `/api/world/painter/vocabulary` (`routes/world_grid_ops.py:266-294`). Have
  `biomes.validate()` (`biomes.py:392`, `:406`) reject a record missing `color`, as it already
  rejects missing `descriptions`.
- `grid-model.js` drops `BIOME_COLORS` for biome, keeping the hash fallback **only** for unknown
  ids so a typo still renders visibly wrong.

### 5. Build the palette (task-596 proper)

Replace the 105-option `<select>` (`editor.js:1194-1276`). Keep the text filter (task-647) and the
`<optgroup>` logic (task-561/568/648) as data — only the rendering changes.

- Layer-aware: renders per `PAINT_LAYERS` (`biome`, `road`, `floor`, `climate`).
- Three family chips + search; the swatch shows the served colour exactly, which makes the
  palette its own legend.
- Tile grid, no nested scrolling. Persistent detail panel (not hover-only) showing name, id,
  family, subgroup, both `descriptions`, tag chips, **and what it does for gameplay**:
  - places: becomes an area, named or unnamed
  - `door` / `glass_door` / `stairway`: mints a way — walkable, and `stairway` climbs
  - `window` / `glass_wall`: see-through, not walkable, mints nothing
  - `wall`: nothing itself; separates regions so they do not merge
  - `void`: an empty unwalkable cell — explicitly **not** an unpainted one, which is a different
    state and usually a mistake worth warning about
  - roads: the entry phrasing, so "cross the bridge" is answerable without leaving the palette
- Keep a compact current-value indicator: painting needs the selection visible without reopening.

### 6. One palette payload, not three agreeing copies

`grid-model.js` already hand-mirrors `PAINT_LAYERS` and `compile_grid`. Serve one assembled payload
and render it. Any palette fact computed in JS needs a comment naming the backend field it came from.

### 7. Correct the terrain fields while touching these records

`wall`, `void`, `window` and `door` all carry `terrain: "urban"`; `stairway` carries
`terrain: "indoor"`. A wall is not urban terrain. Harmless today because grouping reads `tags`, but
any future `terrain`-driven behaviour would misfile them. Do not build the palette on `terrain`.

## Risks

- **Task 1 changes every generated world.** Painted rooms brighten and quieten. This is the
  highest-regression item and needs real lighting measurement, not assumption.
- **Wall descriptions change every compiled place's prose.** Second largest.
- **Three tests assert the inert `props["windows"]`** (`tests/test_world_compile.py:491`, `:519`,
  `:609`). They pin an implementation the engine convention contradicts; update them to assert the
  minted way and record why in the task.
- **A structure colour colliding with a place colour** reintroduces the confusion this plan removes.
- **New `cell_kind` values must not silently break `interior_gen.py:110-120`**, which branches on
  `cell_kind` for plan generation.

## Validation

Playwright against `http://localhost:4444`, screenshots as primary evidence. A surface judged from
markup or one viewport is not judged.

- Palette: all three families reachable; all 105 entries present; search still narrows by name and
  id; each structure entry's stated gameplay effect matches what Generate actually produces.
- Glass: paint a glass door and an opaque door between the same two rooms. After Generate, confirm
  one way carries `see_through: true` and the other does not, and that light/sound differ
  measurably between them.
- Breakable window: paint a see-through wall with `needs_open`, attempt to cross, confirm the
  skill check fires and the state changes on success.
- Walls: paint a room against a wall, Generate, confirm the description mentions it.
- **Scrub the whole panel bottom to top and open every disclosure** — the checklist, blocker badge
  and cell inspector are all collapsible, and that is where the equipment-UI mistake came from.
- Gates: `python -m pytest -q --tb=no --ignore=tests/test_tick_time_scaling.py` comparing FAILED
  *names* against a clean-`master` worktree; `node tools/unit/run.cjs`; `npm run lint`;
  `npm run typecheck`; `python tools/js_module_index.py --check`.
- `tools/unit/run.cjs` does not load `editor.js` (task-574). Extract `_biomePalette` and the payload
  assembly behind a testable surface so the palette has real coverage.

## Filing

- Update `task-596`'s `Acceptance` (currently `- TODO`) for tasks 4, 5, 6, 7.
- File new tasks for **1**, **2** and **3** — engine changes with lighting and prose fallout, which
  do not belong inside a UI task's acceptance.
- `tools/tasks.py new --area ui|world`; do not hand-number. Regenerate `docs/dev_tasks.html`.

## Out of scope

Agreed, not deferred silently:

- Canvas usability: no brush footprint under the pointer, no zoom-scale readout, space-pan and
  wheel-zoom wired but undiscoverable, ~12 browser-native `confirm`/`prompt` dialogs. Real
  findings, separately fileable.
- Fog rendering — `docs/design/worldpainter-knowledge-and-fog.md` leaves granularity open and
  task-499 records `reveal_*` as having no caller.
- Task-597 (grid bounds preview, drag/resize) and task-595 (zoom clamp).
- Unused tags `perceivable` / `impassable`. `see_through` becomes real in task 1; the others stay
  declarative until something consumes them.
- A WorldPainter authoring tab for `biomes.json` (task-589, blocked by task-588).

## Open questions

1. **`door` and `stairway` placement** — derived from your window rule; confirm.
2. **Region-boundary and island-link ways** — should they be open or glazed? Task 1 recommends open.
3. **`props["windows"]`** — recommend deletion once doors are correct.
4. **Wild-terrain grouping** — the 16 are flat and unheaded. Group by `terrain` (7/5/3/1 water/rock/
   forest/farm) or leave flat. Four stubs may read worse than no grouping.
5. **Three climb systems, and one of them is invisible from the palette.** See below — decide
   whether a painted cell can *declare* verticality or only be *read* as vertical.