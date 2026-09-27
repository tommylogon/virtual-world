---
type: task
status: inprogress
area: testing
priority: high
related: [task-528, task-553, task-554, task-557, task-558, task-564, task-566, task-567, task-568, task-525, task-529, task-535, task-536, bug-48]
---

# task-574: Test guide: the 2026-09-27 WorldPainter session

**Filed:** 2026-09-28
**Related:** task-528, task-553, task-554, task-557, task-558, task-564, task-566, task-567, task-568, task-525, task-529, task-535, task-536, bug-48

## Goal

A per-feature test guide for everything built on 2026-09-27, so each can be checked
by hand in the app and against the suite.

Thirteen tasks plus one unfiled feature, in one place, so the next person (or the
next session) does not have to reconstruct what "working" means for each from
the diff. Every entry has the same four parts: **what it is**, **how to test it by
hand**, **what passing looks like**, and **the automated coverage** that already
guards it — so a manual check is for the wiring, not for the logic.

## Preconditions

- **Restart the app.** Every backend change (compiler, grid, routes, engine) needs
  it. Static JS only needs a page reload, but the JS and the API ship together here,
  so restart and reload both.
- Open the WorldPainter from the top menu: **🗺️ WorldPainter**, or
  `VW.worldPainter.open('<scope_id>')` in the console. The tool rail only appears on
  a scope that **has a grid** — a scope without one renders the "no grid" panel, so
  an empty rail is not a bug.
- `python -m pytest -q` — the baseline is **60 failed / 4182 passed**. All 60 are
  pre-existing: 55 × `test_mcp_*` (`'function' object has no attribute 'fn'`, a
  FastMCP wrapper mismatch in this environment), 2 × `test_character_identity`, 1
  each in `test_scenario_name`, `test_social_company`, `test_templates`.
- `node tools/unit/run.cjs` — **371 passed / 13 failed**, and the failure count
  *flickers between 13 and 14* on consecutive identical runs, all in
  `test_plan_tracker.js`. Treat a count of 13 **or** 14 in that file as green.
- `npm run lint`, `npm run typecheck`, `python tools/js_module_index.py --check` —
  all clean.

## Known issues found while writing this guide

Two bugs were found by looking at the app rather than the tests, which is the
reason this document exists. **Both are DOM-only defects that no unit test in the
repo can currently catch.**

1. **FIXED — the grid vanished when the rail moved beside it.** `_grid()`'s wrapper
   relied on `align-items:stretch` from the panel's *column* flex box to get its
   width. As a flex item in a **row** (rail + grid) it took its content width, and
   its only child is absolutely positioned, so the wrapper collapsed to **0px** and
   the 900px canvas overflowed a zero-width box: the canvas was in the DOM with five
   live layers and nothing was visible. Fixed with `flex:1 1 auto; min-width:0` on
   the wrapper. *Test it:* the grid's bounding box must be ~876px wide, not 2.
2. **OPEN — a Select-tool marquee commits only one cell.** Dragging the rubber band
   across several cells selects the anchor cell alone, so `_commitMarquee` is
   reading an un-updated `drag.to`. The single-click path works ("1 cell selected"),
   so the mousedown/mouseup wiring is fine and the fault is in the `mousemove` that
   advances `state.marquee.to`. **Suspect:** every Konva layer is created with
   `listening: false`, and Konva only delivers stage `mousemove` when hit detection
   finds a listening shape — which would also break **paint drag-strokes**, not
   just the marquee. That is worth checking first, because a broken drag-stroke
   predates this session. *Test it:* a drag across 3+ cells selects all of them,
   and a paint drag across a row colours the whole row.

## The features

### 1. Boundary ways out of a hand-placed area (task-528's deferred half — **not filed as a task**)

*What:* a hand-placed area is reserved on its cell and therefore not a region, so
the compiler never saw it and it had **no way to anything**. The compiler now mints
one way per painted cell touching it, on the same terms as any other boundary.

*By hand:* Kraktooth's `world` scope has 10 hand-placed areas. Ungenerate, Generate,
open the graph. `Camp Entrance Trail` at (9,5) should gain ways to `Road (world 9,4)`
(north), `Road (world 9,6)` (south) and `Sparse Forest (world 10,5)` (east).

*Passing:* compass `direction` per way, `kind: "open"`, a `surface`, a midpoint
`cell`, and four connection edges per way. Two adjacent placed areas get **one**
way between them, not two.

*The author's call survives a regenerate:* inspect a cell holding a placed area; the
panel lists each seam as `north → Road (world 9,6)` with a **✕**. Clicking it
deletes the way and records the decision; Ungenerate + Generate must **not** bring
it back. The seam then reads "to removed by you" with a **↺** to hand it back.
Suppressing a non-seam way, or a hand-authored one, is refused with a reason.

*Automated:* `tests/test_world_compile.py` (boundary section),
`tests/test_world_grid_routes.py` (`test_generate_mints_a_boundary_way…`,
`test_suppressing_a_seam_deletes_it_and_it_stays_deleted`,
`test_a_hand_written_replacement_is_recorded_with_its_own_way`,
`test_clearing_an_override_hands_the_seam_back`,
`test_overriding_a_way_that_is_not_a_boundary_is_refused`).

### 2. Indoor room vocabulary (task-568)

*What:* 53 indoor rooms plus a `stairway` cell, so a floor plan can be painted
without unknown-id warnings, and the palette is grouped by purpose.

*By hand:* in the biome dropdown, look for **— Rooms —** with sub-headings
(Circulation, Living, Sleeping, Cooking, Eating, Storage, Workshop, Worship,
Records, Study, Trade, Civic, Service, Outdoor) and a **— Structure —** section at
the end. Paint a small inn: a run of `hallway`, a `kitchen`, a `bathroom`, and a
`stairway` between two rooms. Generate.

*Passing:* no "unknown id" note in the generate report. A `stairway` is **not** a
room — the cell produces a `kind: "stairs"` way with `handle: "stairs"`,
`aliases: ["stairs","stairway","up","down","in","out"]`, and a pass message that
says "You take the stairs to X", never "You climb 0 storeys". Ten cells of
`hallway` are **one** area even with merge off.

*Automated:* `test_every_wild_biome_*` and `test_shipped_taxonomy_validates_clean`
(`tests/test_biomes.py`) — an indoor room must not be asked for a forage tag.

### 3. Per-kind merge rules (task-564)

*What:* merging is per kind instead of one switch for the scope. `merge: always` on
a record, `merge: never` for any building.

*By hand:* paint five `hallway` cells in a row and leave **merge same-biome off** —
Generate. Then paint three `cottage` cells, turn merge **on**, Generate.

*Passing:* the corridor is **one** area; the cottages are **three** areas. Two
`dining_hall` cells are two areas with merge off and one with it on. A wilderness
scope with no rooms and no buildings compiles exactly as it did before.

*Automated:* `test_a_region_never_spans_two_storeys`,
`test_a_building_is_never_merged_with_its_neighbour`.

### 4. The storey-delta climb gate (task-525)

*What:* a grid step across more than three storeys in a **world** scope needs a
path: the way is refused, and painting a road over the step opens it.

*By hand:* in a `mode: world` scope, paint two adjacent cells and set the **floor**
layer to `0` on one and `6` on the other. Generate. Then paint a `road` on both
cells and generate again.

*Passing:* the first way carries `climb_required: true`, `current_state: "closed"`
and a refusal ("The climb is 6 storeys of bare ground — you would need a path cut
into it, or a way round."), and the report says how many steps were gated. With the
road, the same pair is `open`. Do the same in a `mode: interior` scope: **nothing is
gated** — a cellar four storeys under a hall is not a trap. The threshold is
per-scope at `record.climb.max_storey_step` (default 3).

*Automated:* none yet. The behaviour was verified by a scratch script only, so this
is the **weakest-covered feature in the session** and the first place to add tests.

### 5. Entry phrases owned by the record or the placement (task-529)

*What:* a `tunnel` says "go down the tunnel" from its own record; a placement may
override that for one specific mouth; the area description *offers* the move.

*By hand:* place a child scope on a cell with a `tunnel` on the road layer.
Generate, then `look` in the parent area. Then set
`placements.<child>.entry_phrase = "crawl down the old adit"`, regenerate, and
confirm the phrase is still there afterwards.

*Passing:* the description says **"You could go down the tunnel — Shaft is on the
other side."**, not `[go down the tunnel] is clear`. `go in` still works (the short
handles are kept as aliases). A closed seam reads "You could enter the tavern, but
the tavern's door is shut and the sign is turned." The author's phrase survives a
regenerate — placement records are rebuilt from the cell, and author keys are
carried through.

*Automated:* `test_entry_phrases_come_from_the_placement_not_a_hardcoded_in_out`,
`test_every_entry_phrase_keeps_the_short_handles_as_aliases`,
`test_an_override_keeps_the_short_handles`, `test_gateway_is_walkable_in_and_out`.

### 6. Promote a selection into a child scope (task-535)

*What:* an existing area becomes a child scope, with a gateway, and the gateway
carries **no** generated provenance so the parent's Ungenerate cannot delete it.

*By hand:* inspect a cell with a hand-placed area → **🪜 Make this a scope…**. Give
it a name. Then Ungenerate the **parent** scope and Generate it.

*Passing:* the areas move scope (their `cell` marker is cleared, their names, items
and ways stay), the scope appears `baked`/`materialized` in the breadcrumb, and the
gateway **survives** the parent's Ungenerate. Every refusal (empty selection,
duplicate id, an id that is not an area, an entry outside the selection, a cell
that is not a painted place) leaves the world untouched and pushes **no** undo step.
`Ungenerate` on a baked scope is refused with a reason, and a hand-authored way into
a scope is kept and reported in `kept_ways` rather than deleted.

*Not wired:* the graph's **multi**-select (vis runs `multiselect: false`), so the
button promotes one area at a time. The helper takes a list.

*Automated:* none yet — verified by scratch script only. Second-weakest coverage.

### 7. The tool rail, selection and move (task-536)

*What:* eight tools down the left with one key each, marquee and click selection,
paint/erase across a whole selection in one request, and a Move tool that shifts
cells' contents.

*By hand:*
- The rail shows `⬚ Select · 🖌 Paint · 🧽 Erase · ✥ Move · 🧭 Route · 🏠 Feature ·
  📍 Area · 🔍 Inspect` with keys `V P E M R F A I`, and the active tool outlined.
- Press **V**, drag a marquee: the panel counts the cells and the cells are tinted.
  Click a selected cell again: it deselects. **Ctrl+A** selects all, **Escape**
  clears.
- With cells selected, switch to Paint and click once: **every** selected cell gets
  the value, in one request, one undo.
- With cells selected, press the arrow keys: their contents shift one cell, clamped
  at the edge, sources cleared, in one undo.

*Passing:* a drag on Space pans; a drag with Paint strokes; a drag with Select
marquees — and switching tools re-decides which, so a tool switch cannot leave the
canvas panning when it should be painting.

*Two known defects to check first:* the **marquee commits one cell** (see Known
issues) and, underneath it, a possibly-broken **paint drag-stroke** on a
non-listening stage.

*Automated:* none. `editor.js` is DOM code the node sandbox does not load, which is
why both bugs above got through.

### 8. Edge-label wrapping in the graph view (task-558)

*What:* long edge labels wrap, the edge length is computed from the wrapped line
count, `unlocks` edges show three lines of prose, and vis-network is pinned.

*By hand:* open the graph, turn edge labels on, find a long `unlocks` edge. Look at
a two-sided label.

*Passing:* the prose wraps over at most three lines and ends on a sentence
boundary with an ellipsis; the full text is still on the hover tooltip. A short
label ("west") is one line with the same length as before. `vis-network@9.1.9` is
what the page loads.

*Deliberate:* **way nodes were not touched** — they are nodes, and growing a node
box collides with the map layout's margins. Way names keep the label-LOD policy.

*Automated:* `node tools/unit/run.cjs` (the JS suite as a whole).

### 9. Per-area base temperature and the outdoor curve (task-553)

*What:* `base_temperature` (authored) is split from `temperature` (simulated), and
`temp_curve_for_hour` gives a diurnal curve plus a season bias.

*By hand:* paint a `climate` layer (see 10) and `look` at two areas at the same
hour, or step the clock from 04:00 to 14:00.

*Passing:* the two areas differ by exactly their base difference. A 5-storey-climb
clause above applies. **The compatibility guarantee:** an area with no authored
`base_temperature` in a world with no season stays at a flat **21.0 °C** at every
hour, which is what every existing world has always reported. `temperature_mod: 0`
is honoured (not dropped as falsy); a NaN or infinite base falls back to 21.0.

*Automated:* none yet.

### 10. The climate paint layer (task-557)

*What:* five coarse climates that compile to a per-area `base_temperature`.

*By hand:* pick layer `climate` — a legend of five colour chips with the °C each
compiles to appears under the toolbar, and "unpainted is Temperate". Paint
`arctic` on one cell and `tropical` on another in a **world** scope. Generate. Then
paint `arctic` across **half** a merged region and Generate. Then paint a
misspelling such as `tropcial`.

*Passing:* the two areas report −8.0 °C and 27.0 °C. A climate boundary **does not
split** an area — three arctic cells and two tropical ones are still one area, the
majority wins, and the report says so. A road still *does* split. An even split
breaks the same way twice (row-major tie-break). The typo is a reported `WARNING`
naming the cell, not a silent temperate. A `town` or `interior` scope gets **no**
climate — a hall is not −8 °C because of paint. A world with no climate layer
compiles byte-identically to before.

*Automated:* `test_the_five_climates_each_carry_a_base_c_and_a_colour`,
`test_a_climate_cell_paints_in_its_own_colour…`,
`test_the_server_decides_the_base_°C…` in `tools/unit/test_worldpainter.js`, and
`test_painter_vocabulary_lists_real_ids` for the payload.

### 11. Season, read by the engine (task-554)

*What:* one server-side month→season resolver; the frontend's two copies of the
table are gone.

*By hand:* step the calendar across a month boundary (3→4, or 11→12) and watch the
log and the sky. Or set `world_state.season` in a save and load it.

*Passing:* `[Season] Winter arrives.` appears **once** at the change, and the first
tick does not narrate. An authored `world_state.season` beats the clock; an
unrecognised name falls through to the clock rather than becoming a state the
temperature model has no bias for. Winter is 11 °C colder than summer on the same
world. `sky-scape.js` no longer contains a month→season table.

*Automated:* none yet.

### 12. Interiors generated from a building type (task-567)

*What:* 30 drawn floor plans in `data/worldpainter/interiors.json` plus a fallback,
covering all 31 building types, painted as **cells** so the standard compiler builds
the rooms.

*By hand:* on an `interior` scope, **🏠 Paint an interior…** → `tavern`. Edit a cell
(or marquee two). Paint it again and choose `tavern` a second time.

*Passing:* the first paint reports ~60 cells and the scope stays **unmade** — paint is
not places. Generate: 8 rooms across two storeys with a cellar, 16 ways, and a
stairwell threshold, all from the standard compiler. The scope gets a grid if it had
none. The second paint says how many cells it left alone, and the author's edits are
still there while untouched cells are re-written to the plan. `mall` uses the
fallback and says so. A short plan row is padded with a **wall**, never a door, and
the padding is reported.

*Automated:* none yet.

### 13. A character seeking a place by function (task-566)

*What:* `engine/venues.py` — seven venues looked up by the tags a place already
carries. A tired character asks where a bed is and walks there.

*By hand:* in a town where some area carries `sleeps` (an `inn`, a `cottage`, a
`guest_room`, a `bedroom`), drop a character's `Energy` to ~50 and step the sim.
Watch the log.

*Passing:* the log says `Ari walks to The Stag Inn — is looking for a bed`, one hop
at a time. Among several inns the choice is: **fewest hops → familiarity →
preference tier → node name**, so a character with a bed next door does not cross
town, a regular goes back to *their* inn, an inn beats a bunkroom at equal hops, and
the same world answers the same way every turn. In a world with **no** venues
nothing changes and no line is written — the fallback is the old behaviour.

*To make Kraktooth show this:* none of its hand-authored areas carry `sleeps`, so
nothing will move there yet. Paint an inn, or promote the camp and paint an interior.

*Automated:* none yet.

### 14. Map layout while Levels owns it (bug-48)

*What:* acceptance written for a fix that was already in the code. Levels places
every node, so Map would silently do nothing; Map is now **refused** while Levels is
on, visibly (the tab is disabled with a title saying why) and programmatically
(`toggleCardinalLayout` toasts and returns false). `activeLayout()` is the one source
of truth the segmented control reads.

*By hand:* switch to **🌳 Levels**, then click **🗺️ Map**.

*Passing:* the Map tab is disabled with an explanatory title, and calling
`graphManager.toggleCardinalLayout()` toasts and returns `false`.

*Automated:* `tools/unit/test_graph_toolbar.js` — "Map is unavailable while Levels
owns the layout" and "Map is available in the other two layouts", against the pure
`mapTabDisabled(state)` helper.

## What is not covered, and why it matters

Four of the fourteen (climb gate, promotion, temperature, season) have **no
automated test at all** — they were verified by scratch scripts during the session
and by reading the report. The two worst offenders are the ones a user will hit
first in a fresh world: **the climb gate** and **the interior generator**.

The pattern behind both bugs found today is the same: `static/js/worldpainter/editor.js`
is DOM code that `tools/unit/run.cjs` does not load, so nothing in the suite can see
a collapsed wrapper or an option list of `undefined`. The cheap fix is to extract
the two pure functions — `_biomePalette(layer)` and `_layerOptions(layer)` — behind
a small testable surface and assert that every non-separator option has a non-empty
`id` and `name`. That single test would have caught the flattened palette, and it
costs about twenty lines.

## Acceptance

- [x] One entry per feature from the session, each with **what it is**, **how to test
      it by hand**, **what passing looks like**, and **its automated coverage** —
      so a manual check is for the wiring, not for logic already under test.
- [x] The preconditions section states the **actual current baseline** (60 failed /
      4182 passed; 371/13-or-14 JS) so a future reader can tell a regression from the
      known failures, including the `test_plan_tracker.js` count that flickers.
- [x] Known issues are recorded rather than discovered twice: the fixed zero-width
      grid, and the **open** marquee defect with its likely root cause (Konva
      layers created `listening: false`, which may also break paint drag-strokes and
      may predate this session).
- [x] Features with **no** automated coverage are named as such, so the gaps are
      visible instead of implied — and the cheapest missing test is proposed
      concretely.
- [ ] The open marquee defect (Known issues #2) is fixed, with its `mousemove`
      cause established — and if a non-listening stage is breaking paint
      drag-strokes too, that is filed separately as a pre-existing bug.

## Notes

- Written **after** verifying by hand, which is what caught both known issues. The
  lesson recorded here is the one worth keeping: the palette showed
  `undefined (undefined)` in every dropdown, and the grid rendered nothing at all,
  and **neither** was visible to lint, typecheck, the JS suite, the module-index
  check, or the 4182 passing Python tests. Both were one-line fixes found by
  looking at the screen.
- The boundary-way feature (entry 1) has **no dev task of its own** — it is the
  deferred half of task-528, which is in review. Filing it separately is worth doing
  so its acceptance has a home.
