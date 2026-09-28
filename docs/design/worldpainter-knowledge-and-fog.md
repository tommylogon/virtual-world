# WorldPainter grids, belief-based travel, and fog of war

**Status:** design note (target architecture; pieces land across task-495/496/
498/499/500, task-467, task-403, task-411/418)
**Related:** `docs/design/world-environment-taxonomy.md` (the tile vocabulary),
`docs/design/long-horizon-simulation-progress.md` (fidelity tiers),
`docs/design/reversibility-contract.md`

## The insight

Once WorldPainter has **filled the world grid**, the grid is not just an
authoring surface — it is the spatial substrate the runtime reasons over:

1. A **target location** or a **path** can be attached to an item or a character
   by a **trigger** (a map names a place; a note names a road; a rumour names a
   direction).
2. The character **moves by selecting grid cells/edges**, so its route is a walk
   over the painted lattice rather than a hand-authored chain of rooms.
3. As the character walks, it **reveals fog of war** — the known set grows cell
   by cell, and that known set is what the map view draws and what the agent's
   prompt is allowed to contain.

So the grid is simultaneously the authoring model (task-495/496), the movement
model (task-467), and the knowledge/perception model (task-499). That is the
unifying claim this note fixes.

## Pipeline

```
WorldPainter painted grid (task-495)          engine/world_grid.py
        │  compile cells → areas + ways
        ▼
grid→graph compiler (task-496)                engine/world_compile.py
        │  emits GenerationPatch via task-398 contract  engine/generation.py
        │
        ├── areas carry: biome tags (engine/biomes.py, task-497), environment,
        │   floor (storey index: 0 ground, +1 up, -1 down, unbounded),
        │   surface (ground material), world_scope_id, grid cell coordinate
        │   (stable frame)
        │
        ▼
runtime graph
        ├── movement: a target/path from an item/character trigger resolves to
        │   grid cells/edges and the character walks them (task-467)
        ├── travel duration: hop count × TASK_MINUTES["travel"] (already done)
        └── reveal: each visited cell is added to the character's known set
                (task-499), reusing player.known + the existing teach path
```

## Contract details

- **Stable frames.** A cell's identity survives feature moves (task-495
  acceptance). The compiler must map a cell to a stable area id so a save made
  before a feature moved still resolves; moves never silently reassign a cell to
  a different biome.
- **Grid-canonical vs baked-and-hand-edited.** **Decided 2026-09-24 (task-496):
  per-zone `paint_policy`, canonical by default, baked opt-in.** A canonical
  zone may be re-compiled through `apply_patch(allow_regenerate=True)`, but a
  re-run is rejected by default so an edit made after baking is never silently
  overwritten; a baked zone compiles once and is hand-authored thereafter. The
  clobber trap (task-289/290/317) applies: a manual edit made after baking must
  not be silently overwritten by a re-compile.
- **Belief, not omniscience (task-467).** A destination held as a *belief* is
  `heading + budget` ("go west 2h"), not a node id. Arrival validates the belief
  (found / found-not-there). A map or directions teach a *known* entry through
  the existing teach path, which upgrades a belief into a known route. Generation
  at the frontier (task-398/task-9) resolves whatever lies that way.
- **Perception stays honest (task-499).** Unknown cells/zones are fog on the map
  view; an unaware agent is not told about unknown areas. This reuses the
  viewer-aware room perception already in `engine/room_perception.py` and
  `player.known` (tests/test_known.py); `EDGE_KNOWN` remains abilities-only.
- **Fidelity tiers (task-411/418).** Attendance is not a hop-count fiction: the
  attended set derives from awareness channels (sound, co-presence, recency,
  hooks). Fog of war is the *knowledge* dimension; attendance is the *simulation*
  dimension — both read the same grid but neither is the other.

## Scope hierarchy: root then zone

A scope with no `parent_id` **is** a root (`engine/world_scopes.root_scope_ids`);
there is no special root record. The literal id `"root"` is only a projection
alias meaning "list the top-level scopes" (`world_scopes.project`), so it must
never be stored as a scope id.

The authoring sequence is therefore:

1. Create the world **root** scope with no parent
   (`POST /api/world/scopes {name, w, h, mode:"world"}`).
2. Create a **zone** with `parent_id` set to an **existing** scope
   (`{name, w, h, parent_id:"<root id>", mode:"town"}`). `handle_create_scope`
   rejects an unknown parent (`Parent scope '<id>' not found`); the child id is
   appended to the parent's `children`. The **id** is disambiguated on collision,
   the **display name** is never renamed.
3. Paint/place on either grid. Placing a feature records `child_scope_id` on the
   parent cell (`world_compile`), and drilling in opens the child's own grid in
   the next mode (`grid-model.nextMode`: world → town → interior).

**Generation is per scope.** Generating a parent compiles only the parent's own
painted grid; the child's grid is **not** compiled as a side effect, so generate
the zone separately. Keep the root coarse — at world scale a town is a single
cell — and put the detail in the child grid, so no level mints thousands of area
nodes at once (the node-count blow-up that freezes the graph view, task-400).

**Linking a zone to its cell (task-496).** Once *both* a parent and a placed
child are materialized, the compiler emits one gateway `way`
(`way_gateway_<parent>_<child>`) between the parent's compiled cell area and the
child's entry area. Entering uses the `in` direction, leaving uses `out`, so the
two levels are one continuous walk without cascading generation. The gateway is
emitted by whichever scope compiles second, so either authoring order links
exactly once; a placement on an unpainted cell links nothing.

**Painted positions.** Generated nodes carry `properties.x`/`y` from their cell
(`cell * CELL_CANVAS_UNITS`, ways at the midpoint), so the graph view with
physics off lays a compiled scope out in the shape it was painted — the point of
painting over a reference map. This is layout only: travel stays one turn per
cell.

**Aligning the reference art.** The graph background has its own transform, so
right-click empty canvas → **▦ Fit to painted grid** pulls in the selected
scope's painter reference (if the graph has no map yet) and fits it to the whole
painted grid rect, then fits the view. The rect uses the Map layout's spacing —
`GraphLayoutEngine.mapSpacing()` px per cell (default 40), offset half a cell so
cell (0,0) is the origin — because that is where the Map layout puts the nodes.
It fits the *full* grid, not the bounds of the painted cells: the painter fits
the reference into the full grid, so fitting a partial paint would rescale the
art and break the cell alignment.

**Reference move/resize/crop (task-524).** The painter reference stores an
optional `rect` in **cell** units plus a normalized `crop` window; `null` means
auto-fit. Storing cells (not pixels) is what lets the painter (22px/cell) and the
graph map layout (`mapSpacing` px/cell) draw the same picture at their own scale
and still agree. Corner handles scale the whole image (crop unchanged); edge
handles cut it (the source window shrinks proportionally, so content keeps its
scale). Pure geometry — `fitReferenceRect`, `referenceHandlePoints`,
`referenceHandleDrag` — lives in `static/js/worldpainter/grid-model.js` and is
unit-tested.

**Map layout is relative, not absolute.** Stored coords are engine units
(`cell * 40`), but Map mode never uses them raw: it reads the cell *lattice* and
applies a **spacing margin** (`mapSpacing()`, default 40px, override with
`config.graphMapSpacing`). 40px/cell means an area every 40px with the way at the
20px midpoint. The old 3.5× scale (140px/cell) made a 200×133 world ~28,000px
wide and unreadable; spacing keeps the painted topology at a usable density. The
toolbar's **spacing − / +** control (next to `🗺️ Map`) edits
`config.graphMapSpacing` live and re-lays the grid + re-fits the art at the new
pitch — the padding knob for a dense painted map.

**Ungenerate keeps the grid (task-496 follow-up).** `⚙ Generate` writes the
zone's areas/ways; **🧹 Ungenerate** deletes exactly those nodes (provenance
`generated.scope_id`, plus any parent gateway whose `child_scope_id` is the zone)
and resets the scope to `unmade`, keeping the painted grid, reference, map offset
and placements — a clean slate without repainting. A plain re-run
(`allow_regenerate`) now re-stamps existing nodes in place, but it never removes
orphans the new recipe no longer emits; ungenerate is the way to drop those.

**Dense maps hide labels at overview zoom.** Node names are drawn by a zoom-level
policy (`graphManager._showNodeLabels` + `graphLabelMaxNodes`/`graphLabelMinScale`
in `GraphNetwork._nodeLabelPolicy`): above ~400 nodes the names hide until the
view is zoomed past ~0.6 scale, so a 1k-cell map shows topology, not a wall of
text. The toolbar **🔤 Names** button forces them on/off.

**Moving a whole zone (task-523).** Each scope stores an optional `map_offset`
in **cell** units (absent = `(0,0)`, i.e. the painted position). The Map layout
adds the offset of **each node's own scope** (`world_scope_id`, or
`generated.scope_id` for a gateway) to its painted coords, so in the
whole-world/descendant view every zone sits where its author put it. The offset
is authoritative on the scope record and persisted with the scenario; the
painter's cell coords are never rewritten, because a paint edit must not shift
the world under it. In Map mode with a painted scope selected, right-click empty
canvas → **✥ Move zone** drags the whole zone: nodes re-place live
(`GraphLayoutEngine.refreshGridLayout`, no camera refit) and the active map art
is nudged with it; releasing persists the offset via
`POST /api/world/scopes/<id>/offset` (`{x, y}` cells, or `{reset: true}`).
Moving a zone moves **only that scope's own lattice** — a child keeps its own
offset (the level-scoped model: a placed child is one feature cell, and its
interior is authored separately). `▦ Fit to painted grid` fits the reference to
the *offset* grid, so the art follows the moved zone.

**Map mode reads the grid (not the compass).** `applyCardinalLayout` prefers the
painted lattice whenever the loaded nodes carry `properties.cell`
(`hasPaintedGrid`); the compass BFS is only the fallback for hand-authored worlds
with no painted coords. A painted map is *read*, so physics stays off — the
loader must not re-enable it after a grid layout (it used to, which dragged the
lattice into a force blob).

**Map layout reads the grid (task-496 follow-up).** The `🗺️ Map` layout has two
modes: when the loaded areas carry `properties.cell` (i.e. they were painted),
it places areas and ways at those exact coordinates and leaves physics off —
the map is *read*, not simulated. Hand-authored worlds with no painted coords
fall back to the original cardinal BFS over exits + a force settle. So "Map"
means "as painted" for painted worlds, and "as best derived" otherwise.

## Why not a second state model

The same `world_scopes` hierarchy (task-397) backs the editor grid, the runtime
projection, and the known set. A cell is a scope at the finest painted
resolution; a zone is a scope grouping cells. Movement, reveal, and generation
all address scopes, so there is one addressing model, not three.

One consequence worth stating: because a scope is the load boundary, the graph
view can load **one scope's subgraph** (`world_scopes.project_subgraph`, giving
the areas, interior ways, and present characters/items of that scope only)
instead of the whole world. That is what keeps a densely painted world from
freezing the canvas — the browser is never sent nodes outside the selected
scope, so the node count is per zone, not per world.

## Description and direction model (2026-09-26)

Locked with the author; **implemented in `engine/world_compile.py` (2026-09-27)**.

- **Every painted cell is a place, roads included.** A road cell *replaces* its
  biome — one node per cell, the biome is description *context*, not a second
  area. A road-only cell now compiles instead of being dropped by
  `cells = sorted(biome_of)`.
- **The road is the cell's identity, not a coat of paint.** Region merging groups
  by `road:<value>` when a road is painted and `biome:<value>` otherwise, so a run
  of road merges into one road area while a road cell beside forest stays its own
  place. The WorldPainter's "≈ N areas" estimate (`grid-model.estimateCompile`)
  groups the same way, so the header matches what Generate mints.
- **A description composes the place's character** from its neighbours and
  storey step, it does not just list them: "a road along the forest line" (woods
  to the north), "a road in the woods" (woods both sides), "a narrow path, the
  rockface rising on one side and dropping away on the other" (cliff neighbours,
  read from the floor layer). It may look one hop further to say where a road
  *leads* ("the road west leads back into the sparse woods"). Deterministic, no
  LLM — the fragment catalogue is the hook.
- **A neighbour is named for what its place is.** Where a cell carries both a road
  and a biome, the prose neighbour line uses the road, because the neighbouring
  *place* is a road area; a biome cell beside a road instead gets "A track runs
  through it." rather than the road being named as a biome.
- **Directions: compass outdoors, narrative on feature entry.** Exterior
  cell-to-cell moves stay `north/south/east/west` (+ diagonals). Entering a
  **feature** uses a narrative phrase (`enter`, `enter the mine`,
  `climb up the rockface`, existing `in`/`out`) carried by the edge, sourced from
  the feature/placement rather than hardcoded. Movement already resolves by the
  direction string, so the vocabulary widens with **no engine change**. Every
  phrase also carries `aliases: ["in", "out"]`, so `go in` / `go out` keep
  working.
- **A floor is a storey index, not a floor material** (corrected with the author,
  2026-09-27). `properties.floor` is *which storey* the place is on: `0` is the
  ground plane, `1` one up, `-1` one down, and the scale is **unbounded** — three
  rooms stacked over each other, the space around a spaceship, the bottom of a
  lake at `-2`, an 80-storey tower, a hole to hell at `-900`. It is rounded to a
  whole storey because the engine compares whole storeys, not heights. What you
  *stand on* — dirt, grass, stone, pine needles — is a different fact and lands
  on `properties.surface`, read from the biome/road record
  (`engine.biomes.ground_surface`).
  The earlier revision of this design called the WorldPainter's third paint layer
  `elevation`, held a 0..1 *height fraction* in it, wrote that to a separate
  `properties.elevation`, and put the material on `floor`. None of that is
  wanted. The layer is now `floor`, the material is `surface`, and
  `properties.elevation` is gone.
- **Floors inform prose now, gate movement later.** The floor layer feeds the
  cliff phrasing (`CLIFF_FLOOR_DELTA = 2` storeys by default, and only for a
  `world` scope — a storey step inside a town or interior is a staircase, not a
  rockface); a step past ~3 storeys requiring a climb (and potentially blocking
  the step) is deferred to **task-525**.

## Membership, placement, and reading a cell (2026-09-27)

Three things the author asked for, and the distinction that makes them coherent:

- **Membership ≠ placement.** `world_scope_id` on an area node *is* scope
  membership — the scope views read nothing else — and it is edited **on the
  node**: the area inspector has a **🗺️ Scope** section with a dropdown of every
  scope, so a child scope's whole interior can be moved into it in one go
  (`POST /api/world/scopes/<id>/areas` with `{add, remove}` lists, one undo step,
  both ends of the manifest mirror moved together). A cell on a painted grid is
  *placement*, which stays with the 📍 Area tool. That is why the goblin camp's
  rooms belong to the camp without being parked as cells on the world's grid —
  which is also why they stop showing up in the world scope's own view. Leaving a
  scope releases any cell the area held there; a cell it holds in the target
  scope is kept, so re-assigning an area to the scope it already sits on is a
  no-op. A **generated** area cannot be reassigned at all: it already owns a
  cell on the grid of the scope that generated it.
- **The place tool's picker is grouped by scope** (task-541): *On this grid*,
  *This scope, not placed*, and an explicit *Elsewhere in the world* group
  naming the other scope (picking one there is a membership change, not a
  placement). An area with no scope counts as this scope's. The payload already
  carried each candidate's `scope_id`/`scope_name`; it just was not used.
- **Every cell can be read** (task-540): hovering the grid shows the cell's paint
  layers, its placed area and its sub-zone in the HUD; the 🔍 Inspect tool — or a
  right-click on *any* tool — opens a panel with the same facts plus the actions
  that apply to that cell (move/unplace the area, open the area in the graph,
  open or remove the sub-zone, clear the paint). A placed area on a 200×133 map
  is a ~5px marker with no name, so this was the only way to tell what was where.

Noted gap: `world_scopes.project()` (the scope *summary card*) lists
`boundary_ways` only, so an interior's internal doors are missing from that card.
The graph view is fine — `project_subgraph` includes ways with both endpoints
inside. Whether the summary should list internal ways is still open.

## How a big painted map reads (task-526, 2026-09-27)

A compiled area draws as a card whose width is its **name** plus padding, and the
name does not shrink with the map pitch the way the padding does. So a single
global pitch could not serve both a 6×8 camp and a 200×133 world: at the old 40px
default the cards overlapped into a blob, and the only fix was dialling the
spacing control to ~200 by hand. Two halves:

- **Compact dots below `MAP_CARD_MIN_PITCH` (140px/cell).** An area becomes a
  `dot` sized from the *cell* (55% of the pitch, clamped 6–28px), so it always
  fits its own cell and stays visible when a whole world is zoomed out. Names are
  hidden while compact — through the **existing** label LOD, not a second
  mechanism — because a name is what does not fit. The tooltip, inspector, search
  and badges still name every place. 140 is where the clamped card box still fits
  its cell, so the switch happens exactly where the boxes stop colliding.
  Map layout only: the graph view and Levels have no lattice and no overlap.
- **Auto pitch from the painted extent.** `paintedExtent()` measures the drawn
  cells (areas only — ways sit on the lattice between them, and a hand-authored
  area has no cell), then `autoMapSpacing()` aims for `AUTO_SPAN_PX` (1600px)
  across the longest side, clamped to 24–300px, rounded to a tidy multiple.
  Nothing painted → no opinion, and the current pitch stands.

Two rules that are easy to get wrong here:

- **The pitch is decided before anything reads it.** Node sizes, the lattice and
  the background art are all derived from it, so `applyAutoMapSpacing()` runs at
  the top of `loadGraphData` and re-derives the art when the pitch moves. Deciding
  it after the layout is the bug-52 shape: two sources of truth for one position.
- **A layer's rect is in px, so a pitch change makes every picture stale** — and
  the ordinary per-scope reconcile cannot fix that in the whole-world view, which
  has no single grid. `reconcileAllForGapChange()` re-derives *every* mounted
  reference from **its own** scope's grid and offset, then reframes the camera
  (the old framing was computed for the old pitch). It writes nothing: it runs on
  a load path, so `fitToPaintedGrid` — which persists the fitted rect — is the
  wrong call there and stays reserved for a deliberate manual nudge.
- **Auto is the default; the stepper is the override, and it is visible.**
  Nudging the stepper persists `graphMapSpacingAuto=false`, so a person who wants
  40px/cell on a 200-cell world keeps it through reloads and scope switches. The
  stepper shows `80 auto` while derived, an `A` button hands the pitch back, and
  the menu says why the places are dots. Without the `auto` mark, a first nudge
  would silently look like adjusting a number the user had already chosen. And a
  *stored* pitch that differs from the built-in 40 default counts as a choice
  already made — someone who dialled the map to 260 by hand is not re-derived
  over on their next load.

On the goblin camp's real scopes this lands on dots everywhere (20×9 → 80px,
20×8 → 80px, 20×30 → 55px), which is the honest answer: a 20-cell-wide map at a
card pitch is 2800px of canvas, so no pitch shows the whole map *and* keeps the
cards from overlapping. Cards come back by raising the pitch a notch.

## Naming a cell, and what a town is made of (task-560, task-561, 2026-09-27)

Paining a settlement needs two things the wilderness did not, and both were
missing.

**A cell can have a name.** Without it every place is `<label> (<scope> x,y)`, so
a 19-location town is 19 coordinate names and `go inn` has nothing to match. A
name lives in a `names` map on the scope record — *beside* `layers`, not on one,
because a name is metadata **about** a cell rather than paint on it: there is no
name vocabulary, the eraser must not wipe it, and "clear this cell" must not
silently unname a place. The compiler prefers it for the display name and keeps
the fallback. Two rules that are easy to get wrong:

- A name repeated **inside one scope** falls back to the generated form, so no
  single area offers two exits with the same name — which is all `go <name>` needs,
  since `NameMatching.resolve_exit` collects the current area's exits first. Two
  *scopes* may reuse a name, exactly as two hand-authored areas may: ids are the
  key, names are labels resolved to it.
- A merged region takes a name from **any** of its cells, not just its anchor.
  Naming the middle of a High Street is the natural thing to do; making the author
  know that the anchor is the top-left-most cell would be a rule with no purpose.

**A cell can have a type.** Building types are **biomes**, not features — a
building is a *place*, while a feature is something painted on the road layer that
*replaces* the cell's biome. (The file had `town`/`village`/`building` as features,
which meant painting "building" produced a cell the compiler read as a *road*: a
house that merged with the street and described itself as a thoroughfare.) 31
types across nine categories, each carrying three tag families so a later task can
ask the question an author actually has: `building`+`settlement`, a category
(residential / religious / commercial / civic / craft / industrial / military /
rural / transport), and **purposes** — `sleeps`, `food`, `drink`, `hygiene`,
`trade`, `craft`, `worship`, `medical`, `storage`, `transport`. Those purpose tags
are what task-566 will ask for when a tired traveller looks for a bed.

Two consequences worth stating:

- **A building is exempt from the wild-country contract, deliberately.** The
  validator demands a forage tag and resource/hostile distribution for every
  biome; nobody forages berries off a smithy's wall and no wildlife spawns in a
  bank, so `biomes.validate` skips those checks for a record tagged `building`. It
  is a documented exemption, not an omission — a building is still a biome, and it
  still owes a name, a surface and description fragments.
- **`terrain: "urban"` is currently a no-op.** The prose classifier has classes for
  forest/rock/water/farm and falls through to `open`; a new class for buildings
  would apply to wilderness cells too, so that waits for a settlement register.

A town is then a bounded set of **named, typed** cells, and a district is a child
scope on a cell of it — the same mechanism a building's interior uses, one rung up
(the world already nests three deep). What is still missing is everything between
the cell and the door: edge semantics (task-562), entering a building (task-563)
and per-kind merging (task-564).

## What a cell is *to movement* (task-562, 2026-09-27)

A painted cell used to be either a place or nothing, which is enough for
wilderness and not enough for a floor plan. A Japanese high-school plan needs
blanks you cannot walk through, windows you can see through but not through, and
a door you can — and all three *occupy a cell* while not being places. So a biome
record may declare what its cell is to movement, and **the vocabulary decides**:
`engine.biomes.cell_kind` reads a `not_a_place` tag plus a namespaced
`cell_kind:` tag, and the compiler asks that rather than knowing that `wall` is
special. Adding a `hedge` or a `turnstile` later needs no code.

| value | kind | what it does |
|---|---|---|
| `wall` | `solid` | nothing passes it, nothing sees through it |
| `void` | `solid` | nothing there at all — a courtyard, a gap, an unwalkable hole |
| `window` | `see_through` | you can look through it; you cannot walk through it |
| `door` | `passable` | not a place, but a way may cross it |

Four rules, each of which is a decision rather than an implementation detail:

- **A wall works by occupying a cell.** The two rooms either side of it are no
  longer adjacent, so no way is minted — the wall *is* the absence of a route.
  A door occupies the same cell, so the route it stands for has to be built
  explicitly: it joins the two places on **opposite** sides, which is the only
  reading available (any three of four cardinal neighbours contain an opposite
  pair). A door with a place on one side only leads nowhere, and the report says
  so, because that is invisible in the node counts.
- **A passable cell between two *storeys* is a stairwell, not a door.** The storey
  is the stronger signal about what you do crossing it, and a "door" that quietly
  climbed a floor would be a lie in the pass message.
- **A window is not a route**, so it mints no way; the place it faces records it in
  `properties.windows`, so the description can say there is a window in that wall.
  A window with a place on two sides is a passage in disguise — that is a door —
  and one with none is a window onto nothing, which is still a window.
- **The storey is part of a region's identity.** Merging is 8-neighbour and was
  storey-blind, so a classroom above a classroom of the same kind became one place
  with a staircase inside it. A region is one storey's worth of one thing.

Every way now carries `kind` (`open` / `door` / `stairs` / `entrance`) and
`floor_step`, the number of storeys the edge crosses — so task-525's gate and
task-563's `in` have a value to read rather than to re-derive. **A sealed room is
still rescued** by `link_islands`, which is a deliberate reachability guarantee
rather than something the author painted; making a sealed room genuinely
unreachable belongs with task-525 and task-564, not here.

## Entering a building (task-563)

A building cell is a place you go **into**, not a cell you step sideways onto.
Standing in the street, `in` enters the inn; you do not first walk east onto the
doorstep and then go in. The building-ness comes from the vocabulary again — a
`building` tag on the biome record (`engine.biomes.is_building`) — so a modder's
`watermill` is a building without a line of compiler changes.

**Where the doors are.** One `in` way per **cardinal** side that already has a
way. Cardinal, because a door is on a wall and a diagonal neighbour is a corner
of the plot. "Already has a way" is read from the pairs the compiler actually
connected, not from adjacency, so a side sealed by a wall gets no door and a
side reached *through* a painted doorway does — the doorway is what connected the
pair.

**Where the `in` leads.**

| the cell has | the way | state | `out` from the other side |
|---|---|---|---|
| an interior (a materialized child scope) | to the interior's entry area | `open` | the doorstep, via the child gateway |
| no interior | to the building's own cell — the plot | `closed` + `refusal_message` | n/a: the plot's exits are compass |

The interior case is **one-way on purpose**. Inside, `out` has to keep meaning
one thing, or the word is ambiguous; so coming out of the inn lands you on the
doorstep cell, and the adjacent temple is one turn from there. That is also what
makes `dash_to_area`'s chained second hop work.

The shut door is one-way for a sharper reason. The street already has a compass
way onto the plot, so a way *back* would be a second connection for the same pair
— and two ways both answering to `out` on the plot means a bare "out" picks one
at random. That is not hypothetical: it is what the first version did, and
walking in through the street door and typing "out" got you shut out by the
alley door you had not used. One way in; the plot keeps its compass exits and says
so plainly (`Visible exits: west, east`).

A building with no interior is not a hole in the world — it is a building that
owes an interior, and it says so: the way is `closed` and carries a
`refusal_message` drawn from the building's category (a watch house is barred, an
inn is shut, a smithy's bench is cold). `refusal_message` is a **way property
the movement system honours**: it raises that line instead of walking through,
and it holds until the way's state is `open`, which is exactly what a knock, a
key, or an author painting the interior does. A `closed` way without the property
keeps the pre-existing behaviour of being pushed through on approach, so nothing
else in the game changed.

**Both compile orders work.** The parent records its door sides on the placement
(`placements[id].sides`) and mints the ways when the interior is already
materialized; the interior mints them from those sides when it compiles *after*
the parent, which is the common flow (generate the town, then draw the inside).
The ways carry `child_scope_id`, so ungenerating the interior removes them with it
even though their provenance names the parent.

The editor knows all of this before anything is generated: the vocabulary payload
carries each building's `refusal`, and the cell inspector's `enter` row shows
`in → The Inn` or `in → The inn's door is shut.` — from the same
`world_compile.building_refusal` the compiler uses, so the preview cannot drift
from the world.

## Telling the author what to do (task-521, 2026-09-28)

The compiler always knew which scopes it would refuse. It said so only *after* the
author pressed **⚙ Generate**, and what it said was a rule rather than a remedy. The
two refusals that actually cost an author a session were:

- **`paint_policy: "baked"`.** A scope made with **🪜 Make this a scope…** is
  promoted from areas the author had already written, so it is *authored* rather
  than painted and carries no paint at all. It fails with a sentence that explains
  neither how it got that way nor how to get out of it — and `paint_policy` was
  not in the grid payload, so the editor could not show it either. The only place
  the field was readable was the save file.
- **A placement on an unpainted parent cell.** The scope sits on world cell (17,3)
  and the parent's paint has a gap there, so `_gateway` skips it
  (`world_compile.py`, the placement loop) and **no gateway is ever minted**. No
  error, no warning, no report line — the scope is simply unreachable, forever.

So there are three distinct layers of guidance, and only the first was ever filed:

### 1. Preflight — the refusals, as advice

`engine.world_compile.preflight(manifest, scope_id)` returns
`[{code, severity, text, remedy}]`, and `_grid_payload` ships it as `blockers`. The
editor renders it beside **⚙ Generate** and puts the blocked conditions in the
button's own tooltip, so the reason is never more than one hover away.

**`block` is a condition `compile_grid` refuses; `warn` is advice.** The two must
not drift, and `test_preflight_and_the_compiler_refuse_the_same_baked_scope` holds
the seam. A `block` may also be a condition the compiler *starts* refusing once the
author carries out the remedy — the un-painted-placement case is that kind: it is
not refused at all, it is silently ineffective.

The area count in the `node-cap` warning reuses `_regions` rather than counting
painted cells, so it agrees with what Generate mints under the scope's merge switch
and the per-kind merge rules; a painted-cell count reads ~4× high on a merged street
and cries wolf about a map that is fine.

The `unnamed` warning fires for `town`/`interior` scopes, or for any scope with at
least one name already. A wilderness cell compiling to `Sparse Forest (world 7,4)`
is named correctly and is not nagged; a *half*-named world map still is.

`entry-corner` is the one that is advice rather than a defect, and it is the least
guessable fact in the whole system: **a gateway opens into the top-left-most
painted region**, because that is region 0. Paint the approach first if you want
travellers to arrive at the gate rather than at whatever happens to be furthest up
and left.

### 2. A per-mode checklist inside the editor

`editor.js`'s `_checklist` writes out what a scope of this **mode** needs, in
order: a `world` is ground and roads, a `town` is ground → streets → walls → gates
→ buildings → **names** → interiors, an `interior` is rooms → doors → storeys →
names.

Progress is **derived from the payload, not remembered in `localStorage`**. A
checkbox the author can tick without doing the thing is worse than no checklist,
and the state that decides "done" already exists on the record. The panel opens
itself for an empty scope and gets out of the way once there is paint, until the
author clicks it — after which their choice sticks.

### 3. Tips

21 `data-help` hooks and matching tips under a `WorldPainter` group, plus a
`paint-a-town` tour. `tools/unit/test_help_center.js` guards the registry: unique
ids, a group and a body on every tip, every tour step naming a real tip, every
tour reachable from a tip, and **every `data-help` key the app emits having a tip
behind it** — a control hooked to nothing is a button that does nothing when
clicked, and nothing about that throws.

The dead-hook check reads the *sources* rather than a DOM, matching both
`data-help="…"` attributes and the painter's `_help(el, '…')` helper, and
reconstructing the tool rail's eight `wp-tool-*` keys from the `TOOLS` table since
those are built at runtime as `'wp-tool-' + id`. It has already paid for itself:
it found that the **❓ Help button itself** carried `data-help="help"` with no tip
behind it.

## Still open



- ~~Grid-canonical vs baked (task-496) — blocking; must be decided before the
  compiler is written.~~ **Decided 2026-09-24: per-zone `paint_policy`
  (`canonical` default, `baked` opt-in); see above.**
- Whether fog is tracked per cell, per area, or per scope (start at area/scope,
  refine to cell only if a painted wilderness is ever walked at cell scale).
- How a path-from-item is authored: a trigger naming a target scope/cell, or a
  map item whose `use` writes the known set directly. task-499 prefers the second
  (reuse the teach path); task-467 needs the first for beliefs with no map.
