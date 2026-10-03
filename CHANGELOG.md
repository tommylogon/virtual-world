# Changelog

All notable changes to VirtualWorld. See `docs/virtualWorld/Scenario Workflows & UI Audit.md` for the long-term plan this release follows.

---

## Unreleased — "Things Stop Vanishing" (2026-10-03)

**186 commits, 95 distinct tasks and bugs.** This update is dominated by one theme that
the previous entries kept circling: **data that was authored, paid for, and then silently
destroyed by the editor on save.** Two of the fixes below were reproduced in a live browser
*before* any code was written, and both destroyed user content without a warning or an error.

Measured against the running app, not inferred from the code:

```
kiss {target:'player', where:'mouth', intensity:'rough'}  ->  kiss {}    # every param gone
one output wired to two actions                           ->  only the first survived
```

The first was worse than the ticket said. The behavior-graph action node offered **11** action
types and re-emitted **10** on save; the engine dispatches **121**. So **110 of 121 action types
(124 of 149 params) were destroyed** by opening a behavior in the graph and pressing Save.

### 🧠 The behavior graph stops destroying action params (task-388)

`TriggerTypes.BEHAVIOR_ACTION_TYPES` is now **the single action catalog** — 121 types with the
params **the engine actually reads**, extracted from
`engine/triggers/behaviors.py::_execute_behavior_actions`, whose `action_type` branches dispatch
121 types (91 of them reading params). Both editors render from it:
`inspector/behaviors-view.js` dropped its own 121-entry action literal, and the graph's action node
builds its dropdown *and* its field set from the catalog. A new engine action type is now editable
in both editors with no change to either. Params present on a node but not in the catalog are
carried through **visibly** rather than dropped.

**Two known gaps, both cost editability and not data.** The catalog omits `listen` and `trade`,
which the engine does dispatch; and it over-declares `add_tag`'s params as `tag`/`target`/`value`
where the engine reads a shared tail. Both were found by comparing the two lists rather than
assuming they agreed, and neither loses data on a round trip — the carry-through is generic, and
a type absent from the dropdown still round-trips through the "⚠ unknown type" option.

`static/js/shared/trigger-graph.ts::_buildActionFromNode` keeps bespoke defaults for the 11
hand-tuned node types and carries every other prop through verbatim. The carry-through skips
`undefined`/`null`/`''` only, so a real `0` or `false` survives.

The fan-out bug was the same class. `_traceBehavior` and `_traceGraph` used `wires.find(...)`,
so only the first wire off an output was followed. That one is an **editor bug, not a model
limit**: `behaviors.py:45` is `for action in actions:`, a flat action list, so the engine runs
fan-out natively. Both tracers now follow every wire, each branch with its own `seen` set, and a
cycle in an imported blueprint is reported instead of recursing until the stack dies.

`tools/unit/test_trigger_graph.js` (11 tests) asserts **all 121 action types round-trip with
every param intact**. It caught a bug in the first attempt — a fixed exclusion list dropped
`target`/`text` for every non-bespoke type, leaving 50 types failing.

### 🔌 Wires can be edited, and bad wires are refused (task-388)

Wires previously **could not be deleted at all** (task-388 defect #5): a mis-wire meant deleting
whole nodes. Now each wire gets a 14px transparent hit path (the visible 2.5px stroke was never
a usable target, and the SVG layer is `pointer-events:none`); click to select, **Del** to delete,
right-click to select-and-delete. Arrowheads are one `<marker>` per wire colour, oriented along
the bezier tangent so they point into the target socket at any zoom. Cycles and duplicate wires
are **refused at creation with a toast** instead of silently ignored.

A compile-honesty badge in the toolbar names the branches that will not be saved and why. The
behavior NO branch is deliberately **warn-only**: the behavior model has no `else` at all
(`fail_message` exists only for triggers), so it cannot be compiled away and must stay visible.

### ✅ The front end is TypeScript, in full

**158 of 158** classic-script modules under `static/js` are `.ts` sources emitting back to `.js`.
No bundler, no `<script>` changes — `templates/index.html` is untouched. The single gate is
`python tools/ts_convert.py check`, which runs `build:ts`, `typecheck`, `lint`, `module:check`
and the unit runner, verifies every emitted `.js` kept its `@module` header, and fails on an
unreviewed `window.` prefix drop. **It is green**, and it fails when a drop is unreviewed (verified
by injecting one).

Two records back the dropped-prefix check, both with traps now documented:
`tools/window-usage-baseline.json` (the `window.NAME` counts from before each conversion) and
`tools/window-usage-reviewed.json` (the 8 reviewed drops with their reasons). The baseline tool
**only adds files that are not already present** — it can add an entry but never refresh a stale
one, which is how 57 entries came to disagree with HEAD.

The recurring hazard is documented in `AGENTS.md` and `docs/design/typescript-migration.md`:
silencing `Property 'X' does not exist on type 'Window'` by deleting the `window.` prefix makes
the type check pass and turns an undefined-safe guard into a runtime `ReferenceError`. That is how
`test_fear_verbs` broke in a browser before anything noticed.

### 🧪 Things that now refuse to be wrong

A theme rather than a feature: a series of checks that turn silent corruption into a refusal.

- **Save schema gate** (task-453) — `SCHEMA_VERSION` in every save, with a registered migration
  and a refusal on load when the payload is newer than the app understands.
- **Biome lint from `biomes.json`** (task-573) — resource coverage is derived from the biome
  definitions rather than a hand-kept list, so a new biome cannot ship with no coverage.
- **Tag validation stops inventing near-misses** (bug-512) — it no longer suggests a tag you did
  not mean.
- **One carried-or-equipped edge per item** (task-450) — an item in two places is now impossible
  rather than merely discouraged.
- **Equipped ids are pruned when the item node is deleted** (task-654), and an equipped payload
  writes the **edges** too, not just the dict.
- **A dead-interest/fear-tag gate for scenario saves** (bug-513).
- **The character loadout shape gate** (`tools/character_loadout_check.py`) — a dict in an
  `equipped` slot 500s `GET /api/state`, so the check refuses that shape.
- **The worldpainter tool-key scan was scoped to the TOOLS table** (`a608f136`): it had matched a
  compass row and fabricated a defect the app does not have. A test asserting a non-existent
  failure is removed, not worked around.

### 🗺 The world is chunked, scoped, and knows where it is

The largest body of engine work in this window, and it is mostly about **identity and ownership**.

- **Global scope index with gateway targets, load-before-you-move** (task-583), **cross-chunk
  ownership** for locations, triggers and delayed events (task-584), and **scope
  load/unload/merge APIs with ownership checks** (task-582).
- **An id-keyed single location record, edge-authoritative on load** (task-581) — one truth for
  where a thing is, and the edge wins.
- **Id-first area resolution with canonical id projection and duplicate-name diagnostics**
  (task-439): a duplicate name is now a diagnostic instead of a coin flip.
- **Per-area capacity as a sum of occupant footprints** (task-653).
- **Physics defaults off in Map mode** (task-527) — a perf fix that also removed the stutter.

### 🧬 A character is a species, and can be hurt in two axes

- **A species identity the need layer can read**, carried through the serializer `/api/state`
  actually serves (task-549) — the first half without the second is a field that exists and is
  invisible at runtime.
- **One resolver for the vital ceiling, hit dice and one death path** (task-538). The engine had
  no health model; it had a `100`. `Max_HP` was the only vital with a maximum, and writing a
  `Max_*` through the API re-clamped the vital it was supposed to bound (task-538).
- **Two-axis defence and a selectable damage-reduction mode** (task-604/607) — flat or
  percentage, chosen in config, with the log saying which.
- **Ranged weapons and ammunition** (task-518); **a scale-correct ability curve** and the library
  that satisfies it (task-606).
- **Equipment has a coverage default, and wetness reaches the description** (task-489/215) — the
  point being that a vital which does not reach the text is not a vital.
- **Feelings steer behaviour** through one normaliser for a declared feeling (task-652).

### 🎒 An item has a history, a place, and rules

- **Provenance and acquisition history** (task-514) — where it came from and how it was got.
- **Concealed carried items, search-to-reveal** (task-516).
- **Homogeneous stacks and relational piles** (task-473).
- **Structured inscription, reachable by the agent** (task-433).
- **Item biome affinity** as a vocabulary, authored on the four resource templates (task-571), and
  a **biome resource spawner wired into grid generate** (task-569).
- **Kraktooth goblin gear spec and starting loadouts** (task-513/519) — and the spec reuses the
  task-515 Good Knife rather than minting a near-duplicate.
- The library is now **1,999 items** (measured via `GET /api/library/items`), up from 1,915.

### ⚡ Triggers, blueprints and the condition groups they needed

- **AND/OR/NOT condition groups are real graph nodes** (task-502) instead of an encoding trick.
- **A blueprint compiles to runtime nodes, with a searchable blueprint browser** (task-442).
- **Reusable behaviours load into the engine via `behavior_refs`** (task-590).
- **One compiler between trigger edges and `logic_trigger` nodes** (task-636) — there were two.

### 🖌 The painter, and the docs you can reach

- **WorldPainter**: a legible zoom floor, space-pans, tile detail, grid handles (bug-511,
  task-595/596/597); every paint layer always present with described palette tiles (task-651); and
  it stops offering known-bad reference art (task-649).
- **A documentation panel in the inspector and library editor** (task-579), **an authorable docs
  link on library entries** (task-577), and **a resolver route for module and node documentation**
  (task-578). The `@docs` contract now covers Python modules too (task-576).
- **Generated node ids are read-only** in the inspector (task-622); the area-environment editor
  matches the actual light/noise data shapes and surfaces world weather (task-640); and the
  inspector **says why** Generate-from-Personality is unavailable instead of showing a dead button
  (bug-514).
- **Eldenford's town paint is finished, with a bathhouse biome** (task-650).

### 📏 Known state of the suite at this commit

- **JS**: `ts_convert.py check` green — build, typecheck, lint, module:check, **533 unit tests**
  (was 522), 158/158 module headers intact.
- **Python**: **84 failed / 7,171 passed / 2 skipped** (5m15s), against a documented floor of 12.
  The gap is **environmental, not new**: **55** are the MCP cluster failing on
  `fastmcp 2.14.7` — `'FunctionTool' object is not callable` — and the tests were fixed for the
  `>= 3` API, which returns the plain function. Check the installed version before suspecting
  `mcp_server.py`. The remaining **~29** include the known `test_ownership` /
  `test_scenario_data_integrity` / `test_character_identity` / `test_promotion` set, plus
  `test_goblin_loadouts` (7). Verified pre-existing by A/B: those **fail identically on a clean
  `master` scenario**, so they are not caused by this window's work.

### 📌 Two things to know

**`data/scenarios/kraktooth_goblin_camp.json` is modified in the working tree and was
deliberately not committed.** It is the app's own **Commit Scenario** output
(`routes/helpers.py::_save_scenario` writes `world.to_scenario_dict()` over that path), so it now
holds a played session: `players_in_area` went from the authored cast to four sim characters, and
an `active_player` from testing is baked in. The authored scenario is intact at HEAD:

```
git checkout -- data/scenarios/kraktooth_goblin_camp.json
```

**The Python failure floor is 84, not 12, and 55 of that is your `fastmcp` pin.** The documented
"all 69 MCP tests pass" is true for `fastmcp >= 3`. Upgrading is the fix; nothing in the server
changed.

---

## Unreleased

### 🕸 Central gravity follows the layout

`centralGravity` is now **on in the free Graph layout and 0 in Map and Levels**, instead of 0
everywhere. It is a graph-wide field applied to every node on every solver iteration, and vis exposes
no per-mode control for it, so the value is pushed on every switch:

| Layout | `centralGravity` | why |
|---|---|---|
| 🔮 Graph | **0.05** (barnesHut 0.3) | nothing else holds a free force layout together — at 0 a cold load grew +9000 px of width per 40 s |
| 🗺️ Map | **0** | the painted lattice is the map and areas are pinned to it; a pull toward the canvas origin fights the art |
| 🌳 Levels | **0** | vis's hierarchical layout owns positions and forces physics off, so it is never read |

The rule lives in one pure function, `GraphNetwork.centralGravityFor(layout)`, and **all fourteen**
`setOptions({physics:{enabled: X}})` layout switches now go through `GraphNetwork.applyModePhysics(X)`
instead of each re-deciding `enabled` on its own. That is the point: this area already shipped four
silent physics re-enablers when Levels was added, and a per-mode solver value would have been the fifth.

**0.05 is the smallest value that holds the graph**, measured on `kraktooth_goblin_camp` (638 nodes,
all floating in the graph view): 0 runs away, 0.05 settles flat at 1209 px of width, 0.2 settles at
984 px, 0.6 crushes it to 890 px. barnesHut's 0.3 is its historical default and was **not** re-measured;
the two solvers are not on the same scale.

Note the repulsion/spring balance (`-8 / 0.10 / 120`, below) was measured for **Map** mode and is shared
with the graph view, where nothing is pinned.

**Known gap this exposed, which gravity is not the cause of.** vis applies no spring force to a node with
`physics: false`, so a simulated item/character/trigger whose parent is *excluded* from physics is held
by nothing. On `kraktooth_goblin_camp` in the graph layout, **48 of 48** content↔room pairs are in that
state (the scenario freezes 31 of 206 areas, and they are the ones with contents): those contents settle
a **median 3185 px** from their room, up to 5004 px, with the solver reporting `stabilized: true`, so it
never self-corrects. Map mode is unaffected — the grid pass places each content beside its area and
nothing travels far — which is why it only shows in the free graph layout. Not fixed here: the fix is
the rule *a content belongs in the solver only when its parent is*, which needs its own pass across
scenarios.

### 🕸 Central gravity off in Map/Levels, and items and characters are simulated again

`centralGravity` is **0** in both solvers (`graph/network-manager.js`, and the map layout in
`graph/layout-engine.js`). The solver keeps running — springs, repulsion, everything else — and only
the pull toward the origin is gone.

That one number removes the reason task-485 had for keeping a room's contents out of the vis solver.
`centralGravity` is a *global field* applied to every node on every iteration, and a child left in it
was dragged off its parent no matter how stiff its edge — so contents were pinned
(`{fixed:false, physics:false}`) and a **follow pass** re-applied a parent-relative offset every 120 ms,
with a live separation easer on top. That is the visible stutter, and it is gone:

- **Items, characters and logic triggers are in the solver** (verified live on
  `kraktooth_goblin_camp`: 29/29 items, 23/23 characters, 29/29 triggers simulated; areas stay pinned
  to the painted lattice, 204/205).
- **The follow pass is deleted** — `follow`, `_separate`, the frame pump, the 120 ms timer, the
  parent-relative offset map and `rememberDrop`, ~270 lines in `graph/relative-layout.js`. The derived
  ring is a **seed** now: `apply()` places a child once and hands it to the sim, and nothing re-places
  it. Dragging a room no longer re-derives on drop, which is what yanked contents mid-gesture.
- **The spring/repulsion balance had to be re-tuned**, because with no central pull, repulsion is the
  only thing pushing. The old forceAtlas2 numbers ran away: measured cold, **+4069 px of graph width
  per 12 s** with contents a **median 888 px** from the room holding them. Repulsion `-8`, spring
  constant `0.10`, spring length `120` (`config.js` defaults + the Settings fallbacks) put them back:
  cold, in Map mode, contents sit a **median 135 px / p90 208 px** from their room with **0**
  content pairs overlapping. Note that a *stored* `graph_gravitational_constant` /
  `graph_spring_constant` / `graph_spring_length` in the browser still wins over these defaults —
  clear them in Settings → Graph to pick the new balance up.
- **Short-range separation** (`graph/separation.js`) is a seed pass only now — it de-overlaps the
  derived ring, and no longer eases during simulation. Repulsion does that job.
- `layout_distance` / `layout_child_distance` / **Item Edge Length** still scale the ring, but they set
  the *starting* arrangement rather than a permanent leash.

Not re-measured: `barnesHut`'s repulsion/spring numbers were left as they were, so that solver's
balance with `centralGravity: 0` is unverified.

---

## Unreleased — "A Painted World You Can Walk Around In" (2026-09-30)

The 2026-09-28 release made the *simulation* honest about distance, sight and fear.
This one makes the **map** honest about the same things, and then fills it in.

The theme: a painted world had no interior language, no way to give one of your
own places a road, no climate, and no reason for a tired goblin to walk to a bed
instead of lying down in the road. Thirteen tasks, and the smallest of them added
1,383 items to the library.

A plain-language version of this release, for readers who do not know the
codebase, is in `docs/virtualWorld/Patch Notes 2026-09-30.md`.

### 🏠 A floor plan is a language now (task-568)

`data/worldpainter/biomes.json`

- **53 indoor rooms** across thirteen purposes — `hallway`, `classroom`, `taproom`,
  `storeroom`, `oratory`, `nave`, `counting_house`, `bathroom`, `latrine`,
  `hayloft`, `animal_pen`, `dungeon` — each with a surface, prose, and the tags
  that decide what it is. A plan is drawn from real ids, so a floor plan compiles
  with **no unknown-id warning**, which is the whole point.
- `stairway` is a **passable cell tagged `stair`**, and it produces the same
  `kind: "stairs"` way that a passable cell between two storeys does. The two
  spellings agree because task-562's half and this one cannot disagree, or the same
  plan would compile two different ways.
- Rooms are **exempt from the wild-country contract** for the same reason buildings
  are: nobody forages mushrooms in a latrine. Read from the `indoor` tag, so a
  modder adding a `cellar` is exempt by being one.
- The palette groups them: "— Rooms —" with a purpose sub-heading each, so a plan
  is not chosen from one flat column of 105.

### 🔀 Merging is per kind, not one switch (task-564)

`engine/world_compile.py` · `engine/biomes.py`

- `merge: always` and `merge: never` are **tags on a record**, for the same reason
  `cell_kind:` is. A hallway is a *shape*, so a ten-cell corridor is one corridor
  whatever the scope's switch says; a building cell is a **plot**, so a terrace of
  three cottages is three cottages and three doors, and the switch cannot be used
  to get either.
- The rules are resolved in one place, in the fill itself, so a half-merge — a run
  broken in the middle — is impossible.
- **Rooms follow the switch, buildings never do, corridors always do.** A
  wilderness scope with no rooms and no buildings compiles exactly as before.

### ⛰ A cliff is not a step (task-525)

`engine/world_compile.py` · `engine/weather_forecast.py`

- A grid step past **three storeys** in a `world` scope is refused, with the
  author's own sentence: *"The climb is 6 storeys of bare ground — you would need
  a path cut into it, or a way round."*
- **World scopes only.** A storey step indoors is a staircase, not a rockface, and
  this is the correction the task itself records: gating interiors would make
  task-568's vocabulary unusable, since a cellar four storeys under a hall would be
  a trap.
- **A road across the step is a built path** and carries you. Same two cells, same
  paint, and the only difference is whether the author cut a road over them. No
  `ledge` vocabulary was invented for it.
- The threshold is per scope (`record.climb.max_storey_step`), because a wilderness
  world wants three and a mountain range wants eight.

### 🚪 A place you wrote can have a way out (task-528, deferred half)

`engine/world_compile.py` · `engine/world_grid.py` · `routes/world_grid_ops.py`

- A **hand-placed area is reserved on its cell, so it was never a region, so the
  compiler never saw it and it had no way to anything.** It now mints one way per
  painted cell touching it, on the same terms as any other boundary: compass
  direction, `kind: open`, a surface, a midpoint, four connection edges.
- **Those ways are a draft the author owns.** Inspecting a placed area lists each
  seam with a ✕: the way is deleted and the decision recorded, so **Ungenerate and
  Generate will not bring it back**. A seam already taken over reads "to removed by
  you" with a ↺ to hand it back. A way that is not a seam of a placement is
  refused, with a reason.
- `world_grid.place` now **refuses a cell holding a hand-placed area** — the one
  collision where the route accepted the placement and the compiler silently minted
  no gateway — except under the explicit new `gateway` policy, where the area
  becomes the child's **doorstep**.

### 🎛 The painter grew a rail, a selection and a move (task-536)

`static/js/worldpainter/editor.js`

- Eight tools down the left, one key each (`V P E M R F A I`), active tool
  outlined, and the options that belong to the active tool under it.
- **Select**: marquee, shift-click, Ctrl+A, Escape, and a plain click on a selected
  cell deselects it. **With cells selected, Paint and Erase hit all of them in one
  request** — one undo step, not a repeated single-cell edit.
- **Move** (`M`, or the arrow keys) shifts the selected cells' contents, clamped
  at the edge, sources cleared and values written, in one batch. Clear-then-write,
  so a value moving east is not erased by its own neighbour's clear.
- The layer/value/brush controls stayed in the top row on purpose: they are options
  of four tools, not one, and moving them into the rail would mean switching tools
  to change a setting that outlives the switch.

### 🗺 A scope is at the top of the outline, and the map names its places (task-592, task-558, bug-48)

`static/js/graph/scope-tree.js` · `static/js/graph/tree-view.js` · `static/js/graph/layout-engine.js` · `templates/index.html`

- **One hierarchy, in one place.** Scope navigation was in three surfaces (a
  toolbar dropdown, a breadcrumb, and a tree at the bottom of the graph) while the
  Outline tab — the panel that already held a hierarchy — held only the bottom of
  one. The scope tree is now the **top of the Outline tab**: world, then scope,
  then the areas inside it, with an unmade scope's **🖌 Paint** jump opening that
  scope in the WorldPainter. The breadcrumb stays in the graph, because "where am
  I" is a question about the canvas.
- The clipboard copy of the outline now carries the **whole** hierarchy. Copying
  areas alone silently dropped the two levels above them.
- **The map names its places by default.** `AUTO_SPAN_PX` 1600 → 4200, so a
  20×30 painted extent derives 140px/cell — the card threshold — and the Map
  layout draws **named cards** instead of anonymous dots. The ladder still holds at
  both ends: a small zone clamps to 300 and gets roomy cards, a 200-cell world
  clamps to 25 and takes the whole map in view as dots.
- **vis-network is pinned to 9.1.9** with a comment saying to bump it deliberately
  and check the graph view when doing so.
- Edge labels wrap, and **the edge length is computed from the wrapped line
  count** — so wrapped labels do not overlap the nodes at either end. An `unlocks`
  edge carries a whole paragraph, so it is now cut to whole sentences and at most
  three lines, with the full text still on the hover tooltip.
- **Map is refused while Levels owns the layout**, visibly and programmatically,
  with `activeLayout()` as the single source of truth (bug-48's acceptance; the
  fix itself was already in the code).

### 🌡 Weather reaches a painted map (task-553, task-554, task-557)

`engine/weather_forecast.py` · `virtual_world_engine.py` · `engine/world_grid.py`

- **`base_temperature` is separate from `temperature`.** One is the world's own
  climate, the other is what the simulation is doing right now — two different
  facts, and a save carrying only the second lost the first on the next tick.
- **The outdoor curve is opt-in, and that is the compatibility guarantee.** It
  applies when an area authored a climate *or* the world has a season; a bare
  placeholder stays at a flat 21 °C, the number every existing world has always
  reported. Simulating a diurnal swing around a placeholder would invent variation
  nobody asked for.
- **The engine is the only month→season table.** Two copies in the frontend are
  gone; it ships its answer in the API and the sky widget reads it. An authored
  season beats the clock, the clock decides otherwise, and a change is narrated
  (`[Season] Winter arrives.`).
- **A `climate` paint layer**: five enums, and a region takes the majority climate
  of its cells. A climate boundary **does not split an area** — a road still does —
  and an unpainted cell is not a vote, so a world with no climate layer compiles
  byte-identically to before. World scopes only: a hall is not −8 °C because of
  paint.
- An unknown climate is a **reported typo**, not a silent temperate.

### 🛏 A tired character looks for a bed (task-566)

`engine/venues.py` · `engine/background_simulation.py`

- There was **no venue concept at all**: the only lookup the background sim had
  was by item tag, and a bed is not an item. A painted town has beds in it — the
  inn carries `sleeps`, so does a guest room — and nothing knew it.
- A venue is a set of **tags the world already has**, so a building becomes a
  venue for free by being tagged. Seven of them: `rest`, `meal`, `drink`, `bath`,
  `work`, `worship`, `care`. Matches on names as well as tags, because a room
  expresses what it is through its id.
- **Choosing among several is explicit**: fewest hops, then familiarity, then
  preference, then node name. A character with a bed next door does not cross town
  for a better one; a regular goes back to *their* inn; the tie-break means the
  same world answers the same way every turn.
- A world with **no** venues behaves exactly as before, and says nothing in the
  log — a town should be something a character *walks* to, and its absence must
  not leave anyone waiting for a building nobody painted.

### 🏗 A building can bring its own interior (task-567)

`data/worldpainter/interiors.json` · `engine/interior_gen.py`

- **30 drawn floor plans** plus a fallback, covering all 31 building types, painted
  as **cells** so the standard compiler builds the rooms. The generator mints no
  areas of its own, which is why an author edits a generated interior by editing
  paint.
- **Author edits survive a regenerate because they are detected, not locked.** The
  scope records what the generator wrote, and a cell whose value no longer matches
  is left alone — so a cell the author never touched *is* brought back in line with
  a corrected plan, and a cell they erased stays erased.
- Every building type resolves. "This building has no interior" is a worse answer
  than "this building has a plain one".

### 🧵 A config value that could not be set (bug fix)

`engine/runtime_config.py`

- The coercion ladder had no `str` arm, so a string-defaulted key fell into the
  `else: float` one. `float("exterior")` raised, so **`forecast.apply_scope` was
  unsettable** — warned about on every load, and dropped *in silence* by the API
  path the Settings menu uses. One key, one warning, one setting that did nothing.
- Both paths now share one coercion, keyed on the **default's** type rather than
  the value's, which also fixes `bool("false")` being `True` and a bool being
  silently accepted where a number is declared. A key may declare `choices`, and
  `forecast.apply_scope` does — without it, `"exteriorr"` quietly applies the
  weather to every area.

### 📚 1,383 new items, and a generator that is in the repository

`tools/item_shapes.py` · `tools/item_content_pass1..5.py` · `tools/audit_item_content.py` · `tests/test_library_content_pass.py`

- The library goes from 532 to **1,915**: vegetables, herbs, medicinals, dyeing
  plants and incense, orchard and hedgerow fruit, pulses and oilseeds, mushrooms
  (**including the two that will kill you**, `fly_agaric` and `deathcap`, tagged as
  hazards rather than food), meat, fish, dairy, breads, preserves and drink, natural
  materials, **a toolkit per trade** (mining, smith, miller, cooper, wheelwright,
  tanner, weaver, dyer, potter, glazier, plumber, thatcher, slater, sawyer),
  clothing by class, textiles, kitchenware, lighting, manors and market squares.
- The content lives in the repository and **the shipped files are held against the
  authored tables by a test**. That is not ceremony: on 2026-09-30, 545 authored
  items were silently absent from the library and the pass was still being reported
  as written, because the count came from what the generator *wrote* rather than
  what was *there*. The same comparison then found 194 items whose weight had been
  truncated to an integer by a scratch helper and then defaulted to 1.0 — an ash
  scoop weighing a stone instead of three quarters of one.
- `item_shapes.py` carries the lessons as enforced rules rather than as a note to
  self: a row's **shape** decides what it is (four transposed-column bugs in one
  session), a claim that cannot be backed is **dropped rather than half-written**,
  and a typo'd wearables id **raises** instead of skipping silently (which is how
  seven items shipped with no equip slot).

### 🧹 Also

- `tests/test_search_loot.py` asserted the drawn find was one of exactly three ids
  — the whole food pool when written. It now asserts the **property**: whatever is
  drawn is tagged `food` *and* authors a real `on_eat` that relieves Hunger
  downward. Same for the soaked forage test's hardcoded `80 - 45`.
- Six scratch screenshots taken while verifying UI work were left in the repository
  root; removed.

---
## Unreleased — "A World That Notices" (2026-09-28)

Four worktree lanes (one serial spine, three parallel arms) closed 28 tasks in
a day, and the theme is that **the simulation stopped faking three things it was
supposed to know**. Sound stopped being "within two rooms". Being seen stopped
being unrecorded. Fear stopped being impossible. Alongside that, characters
gained a real fear response, items became objects with parts and owners, and
distant parts of the world stopped costing full price to exist.

A plain-language version of this release, for readers who do not know the
codebase, is in `docs/virtualWorld/Patch Notes 2026-09-28.md`.

### 🔊 Audibility replaces hop radius (task-418)

`engine/sound.py` · `engine/awareness.py` · `engine/background_social.py`

- `radius_hops` was a proxy: "within two rooms" meant "co-present at one
  remove", which is not a distance the world has. **AwarenessChannel** is the
  replacement seam — `propagate(graph, origin_area_id, context) -> area_id ->
  strength 0..1` — with `SoundChannel` implemented and a test double proving a
  second channel needs nothing but `propagate`.
- A **locked door is a latch, not a soundproof wall**: locked and closed get the
  same barrier, so a shout crosses one locked door and exclusion comes from a
  *chain*. The arithmetic is in the test names because the arithmetic is the
  test.
- Caching keys on graph revision **and** a door fingerprint, because
  `way.properties["current_state"] = "locked"` mutates in place and never bumps
  the revision — caching on revision alone would keep a door's pre-lock
  awareness after it was locked, which is the case the channel exists for.
- `select_attended` calls `characters_by_area` once per *audible* area and never
  for an area nothing perceives, so cost is bounded by how much of the world is
  audible from the anchors rather than by population. 200 characters in one room
  attends 8 and iterates the roster dict zero times.

### 👁 Who saw whom, and what a character fears (tasks-547, 552, 484, 354)

`engine/observation_signal.py` · `engine/fear.py` · `engine/background_social.py`

- **The load-bearing fix: `engine/fear.py` was inert twice over.** A 3-day
  Kraktooth soak recorded *zero* threat actions with five humans living inside
  the goblin camp. The first conclusion — nothing can represent "that is not
  mine" — was right. The second was wrong and mattered more: `fear_sources`
  matched a co-present character on the **graph node's** `tags`, and a
  character node is created bare (`Node(id=..., type="character", name=...)`),
  so it never carries tags at all. Every shipped character puts its species in
  `player.tags`. So `fear_tags: ["goblin"]` on a human would have done nothing,
  and the field round-trips saves correctly, so it looked entirely functional.
  `character_tags()` now reads `player.tags`, the trait keys and the node.
- task-552 adds `run_fear_pass()`, called before the social pass so fear can
  pre-empt sociability. Fear produces a visible threat: a line, a trace, a
  memory, a Social cost, an `afraid` spike and a closeness cost. Four reactions
  from a draw seeded by `(character, source, tick)`, so five characters do not
  flee in lockstep.
- task-547 records who observed whom per turn and whether it was public, built
  on the bystander-reaction pass. Not serialized — it is derived per-turn state,
  which also keeps the task off the `serialization` and `player` hubs.
  Noticing and commenting are separate facts: an observer whose reaction
  resolves to "ignore" is recorded even though it emits no line.
- task-484 is only the `ends_on` half. `frightened` gates behaviour toward one
  named source, so a flag kept after that source left was a stuck flag that sat
  for its full 30-minute timer. The tuning numbers are **deliberately
  untouched** — no shipped scenario authors a single fear yet, so there is
  nothing to calibrate against.
- task-354 is the MVP the task file specifies: pack identity is a `pack:<name>`
  entry in the existing tags rather than a new `Player.pack` attribute
  (`player.py` is a hub), and packmate awareness walks the area graph rather
  than using a flat distance.

### 🧟 Undead defend themselves properly (task-490)

`engine/combat.py` · `engine/conditions.py` · `engine/undead.py`

- 5e resistance **halves** and immunity **negates**; a halved point of damage
  is nothing, and this is not the flat subtraction `aggregate_bonuses` already
  applies to equipped items. Folding undead into that would also make a sword
  do less damage to a ghost, which is what neither rule means.
- The rule is resistance to damage from **nonmagical weapons** — about the
  weapon, not the injury. The first cut keyed on damage types, so a mundane
  sword did full damage to a ghost while lightning halved no matter what struck
  with it, which is backwards. The profile carries a `NONMAGICAL_WEAPON`
  sentinel and the caller says where the hit came from, because a bare fist is
  not a nonmagical weapon.
- Ghost and zombie lists genuinely differ, and a test asserts they differ by
  exactly exhaustion — so a well-meaning edit fails instead of silently
  rewriting the rule.

### 🎒 Items with parts, owners, and counts (tasks-493, 504, 515, 517)

`engine/items/action_contract.py` · `engine/items/ownership.py` · `engine/room_perception.py`

- task-493: containment is an ordinary `in` edge; the only thing that says "this
  is a component" is that the part does not declare `take` in its `actions`.
  Every verb that *moves* an item now asks — before this only `take` read the
  action list, so a part was untakeable but still droppable, stealable and
  giveable. **Charge is the generic `uses`**: no `power` property, and a test
  asserts no library item invents one. Depletion is explicit — a used-up part
  goes `unlit`, fires `on_depleted` and **keeps its place**, because the old
  path cut the `in` edge and fished the battery out of the phone.
- task-504: one node can now stand for many. "40 berries" reads correctly and
  costs one node. Underneath it is the pooled resource node: `take 3 berries`
  reaches the thicket, spawns 3 real copies and decrements the pool, handing the
  node to the task-424 `on_depleted` teardown at zero. Kept distinct from
  `uses` — a stack of 40 berries is not one berry with 40 charges, and a tree is
  not something you can carry. `lint_library` gains `resource_pools` so a
  quantity without a yield fails at lint time.
- task-515: `owner` is a node property, not an edge. An item with no `owner` is
  nobody's in particular and behaves exactly as before. **A missing or
  incapacitated owner lifts the refusal** — a dead goblin's knife is not a
  sacred object — but an owner who is merely *elsewhere* still owns it. A
  Social/Intimidation check does **not** lift it: `steal` is already a roll, and
  a second one hidden inside `take` would make an ordinary verb unpredictable.
  So the verbs refuse plainly and `steal` is the way through, never blocked,
  just harder.
- task-517: a carried item is a **fallback** and the area is still checked first,
  deliberately — a camp with a drum must behave exactly as it did. `uses: -1`
  means no charge model; a drum at zero charges reports False rather than
  topping a character up from an empty drum for the rest of the run.

### 🌳 The world has a shape you can navigate (task-397)

`static/js/graph/scope-tree.js` · `engine/world_scopes.py` · `routes/graph.py`

- A hierarchy **over** the existing graph, not a second spatial model. A scope
  is a durable grouping and load/view boundary; its leaf areas stay normal
  `area` nodes, so every existing movement rule is unchanged.
- `scope-tree.js` nests the payload the server already sends
  (`GET /api/world/scopes?flat=1` already carries `parent_id` and `depth`) into
  a collapsible tree. No new endpoint, no per-scope request. The rules are pure
  functions (`buildTree`, `visibleRows`, `toggleCollapsed`, `rowLabel`) with 16
  unit tests, so the panel's behaviour is checked rather than eyeballed.
- An unmade scope reads **"Apartment 3B — not built"** rather than "0 areas",
  because a materialised-but-empty scope is a different fact.
- `visibleRows` carries a cycle guard: a card renders at most once, because
  hanging the panel is the one failure an author cannot work around.

### 🏠 The apartment recipe (task-398)

`engine/generation.py` · `engine/library_nodes.py` · `routes/library_ops.py`

- The contract in `engine/generation.py` was implemented but nothing consumed
  it. This adds the first real recipe: an apartment of three areas with a front
  door in from a hallway, and tag-aware furniture.
- **Same seed gives a byte-identical patch**; a second apply is refused and
  leaves the graph untouched; a manual edit to a generated item survives a
  refused second generate; every generated node carries provenance.
- `engine/library_nodes.py` exists because `materialize_library_item` takes a
  Flask app and mints ids from `time.time()`. Fine for a player picking
  something up, unusable for a generator, which must be able to name the node it
  wants and produce the same patch for the same seed. Child and trigger ids are
  derived from the parent id (`<id>_content_0`, `trigger_<id>_<type>_0`).
- The recipe generates **no resident** — the task forbids silently
  manufacturing an LLM character, so it takes no resident argument at all.

### 🏔 Chunk persistence begins (task-401 → 581, 582, 583, 584)

task-401 became an umbrella over four ordered sub-tasks. Nothing is built yet;
this is the split, recorded so each piece is independently reviewable. 581
(stable area ids) is worth landing on its own merits: it removes a real
correctness hazard — a duplicate area name splitting a character's location —
whether or not chunking ever happens.

### 🔧 The goblin camp, cleaned up (tasks-408, 550, 565, 522)

`data/scenarios/kraktooth_goblin_camp.json` · `data/worldpainter/` · `routes/world_grid_ops.py`

- task-408: 46 authored character nodes collapsed to 23 via `character_*`
  aliases, 422 way endpoints canonicalised to area ids, `high_metabolism`
  attached to the 10 goblins, 21 camp areas plus Eldenford and its inhabitants
  tagged with `held_by`/`faction`. **Folder-based authoring** compiles to a
  single JSON, because asking an LLM to emit one huge scenario JSON kept
  producing broken output.
- task-550: faction and ownership are tags, so the camp's single water source
  and waste disposal are a claimed resource and using someone else's is an
  event. A camp's water is the camp's.
- task-565: the scope's id was still `deep_woods_2` because ids are minted once
  as a slug of the name and the rename route only touches the display name. The
  project rule is that **ids change and display names do not**.
- task-522: a plain close action must **not** close an outdoor way — you cannot
  close a road into a forest by hand. Blocking is done by an item or trigger
  (fallen tree, barricade, rockslide). Selection is a deterministic FNV-1a
  ordering, connectivity is re-checked per candidate, and each blocked way gets
  `blocked_by`, `blocked_description`, `refusal_message` and `prevent_close`.

### ⚡ The tick loop stopped guessing who is together (task-416)

`engine/tick_manager.py`

- Co-presence was reconstructed inline wherever needed, scanning the whole
  roster once per character — quadratic in population. It is now a reverse
  index (area → character) built once per turn and kept live, so a lookup
  returns exactly what the old scan would have, in the same roster order.
- The standing-item sweep is one area-major pass, sorted by area id then node
  id, so it is a pure function of the graph. That fixed two **pre-existing
  determinism bugs**: the old passes ran in insertion order, then trigger-index
  set order. Flat co-present read at 160 characters: 45.0 → 32.5 µs.
- The acting queue is deliberately untouched: area grouping decides the order
  of scoped evaluation only, never who acts.

### 🕯 Fog, sightlines, and parts of the world that are not loaded (tasks-499, 498, 421, 411, 500)

`engine/fog.py` · `engine/beyond_visibility.py` · `engine/barriers.py` · `engine/zones.py`

- task-499: an area/scope-level known set per character. Unknown cells are fog
  on the map; walking, examining or finding a map item reveals them.
- task-498: sightlines chain along a run of open/see-through ways, broken by a
  floor step or a turn.
- task-421: `engine/barriers.py` gives light the same way-state ladder sound
  already had, with separate cost and transmission tables.
- task-500: zones are the spatial key for the fidelity tiers, so a distant zone
  exists as a scope record and materialises its areas on approach. The loader
  refuses occupied, baked, hand-authored and orphaned-parent zones and recovers
  its seed.
- task-411: an attention cap with deterministic eviction and threshold
  hysteresis, with save/load state.

### 🧟 A ghost was free to gawk (bug fix)

`engine/background_social.py`

`is_undead_ghost(player_name: str)` looks a character up **by name**. A call site
was handing it the `Player` **object**, so the dict lookup could never match and
the guard has never once fired. A ghost was therefore free to gawk at, and
comment on, whatever was happening. The mismatch between the two sibling guards
is what made it visible: one passed `npc.name` and was always correct. One of the
two had to be wrong, and the signature said which.

### Two bug reports closed as "was not ours" (bug-28, bug-29)

`tests/test_speech_verbatim.py` · `tools/unit/test_conversation_context.js`

Neither has a live repro, so **this changes no behaviour** — it is the
investigation plus regression guards.

- bug-28: the corruption was real, the transform is gone. Across all three
  exports it is exactly apostrophe-to-space plus a full lowercase; em dashes,
  interrobangs, ellipses and `*burp*` all survived. The "letter scrambling" in
  the report was a *second, separate* thing and not ours — the event log line
  already reads `Pleas edont try to be cnormal` **stored mangled before any
  prompt was built**, so it is the NPC agent's own generated line, upstream of
  the engine entirely.
- bug-29: premise disproven on the artifact. The two cited lines are different
  utterances by the same speaker, not one utterance twice. The predicted
  alternative — speaker-label instability — is also unreachable today.
  Recorded rather than patched, since patching unreachable code on a disproven
  bug would be inventing a fix.

### 🧪 The test baseline was fiction, and 55 of 60 failures were one bug

`tests/test_mcp_*.py` · `AGENTS.md`

`mcp_server.py` was never broken — it registers 85 tools cleanly. **FastMCP ≥ 3
returns the plain function from `@mcp.tool()`**, not a wrapper exposing `.fn`,
and 62 test call sites still used `.fn()`. All 69 MCP tests now pass.

This matters beyond the count. The old documented baseline was "~60 failed", and
**55 of those 60 were the MCP tests**, which made the "compare to baseline"
merge gate nearly blind — a lane could introduce 50 genuine regressions and
still be "at baseline". The real baseline is now **5 failed / 4274 passed**, and
`AGENTS.md` names each of the five.

### 🛠 Working in parallel without a merge bonfire

`.kilo/lanes/` · `docs/design/worktree-parallelisation-plan.md` · `docs/design/typescript-migration-plan.md`

- All 272 actionable dev tasks were mapped to the files they touch, then cut
  into **one serial spine and three parallel arms**. Eight files are the merge
  magnets (`engine/tick_manager.py` alone is claimed by 13 queued and 12 review
  tasks); one lane owns them. `templates/index.html` and `tools/unit/run.cjs` are
  shared append-only, not hubs. Past four lanes the merge debt exceeds the gain
  (K=4: 385 colliding pairs; K=8: 442).
- A size-ordered TypeScript migration plan: 151 files, 64,620 lines, six waves.
  `window.Lit` gates 46% of the corpus and is undeclared, so it is a W0
  prerequisite; and only 15 of 151 files convert without touching
  `static/js/types/globals.d.ts`, making it a hub in the same sense.
- `bug-54` was used twice. The test-isolation bug is now `bug-55` and
  `tools/tasks.py validate` exits 0 for the first time in a while.

---

## Unreleased — "A Town You Can Walk Into" (2026-09-27)

A painted map stopped being a picture of a world and became a place you can
stand in. The WorldPainter session that began with "every painted cell is a
place" finished the job in the other direction: **a cell can now be a name, a
building, a wall, or a door** — and a building is something you go *into*. Along
the way the compiler's worst lie was found and cut out: `floor` was a *material*
where it should have been a *storey index*, which had been quietly merging a
classroom with the one above it. A separate pass gave the weather a voice, and in
doing so discovered that **the moon has never been narrated, in any world, ever**.

Commits: `362bb24` (the town), `4467da8` (storeys), `6b8598c` (weather),
`b885878` (camp state + filed follow-ups).

### 🏙 You go *into* a building, you do not walk onto it (task-563)

`engine/world_compile.py` · `engine/biomes.py` · `engine/movement.py` ·
`data/worldpainter/biomes.json`

- A building cell is entered with **`in`** from every *cardinal* side that already
  has a way, so standing in the street you type `in` instead of stepping sideways
  onto the doorstep first. Cardinal, because a door is on a wall and a diagonal
  neighbour is a corner of the plot; "already has a way" is read from the pairs the
  compiler actually connected, so a walled side gets no door and a side reached
  *through* a painted doorway does.
- **With an interior** the way leads to it, and is one-way: inside, `out` has to
  keep meaning one thing, so you come out onto the doorstep and the adjacent
  building is one turn from there — which is also what makes `dash_to_area`'s
  chained second hop work.
- **With no interior** the way is a `closed` door carrying a `refusal_message`
  drawn from the building's category: *"The smithy's door is shut and the bench
  is cold."* A watch house is barred, an inn is shut. The refusal holds until the
  way is `open`, which is what a knock, a key, or an author painting the interior
  does — so a building that owes an interior says so instead of being a hole.
- `refusal_message` is a **general way property** the movement system honours,
  checked *before* the state machine (a `closed` way otherwise auto-opens on
  approach, which would make the refusal cosmetic). A way without it keeps every
  existing behaviour, including the auto-open.
- **One-way in both cases**, for a sharper reason found by walking it: the street
  already has a compass way onto the plot, so a way *back* was a second connection
  for the same pair, and two ways both answering to `out` on the plot meant
  walking in the street door and typing "out" got you shut out by the alley door
  you had not used.
- The painter knows all of this before anything is generated: the vocabulary
  payload carries each building's refusal and the cell inspector shows
  `in → The Inn` or `in → The inn's door is shut.` — from the same
  `world_compile.building_refusal` the compiler uses, so the preview cannot drift
  from the world.

### 🧱 A cell can be something that is *not* a place (task-562)

`engine/biomes.py` · `data/worldpainter/biomes.json` · the painter's palette

- `wall` and `void` block, `window` sees through without passing, `door` is a
  threshold — and the *vocabulary* decides, via `biomes.cell_kind`, so adding a
  `hedge` or a `turnstile` later needs no code.
- **A wall works by occupying a cell**: the two rooms either side of it are no
  longer adjacent, so no way is minted. A door occupies the same cell, so the
  route it stands for is built explicitly, joining the two places on *opposite*
  sides. A passable cell between two **storeys** is a stairwell whatever it was
  painted as, and every way now carries `kind` and `floor_step` so task-525's gate
  and task-563's `in` have a number to read instead of re-deriving one.
- An unknown biome id compiles to a place with a **warning** instead of silently
  becoming a barren area. A typo is invisible in node counts, so it is named.

### 🏠 31 kinds of building, and a name you wrote (task-561, task-560)

`data/worldpainter/biomes.json` · `engine/world_compile.py` · the painter

- Buildings as **biomes**, not features — they used to be features, which made a
  house compile as a road. 31 types across 9 categories, each tagged with a
  category and its purposes (`sleeps`, `food`, `craft`, `worship`, …), which is
  the hook task-566 needs to let the simulation seek a place by function.
- A cell can be **named** by the author, on a `names` map beside the paint layers
  because a name is metadata and not paint (the eraser must not wipe it). The
  compiler prefers the authored name, with a duplicate-inside-a-scope fallback so
  no area ever offers two exits with one name.

### 🏢 A storey is a number, not a floor (4467da8)

`engine/world_compile.py` · `engine/world_grid.py` · `graph.py` · 24 files

The one correction that made the rest possible. `floor` had been a **material** —
dirt, stone, wood — on a layer the graph compared for walking, while a separate
`elevation` layer held the height. So `floor` is now a whole-number **storey
index**: 0 ground, 1 up, -1 down, unbounded (three stacked rooms, a lake bottom
at -2, an 80-storey tower, -900 in a hole to hell). What you stand on is a
different fact and lives on `properties.surface`. Legacy files migrate on load,
the recipe id moved to `grid.v2`, and every consumer that formatted a floor as a
material — the inspector, the map, the world export — now reads a number.

### 🗺 The map learned to size itself (task-526)

`static/js/graph/layout-engine.js` · `network-manager.js` · `graph-background.js`

A compiled area draws as a card whose width is its **name** plus padding, and the
name does not shrink with the pitch the way the padding does — so one global
pitch could not serve both a 6×8 camp and a 200×133 world. The pitch is now
**derived from the painted extent** (a 20×9 zone gets 80px/cell, a 200×133 world
30px) with the stepper as a visible override and an `A` button to hand it back,
and below 140px/cell an area draws as a cell-sized dot with no name, through the
existing label LOD rather than a second mechanism. A layer's rect is in px, so a
pitch change makes every picture stale: the whole-world view re-derives every
mounted reference from its own scope's grid and reframes.

### 🌧 The weather has a voice, and the moon is back (task-559)

`engine/area_description.py` · `engine/weather_forecast.py` · `routes/action_handlers.py`

`env["weather"]` had exactly two readers in the whole backend: the light
multiplier and the DC of `guess time`. Nothing ever said it was raining. Now
there is one sentence per state in `WEATHER_STATES` (so a forecast can never
write a state with no sentence), one per wind magnitude, and a time-of-day line
for exteriors — all gated on an open sky, because a storm is not something you
hear through a stone wall.

- **The moon has never been narrated, in any world, ever.** `get_area_description`
  read a local `node` on the first line of the moon block, but Python resolved
  `node` as a local because it is assigned *later* in the same method — so the
  line raised `UnboundLocalError` and the bare `except Exception: pass`
  underneath swallowed it. Proven by AST and by a repro that produced no moon
  text at 22:00 with a full moon. The except is now narrowed to the provider
  errors it was written for, so the next real failure is not invisible too.
- Wind was one phenomenon under two keys: `noise_prose` read `noise`, the forecast
  wrote `wind`, so an *authored* `noise: "windy"` narrated wind and a forecast
  gale did not.
- Two divergent weather vocabularies are now one. `WEATHER_ALIASES` +
  `normalize_weather()` live in `weather_forecast.py`, the DC table moved next to
  the vocabulary, and the private list in the action handler — which knew
  `sunny`/`overcast`, neither of which the forecast can write — is deleted.

### 📋 Filed for next

- **task-568 an indoor vocabulary.** A building you can enter is somewhere you can
  be *in*, and there is still nothing to paint it with: `classroom`, `hallway`,
  `stairway`, `kitchen` are unknown ids, so a real floor plan compiles to bare
  places plus a warning.
- **task-564 per-kind merge rules**, and the two-`in`-exits ambiguity on a street
  that faces two buildings.
- **task-567** a building's interior generated from its type, then edited.
  **task-566** the simulation seeking a place by function. **task-565** the goblin
  camp's stale `deep_woods_2` id. **task-557** a coarse climate layer.
  **task-525** the storey-delta traversal gate — the data exists, the gate does not.
- **bug-54** compiled areas carry no `outdoor`/`exterior` tag, so weather is
  invisible to them at the engine level. **task-556** the state snow needs,
  **task-553/554/555** base temperature, season, and wind with a direction.

---

## Unreleased — "The Camp Breathes" (2026-09-24)

One theme runs through the whole day: **characters stop being generic and start
being themselves** — at what they are good at, in what they can find, what they
will do unobserved, and whether the camp can actually feed them for a week. Skills
became a real per-character surface (roles, proficiency, opt-in growth), search
gained depth and breadth, the background tier gained an *actor-driven* agenda, and
the plants that are supposed to sustain a camp were finally proven to grow — on the
spawned path the soak had never exercised. The morning's commits (399/406/497/501/
503, bug-40/42) are part of the same push; this entry covers the full day.

### 🎭 A character is good at what they *are* (task-476)
`data/library/roles.json` · `engine/roles.py` · `engine/checks.py`. Roles are
**namespaced tags** (`role:hunter`, the `faction:guard` shape), so a role is
authored and saved like any other tag and needs no new field, no migration.

- Thirteen profiles (hunter, trapper, guard, thief, healer, scholar, smith, cook,
  farmer, ...) map to real skills and merge into the one check pipeline as a `role`
  source, so `skill_check`, `resolve` and `opposed` all see them with no second path.
- **Only `role:`-prefixed tags resolve**; a bare `cook`/`farmer` tag stays inert, so
  every existing character's checks are unchanged until a data pass authors roles.
- Proof: same roll and stats, a `role:trapper` out-forages a roleless child on
  Survival and a `role:guard` beats a `role:cook` on Perception.

### 🔎 Search grew a spine and four more eyes (task-478, task-483)
`engine/foraging.py` · `data/library/foraging.json`. Noticing and searching are now
two steps, and the skill list has content beyond Survival/Perception/History/Religion.

- **Notice-then-search**: `notice()` (Perception) spots that there is something worth
  looking for and remembers it on the area; `search_hidden()` then lets the search
  skill find it. A failed notice means the character walks past — even on a great roll
  there is no find they never saw.
- **Nature, Investigation, Arcana and Medicine** tables and area bonuses (forest →
  Nature/Medicine, ruin → Investigation/Arcana, temple → Arcana). **No new area tags**,
  so the existing "can this area yield" gate is unchanged.
- **The tables are data now** (`foraging.json`, seeded exactly from the old constants),
  with a per-area `forage_tables` override that adds local finds and makes an otherwise
  barren area searchable, plus `findable_here()`/`findable_hint()` for the HUD.
- `find <skill>` is discoverable: the autocomplete now suggests the search skills.

### 📈 Growth, proficiency, and set-in-stone stats (task-480)
`engine/skill_progress.py` · `data/library/skill_packs.json` · `player.py` ·
`engine/checks.py` · `engine/effect_handlers/vitals.py`.

- **Proficiency** is a separate term (`player.proficiency`, default 0) merged as its
  own modifier source — the sheet can express trained value *and* proficiency apart.
  At 0 it is exactly the pre-task-480 result.
- **Use-based growth is opt-in**: `record_use` counts *successful* uses and raises a
  skill at the threshold (reset on raise, capped, failures never teach), and it only
  runs when a scenario sets `skill_growth`. Existing saves and soaks do not move.
- **Setting skill packs** grant starting skills (`apply_pack`, raise-only/idempotent),
  and the new `adjust_stat` effect lets play train or drain an ability (clamped 1–30,
  reusing the character's own key casing).

### 🥷 Background characters now want things (task-468)
`engine/background_social.py` · `engine/background_simulation.py`. The social pass had
opinions but no agenda; now an unobserved character can *act*.

- **Theft agenda** (`run_theft_pass`): a `thief`/`kleptomaniac`/`pickpocket` trait or tag
  — or a starving character after food — attempts `steal_item` on a co-located target
  through the **real** Sleight of Hand vs Perception path, cooldown- and daily-capped.
  The failed attempt writes the same "notices" line the interrupt evaluator reads.
- **Approach variety**: approaching the player is no longer always `chat`; the
  relationship band picks the kind (confide at friend, flirt at close friend), never
  hostile and never a no-op.

### 🌿 The plants actually grow — including the path the soak never touched (task-410)
`engine/effects.py` · `tests/test_renewable_plants.py`. The camp's bushes live in the
scenario, so the soak never exercised the **library-hydrate** path — which had two
real bugs:

- `_hydrate_item` dropped the library `parameters` dict, so a spawned plant came up
  with no growth gauge at all (the same class of bug fixed earlier for the other
  placement path).
- `_materialize_spawn_triggers` did not carry the legacy singular trigger shape
  (`condition` + `effect_type`/`effect_params`), so a hydrated plant's growth trigger
  had no conditions and no effects — it could never grow. It now carries the shape
  **and** stops emitting an empty `conditions: {}` that masked the singular fallback
  and made the trigger fire unconditionally.

A hydrated bush now grows by game-minute, matures into produce, resets, respects the
10-produce cap, and is never food-tagged (so it cannot be eaten and deleted).

### 🍞 One consumption path, background or not (task-424, change 1 of 3)
`engine/background_simulation.py`. When an item authors its own `on_eat`/`on_drink`,
the background tier now runs the **player** consume path with the character swapped
into the active slot, so the trigger fires and the item depletes its own way. The
hardcoded count/uses/remove stays only as a logged fallback for silent items —
so today's camp, whose five consumables author no triggers, is deliberately unchanged.

### 🧠 Background life got a memory bridge (task-399, committed this morning)
`engine/promotion.py` · `player.py` · `engine/structures.py` · `engine/tick_manager.py`
· `routes/world_scopes*.py`. Characters can be offloaded to a deterministic tier with
**zero LLM calls**, then promoted back to one bounded `source:"background"` memory
summarizing the span — idempotently. Transitions are *queued* and applied as one batch
at tick start (no character resolves under two modes), and `POST
/api/world/scopes/<id>/observe` promotes a scope's residents.

### 🧭 The trigger editor stopped lying (task-501, task-503, committed this morning)
`static/js/shared/trigger-graph.js` · `static/js/inspector/behaviors-view.js`. The
editor used to silently flatten OR/NOT conditions, drop NO-branch effects, and discard
NO-branch behavior actions on compile. It now preserves what it draws and **refuses to
save a lossy compile** with a clear error instead of quietly changing the author's
intent.

### 🌍 WorldPainter got a biome taxonomy (task-497, committed this morning)
`data/worldpainter/biomes.json` · `engine/biomes.py`. Sixteen biomes and nine features
with resource and hostile distribution, reusing the existing foraging tag vocabulary so
a painted area forages with machinery that already exists — data-only, no engine change
to add a biome.

### 💾 Save dialog: no literal HTML, no accidental autosave loss (bug-40, bug-42)
`static/js/ui/saveload-view.js` · `routes/saveload.py`. Save-list badges render as
elements; "Delete All" is a single confirm backed by `POST /api/save-games/delete-all`
and keeps the autosave slot unless explicitly told otherwise.

### 🧪 Standing items are guarded by tests (task-406, committed this morning)
`tests/test_trigger_system.py`. The event-index dispatch and the standing-item `on_tick`
path (what a plant relies on) now have coverage: it fires exactly once, never
double-fires a carried or lit item, and survives add/remove/load/clear.

### 📝 Design note: the turn is the unit of agency (task-409)
Recorded on the task: the old "96 actions/day, one decision per 10 minutes" action-credit
model is retired. A character takes **one action per turn**, a turn is a timeframe
(default 1 minute, ~1440/day), and actions carry authored `TASK_MINUTES` durations that
span turns. The fix for schedule starvation is therefore **bundled chore tasks modelled
on crafting recipes** — a decision, not the old budget arithmetic.



A skip is not a special mode — it is the controller swap `Simulation Model` already
implied. This pass makes it real: **a human can hand their character to a
deterministic policy for a span and walk away**, the background tier gets a genuine
action model (skill-checked finding, risky ground, fear read from tags), and the
dice get one home. The graph, meanwhile, stopped trusting the `x`/`y` it was handed
and started deriving position from the relations that were always the truth.

### ⏳ A timeskip is a controller swap, not a mode
`engine/timeskip.py` · `routes/timeskip_ops.py` · `static/js/ui/timeskip.js`. Declare
an intent plus a span; the world advances **minute by minute** with the character's
decisions supplied by a policy, and control returns the moment something relevant
happens to them.

- **Five intents** — `idle`, `leisure`, `search`, `explore`, `travel` — and a span in
  minutes, hours, turns, a derived travel route, or "until dawn/dusk/noon". Dialog
  presets 30m/1h/2h/4h/8h + custom; entry also from the command palette.
- **The frame dial is never changed by a skip.** A skip advances whole turns of the
  scenario's `time_per_tick_minutes`, so the clock (ticks × dial) stays consistent:
  a 1-minute world resolves interrupts every minute, a 5-minute world every 5.
- **No stasis, no protection.** Vitals decay and the environment applies — a wait in
  a forest with no food or water can kill. The skip removes *decisions*, not
  *consequences*.
- **Zero LLM calls inside a skip**; exactly one bounded resume memory is written, and
  the skip summary reports notable world events, not just the character's own trace.
- **Interleaving mutations are refused** (`409`) while a skip runs, and the result
  carries `vitals_before`/`vitals_after`, `clock_after` and the interrupt that ended it.

### ⏭ Soak orders: one per character, on that player's turn
`engine/soak.py` + `tick_turn`. In a shared world a timeskip is **not** a table-wide
consensus and **not** a blocking server jump — it is an order attached to the
character who declared it, declared on their turn and run by the normal turn loop
exactly like an agent or a distant NPC.

- **Genuinely background while it runs:** `simulation_mode` becomes `background`, the
  soak tier drives the character, and the turn queue treats it as not attended; the
  previous mode is restored when the order ends.
- **Promotion hands control back early** on something feared, a hostile condition, a
  vital in its danger band, or a discovery matching the order's `watch_tags`. It uses
  **absolute** checks rather than crossings, because an order runs for many turns. A
  search that turns up its target is a discovery exactly like in a blocking skip — the
  policy result used to be dropped here, so a character searched straight past the
  thing they were looking for.
- **Re-queue follows the normal order rule** when the character is promoted back into
  a table: sequential→alphabetic, random→shuffled, initiative→a fresh d20+DEX keeping
  the current slot, simultaneous→the next unused slot.
- **Cancel from the roster row** (`DELETE /api/world/soak?character=<name>`; defaults
  to the active character, 404 on an unknown name, a clean no-op when nothing is
  declared). **Status lives in the initiative/roster list** (`⏩ intent 42m` + ✕),
  never in the composer — the composer is where you *declare*, not where you *watch*.
- **No active character ⇒ a world advance** (`mode: "world"`): there is nobody to
  attach an order to, so everyone soaks and the world jumps in one request.
- Requests are capped at **1,440 minutes** — a synchronous request must not hold a
  worker for a game week; the engine itself supports up to a week
  (`MAX_MINUTES = 10080`).
- `tests/test_soak_orders.py` (16) and `tests/test_soak_chain.py` (5 — background pass
  → policy → time spent → promotion → resume memory → `soak_end`) drive the real
  `world.tick_turn()`, covering fear mid-span, a search finding its target, span
  accounting and death inside a soak.

### 🎲 One home for the dice (task-472)
`engine/checks.py` is the single resolution path: advantage and disadvantage cancel,
degrees of success, criticals, auto-fail, `DCS`/`dc_band` and `opposed`.
`SkillSystem.skill_check`/`saving_throw` are thin adapters that preserve their old
tuple+message return, so nothing downstream had to change.

- **Conditions feed the roll.** A condition definition (or instance) may carry
  `check_advantage` / `check_disadvantage` / `auto_fail_checks` naming skills,
  abilities, or the literal `"attack"`/`"*"` (`engine/checks.py::condition_flags`).
  `restrained` now ships `check_disadvantage: ["attack"]` — it already had a flat
  `attack_mod −2`, but a ties-up is *disadvantage*, not a bonus that stacks with a
  bonus. All 38 library files gained the two empty lists, so a Definition-Schema edit
  shows the fields instead of the code silently defaulting.

### 🧑🎓 The whole skill sheet lives on the base sheet (task-474)
The base sheet is **18 skills** — the six adventuring basics (Athletics, Acrobatics,
Stealth, Perception, Survival, Persuasion) start at **1**, the other twelve at **0**.
A save or library restore now **merges over** the defaults instead of replacing them,
so a character authored before a skill existed still gets it.

### 🍓 Finding things is a skill check now (tasks 469–471)
- **Foraging is skill-checked in the soak tier**, and the `forage` mechanics tag
  curates what a search can turn up in the wilds; `_pick_item` prefers forage-tagged
  candidates.
- **Searches can turn up junk, and the skill margin decides how useful it is** —
  finding *something* is not the same as finding the right thing.
- **Fear is a tag, not a global hostile flag.** `engine/fear.py` + per-character
  `fear_tags` make what frightens a character data, driving `frightened` and the
  involuntary/interrupt passes. `BackgroundSimulation` can also approach the player,
  with relevance-gated interrupts so an unrelated distant event no longer moves the
  human.

### 🥾 Risky ground rolls; routine ground just takes 10 (task-475)
`engine/traversal.py` turns "walk over there" into a real action for the soak tier.
Routine ground takes 10 and never rolls; **risky ground** rolls the relevant skill
against `HAZARD_DC 12`, and a failure spends the turn and lands the
`HAZARD_CONDITION`. A refusal is remembered on the character (`traversal_avoid`) and
one immediate detour is attempted rather than looping; `traversal.hop` never raises.

- Wired through `BackgroundSimulation._hop` / `_travel_toward` / `_travel_to_area`
  and `timeskip._move`, with `_target_step(avoid=…)`.
- **Gaps recorded:** `engine/npc_behaviors.py` still calls `movement.move_to_area`
  directly; there is no `swim`/`force` verb yet; and the actions in `SOAK_ACTIONS`
  whose systems do not exist yet (calm/ride 476, treat/diagnose/identify_plant 478,
  read_mood/investigate 468) wait on those tasks.

### 🕸 Graph positions are derived, not remembered (task-485)
`static/js/graph/relative-layout.js`. A saved snapshot of every node's `x`/`y` is
stale the moment anything is created or deleted, and it never explained *why* a node
sat where it did. Layout is now **derived from the relations** — parent priority
carrying > equipped > at > in > triggers — and re-derived, not restored.

- **A room's contents orbit it** instead of stacking on its label; the ring grows with
  the crowd, and a mixed-`in` group's direction is resolved by depth from the area
  roots. Ways sit at the midpoint of their two rooms.
- **Explicit distances are exact** (labels may overlap); the comfort floor/cap and
  crowd-spacing growth apply only to *inherited* distances.
- **Physics settings finally reach the contents.** vis-network's `centralGravity` is a
  *global field* applied to every node on every solver iteration, and the edge spring
  cannot outvote it — measured, a large change to `springConstant`+`centralGravity`
  moved a settled layout by **2 px of ~5900**. Contents therefore stay out of the
  global solver (`{fixed:false, physics:false}`) and hold a parent-relative offset the
  follow pass re-applies. **Item Edge Length** now scales the orbit; the other physics
  sliders govern areas and ways.
- **The follow pass is incremental and budgeted** (only moved parents; `FOLLOW_MS 120`,
  `FOLLOW_BUDGET 500`, and it sleeps when physics is off) after the original per-frame
  graph sweep proved too expensive.

### 🪜 A levels layout, and per-node physics (task-485)
- **🌳 Levels** mode (toolbar `#btn-layout-mode`, config `graph_layout_mode`) hands the
  graph to vis's hierarchical solver for an outline-like view, switching back to free
  physics cleanly. Making that switch honest meant killing four silent physics
  re-enablers (`applyCardinalLayout`, `graph-background._applyLockState`, the persisted
  `graph.physics_enabled` load/switch paths, `_clearOverlay`).
- **Per-node control** — `layout_static`, `layout_distance`, `layout_child_distance`,
  `layout_child_spacing`, `layout_min_radius`, `layout_max_radius`, precedence
  child → parent → global — editable from the inspector's **Graph Physics** section.
  Verified live: inherited 146–147 px; a parent at 80/40 gives 79–81; at 320 gives
  319–320; one child pinned at 90 sits at 90.
- **A frozen node is honoured in every layout** (bug-45), and **cardinal
  auto-placement only runs in map mode** — in graph/manual view, hand-placed nodes stay
  where they were put.

### 🐛 Bugs killed
- **bug-44** (filed): 21 authored container contents in the boot template carry an
  **inverted** `in` edge (`item_Backpack → item_Ink`, `grandfather_clock →
  brass_key`, `medicine_cabinet → antiseptic`), so the engine cannot see them.
  Canonical direction is contained → container; this is repaired as data, not by
  papering over the reader.
- **bug-45** (fixed): a frozen node (`central_gravity_enabled: false`) was moved anyway
  by the cardinal layout, and the cardinal layout ran in graph mode where it should not.
- **bug-46** (fixed): the client event stream persisted in IndexedDB was restored into
  whatever scenario loaded next, so exports mixed two worlds. It is now stamped with a
  world key (`_scenario_name` → `scenario_source` → `body.dataset.scenarioName`) and
  dropped when the key differs.

### 🗃 Identity collapse, simultaneous turns, and the library as truth
- **Character identity collapse + the fourth turn mode** (`53420e6`): `simultaneous`
  resolves against a snapshot and commits together, on the same dial as
  sequential/random/initiative.
- **`6fb0887`**: the condition JSON library is the single source of truth; the
  hardcoded `CONDITION_DEFINITIONS` dict is only the fallback, so a truncated or
  corrupt file can never wipe definitions.
- **Content refresh:** `world_template.json` was re-saved by the new engine — full
  18-skill sheets, `soak: null`, `fear_tags`, derived node positions,
  `central_gravity_enabled`, the Living Room's per-node layout tweaks, and **both
  `graph_background` map layers** ("frosen wilds", "valerious-house-interior"), whose
  images are committed alongside it.

### 📋 Filed for next
The `task-475` gaps above · `task-482` long spans, leisure vendors, the explore
frontier · `task-483` search affordances, hints, per-area forage tables · `task-484`
`frightened` tuning under per-character fear tags.

---

## Unreleased — "One Copy of Every Truth" (2026-09-20 → 09-21)

A saved world was carrying the same facts three times over, the natural-language
editor was quietly discarding failed edits while burning its entire context, and
a locked door was treated as more soundproof than a closed one. This pass makes
the graph the single source of truth, gives the NL editor an honest ledger, and
fixes the two bugs that stopped a saved background map from ever coming back.

### 🗃 Scenario files are graph-only — 28% smaller
A saved scenario held `areas`, `rooms` **and** `graph.nodes`, all describing the
same world. `rooms` was a byte-identical duplicate of `areas` (the same dict
assigned to two keys), and every `areas` entry carried a verbatim copy of its
node's `properties`, plus `ambient_light`/`light_description` recomputed each tick
and an `items` list that was always empty. Every remaining field was audited:
**nothing in `areas` was unique** — `name` is `node.name`, and
`description`/`environment`/`floor` are `node.properties`.

- **`to_scenario_dict()` no longer writes** `areas`, `rooms`, `ways` or
  `item_registry`. The goblin camp drops **455,567 → 322,407 bytes (−28%, ~131 KB)**
  with identical reload behaviour (31 areas, 23 players, descriptions intact).
- **…but the live payload keeps them.** ~20 frontend call sites read
  `worldState.areas` (agent-engine, agent-lens, inspector, item-library/placement,
  graph/layout-engine), so the projection stays in `/api/state` and only the *file*
  is stripped. `tests/test_scenario_graph_only.py` locks both directions so a
  future tidy-up cannot collapse the wrong one.
- **The Changes panel now reads areas from the graph**, exactly as it already did
  for items and ways — areas had simply never been migrated. Its fingerprint also
  drops `exits`, which every written payload strips: that made it a constant on
  the live side and a false "changed" for any older file still carrying a copy.
- **`_scenario_name` round-trips again.** Every save dropped it, so a restored file
  was "unnamed" — and because the name is what keys the local background-map cache,
  that single omission made a saved map unloadable. An empty name is now omitted
  rather than written as `""`, which `data.get(...) or ...` reads as "unnamed" and
  would let it outrank a real name.

### 🧠 The NL editor needed an honest ledger
- **A partially-failed Apply threw away the failures.** `/api/graph/batch` answers
  `207 partial` with `applied[]`/`errors[]`; the editor showed the errors and then
  cleared *every* op it had sent, so edits that never applied vanished with no way
  to retry. Only ops the server reports as applied are cleared now, and the toast
  says how many are still staged. A regression harness drives the real
  `StagingBuffer` through success / partial / total-failure / selective-apply and
  both replay paths (23 checks).
- **Context pruning had disabled itself.** `prune()` reset the counters it then
  guarded on, so the next call handed back the *entire* transcript: at iteration 90
  the model received **179 messages** while the tracker claimed ~1,004 tokens, and
  `overLimit` read false forever. Metadata is now keyed by message identity instead
  of array position, the window is measured from the array actually being sent, and
  critical retention is bounded newest-first. The same loop now sends **29**.
- **The `[Summary: N earlier turns omitted]` marker never fired** — it was gated on
  index 0 being dropped, but index 0 is the system prompt and always kept, so
  dropped turns disappeared with no signal to the model.
- **Errors were invisible.** `turn:end` fires from `finally` and reset the badge to
  "Ready" immediately after the error handler set "Error", and the message was
  never rendered in the chat. Both fixed, plus the hardcoded `round x/10` label
  that the 100-round cap had made a lie.
- **The ghost preview never panned for spawns** — the spotlight looked up
  `nlghost_<parent_id>` while the ghost was created as `nlghost_spawn_<op_id>`.
- **`get_background_map`** tool added, so the agent knows a reference map exists
  (path, transform, opacity, lock) without pretending it can see the pixels. The
  catalog is **24 tools**; the header claimed 20 and was already wrong at 23.

### 🔊 A lock is not soundproofing
`get_way_barrier`'s own contract treats closed/blocked/locked as one "solid state"
for a per-door `sound_barrier` override, but the defaults disagreed: a locked door
blocked **2** where a closed one blocked **1**. A lock is a latch on a door that is
already closed, so `sound.way_locked` and `sound.way_blocked` are now **1**
(`hidden` stays 2). Behaviour change: a shout carries through a locked door, and a
scream carries through an open+closed+locked chain — the loudest channel is no
longer stopped by a latch. The value was duplicated in four places, including a JS
mirror in `turn-feed.js` that would otherwise have disagreed with the engine.

### 🗺 …and why the background map would not come back
Two defects, both upstream of the image itself:
- **The scenario name never reached the client.** `_serialize_world()` omitted
  `_scenario_name`, so `/api/state` never carried it and the client only knew the
  name if it had set it that session. `graph-background.js:_scenarioIdentity()`
  returns `null` without a name, and the local cache is consulted only for a named
  scenario — so a locally-held map was **never** restored.
- **The two "which scenario am I" functions disagreed.** `_scenarioKey()` accepted
  the `body.dataset.scenarioName` fallback that Save/Export Scenario writes;
  `_scenarioIdentity()` did not. The key is now derived from the identity, so they
  cannot diverge.

### ⏱ Vital decay now scales with the tick's game time
Every rate in `vital_rates` is *per in-game minute*, but `time_per_tick_minutes`
is settable per scenario and live from Engine Config — and nothing multiplied by
it. A tick applied one minute's worth of decay no matter how many minutes it
covered, so the clock and the meters disagreed silently the moment the tick
stopped being a minute.

- **`vital_rates.change()` takes `minutes`**, and `tick_minutes(world)` is the one
  place that reads `time_per_tick_minutes` (tolerating junk: `0`, `None` and
  `"nonsense"` all fall back to 1, and a negative sign is treated as a typo).
  `TickManager._decay()` routes every per-minute effect through it.
- **The baseline loop uses the same accumulator as everything else.** It had its
  own `_decay_accum` separate from `change()`'s `_rate_accum` — two parallel
  implementations of the same idea, and a second source of truth per meter.
- **The starvation grace is counted in minutes, not ticks.** It is a wall-clock
  reprieve (360 min of hunger, 60 min of thirst); counted in ticks, a 15-minute
  world would have stretched the 1-hour thirst grace into 15 hours. Damage past
  the grace scales with the tick too (0.5 HP/min × 15 = 7.5 HP).
- **`soak_sim.py`'s `TICKS_PER_DAY` was hardcoded to 1440** "at
  time_per_tick_minutes == 1", so the day/week/month projections lied by exactly
  the tick-length factor while `fmt_span` printed the real spans.

Consequences worth knowing: the **boot `world_template.json` runs at 5
min/tick**, so decay in the default world was running **5× too slow** (the
kraktooth campaign pins 1, so its soak numbers are unaffected). The pleasure
meters (`Arousal`/`Stimulation`/`Pleasure`) are in `baseline_decay` and were
marked *"still per-tick; not yet folded into the per-minute scale"* — they are
now folded in, so they drain 5× per tick in a 5-minute world and may want
re-tuning. `tests/test_tick_time_scaling.py` covers the invariant (equal game
time, equal decay, at 1/5/15-minute ticks); the pleasure and Social-company
suites pin a one-minute tick because they assert per-minute calibration.

### 🎟 Background decisions are paced in game minutes, not ticks
Decay was only half the story. `engine/background_simulation.py` gated
decisions on `DECISION_INTERVAL = 10` **ticks**, so at 15 min/tick a character
decided every 150 minutes instead of every 10 and got a fifteenth as many
decisions per game hour. A week soak at 15 min/tick killed everyone of
exhaustion inside a day at first, then 3/23 once decay was scaled — with food
in reach.

- **Action credit replaces the tick interval.** Credit accrues at
  `time_per_tick_minutes / DECISION_MINUTES` (10) and is spent one decision at
  a time, capped at `MAX_ACTIONS_PER_TICK` (4). A busy or unconscious character
  neither decides nor banks credit, so a long sleep cannot leave a backlog to
  dump on waking. First sighting acts at once, and an explicit future
  `next_due_tick` from a save or tool still defers.
- **Measured invariant:** over the same 1,440 game minutes, 1 min/tick gives
  78.2 decisions/hour and 15 min/tick gives 78.0 — identical within noise,
  where it used to be 15x apart.
- **Body-temperature drift is scaled too.** `drift`/`converge_rate` were
  per-tick while the cold/heat damage they feed was per-minute, so a 15-minute
  tick spent 15 minutes taking band damage per 1 minute of *leaving* the band.
  That was killing poorly-sheltered and cold-blooded characters (Croak-Mother
  in Blackmarsh at 8h15m). Fixed, and the death is gone.
- **`soak_sim.py` gains `--minutes-per-tick`** (it previously only read the
  value from the scenario, so the one thing worth tuning was the one thing you
  could not vary) **and `--mature`**. Both the camp scenario and
  `world_template.json` ship `mature_content: false`, and with it off
  `sync_pleasure_vitals` *strips* Arousal/Stimulation/Pleasure and their decay
  rates — so every soak so far ran a world missing that whole subsystem. With
  `--mature` the sweep is unchanged (those meters start at 0 and do not feed
  survival, and background characters never trip the cascade), but the run is
  now the real world. Worth deciding whether the camp *should* ship it off: the
  players carry `body_state`/`region_exposed` data that implies otherwise.

Week soak, `--background-all`, same game week: **1 min/tick 23/23 alive**;
**15 min/tick 21/23** in 9s instead of 70s, the two deaths being starvation at
6d14h+ — the known finite-food issue (task-410), not the tick length. The
1-minute result is unchanged, which is the point: `×1` scaling is a no-op.

A tick-length sweep over the same game week is flat until the step gets
coarse — **23/23 alive at 1, 2 and 5 min/tick**, then 21–22/23 at 15/30/60. The
death is the *same character* (Silver-Talon) at every coarse step and the whole
camp's food is consumed either way, so the tail is the finite-food problem
(task-410), not the time scaling: at 1 min/tick the hungriest three end the
week at Hunger 100 *alive*. Use ≤5 min/tick when tuning rates.

### ⏳ Condition durations are game minutes
`player.py` documented `duration = ticks remaining` and
`engine/conditions.py` counted one down per tick, so a 5-minute `unconscious`
lasted **75 game minutes** in a 15-minute world, `satisfied` 5 hours and
`sensitized` 150 minutes.

- **Durations and condition `periodic` drains are per game minute.**
  `process_tick` counts down by the tick's minutes and routes periodics through
  `vital_rates.change(..., minutes=…)`, so sub-1 periodics also stop truncating
  to nothing (they were written straight into `vitals` before).
- **`get_active_conditions` reports `minutes_remaining`** rather than
  `ticks_remaining` — nothing consumed the old key.
- **Save compatibility:** instances store a bare number, so a save written at
  1 min/tick is byte-identical in meaning; at a longer tick an old value now
  reads as minutes, which is the correct interpretation.
- Verified: a 10-minute condition expires after 10 / 2 / 1 ticks at 1 / 5 / 10
  minutes per tick (`tests/test_tick_time_scaling.py`).

Re-running the sweep after this changed nothing (same deaths, same identities),
which is the expected negative result: it confirms the remaining soak deaths are
food-limited rather than a residue of tick-quantised time.

Still tick-quantised and not yet converted: `npc_behaviors.npc_action_interval`
(a second, older action scheduler).

### 🧾 Character memories are no longer capped at 200
`player.add_memory` silently dropped the **oldest** memory once a character
passed 200 — a cap nobody chose, and FIFO, so a busy week of generated events
would have pushed the hand-written backstory out first.

- The cap is now `memory.max_per_character` (Engine Config → memory, default
  **0 = unlimited**), read at call time like every other engine setting.
- When a limit *is* set, eviction skips `source: "manual"` memories, so authored
  backstory is the last thing to go rather than the first.
- Verified: 600 generated memories all retained by default; with a cap of 50 the
  total trims to 50 and **all 10 authored memories survive**.

This matters for the background social work (task-423): at the measured decision
rate a character accrues ~2–4 memories per game hour, which would have started
evicting the authored past after roughly three game days.

### 🔗 Relationships fade when nobody maintains them
Closeness only ever moved on an event: `last_interaction_tick` was written in
five places and **read in none**, so a pair that never met again kept its value
forever and a week of simulation could only ratchet.

- **`Player.decay_relationships()`** eases closeness toward 0 by elapsed game
  days, driven from the tick loop **once per game day** — so a 1-minute world and
  a 15-minute one drift identically, and the cost is daily rather than 23
  characters × N relationships every tick.
- **Safe on authored data, deliberately.** The step can never cross zero, shared
  history damps the rate through `interaction_count` (the same counter that feeds
  `derive.familiarity`, so six prior interactions roughly halve the drift), and an
  authored `label` ("my brother") is a *declaration* rather than a measurement, so
  it is never touched — only the computed closeness moves.
- Sub-1 daily steps accumulate per relationship the way vitals do; a 0.5/day rate
  would otherwise round to nothing every day.
- Tunable at `relationship.decay_per_day` (Engine Config → relationship, default
  0.5). Verified tick-length independent: 3 days at 1 min/tick and at 15 min/tick
  land on the same closeness.

### 🏷 Scenarios name themselves from the filename
A blank `_scenario_name` is the failure mode that made saves land as "unnamed"
and left the frontend's local background-map cache unreachable, since
`_scenarioIdentity()` keys off the name. `world.set_scenario_source(path)` is now
the one place that keeps source and name consistent: it derives the name from the
filename stem when the world has none, never overwrites an existing name, and
`None` clears the source only. All seven path-bearing assignments route through it.
`_scenario_name` is also initialised in `VirtualWorld.__init__` instead of only
appearing once something set it.

### 📋 Filed for next
`task-416` area-major tick iteration · `task-417` co-presence gate for coarse
meetings (amends `task-409 §4`, which would otherwise pair characters on opposite
sides of the map) · `task-418` awareness channels replacing `radius_hops` ·
`task-419` one `at` per character + anchor budget · `task-420` a single
relationship write path · `task-421` light barrier parity with sound · `task-422`
NL editor budget controls; `bug-36` `moveNode` called for absent nodes.

---

## Unreleased — "Long-horizon simulation: Phase 0 + trace" (2026-09-19 → 09-20)

Groundwork for running a scenario for weeks of in-game time with every
character a real agent. Two things made that impossible: vitals were still on
session timescales outside the drives (environment/regen/comfort vitals killed
everyone in ~2 hours), and there was no objective record of what a background
character did. See `docs/design/long-horizon-simulation-progress.md`.

### ⏳ Vitals on a true per-minute scale
- **`vital_rates.py`** — new single source of truth for per-minute rates (1 tick
  = 1 in-game minute). From a full meter: Hunger ~3 weeks, Thirst ~3 days, Energy
  ~16h; Social/Hygiene/Entertainment ~1–2 days; Sanity ~14 days. `change()` is a
  fractional accumulator so sub-1 rates actually accrue.
- **All environmental/temperature/social/sanity/bladder/sleep/HP-regen effects**
  in `engine/tick_manager.py` routed through it and rescaled; `engine/activities.py`
  activity regen rescaled too. Cold/heat now measured per minute, heat correctly
  *raises* Thirst (drive), and HP regen no longer outpaces starvation.
- **`tools/migrate_decay_rates.py`** — new: re-bakes per-player `decay_rates`
  (baked rates override engine defaults, so the calibration was otherwise
  invisible). Applied to `world_template.json` and the goblin scenario.
- **`data/library/traits/high_metabolism.json`** — new goblin trait (Hunger ×2,
  Thirst ×1.5, Energy ×1.3).

### 🧾 Objective character trace (task-399 foundation)
- **`engine/trace.py`** — new append-only, code-written history per character:
  `record / recent / since / summarize_window / rollup / load / to_list`, capped
  at 200 entries with salient-first retention. Wired into need tier crossings
  (`why="needs:*"`), deaths (salient), and resolved actions. Round-trips through
  `Player.to_dict` / `_deserialize_player`.
- **Design contracts** — `docs/design/reversibility-contract.md` (one state
  model, two decision policies; what must stay live while backgrounded) and
  `docs/design/trace-format.md` (entry schema, kinds, reason tags, trace→memory).

### 🌦 Scenario fixes
- **Kraktooth forecast** rewritten from a perpetual blizzard (`temperature_mod`
  -15, light -12) to a clear → overcast → rain day cycle. The frozen baseline was
  killing every exterior character with hypothermia within ~11 game-hours.

### 🧪 Tooling & tests
- **`tools/soak_sim.py`** — headless long-run harness with live progress
  (bar/ETA/ticks-per-second/deaths), day/week/month wall-clock projections,
  survival breakdown, `--debug-hp`, `--neutral-environment` (now clears weather
  too), `--engine-decay`, `--override`, `--set`, `--apply-trait`, `--report`.
  Measured ~6–9 ticks/s with 23 characters → a game week ≈ 18–29 min.
- `tests/test_trace.py` (new); `test_activities.py` / `test_social_company.py`
  updated to the per-minute model. **2828 passing** (excluding pre-existing,
  unrelated `test_mcp_*` failures).

### ⚡ Trigger/edge indexing and background scale (tasks 406/407)
- **`graph.py`** — a trigger-event index (`get_trigger_sources`) plus edge
  indexes keyed on lowercased source/target. Turn/time trigger sweeps now visit
  **only** nodes that own that trigger (any node type) instead of every node,
  and edge lookups no longer scan the whole edge list or call `.lower()` per
  edge. A `_revision` counter drives cache invalidation; a length check lazily
  rebuilds if code mutates `edges` directly.
- **Standing items can tick** — `engine/tick_manager.py` now fires `on_tick` for
  items that are neither carried/equipped nor lit/on (a bush, nest, shrine),
  exactly once, without disturbing the existing carried/lit paths.
- **Cheaper trigger execution** — `_execute_triggers` fetches trigger edges and
  type-filters them before building its template context, and resolves the
  current area by id instead of reading the legacy `current_area` property
  (which rebuilt an `Area` plus its exits on every access).
- **Authoring exits cached** — `build_exits_for_area(include_hidden=True)` is
  memoised by graph revision. The game-facing view depends on per-player
  discovery state and is deliberately **not** cached.
- **Lighting** — effective light is now explicitly the **brightest single
  source** (`max`), not a sum: the old `own + items` was computed and then
  discarded by the brightness ceiling anyway (four dim torches never out-shone
  one torch). Every area's light is recomputed **once per tick** into a stamp
  the render/tick paths read, instead of rescanning the room and its neighbours
  on every access; `_item_light_stats` also collapsed from two content passes
  to one. `graph.retarget_edge` was added, and unequip now moves its edge in
  place instead of remove + add.
- **Scenario cleanup** — deleted four generated goblin byproduct scenarios
  (`*_assembled`, `*_populated`, `*_generated`, `*_generated_connected`); one
  goblin scenario remains.
- **The turn-event buffer was O(n²).** `GameLogger.record_turn_event`
  (`engine/logging_events.py`) rebuilt the whole buffer on *every* append. The
  browser clears it each turn, but a headless run never calls
  `clear_turn_events`, so it grew to ~17,000 and each append scanned all of it —
  the real cause of a 265 → 135 ticks/s decline across a week. It now prunes only
  when the turn changes and hard-caps the buffer at 2,000.
- **Take/drop move edges instead of remove + add.** Placement edges are
  captured, then retargeted onto the player (take) or back into the room (drop),
  the way unequip already was. A failed take no longer orphans the item, because
  the capacity/hand checks now run before any graph mutation.
- **Regression guard** — `tests/test_perf_guards.py` asserts the *shape* of the
  hot paths (buffer bounds, index usage, trigger-sweep scope, brightest-source
  lighting, stamp invalidation) instead of wall-clock time. Verified to fail
  when a fix is reverted.
- **Measured** — a one-week (10,080-tick) background soak runs in **~56s
  (181 ticks/s), 23/23 alive** (roughly 56–71s depending on host load) — down
  from ~6–9 ticks/s and from 9m49s after the first pass. Survivor vitals and
  trace are identical to the slower run, so this is pure speed. After the
  logging fix, function-call counts are flat early vs late in a run. Full suite
  **2831 passing** — four fewer than before only because
  `tests/test_data_no_mojibake.py` is parametrized over every scenario JSON and
  four files were deleted.
- **Not yet playable at speed** — the browser is still the metronome (~2s/step,
  one `tick_turn` per roster wrap). Server-side batch advance is task-414.

### 🧰 Gotchas (this pass)
- The interactive ~2s step delay is **UI pacing, not a rate limit**. Rate
  limiting is `RateLimiter` (`agent-engine.js:412–425`, driven by
  `config.rpmLimit`); the sleep predates it. Keep it for readability, make it
  configurable, and use 0 in headless/batch paths.
- The camp's 11 authored triggers are **dead data**: written as
  `logic_trigger → area` edges with `event` on the node, but the runtime matches
  `trigger_type` on the edge with the owner as source. None of them fire.

### 🔬 LLM Inspector — raw request/response capture (task-405)
- `shared/dataset-collector.js` gains `captureRaw` / `getAllRaw` / `clearRaw` /
  `countRaw` over a new IndexedDB store `llm_raw_exchanges` (DB version 4). It
  stores the full request body, response status/headers/raw body, duration, and
  usage. **Authorization/API-key headers are redacted** before storage, and the
  store is capped at 200 entries.
- `llm-client.js` captures after `resp.json()` (non-streaming), after
  `_handleStream` (streaming), and on error responses (400/429/500) so provider
  error shapes are visible.
- New `ui/llm-inspector.js`: a floating **🔬 LLM inspector** panel with
  per-entry expand, a usage line (including `reasoning_tokens`), **Copy
  request / Copy response**, filters by label and status, body search, and
  Clear. Entries survive reload.
- New Settings toggle **🔬 Show Raw LLM** (`config.showRawLLM`, default off) —
  capture is opt-in.

### 🐛 Fixes (settings + active character + DeepSeek)
- **Settings silently reset four toggles.** `populateForm()` never restored
  `agent-mature-content`, `agent-auto-retry-invalid`, `agent-simultaneous-mode`,
  or `agent-structured-output`, so they rendered unchecked and the next Save
  wrote them back as `false`. All four are now restored on form load (and a new
  guard audits that every settings checkbox is covered).
- **"No agent selected" after refresh.** `config.controllingPlayer` is
  client-only and not persisted, while the header's `Active:` comes from the
  server's `active_player`. `step()` and `startRun()` now fall back to the
  server's active player instead of refusing to run.
- **DeepSeek model names.** Profile + model dropdown updated to
  `deepseek-flash` and `deepseek-v4-pro`; `deepseek-v4-flash`, `deepseek-chat`,
  and `deepseek-reasoner` are retired aliases. Thinking is enabled by default at
  `high`, so the disable path is explicit, and effort `none` now means "thinking
  off" rather than being sent as an invalid `reasoning_effort`.

### 🗺️ Scenario authoring fixes + two engine effects
The camp's trigger validator reported **78 issues across 45 nodes**; it now
reports **0**, and the 11 previously-dead triggers fire.

- **Triggers (11).** Authored as `logic_trigger -> owner` with the event on the
  node — a shape the runtime never matches, so none fired. They now use
  `owner -> logic_trigger` with `trigger_type` on the edge, and their legacy
  flat fields migrate into `effects[]` (`message`, `spawn_items`,
  `grant_memory`).
- **`grant_memory` effect (new).** Adds a memory entry to the target player via
  `Player.add_memory`. Registered in `EFFECT_TYPES` with an editor template
  (`data/library/items/template_grant_memory.json`).
- **`once` triggers (new).** A trigger node with `once: true` fires exactly
  once (`fired` persists on the node). Without it the camp's discovery triggers
  repeated their message and duplicated their spawned items.
- **Effect aliases.** `decrement_uses` → `adjust_uses {delta:-1}` and
  `roll_condition` → `save` (with `on_success`/`on_fail` wrapped as lists) —
  both were unknown effect types that silently did nothing.
- **Ways.** Every bidirectional way had only one authored side, so the reverse
  exit fell back to the way name and read backwards (*"passage to scouting
  rooms"* from inside the rooms). Reverse sides now carry the opposite cardinal,
  a direction label, and a view of the far area.
- **Weapons.** Club / Knife / Rusty Hatchet / Spear had `damage_dice` but no
  `damage`, so combat silently used a flat 5; `damage` now mirrors the dice.
- **Tooling.** `tools/fix_scenario_authoring.py` (dry-run by default) applies
  all of the above; `tests/test_camp_trigger_wiring.py` locks the wiring, the
  once gate, and `grant_memory`.

### 👁️ Human panel perception + stranger targeting
- **"Since your turn" no longer leaks the world.** `agent/turn-feed.js`
  subscribed to the global `events` log, and `digest()` returned *everything*
  logged since the last turn — so the human saw other characters acting in other
  areas, written in second person as if it were their own action. `event-stream.js`
  now carries the acting character on the `log` bus payload (explicit actor,
  else the open turn card's actor; system rows stay unattributed), and both the
  digest and the "What happened" feed filter to what the viewer could perceive:
  their own rows plus rows acted by characters in the same room.
- **Audio propagation through ways.** Speech in *other* areas is now included
  when it carries. The panel mirrors `engine/sound.py` exactly — BFS from the
  speaker's area accumulating per-way barriers (`sound.speech_*` 0/1/1/2/3 for
  whisper/normal/sing/shout/scream; `sound.way_open` 0.5, see-through 0.75,
  closed 1, locked/blocked/hidden 2; ambient noise dampening at the origin) and
  a room hears the line when `penetration - accumulated > 0`. So a shout through
  a closed door carries, normal speech carries through an open passage, and a
  whisper stays private. Uses the model's default values — a customised Engine
  Config override is not read by the panel yet.
- **Unmet characters can be targeted by the label the scene shows.**
  `matching.py _match_character_name` gained an appearance-label tier, so a
  stranger resolves by their `unknown_display_name()` ("the woman") — exact,
  partial, or significant-word match, with ambiguity still returning candidates.
  Previously `approach the woman` failed with *"There's no 'woman' here to
  approach."* while the scene listed her. Once met, the real name is what matches.
- Tests: `tests/test_stranger_targeting.py`.

### 🗺️ Graph map background — right-click + on-canvas handles
- **Right-click empty canvas** → 🗺 menu: **Add background image…**, then
  **Edit image**, **✂ Crop**, **⤢ Fit to nodes**, **🎚 Opacity…**, **🗑 Remove
  image**, plus **🔒 Lock nodes** and **💾 Save node layout**. No permanent
  toolbar — the map is opt-in per right-click.
- **Manipulate on the canvas**: drag the image to move, corner handles scale it
  about its centre, the top dot rotates it, and in crop mode the amber inner
  edges crop it (crop is a normalised source window, so cropping enlarges the
  kept region to fill the frame). A small hint chip appears while editing, with
  opacity and Done.
- Rendering: an `<img>` layer is inserted as the **first child** of
  `#graph-container`, so it paints beneath the (transparent) vis canvas — nodes
  draw over the map and the map never covers the legend. It is kept glued to the
  view transform on every `afterDrawing` (`translate(centre) scale(s)
  translate(-viewPos)`), so it pans and zooms with the graph. A second,
  above-canvas handle layer is `pointer-events: none` except on the handles, so
  normal graph interaction is untouched when not editing.
- Persisted per scenario in IndexedDB (`graph_assets`, DB version 5): image data
  URL, rect, rotation, crop, opacity, lock flag, and node positions. Locking
  freezes physics and applies the saved positions.
- Caveat: the storage key is the scenario `_scenario_name` (falling back to
  `default`), so until the camp scenario carries a `name` (task-408) its layout
  is filed under the boot name.

### 📚 Front-end module documentation sweep
- Every non-vendor module under `static/js` (**133**) now opens with a
  `@module` / `@contributes` / `@powers` / `@relates` / `@docs` contract, so
  "what does this file contribute and what feature does it power?" is answerable
  without reading the file.
- `tools/js_module_index.py` generates `docs/design/js-module-index.md`
  (module · purpose · file · contributes · powers · docs), and `--check` **fails
  on any new module missing the contract**. The legacy baseline was retired as
  files were documented and is now empty.
- Bugs found by the sweep (all fixed): an **unreachable `Social` tier** in
  `prompt-builder/character-state.js` (the `[social_need: moderate]` cue never
  fired — two identical `if (v < WARNING)` branches), and `agent/vital-thresholds.js`
  not exporting its own `DRIVE_*` constants. Also: the duplicated lore/brevity
  block in `system-prompt.js` extracted to shared helpers, stale counts in the
  `prompt-builder/index.js` manifest, and missing headers on `event-bus.js`,
  `graph/layout-engine.js`, and `graph/edge-inspector.js`.
- Docs health: `tools/fix_docs_mojibake.py` repaired **233** cp1252 sequences
  across 34 files, and `tests/test_docs_no_mojibake.py` now guards **all** of
  `docs/` (previously only `data/` was checked). `_Index.md`'s stale hardcoded
  repo path was corrected.
- Open decisions raised by the sweep are collected in
  `docs/design/pending-confirmations.md`.

### 🧼 Readable locals + TypeScript toolchain
- **163 cryptic single-letter locals renamed** across 11 files (`v` / `T` / `n` →
  `value` / `thresholds` / `vitals` …). Worst offender:
  `prompt-builder/character-state.js: describeVital`, where `v < T.WARNING`
  became `value < thresholds.WARNING`. Loop indices and coordinates (`i`, `x`)
  are still fine; the convention is documented.
- **TypeScript adopted, incrementally** (`.js` and `.ts` coexist; the app works
  at every step):
  - `tsconfig.json` (`npm run build:ts`) compiles `static/js/**/*.ts` → `.js`
    beside the source — `strict`, `noEmitOnError`, comments preserved.
  - `tsconfig.check.json` (`npm run typecheck`) parses **every** JS + TS with
    `noEmit`; JS opts into checking per file via `// @ts-check`.
  - Converted files stay **classic scripts** (no `import`/`export`) and use
    ambient globals in `static/js/types/globals.d.ts`, so the `<script>` load
    order is unchanged.
  - First module converted: `agent/rate-limiter.ts` → generated
    `rate-limiter.js` (doc header + module contract preserved, `window.RateLimiter`
    intact). `npm run typecheck` is clean across all 133 modules.
  - TS 7 notes: `module: "none"` and `alwaysStrict` were removed (using
    `esnext`), and emitted files begin with `"use strict";`, which the module
    contract guard now steps over.
  - Convention and conversion recipe: `docs/design/typescript-migration.md`.

### 🗺️ Graph layout durability + adaptive edges
- **Node positions persist to the WORLD.** 🗺 → **Save layout to world** (and
  locking) writes each node's `properties.x`/`y` through a single atomic
  `POST /api/graph/batch` — so a layout survives reloads, travels with the
  scenario file, and is one undo step. `buildNodeConfig()` seeds `x`/`y` from
  those properties on load. **`x`/`y` never reach library templates** —
  `handle_library_create_or_update` strips presentation-only properties, and the
  template-refresh paths already build explicit key lists, so a refresh cannot
  clear a node's saved position either. `tests/test_library_presentation_keys.py`
  locks both the helper and the route.
- **Background map stored as a FILE, not base64.** New
  `POST /api/graph/background/image` saves to `static/images/backgrounds/…`, and
  the path plus transform (rect/rotation/crop/opacity/locked) lives in a new
  scenario-level `graph_background` block, serialized like `world_lore`.
  Embedding the map as base64 would have added ~2.7 MB to the scenario per
  commit for a 2 MB image; IndexedDB remains a local fallback for maps never
  uploaded.
- **Search no longer wrecks hand-made layouts.** `graph/focus.js` called
  `network.moveNode()` on *every* match regardless of `physics: false`, and
  `_kickClusterPhysics()` switched global physics on and ran `stabilize(60)`
  even when physics was off — re-settling the whole layout. Frozen nodes are now
  excluded from the cluster grid, and the kick is skipped entirely when physics
  is disabled.
- **Adaptive connection edges.** Area↔way edges size to the label actually
  drawn: `clamp(45…130, 35 + 3.2 × labelLength)`, so unlabelled edges stay tight
  and long names get room without stretching the map. A per-way `edge_length`
  property still overrides.

### 🌍 Scenario naming + per-scenario isolation
- **The top-bar name is now real.** The click-to-rename chip only ever wrote
  `document.body.dataset.scenarioName` — never the server — so the name was
  cosmetic, vanished on reload, and even keyed the graph-background cache. New
  **`POST /api/scenario/name`** sets `world._scenario_name` and, when the source
  file has a different basename, **repoints the commit target** to
  `data/scenarios/<name>.json` — so a world booted from the boot template stops
  committing into `world_template.json`. Existing files are never clobbered.
  The chip updates immediately and reverts if the server rejects the name.
- **Graph backgrounds are per-scenario.** Loading a different world left the
  previous world's map on screen, and the IndexedDB fallback keyed unnamed
  scenarios to one shared `default` slot. The **world is now authoritative**:
  every state refresh re-derives the background (clearing it when the world has
  none), the local cache is consulted only for a *named* scenario, and a
  previous world's physics freeze is undone rather than inherited.

---

## Unreleased — "Survival balance & Sanity breakdown" (2026-09-08)

The mansion survival fix: teenagers were dying of starvation in ~45–63 in-universe minutes despite carrying granola bars and water bottles, because the drive decay was 1/tick, vitals were invisible to the agent, and the moodlets never told anyone *what to do*. Low Sanity was also still draining HP and being listed as a cause of death — going insane doesn't kill you, it makes you more dangerous.

### 🍞 Survival rates → real-world scale
- **Decay rates are now per-minute, not per-tick.** 1 tick = 1 in-game minute, so a healthy adult can now go ~3 weeks without food and ~3 days without water instead of ~15 minutes. Hunger 1→**0.06/min**, Thirst 1→**0.18/min** — applied in `virtual_world_engine.py`, `player.py`, and all 9 players in `data/scenarios/mansion.json` (the scenario was shipping lowercase `hunger`/`thirst` keys the tick loop silently ignored, so the values were never used).
- **Fractional accumulator** in `engine/tick_manager.py`: sub-1/tick rates were vanishing under `int()` truncation, so the drives barely moved. The leftover now carries over tick-to-tick and the real rate actually accrues.
- **Death slope softened.** Hunger/Thirst now drain HP only after a grace period at max (60m / 30m), then at 0.5/1.0 HP/tick instead of 1/2 — a real recovery window. HP stays an integer.

### 🧠 Maslow-prioritized moodlets & plans
- Hunger/Thirst tiers in `describeVitals` rewritten as **imperatives that name the exact carried item**: *"EAT your granola_bar or FIND SOMETHING TO EAT NOW"*, *"DRINK your water_bottle"*, falling back to *"FIND SOMETHING TO EAT NOW"* when nothing is carried. Threat-qualified so they don't contradict the existing `ThreatDetector` alert. Generic — driven by item tags and carried-item graph edges, no scenario-specific strings.
- The plan prompt's critical-needs note now cites **Maslow's hierarchy** and requires the first plan step to satisfy the most urgent physiological need before exploration, investigation, or social goals.

### 👻 Sanity makes you dangerous, not dead
- **Removed the Sanity → HP drain** (`engine/tick_manager.py`) and dropped "madness" from the death-cause list. Sanity ≤ 0 has no physical consequence. Going psychotic, seeing friends as enemies, getting anxious or suicidal is bad for your health in the way that matters here: it makes you a worse fighter and a worse ally, not a corpse.
- **Two new Sanity-triggered conditions** (`engine/player_conditions.py`), mutually exclusive, wired in the tick loop alongside `social_breakdown`:

| Condition | Trigger | attack | defense | periodic | ends on |
|---|---|---|---|---|---|
| `paranoid` | Sanity < 50 | **+1** | −2 | Sanity −1 | comfort, rest, socialize |
| `hallucinating` | Sanity < 25 | **+2** | −3 | Sanity −2 | comfort, rest, meditate |

- **`buildInsanityContext` tiers rewritten as behavioral directives** — *"You are HALLUCINATING... Trust your instincts over your senses. Attack first, ask questions never"* / *"You are PARANOID... assume it's an attack"* — so the LLM steers toward the dangerous behavior instead of just narrating mood.
- **`Involuntary` flavor** for both: paranoid → stutter speech + glance-around/white-knuckles emotes; hallucinating → ramble speech + stare-at-nothing/mutter-to-empty-corner emotes.

### 🧪 Verification
- `npm run lint` clean over all of `static/js/`.
- All edited Python parses and imports; conditions load (38 total).
- **233 condition/vital/tick/sanity tests pass.** 2,672 tests pass overall; the only failures are 56 pre-existing `tests/test_mcp_*.py` harness breakages (`'function' object has no attribute 'fn'`), which touch none of these files and were already broken before this change.

### 🧰 Gotchas
- The scenario's `decay_rates` keys were lowercase (`hunger`/`thirst`) while `Player.decay_rates` and the tick loop use capitalized `Hunger`/`Thirst` — so the scenario values were silently ignored and fell back to the engine default. Normalized to the canonical casing. If you hand-author `decay_rates` in a scenario, match the Player convention or they won't take effect.
- `mansion.json` is the only scenario patched; other scenarios still ship the old 1/tick rates. Patch them when you re-run them.

---

## 1.7.1 — "Self-healing JSON & dataset capture" (2026-09-07)

The parse-failure follow-up: when heuristic JSON repair gives up, the LLM now fixes its own broken output (the sports-bra response had 5 stray closing braces — `19 {` vs `24 }` — unrecoverable by regex); and every request/response pair is now captured to IndexedDB so it can be exported as a chat-format JSONL fine-tuning dataset.

### ⚡ LLM-backed JSON repair (last-resort fallback)

- `parseJSONFromResponse` now also returns the **parser error message** alongside `{json, raw}`.
- `AIGenerator.generate`: when `extractTopLevelJSON` + `repairJSON` both fail, the broken JSON **and the error** are sent back to the LLM ("This JSON is invalid. Identify and fix the issue based on the error message, and return ONLY the corrected JSON object."), re-parsed, and used as if the original parse had succeeded. Falls through to the existing failure path if the repair also fails. Verified end-to-end: broken bra-JSON → parse null + `"…at position 354"` → one repair call → success.

### 🧪 Dataset collector (fine-tuning pipeline, step 1)

- `shared/dataset-collector.js`: captures every completed `llmClient.chat` call — `{messages, response, label, model, parsed_ok, repaired}` — into a new IndexedDB store (`llm_dataset`, storage v3). Streaming and non-streaming both covered.
- Floating **🧪 dataset** button (bottom-right): live count (captured / parsed-OK / failed), **Export all / parsed-OK only / failures only** as chat-format JSONL (system→user→assistant + meta), and clear.
- The negative examples (failed parses, like the bra) are exactly what a tiny fine-tune needs to learn "emit valid JSON in the app's exact shapes" — pair them with the AI-repaired output as the target.

### 🛠 Fixes

- **`graphManager is not defined`** on load (`static/js/graph/focus.js`): `init()` dereferenced `graphManager` at parse time; it now defers until the global exists (`DOMContentLoaded` / `state:updated` self-guard).
- **ESLint guard**: flat config (`eslint.config.js`) with `no-undef` over `static/js` + the full cross-file global set (excludes 3rd-party `vendor/`). `npm run lint` clean. Would have caught the `graphManager` bug statically.

### 🧰 Gotchas

- Restart your server — storage version bumped to 3 (IndexedDB upgrades on next load; existing data preserved).
- Dataset export is manual (the 🧪 button); nothing leaves the browser until you click export.

---

## 1.7.0 — "Trigger Smith & Triage" (2026-09-07)

The authoring-and-triggers day: an AI trigger suggester that finally writes *correct* triggers (full catalog + worked-example prompt, `{triggers:[...]}` object output, fixed local-model response parsing), a plan-driven heuristic floor that can't invent "eat the spyglass", a review-the-diff modal instead of blind overwrites, a batched apply that doesn't lag the graph, a validator that became a triage panel (group by node/code, dismiss-until-touched, derived progress), graph search that freezes hidden nodes and clusters matches, and a fixed dead `on_light` trigger. **Full suite at 2636 passing** (81 MCP/emote tests deselected — pre-existing harness breakage, see Gotchas).

### 🤖 Trigger AI generator — works now

- **Prompt is a real catalog, not a schema dump** (task-396): every trigger type, condition, and effect with a plain-language description AND a worked example; three complete style-anchor objects (food, tainted-drink, haunted-take). Hard rules the model used to miss: `effects[]` is mandatory (≥1 per trigger), prose lives in `effects[].params.message` / `adjust_vital.success_message` (top-level strings stay `""`), consume uses exactly ONE of `on_eat`/`on_drink`/`on_use`, finite-uses get a `uses_above:0` guard, heat sources are item **properties** (`target_temperature`/`heating_rate`), not triggers.
- **Model output is now `{"triggers":[...]}`** (object wrapper) — local models handle that far better than a bare array; the parser also still accepts a bare array defensively. `extractTopLevelJSON` correctly handles top-level arrays (brace-only extraction was destroying them).
- **Local-model streaming fixed**: the whole answer rides inside the `response.completed` envelope for Responses-API providers (ornith-1.5-9b etc.); `_handleStream` now pulls content out of it AND logs the raw response to the event stream like every other generator — no more opening the network tab to see what the model made.
- **`on_light` is no longer dead**: it was registered but never fired. `toggle_item_status` now fires it as a companion to `on_toggle_on` when a toggleable turns on, so authors can bind "this got lit" flavor without the toggle_on/off dichotomy. Never author both `on_light` + `on_toggle_on` (they fire together). 4 new tests (`tests/test_toggleable_items.py`).

### 🎯 Trigger suggester — heuristic + AI + diff review

- **Plan-driven**: the item's own actions decide WHICH triggers exist (`examine/use/take/drop/equip/unequip/eat/drink/read` → their `on_*`), tags/category decide WHAT they contain. Category detection is tags + explicit actions only — no free-text word matching, so "lea**ther**" can never turn a spyglass into food (validated across all 472 library items: zero eat-without-eat-action, zero duplicates). Augments: lights → `on_light` + `on_toggle_off`, books → `on_read`, consumables with only a `use` action carry the vital on `on_use`.
- **Heuristic floor is provably solid**: empty-guards, CON-save poison on tainted/cursed, Arcana/Survival examine reveals, haunted take-whispers — and it beats the hand-authored `water_bottle`/`energy_drink`/`tainted_wine` (which lacked the guard/poison entirely).
- **AI authors the prose** on the same plan (`TriggerSuggestAI` → shared `AIGenerator`), with heuristic backfill for plan types the model skips.
- **Diff modal, not overwrite** (`trigger-suggest-diff.js`): per-trigger cards with Keep existing / Use suggested / Skip both pills, live "Apply N changes" footer, and `covered()` dedupe so a food item that already has `on_eat` Hunger is left alone. Applies in both the item-library form and the item/way/area inspectors, via one atomic `/api/graph/batch` (single undo) instead of N sequential createNode+createEdge round-trips — the apply no longer lags the graph.
- **Architectural cleanup**: `ItemLibraryAI` never was a separate AI (it always wrapped the shared `AIGenerator`); the trigger-AI moved to `shared/trigger-suggest-ai.js` so the inspector doesn't reach through the item-library namespace.

### 🛠 Validator → triage panel (task-393)

- **Group by node / by code**: one row per way/item/area (a way's 6 side-warnings collapse to one expandable row; candy_jar's 4 empty stubs collapse to one) or one row per issue class ("way_missing_cardinal ×58"). De-duplicates the flat 254-row wall.
- **Dismiss-until-touched**: 🚫/🔓 writes `ignored_issues` into the node itself (survives reloads — your whole "can't remember what's fixed" pain); a dismissal expires if the node is edited after (`_ignored_at` vs `node.updated`).
- **🧹 remove all empty stubs**, **⚡ quick-fix** for mechanical info nudges, **⚡ Fix all** (one batch), and a derived progress bar (clean/total item+way+area nodes with no undismissed issues — computed, can't drift).
- **Scrollable list + sticky count**, sticky filter toggle, `POST /api/triggers/ignore` backend.

### 🧭 Graph search freezes + clusters (task-394)

- Hidden (non-match) nodes are **excluded from physics** during a search — they were invisible but still repelling, which is why "food" results stayed wedged in place. Matches settle freely now.
- On settle, the match cluster gets **gathered into a compact grid at the viewport center** (positions + viewport saved); clearing the search **restores the exact prior layout**.
- **KEEP checkbox** next to the search box: freezes hidden nodes but leaves matches geographically in place — for "where does food live in this house?" reasoning.
- **Tag filtering** landed in both the graph search and Ctrl+K palette (write what you *think* exists in tags, fuzzy-match reveals those nodes too).

### 🚪 Way-orientation honesty (task-395 rework)

- The earlier blind bulk-fill (churching "north" cardinals, templated pass/visible messages) was **removed** — it would have written false facts into ways. `way_missing_pass_message` / `cardinal` / `view_direction` downgraded from `warning` to `info` (they have engine defaults), a `clear_way_fix_fields` op undoes any legacy mints exactly, and the panel's button now routes to the existing per-way ✨ Improve AI instead of templating prose. Remove-`fix_way_orientation` no-op deleted.

### 🧰 Gotchas in this release

- **Restart your server** — engine changed (`toggleable_items.py`, `trigger_validator.py`, `routes/triggers.py`, `routes/graph_ops.py`); static JS is reload-only.
- **Mansion scenario file churned** by live testing saves — inspect before mixing with other templates.
- **81 tests deselected** (`-k "not mcp and not emote"`): the pre-existing MCP harness breakage (`'function' object has no attribute 'fn'`) plus the emote suite; unchanged by this release.
- The AI trigger suggester needs a configured API key/model; the heuristic `⚡ Suggest` works fully offline. Diff modal defaults: conflicts → keep existing, adds → add.
- `on_light` now fires with `on_toggle_on`; existing items that had BOTH will double-fire (remove one).

### 🧪 Behind the scenes

- New modules: `static/js/shared/trigger-suggest-ai.js`, `static/js/shared/trigger-suggest-diff.js`, `static/js/item-library/consumable-triggers.js`, `tests/test_toggleable_items.py` (4).
- Updated: `engine/toggleable_items.py`, `engine/trigger_validator.py`, `routes/triggers.py`, `routes/graph_ops.py`, `static/js/{llm-client,api,validator-panel}.js`, `static/js/shared/{json-utils,trigger-editor}.js`, `static/js/inspector/trigger-helpers.js`, `static/js/graph/{focus,projector,tooltips}.js`, `static/js/ui/command-palette.js`, `static/js/item-library.js` + `item-library/ai-generation.js`, `static/js/agent/prompt-builder/{contextual-actions,system-prompt,turn-prompts}.js`, `templates/index.html`.
- Tasks: task-393 (validator triage), task-394 (graph search cluster), task-395 (way-orientation rework), task-396 (AI trigger prompt examples — reference + embedding).
- Full suite at **2636 passing** (81 deselected).

---

## 1.6.0 — "Cold Open" (2026-09-04)

The believability day, run against a live tick-by-tick event log: the planner was found **disconnected from the decide prompt since the PlanTracker migration** and re-wired end-to-end, the human turn panel became an honest observer (no whispers, no other minds), the react phase got its own minimal prompt (~6.2–8.1k → ~2.5–3.5k tokens, internal contradiction deleted), stranger descriptions stopped leaking names through their "appearance handle", and the taco_bell_date scenario was rebuilt to open **cold** — two strangers, one crash, zero shared history. **Full suite at 2653 passing** (pre-existing MCP harness failures unchanged; see Gotchas).

### 🗺 Planner — visible, honest, unit-tested

- **The plan was never shown to the decider.** `buildPlanContext` / `hasPlan` / the inspector read `window.VW.agent._plans` — a store `PlanTracker` had replaced. Fixed: all three read `PlanTracker`, so `=== YOUR PLAN ===` (with `(done)` / `(CURRENT)` markers and the blocked-step warning) now renders in the decide prompt for the first time since the migration. Fresh plans are visible **the same turn** (the decide snapshot refreshes after `setPlan`).
- **`trackStep` matching fixed twice**: stop-words are filtered for real (the old `length > 2` filter passed "the", so *any* action containing "the" completed *any* step), and an action **with a target must match a non-verb step word** — `approach the order counter` no longer completes `approach the round the corner to oak lane` on the shared verb alone. Bare verbs (`look`, `wait`, `rest`…) still advance on the verb.
- **`shouldReplan` returns a reason string** consumed by the task-340 crisis log: `no plan` / `plan aged out` / `current step failed repeatedly` / `threat detected` / the critical need itself — replacing the fallback label that logged every no-crisis replan as a fake `plan stalled`.
- **`setPlan` records the turn clock** (was `time_ticks`, compared against `turnNumber` — a mixed-units bug that broke plan-age checks across engine re-inits).
- `getFailures` exported; the PREVIOUS PLAN prompt section reads PlanTracker directly.
- Tests: 6 new tracker tests (stop-words, verb-vs-target, reason strings, block-and-advance semantics).

### 👁 Observer feed (human turn panel)

- **`turn-feed.js` rewritten** around structured entries: raw event lines parse into speech / whisper / action / emote / result / system / NPC / recall, grouped and styled with icons, colored actor labels, quoted speech, italic emotes.
- **Observer Concise view is the default**: whispers collapse to *"X whispered"* (never the words), inner monologues, memory-recall dumps, plan stalls, and meta noise are filtered out; a short narrative summary ("Since your turn: …") opens the feed. **Detailed** toggle restores the full styled log.
- Stranger names are masked in the feed via the same `anonymousName` logic as the scene.

### ⚡ React phase — own mind, own prompt

- **Dedicated minimal react system prompt** (`buildReactSystemPrompt`): lore + emote rules + speech/volume + JSON rules + length. The action-law blocks (ACTIONS / ACTION STRUCTURE / ITEMS vs FLAVOR / INTIMACY) are gone — they were ~1.2k of weight that also directly contradicted the react instruction *"MUST NOT include action or item fields."*
- **Fresh 2-message conversation** for the react call: the decide-phase replay (~2–3k of persona/room/plan/available-actions duplication) and chain-follow-up bloat no longer ride along. React calls drop from **~6.2–8.1k to ~2.5–3.5k tokens**; the exchange is still mirrored into the character history for next-turn continuity, and the persona rides in the react user message.
- **Movement-aware react context**: a `go` now says *"You just moved — you are now in X. The full description of your new surroundings is in === WHAT HAPPENED === below."* instead of the lying *"surroundings are unchanged — see your observation above"* pointing at the room you left.
- Inline truncated-JSON retry re-asks in the same conversation with a completion nudge, and the final (retried) response is what lands in history.

### 🙈 Stranger descriptions stop leaking names (task-339 companion)

- **New `engine/name_masking.py`** + scrubbing applied in **both** people renderers: `scene_snapshot.py` (decide-prompt People lines, incl. the JS dim-light `"A vague shape in the gloom — …"` prefix) and `area_description.py` (the backend `look` People line). A stranger's first sentence is an *appearance* handle — descriptions that open with the character's own name no longer leak it; the name is learned by hearing it, as designed.
- Previously this leak let an observer-LLM "learn" a name nobody had spoken.

### 🎭 Scenario: `taco_bell_date.json` rebuilt as a cold open

- **Premise**: Miki's date (Bradley — patreon discovery, ended on a sidewalk an hour ago) went bad; Jake is simply out for food. They crash into each other at the blind corner — **that is turn 0**. Both start on Elm Street, seconds after the collision, as strangers.
- **Jake's 5 first-date memories replaced** with stranger-state seeds: the fridge inventory that sent him out, the pegging shout (now a *past* visit), a neon-sign photography hyperfixation aimed at the flickering `'bell'` panel, and the crash itself. His personality no longer pre-decides "you noticed miki tonight… intentional date."
- **Miki**: keeps the Bradley anchor; the earring contradiction resolved as story — it went missing during the date and *she* found it crumpled in her hoodie pocket (clasp bent), so prose and live equipped-state finally agree. Relationships wiped both ways: the anonymizer ("the man" / "a man's voice") is now correct, and names get learned in-run.
- **World fixes**: ` Streetlight (copy)` (an Elm Street lamppost — spray-painted arrow and all — sitting in the wrong alley) is now **String of Bare Bulbs** matching oak lane's prose; both streetlight names lost their phantom leading spaces; the impossible old meet-cute spill trigger (4 copies, spilling from a crushed empty can) is neutralized.

### 🛠 Fixes

- **Witnessed dedupe** — a character's decide emote and identical react emote no longer render as two WITNESSED lines; repeated heard sounds dedupe too.
- **Comprehensive AVAILABLE ACTIONS** — the block now lists every actionable verb per turn with concrete targets (per-way go/dash/examine/open/close, per-item take/use/read/toggle, self verbs with need hints) instead of a curated sparse subset; the scene view's way menu respects already-standing-at-the-way state (no duplicate `approach`).
- **System prompt trimmed** post-AVAILABLE-ACTIONS: rules that duplicate what the per-turn block demonstrates (go/approach semantics, action structure examples) cut ~40%.
- Plan-stall label honesty, memory-recall label cleanup, and NPC idle lines parse as typed entries in the feed.

### 🧰 Gotchas in this release

- **Restart your server** — engine changed (`name_masking.py`, `scene_snapshot.py`, `area_description.py`); static JS is reload-only.
- **Scenario edits apply on reset to initial state** — existing saves keep the old state. The rebuilt taco_bell_date opens cold; older runs in your saves/ folder are from the previous premise.
- The observer feed defaults to **Concise**; the Detailed toggle shows whispers' existence, system rows, and typed raw entries — it is a debug view, not the intended read.
- React calls are ~2.5–3.5k tokens now, but keep LM Studio context ≥ 9k anyway: the context window, not `max_tokens`, was silently truncating completions mid-JSON (diagnosed via two identical ~196-token cuts on ~6k prompts).
- Plan steps still match by word overlap on prose steps — structured `goal/step/then` plans are the designed follow-up (see session analysis).

### 🧪 Behind the scenes

- New: `engine/name_masking.py`, `tests/test_name_masking.py` (5).
- Updated: `tests/test_plan_tracker.js` (+6), `engine/scene_snapshot.py`, `engine/area_description.py`, `static/js/agent/{plan-tracker,agent-engine,turn-feed}.js`, `static/js/agent/prompt-builder/{character-state,helpers,room-context,system-prompt,turn-prompts}.js`, `static/js/inspector/agent-view.js`, `data/scenarios/taco_bell_date.json`.
- JS unit suite **52 passing**; engine name/masking/snapshot/area tests **34 passing**; full Python suite **2653 passing** — the pre-existing `tests/test_mcp_*.py` harness breakage (54–55 failures, `'function' object has no attribute 'fn'`) predates this release and is unchanged by it.

---

## 1.5.0 — "Tender Magic & Graph Forge" (2026-09-02)

A sweeping working-tree day: environment/time/weather engine plumbing, trigger-graph viewport and compile-honesty overhaul, broadened NPC behavior vocabulary, character/schema cleanup, and a 15-spell Lyrie spellbook design task. **Suite at 2507 passing**; no regressions in the core scenario/turn flow.

### 🌦 Environment & Time (engine)

- **Area status engine** (`engine/area_statuses.py`): data-driven area status definitions, persistence, and save/load round-trip.
- **Environment propagation** (`engine/environment_propagation.py`): temperature/light decay and adjacency propagation wired into the tick loop.
- **Effect handlers** (`engine/effect_handlers/environment.py`): `set_environment`, `adjust_environment`, `set_weather`, `set_time`, `set_date`, `forecast_override`, `adjust_forecast`, `apply_area_status`, `clear_area_status`, `set_wet` implemented as item/trigger effects.
- **Tick integration** (`engine/tick_manager.py`): area status + environment updates execute each tick.
- **Trigger validator** (`engine/trigger_validator.py`): new catalog entries for the expanded environment/time effect set.

### 🧠 NPC Behaviors

- **`engine/triggers/behaviors.py`** (+899 lines): new action types `add_memory`, `set_emotion`, `set_flag`, `hide_in`, `hide_behind`, `hide_under`. NPCs can now leave memories, change mood, set runtime flags, and take cover.

### 🎨 Trigger Graph Editor

- **Viewport**: pan, zoom-to-cursor, Fit, dot-grid background, per-graph viewport persistence.
- **Wires**: left-in/right-out socket layout, YES/NO branch coloring, arrowheads, wire selection + delete, cycle/duplicate guards.
- **Compile honesty**: badges/warnings for fan-out drop, behavior NO-branch drop, and Y-position priority override.
- **Catalog parity**: trigger node now supports multi-select trigger types from the shared registry; condition node grouped dropdown covers all 27 conditions; effect node covers the full 42-effect catalog plus save-gate branches, `llm_respond`, `scry`, memory effects, and environment presets.
- **Interaction fixes**: field commits on `input`, selection class-toggle instead of rebuild, Escape/close guard, draft autosave.
- **Tests**: `tools/test_trigger_graph_viewport.cjs` (19/19), `tools/test_behavior_action_cards.cjs` (119 action types).

### 🧍 Characters

- **Lyrie** (`data/library/characters/Lyrie.json`): equipment slots normalized from string refs to full item objects; memory schema unified (`salience_override`, tick normalization, text formatting cleanup); vitals corrected (`Hunger 94→6`, `Thirst 94→6`); stray markdown artifact removed from `personality`.
- **Whiskers** (`data/library/characters/whiskers.json`): character data update.

### 🗺 Scenario & World Template

- **`data/scenarios/mansion.json`**: migrated to the current scenario schema (`players` map, `current_area`, `area_presence`, equipment objects).
- **`world_template.json`**: refreshed to match the new schema.
- **`virtual_world_engine.py`**: small schema/plumbing updates to keep live state aligned with the migrated format.

### 📚 Library Items & Triggers

- **New templates**: `template_adjust_forecast`, `template_apply_area_status`, `template_clear_area_status`, `template_forecast_override`, `template_set_date`, `template_set_time`, `template_set_weather`, `template_set_wet`.
- **New scratch trigger**: `data/library/triggers/untitled.json`.
- **New reference**: `docs/Trigger-Condition-Effect-Cheat-Sheet.md`.

### 🛠 Fixes

- **Behavior form editor crash**: `weighItem`/`inventoryItem` undeclared consts fixed; all 119 behavior action cards now build without throwing.
- **Graph field persistence**: inline handlers now reference `TriggerGraph` correctly; id substitution no longer mangles quoted ids.
- **Behavior graph layout**: re-layout from single tall column to priority-ordered row-major grid; fit zoom improved on dense behavior sets.
- **Wire rendering after reopen**: wires now redraw after viewport settle, preventing offset/scattered wires on open.

### 🧰 Gotchas in this release

- **Restart your server** — engine, routes, and frontend all changed.
- The mansion scenario file is large and structurally different from older scenarios; inspect via the Scenario Manager before mixing with older templates.
- `llm_respond` remains blocked in trigger contexts without a host-side LLM provider decision.
- Some new effect types (`polymorph_target`, `create_illusory_companion`, `broadcast_emotion`, `repair_item`, `ward_area`, etc.) are proposed in `task-391` but not yet implemented in the engine.

### 🧪 Behind the scenes

- New modules: `engine/area_statuses.py`, `engine/environment_propagation.py`, `engine/effect_handlers/environment.py`, `static/js/shared/env-presets.js`.
- New tests: `tests/test_area_statuses.py`, `tools/test_trigger_graph_viewport.cjs`, `tools/test_behavior_action_cards.cjs`, `tools/_probe_parity.cjs`.
- New tasks: `task-388` (trigger-graph overhaul), `task-389`/`task-390` (NPC behavior phases), `task-391` (Lyrie spell items + engine effect proposals).
- Task vault reorganized: 10 environment tasks moved to `done/environment/` or `cancelled/`; sequence doc bumped to 392.
- Full suite at **2507 passing**.

---

## 1.4.0 — "Body Language" (2026-09-01)

The mature-content pleasure system (vitals, intimacy verbs, arousal conditions, release loop,
mature traits), a company-aware Social overhaul, vitals-driven emotions, involuntary actions,
invisible undead-ghost NPCs, and the identity foundation for id-backed characters. Everything
adult is opt-in behind a single 🔞 toggle and leaves the base game untouched. **2589 passing**
(69 MCP tests deselected — pre-existing harness breakage, see Gotchas).

### 🔞 Mature content toggle (task-206)

- **World flag** `mature_content` mirroring ghost_mode end-to-end: `GET/POST /api/settings/mature_content`,
  world attribute, save/load round-trip, settings-modal toggle (🔞 Content group), IndexedDB persistence.
- Everything below is gated on it: toggle off → no pleasure vitals exist, intimacy verbs reject with a
  flavor message, adult traits vanish from library pickers, arousal conditions strip themselves.

### 💗 Pleasure vitals & release loop (tasks 207/208)

- **Three new vitals** — Arousal (slow ebb), Stimulation (medium drain), Pleasure (fast fade) — appear
  only in mature worlds, self-healing via `Player.sync_pleasure_vitals()`, with baseline decay rates.
- **Clothing friction** (task-208): equipped items' `friction` property trickles Arousal (0–3/tick).
- **Edging**: Stimulation 50–64 stacks the `sensitized` condition and feeds Arousal.
- **Release**: Stimulation ≥ 65 ∧ Arousal ≥ 40 fires the cascade — Energy −20, Entertainment +30,
  Hygiene −10, Sanity +15, meters reset, `satisfied` + `overstimulated` applied, log line for the
  active player.

### 💘 Intimacy verbs (tasks 211/212)

- **New module** `engine/pleasure_actions.py`: 8 verbs (kiss, caress, lick, suck, bite, pinch, blow,
  tickle) with a `VERB_BASE` pressure/pleasure/pain table.
- **Body-part targeting**: `kiss lydia on neck`, `pinch her on the left nipple` — same region resolver
  as task-253 combat. Omitted `where` defaults per verb (kiss → lips). Covered regions land
  *through clothing* (damped ×0.4).
- **Multiplier pipeline** (task-212): intensity (light/normal/firm — leading "firmly kiss…" and
  trailing "…gently" both parse) × region sensitivity (paperdoll `body_state`) × trait
  `body_part_multipliers` (e.g. `wired_differently`: nipples ×3.0, genitals ×0.1) × closeness bonus.
- **Pain flips**: `pain_potential` verbs (bite, pinch) can drive Pleasure negative → `overstimulated`.
- **Interact-type**: never damages, recorded as `interact` turn events, no weapon/roll path — a clean
  `interact` vs `attack` split in the dispatch.
- **Frontend** (`action-normalizer.js`): mature worlds accept/emits
  `{action:"kiss", target, where, intensity}`; the system prompt gains an intimacy schema section.
  Non-mature worlds never accept or advertise the verbs.

### 🧬 Arousal conditions & mature traits (tasks 209/213)

- **13 new conditions**: `warming_up` / `aroused` / `highly_aroused` / `frantic` (threshold-driven
  from the Arousal vital, applied/removed automatically each tick), `overstimulated`, `nipple_hard`,
  `blushing`, `wetness`, `sensitized` (edging stacks), `satisfied` (afterglow), plus base-game
  `itch`, `goosebumps`, and `social_breakdown`.
- **Guard**: condition periodic effects can no longer CREATE vitals — an arousal condition on a
  non-mature world can't leak an Arousal key into `player.vitals`.
- **7 mature traits** (`wired_differently`, `quick_recovery`, `sensory_memory`, `sex_addict`,
  `attention_seeker`, `exhibitionist`, `single_track`) — marked `mature: True` and hidden from
  library listings unless the toggle is on. Wired hooks: `quick_recovery` halves the
  overstimulated bout, `sensory_memory` leaves lingering sensitivity after release, `sex_addict`
  doubles Entertainment decay at low Arousal.

### 🪞 Body-state descriptions (task-210)

- **Equipment description enrichment**: the appearance prompt now carries per-item detail properties
  (opacity / coverage / current_state / friction) plus a visible-physical-state section (flush, hard
  nipples, trembling, desperation…) — woven into the prose in both the LLM and fallback paths.
- **Agent prompts** gain first-person body-state lines derived from the arousal conditions.

### 👻 Undead ghost NPCs (task-309 MVP)

- Tag a character `ghost`/`undead`: invisible to room listings and social presence, skips ALL vital
  processing (no hunger/cold/fatigue), untargetable ("the blow passes straight through"), and
  **phases through locked/blocked/one-way/item-gated ways** — perfect for atmospheric stalkers.

### 🗼 Emotion from vitals (task-142)

- `engine/emotion.derive_from_vitals()`: when no explicit emotion has been set (or the affect map
  decayed back to neutral), mood is derived from actual physical state — starving → craving/anxious,
  frozen → uneasy, exhausted → irritated/melancholic, injured → afraid, dying → deep calm (ghosts),
  asleep → silent. Explicit emotions always win; vitals only fill the silence.

### 👥 Company-aware Social overhaul (task-353)

- **Isolation timer**: after 5 consecutive alone-ticks, Social decay accelerates (extra −1/tick);
  introverts exempt, **loners reverse it** (+1/tick in solitude).
- **Physical ≠ social** (task-353 §2): humid air and `humidity: humid` now sap **Hygiene** (not
  Social); perfume boosts **Entertainment** (not Social). A lone character in a perfumed room is
  still alone.
- **GROUP_ENERGY_DRAIN** is now consumed: crowds of 3+ sap Energy per the trait value.
- **Self-talk**: speaking with no living listeners in the room gives +1 Social instead of +5.
- **chatty trait**: +2 per exchange (speaker +7, chatty listeners +5).
- **Behavioral gates** (§5): prompt flags (`social_need: moderate/desperate`) at Social < 50/25 and a
  `social_breakdown` condition below 10 (Sanity drain, removed once Social recovers ≥ 15).
- New traits: `loner`, `chatty` (conflict-correct, library-seeded).
- **Fixed 5 pre-existing `test_social_company.py` failures** (the humid-area Social double-drain).

### 💬 Involuntary actions (task-166)

- **`static/js/agent/involuntary.js`**: condition-driven speech/emote interruptions — frightened →
  stutter ("W-what did you say?"), freezing → chattering stutter, sick/poisoned → coughs,
  social_breakdown → hollow muttering, itch/goosebumps → scratch/shiver emotes, plus a low random
  baseline (hiccup/burp/yelp). Pronoun-aware, never blocks the intended action, injected before the
  text is sent so the room and event stream both see it.

### 🛠 Fixes

- **Mana vital leak** — non-magic characters showed a Mana bar because saves/scenarios hardcode
  `"Mana": 0` and every hydration path overwrote vitals after the tag sync. All five hydration
  paths (save load, library spawn, template load, library import, player import + graph copy) now
  re-run `sync_vitals_with_tags()`.
- **Latent `AttributeError`** in the NPC hunter facade (`_get_nearest_player_to` /
  `_get_path_to_area` called non-existent undecorated names on `npc_behaviors`).
- **TickManager ghost check** — `TickManager.player_manager` is actually the engine; the undead-ghost
  decay skip went through a facade that resolved to `None` (found by the new tests).
- **Release cascade** — `satisfied`/`overstimulated` no longer exclude each other (refractory
  overload + afterglow coexist).

### 🧪 Behind the scenes

- New test file: `tests/test_pleasure_system.py` (21 tests) covering the toggle gating, multiplier
  pipeline, dispatch (incl. the leading-adverb form), friction/edging/release, quick_recovery,
  ghost NPC behavior, phasing through locked ways, and id round-trips.
- **task-316 foundation** (safe subset): stable opaque `Player.id` (uuid8, serialized/restored) and
  `graph.add_node` no longer silently overwrites duplicate **character** nodes. The full
  registry/relationship re-key remains a dedicated follow-up.
- Task vault: 142/166/206/207/208/209/210/211/212/213-lite/309-MVP/316-foundation/353 — implemented
  in this session.
- Full suite at **2589 passing** (+21 new; 69 MCP tests deselected).

### 🧰 Gotchas in this release

- **Restart your server** — the engine, routes, and frontend all changed.
- **Mature content is opt-in and off by default.** Toggle it in settings (🔞 Content group) or
  `POST /api/settings/mature_content`. Toggling mid-session strips/creates the three vitals and
  their conditions automatically — nothing leaks into clean scenarios.
- **Item `friction` / `opacity` / `coverage` properties** drive the new description + arousal
  behavior but no library items have them yet — set them in the inspector/library and they work.
- **Ghost NPCs** need the `ghost` or `undead` **tag** on the character. They're fully invisible:
  no room listing, no social presence, no tick processing. Include them in queries with
  `include_ghosts=True`.
- **MCP test modules** (`tests/test_mcp_*.py`) are broken by a pre-existing harness issue
  (`'function' object has no attribute 'fn'`) that predates this release — 69 tests deselected
  until that harness is fixed.
- The 4 remaining mature traits (attention_seeker, exhibitionist, single_track, sex_addict's
  perception side) are defined but await the NPC-perception framework (task-214) for their hooks.

---

## 1.3.0 — "Weather Eye & Wild Words" (2026-08-31)

A forecast schedule engine, game calendar, moon phases, wind/humidity, a triple-feature NL Editor
power-up (ghost previews, populate_area, selective apply, mechanic inference, lore-aware prompts,
palette shortcut), a sky widget driven by live state, trigger effects for time/weather, and
moonlight descriptions. **2633 passing**.

### 🌦 Weather & Sky (engine)

- **Forecast engine** (`engine/weather_forecast.py`): authored (hourly/weekly/yearly), deterministic
  state-machine, random, or hybrid modes. Zero authored entries = strict no-op — existing scenarios
  are unaffected. GM/trigger `forecast_override` with duration countdown & auto-revert.
- **Calendar** (task-228): `game_day/month/year` derived from ticks + `calendar_config`
  (`minutes_per_day`, `days_per_month`, `months_per_year`), exposed in `/api/state`. `set_game_time`
  / `set_game_date` effects.
- **Moon phases** (task-229): deterministic 30-day cycle (`new → crescent → quarter → gibbous →
  full → waning`). Outdoor night areas add the moon's `light_bonus` to ambient light (full moon
  +25, stormy nullifies it, foggy halves it). `blood_moon` override stains the sky red (+30).
  Moonlight lines in area descriptions.
- **Wind** (task-231): `none/breeze/wind/gale/storm/hurricane` — accelerates heat propagation
  (stronger wind wins), wind chill resisted by `wind_resistance%`, extiguishes lit items on
  gale+ (10%–60% chance/tick), drains Energy on exterior moves. New item properties
  `wind_resistance`, `water_resistance`.
- **Humidity** (task-232): `dry/humid/wet/flooding` — affects effective temperature (hot +2/+3/+4,
  cold -1/-2/-3), saps Social in humid air, flooding adds +1 Energy cost to movement.
- **`effective_temperature`** now accepts `wind_level` + `humidity` kwargs (backward-compatible).
- **Trigger effects** (task-234): `set_time`, `set_date`, `set_weather`, `forecast_override`,
  `adjust_forecast`. `set_environment`/`adjust_environment` extended with `weather`, `wind`,
  `humidity`, `transparent` keys + cycling. New trigger types: `on_turn_start`, `on_turn_end`,
  `on_dawn`, `on_dusk`, `on_day`, `on_night`, `on_full_moon`, `on_blood_moon` (one-shot per
  game-day via last-fired cache). New conditions: `date_equals`, `moon_phase_equals`, `weather`.
- **Settings**: `GET/POST /api/settings/forecast`, `POST /api/settings/forecast-override`,
  `/api/state` exposes `game_day/month/year`, `moon_phase`, `forecast_schedule`, `forecast_override`.
- **Engine Config**: `forecast.apply_scope` (exterior/all), `heat.base_rate`/`heat.max_delta` now
  apply wind multiplier.

### 🌠 Sky Clock widget (GUI)

- **Top-bar live widget** (`static/js/sky-scape.js`): `🕐 09:40 · Jan Day 1 · 🌑 new moon · ☀️ clear
  · rain in 2h` — replaces the bare `#ui-time` clock. Driven by engine state, clickable → opens the
  **World Sky panel**.
- **World Sky panel** (modal): animated sky stage (gradient, sun arc, moon arc with v2 realistic
  moonrise/set, seasonal hill colors, weather layers with clouds/rain/snow/fog). Time skips
  (+15m/+1h/+1 day), weather override dropdown + duration + Set/Clear, forecast next-change
  indicator, GM override indicator. Ported from the qwen/GLM mockups and wired to engine APIs.
- **Design note** reconciling mockups + roadmap + implementation: `docs/design/sky-widget-reconciled.md`.

### ✨ NL Editor power-up (9 features)

- **Ghost-node canvas** — staged entities appear as translucent dashed nodes on the graph in real
  time; updates/deletes tint the live node amber/red; attach/detach get dashed ghost edges.
  Re-applies after every graph reload.
- **Auto-pan spotlight** — when a turn finishes with fresh staged ops, the camera gently pans to
  the newest staged target ("here's what I just drafted").
- **Selection-aware prompting** — the system prompt reports the currently-selected node as the
  default "this room/node"; `update_node`/`delete_node`/`get_node`/`spawn_library_item` auto-fill
  a missing id from the selection.
- **Inline staged property tweaker** — ✎ on any staged row → editable JSON payload, save/cancel.
- **Selective partial apply** — checkbox per op + **Apply Selected (n)**; unchecked ops stay staged.
- **`populate_area(area_id, theme)`** — one call stages a whole themed pass: 9 theme packs
  (apothecary, kitchen, garden, study, smithy, warehouse, shrine, bedroom, generic), each with an
  NPC, items, attachments, and area ambience.
- **Smart mechanic inference** — glowing crystal → `light_source`/`dim`/`lit`; roast chicken →
  `eat` action; plus sound/heat/weapon/armor/read/drink rules — all automatic from the name.
- **Lore & style awareness** — system prompt injects scenario name, theme, up to 6 world-lore
  entries, and the selection; rule 6 enforces style consistency.
- **`>` palette route** — Ctrl+K → `> make the tavern darker and add a violin` → Enter → NL Editor
  opens, input filled, agent runs in the background.

### 🛠 Fixes

- **`POST /api/graph/batch`** — NL Editor's Apply now sends all staged ops as one server-side
  batch, recording exactly ONE undo snapshot. A single Undo reverts an entire Apply. (Previously
  each per-op API call pushed its own snapshot, and several op types hit wrong routes giving 405 or
  silent no-ops.)
- **`update_node` flat patch** — the agent hands `{description: "..."}` and the PATCH route now
  accepts it (was silently ignored).
- **`link_to_library`** — `template_id` now correctly lands in `properties`.
- **`connect_areas`** — connection edges now carry `direction` + `visible_in_direction` props so
  exits actually resolve.
- **`search_library_areas`** — now searches `description` too (matching the items search).

### 🧰 Gotchas in this release

- **Restart your server** (`start.bat`) — the running process needs to pick up the new engine code
  (calendar, forecast, moon, wind, humidity, trigger effects, routes).
- Weather forecast scenarios: **zero authored entries = no behavioral change** — existing scenarios
  are unaffected. To use weather, author a forecast schedule via `/api/settings/forecast` or set
  a GM override via `/api/settings/forecast-override`.
- Moon/turn/time triggers fire only on nodes with attached trigger nodes of the matching type.
- The Sky widget's time skips (+15m/+1h/+1 day) adjust the clock display but do NOT run engine
  ticks — they're visual helpers. Use `/api/turn/apply` for actual world-time advancement.
- `wind_resistance`/`water_resistance` are item properties set via the inspector or library; no
  library items have them yet. They work as soon as set.
- The after-request hook's post-state snapshot push for simple graph edits (PATCH `/api/graph/node/`)
  still makes the first Undo a no-op — the batch endpoint is exempt but the per-edit quirk remains.

### 🧪 Behind the scenes

- New test file: `tests/test_graph_batch.py` (6 tests), `tests/test_engine_config.py` baseline
  updated for `forecast.apply_scope`.
- Task vault: 227/228/229/231/232/234/378/379/387 — all implemented in this session.
- Full suite at **2633 passing**.

---

## 1.2.0 — "Craft & Carry" (2026-08-31)

Items stopped being cardboard props. Uses, durability, weight, freshness, stacking, crafting,
teaching, auto-dressing, gated shortcuts — and a pile of the item/gameplay todo queue landed in
one pass, tested with **2615 passing**.

### 🧰 Items grew up

- **`max_uses` + weight reconciliation**: a half-eaten loaf weighs what's left
  (`base_weight × uses/max_uses`); infinite-use items stay static; `combine` merges two
  identical stacks (uses summed, clamped at max, source destroyed), `split <item>` divides one
  into parts — capacity re-checked, "stackable twins" ignore the auto-renamed copy suffix.
- **Armor & equipment wear on hit**: outermost armor/clothing decrements uses; at 0 it breaks —
  back to carrying + `on_break` trigger. **No raw numbers anywhere**: prompts read
  `[pristine/worn/battered/about to break/broken]`, the HTC chips and paperdoll modal show
  plain words, the item inspector has a durability bar.
- **`on_use_progressive`** trigger type — fires on every use; gate thresholds with the existing
  `uses_reached`/`uses_above` conditions.
- **Freshness**: `perishable` food decays per tick → `spoiled` (fires `on_spoil`), cooking —
  use fresh food on an oven/stove/heat source → `cooked`, decay halts. Examine and prompts say
  it in plain words: `(fresh)`, `(cooked)`, `(spoiled)`.

### 🗺 Gated paths & movement

- **`requires_item` on ways** — a bike lane needs a bike, a fly path needs an item tagged `fly`:
  visible-but-blocked without the gear, open with it. Prompt exit lines show `(needs: bike)`.
- **Over-encumbrance = one size larger**: ≥50% load bumps your effective size tier — narrow
  passages stop fitting.
- **Chain follow-ups (task-104)**: the dash→go chain generalized — `lead` → go/approach/
  release, `grab` → approach/release. One same-turn follow-up, agent-decided.

### ⚒ Crafting & knowledge

- **Full recipe system**: recipe graph nodes + `engine/crafting.py` — inputs (consumed or not),
  conditions (`state_equals`/`has_item`/`random_chance`/`skill_check`), outputs hydrated from the
  library, learning via `global` / `skill:<name>` / `item:<name>` / discover-on-first-craft,
  persisted `crafting_known`. Commands: `craft`/`make`. 🧪 Recipes panel in the agent inspector.
- **`teach <recipe | skill:NAME> to <character>`** — teacher must know it, student must be
  present; recipes transfer, skills +1.
- **`use N items on target`** — structured `amount` on use_on (`use 2 eggs on pan`) validates
  against tracked uses and consumes N; prompt shows the syntax.

### 🧍 Characters dress themselves

- **🤖 Auto-Dress from Interests** (Inventory tab): scans the item library for wearable pieces
  matching `interest_tags`, equips through the normal stacking rules, weather-aware
  (hot → skips heavy insulation, cold → wants it), idempotent by construction.
- **✨ Generate from Personality** (Bio tab): the character's LLM gets the full system tag list
  and answers with JSON/CSV tags → sets `interest_tags` in one click.
- **🌊 Simultaneous Mode (experimental)** — every autonomous character acts on its own
  countdown derived from Social/traits/Energy (high-Social acts more, exhausted slower).
  Chaos by design; sequential mode untouched; off by default.

### 👁 Senses & health

- **`scry` effect**: a frozen distant-area view (rendered description + ambient light + exits) —
  the shared observer path is untouched. Editor entry with area picker + lead-in/fail text.
- **`proximity_effect` items** (EMF-style): BFS room-distance readings on examine — sharp when
  they're right here, needle-jumps adjacent, faint blip beyond, prose only.
- **Context-aware vitals**: isolated-wording only when you're actually alone and quiet; company,
  addressed-to-you, noisy rooms, and visible food/drink all change the lines. Sanity is now a
  neutral stress curve — no more "the shadows seem to watch you" in a bright Taco Bell.
- **Encumbrance in the prompt + HTC** — natural language ("at the edge of your capacity"),
  never numbers.

### 💬 Input & feedback

- **Invalid-action auto-retry** (setting, off by default): one same-turn retry with the error
  fed back for rejected and engine-failed actions.
- **Appearance grammar guardrail**: third-person directives + few-shots, validator catching
  `you is`/`body is who` leaks, one silent repair pass, safe fallback — broken text never
  persists (it re-sends into every prompt forever).
- **Carried/worn prompt lines**: full untruncated description + allowed actions +
  (known / not yet examined) + durability + freshness.
- **Gear totals strip** in the Inventory: armor / best weapon / insulation / resistances as
  pills with "from: …" contributor tooltips — one place, no per-item duplication, same
  aggregation rules as the engine.

### 🧪 Trigger-effect templates

- **42 library items** — `template_<effect>` (e.g. `Template: Scry`), each with a wired
  `on_use` trigger demonstrating that effect; generator at `tools/gen_effect_templates.py`
  (re-run after new effect types, a coverage test guards it) + index in
  `docs/virtualWorld/Templates/trigger-effect-template-items.md`. Scenario-ending/room-spawning
  ones are loudly flagged ⚠️.

### 🎓 Help, tips & guided tours

- **❓ Help Center** (top bar or **F1**): a coach-tip system that fires *when you touch the
  thing* — welcome tip on first load, inspector tips per view type (area/item/way/agent),
  button-triggered tips for Settings, the Game menu, Overlays ▾, More ▾, Triggers, ▶ run,
  auto-dress, crafting, and a ⚠️ warning when Simultaneous Mode flips on.
- **Spotlights**: "Show me" physically highlights the UI element the tip describes (the card
  stays put; ESC/✕ clears).
- **Guided tours**: *First five minutes*, *Triggers & effects*, *Scenario workflow* — ordered
  chains with Next steps.
- **State**: tips remember themselves (localStorage per-id) with session re-shows; the index
  lists every tip with one-click replay and Reset all. No second system — tips point at the
  real UI, and the registry is one easy-to-extend array.

### 🛠 Fixes

- **⋯ More ▾ and Overlays ▾ dropdowns** were opening *invisibly* — the toolbar's
  `overflow-y:hidden` clipped them; now visible.
- **`take` puts everything in a hand first** (generic held; hands full → one item auto-stowed
  to carrying, then pick up, same turn; `two_handed` needs both hands; intrinsic abilities skip
  to carrying). New **`stow`** verb.
- **Saved worlds are graph-only** — no more redundant per-room `exits`/`exits_authoring` in
  scenario files (runtime `/api/state` payload still computes exits live).

### 🧰 Gotchas in this release

- **Restart your server** (`start.bat`) — engine + route changes need the fresh process; static
  JS/UI is reload-only.
- The **mature-tags → inspection reveal** discussion stays open: newer item mechanics
  (freshness/proximity/max_uses) aren't yet wired into the tag-reveal pattern in the item
  inspector — say the word and they get the same treatment.

---

## 1.1.0 — "The World Is Yours" (2026-08-30)

The big one: authoring stops fighting you. Everything below shipped in one working session, tested with 2500+ automated tests.

### 🌍 Scenario workflows — no more losing work

- **Scenario status chip** (top bar): `📦 <scenario> ●` lights up the moment the live world drifts from its source, with **💾 Commit** and **🌀 Restart** right there. Commit writes your live world into the scenario source so Restart keeps your changes — the old "I built it and the restart ate it" trap is dead.
- **Honest Save menu**: `💾 Commit Scenario` (server-side, updates the source you're working on) vs `📤 Export Scenario File…` (download), no more pretending a download saved your scenario.
- **Import preview**: before `Load JSON…` touches your world you see rooms/items/ways/characters, format, and sanity notes (dangling exits, players in missing rooms) — then **Apply (Undo protects)** or **Cancel**.
- **🔬 Deep audit** (import preview + Scenario Manager): the full trigger validator runs against a file *before* you load it — "3 errors · 2 warnings · 4 info" with the top issues.
- **🗂 Scenario Manager**: every `data/scenarios/*` file listed with stats — Open (undo-protected), Audit, Copy, Rename, Delete, Refresh.
- **Changes-since-source diff** endpoint: structural diff (rooms/players/env/exits) between live world and source — the backend for reviewable commit/discard.
- **Restart stays undo-safe**; undo now shows **labels** via the visible **📜 history dropdown**.

### ⚡ Authoring speed

- **Ctrl+K command palette**: type `kitchen`, jump to it. Type `save`, run it. Nodes, system actions, panel tabs — one fuzzy search.
- **🧩 Trigger snippets**: one click fills an entire trigger — Chest, Light Source, Heat Source, Recorder (captures recent speech!), First Aid, Book, Whispering Door.
- **Spawn item** editor fields for **Place into (area/container)** and **Capture recent speech** — the recorder/chest recipes survive saving.
- **📋 Duplicate room** (with items, contents, triggers — `"Kitchen (2)"`) and **duplicate item** (`"Lantern (copy)"`, placement preserved).
- **🕘 Recently-edited rail**: last 10 nodes you touched, click to jump back.
- **Keyboard map**: **Ctrl+S** commit, **Ctrl+Z / Ctrl+Shift+Z** undo/redo (typing-safe).

### 🧲 Trigger system — way more toys

- **New effect types**: `spawn_way` (runtime doors, one-way supported), `spawn_area` (runtime rooms), `set_way_target` (portals/elevators — repoint a door at runtime), `set_way_view` (see-through / view text).
- **New condition**: `item_relationship` ("does this item have anything inside?" by edge type, with target filter).
- **New template params**: `{uses}`, `{weight}`, `{current_state}`, `{name}` and **`{vital:Thirst}`** readouts in messages.
- **Result**: recorded during authoring — the spread of "flavor" engines you can build with effect-composition is dramatically wider.

### 🩺 Conditions — six new ways to be in danger

- **wet** — soaked clothing keeps only 20–60% of its insulation (levels 1–3).
- **injured** / **bleeding** — body-part wounds, level-scaled HP drain, ends on fix/bandage/medicine.
- **hypothermia** — level-scaled Energy/HP drain, dexterity auto-fails, staged symptoms (shuddering → shaking → warm and sleepy).
- **suffocating** — blocks actions + movement, drains, staged symptoms, ends on breathe.
- **petrified** — stone: blocks everything, +5 defense, STR/DEX/CON saves auto-fail.
- All six live in the data-driven condition library — **browser-editable**, like every other condition.

### 🗺 World creation

- **✨ Scenario from Text**: one premise sentence → AI drafts rooms, doors, items, characters, lore → review cards (accept per room, regenerate a room, prune items) → apply, undo-safe. TemplateLoader now carries item tags + light/heat props and a supporting `characters` cast.
- **Save/Load modal**: autosave slot (pinned AUTO), per-save stats (time/turn/player/room counts/size), overwrite-in-place, rename, delete, and **app version** stamped on every save.

### 🛠 Fixes & honesty

- **Temperature rounding**: no more `-10.452438125°C` anywhere — stored and displayed at 0.1°.
- **Honest defaults**: the Light Level field says "— unset (engine uses Dim) —" instead of pretending; heat-source inputs show real placeholders; Issues panel gets an **⚙ quick-fix** and info-level notes for defaulted mechanics (light/heat) instead of false broken-tag warnings.
- **`go to the doorway` now walks you up to the door and stops** — crossing is explicit (`go through`, `go <room>`, `dash`); new **`approach`** verb everywhere (MCP + prompts + GUI).
- **Character knowledge** moved into a proper modal (Advanced tab → Knowledge): category tabs, search, bulk select, stale-ref cleanup — and the per-entity "Known by" panels removed from items/areas/ways.

### 🧰 Gotchas in this release

- **Restart your server** (`start.bat`) — the running process needs to pick up the new engine code.
- `give`/`steal` item matching is still strict (bug-35 filed — typos like `jumptuit` fail); take/equip no-op wording is being reworked (bug-25 reopened).
- `llm_respond` (trigger-driven chat) is **blocked** — the engine has no LLM provider; needs a host-side decision.

### 🧪 Behind the scenes

- New test files: `test_template_loader`, `test_trigger_effect_ways` (12), `test_more_conditions` (11), `test_scenario_commit` (5), `test_undo_history` (5), `test_duplicate` (4), `test_scenarios` (7), `test_scenario_diff` (4) + validator tests — suite at **2507 passing**.
- Task vault restructured: 20 new tasks (367–386) from the workflow audit; duplicate numbers resolved; sequence doc accurate.
