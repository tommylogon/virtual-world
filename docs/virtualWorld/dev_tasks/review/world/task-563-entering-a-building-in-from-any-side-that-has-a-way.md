---
type: task
status: review
area: world
priority: high
---

# task-563: Entering a building: 'in' from any side that has a way

**Filed:** 2026-09-27
**Related:** task-562 task-561 task-535 task-567

## Goal

A building on a town grid is entered with 'in' from ANY side that has a way, not walked into with a compass direction. Today a cell-to-cell adjacency inside a grid is always a compass step and only a child-scope boundary is a narrative 'enter', so a building cell is a place like any other. Change: a cell that has a child scope (an interior) is entered with 'in'/'out' like a feature entry; a cell with no interior gets a themed refusal drawn from its building type ('The door is shut.' / 'It's locked.' / 'Closed for the season.') on a closed/locked way state, so a key or a knock can change it later. The movement semantics then fall out of the existing way graph: 'out' from inside a tavern lands on its cell, an adjacent temple is one turn, and dash_to_area already chains a second hop in one turn. A gap between two buildings is not a place, so an alley only works if the author paints it.

## What was built

`engine/biomes.py`

- `BUILDING_TAG` / `is_building(biome_id)` — the vocabulary decides, from the
  `building` tag task-561 gave the 31 types, not from a list of ids in the
  compiler. A modder's `watermill` joins without a code change.

`engine/world_compile.py`

- `building_subject()` / `building_refusal()` — a building's name as a thing you
  can be inside of ("inn", "ferry landing") and the line its door gives when
  there is nothing behind it, composed from the building's category tags
  (`BUILDING_DOOR_TAILS`): a watch house is barred, an inn is shut, a smithy's
  bench is cold. Two tails per category, chosen by `_stable_index` on the biome
  id, so the same building always refuses the same way and two of a kind do not
  read as clones. The editor reads the same function (see the route below), so
  the painter's preview and the world cannot drift.
- `_enter_way()` — the way itself. `direction` is the phrase `enter the inn` and
  `aliases: ["in"]` keeps `go in` resolving, as the child gateway already does.
  `see_through: False` (a front door is not a window) and `kind: "entrance"`,
  which is deliberately *not* `door`: a painted door **cell** is structure the
  author drew (task-562) and a building's front door exists because the cell is a
  building, so "how many doorways did I paint" and "how many buildings are on
  this street" stay separately answerable from the graph.
- **One-way in both cases.** With an interior, because `out` inside must keep
  meaning the doorstep. With no interior, because the street already has a
  compass way onto the plot: a way back would be a *second* connection for the
  same pair, and two ways both answering to `out` on the plot means a bare "out"
  picks one at random. Walking a real world found exactly that — in through the
  street door, type "out", and the shut **alley** door answers — so the plot keeps
  its compass exits and says `Visible exits: west, east`.
- The emitter, in `compile_grid` after the doorways: for every building region,
  the **cardinal** sides that already have a way (`emitted_pairs`, so a walled
  side gets no door and a side reached through a painted doorway does), then one
  way per side. Cardinal only because a door is on a wall; a diagonal neighbour
  is a corner of the plot.
  - **With an interior** (a placed child scope that is materialized): the way
    leads to that interior's entry area, open, and **one-way**. One-way on
    purpose: inside, `out` must keep meaning one thing — the doorstep the child
    gateway points at — and a second `out` onto the street would make the word
    ambiguous. You come out onto the doorstep and walk off it, which is also
    what keeps an adjacent building one turn.
  - **With no interior**: the way leads to the building's own cell (the plot) and
    starts `closed` with `refusal_message`. `current_state: "closed"` is the
    state a knock or an `open` can change, and the refusal holds until it becomes
    `open`, so the door can be opened later instead of being permanently
    impassable.
  - **A child placed but not yet generated**: nothing is emitted at all. Emitting
    the shut door would be a lie (there *is* an interior, we have just not seen
    it) and the `in` way needs an entry area id we do not have.
- The parent records its door sides on the placement (`placements[id].sides`),
  and the child mints its own `in` ways from them when it compiles. This is what
  covers the **common** order — generate the town, *then* draw the interior —
  where the parent had no entry area to point at. The alternative was
  re-deriving the parent's whole region naming from the child side for the sake
  of one string.
- The ways carry `child_scope_id`, so `world_scopes.ungenerate_scope` removes
  them with the interior even though their provenance names the parent (the
  gateway's existing rule).
- The generate report says how many doors and how many of those are shut.
- Areas for a building cell record `properties.building`, the fact the map, the
  description and the inspector all read.

`engine/movement.py` — `refusal_message`

- A way with a `refusal_message` raises that line instead of letting you through,
  and holds until `current_state` is `open`. Checked *before* the state machine,
  because a `closed` way otherwise auto-opens on approach and the refusal would
  be cosmetic. It also replaces the generic "The {direction} is locked" line for a
  way that *is* locked, so a themed door does not also get the engine's guess
  that a key exists.
- Nothing else moved: a way without the property keeps every existing behaviour,
  including the `closed` auto-open (tested).

`routes/world_grid_ops.py` + `static/js/worldpainter/`

- The vocabulary payload carries `refusal` for buildings, from
  `world_compile.building_refusal`.
- `grid-model.cellEnter(vocab, biomeId, child)` and `info.enter` in `cellInfo`:
  `in → The Inn` when the cell has an interior, `in → The inn's door is shut.`
  when it does not, `''` for anything else — including a road painted over a
  building cell, which the compiler also does not treat as a building.
- The cell inspector shows an `enter` row, and the hover readout shows the shut
  line so the author notices it while painting rather than in play.

## Acceptance

- [x] A building cell with an interior emits one `in` way per cardinal side that
      has a way, pointing at the interior's entry area, `open`, one-way out, with
      `aliases: ["in"]` and a `child_scope_id`.
- [x] A building cell with no interior emits one `in` way per such side, pointing
      at the plot, `closed`, with a themed `refusal_message` drawn from the
      building's category, and one-way in.
- [x] `move_to_area` raises the refusal, does not auto-open the closed way, and
      lets the character in once it is `open`; a way without the property is
      unchanged.
- [x] The door appears as a real exit of the street (`build_exits_for_area`), and
      `in` still resolves through the alias tier.
- [x] A walled side gets no door; a diagonal neighbour is not a door; a road over
      a building cell is not a building; a plain field gets no doors at all.
- [x] Both compile orders work: the parent emits when the interior is already
      materialized, the interior emits from the recorded sides otherwise.
- [x] `ungenerate_scope(interior)` removes the doors.
- [x] The generate report says how many doors and how many are shut.
- [x] The editor's cell inspector and hover show the same sentence the world
      gives, from the same function.

## Left open (deliberately, and where it goes)

- **A street facing two buildings has two `in` exits**, so a bare `go in` is
  ambiguous there. The name tier disambiguates ("go in to the temple") and the
  matcher's own message lists the candidates, which is realistic but worth
  watching in play. task-564 (per-kind merge rules) is the place to decide
  whether a building's door should be *named* rather than numbered.
- **`out` from a plot is not a word.** On the building's own cell the exits are
  compass, because `in`/`out` name the threshold crossing and the plot is past it.
  A character who walks in and then says "out" gets `No exit 'out'. Visible exits:
  west, east`, which is honest but not generous. If it matters, the fix is a
  `leave the {subject}` phrase on the plot's compass ways — a prose call for
  task-564, not a movement rule.
- **The plot's prose.** A building cell still compiles to an area, because the
  placement record and the `out` side of every interior point at it, and it
  carries the building biome's descriptions — which read as the *inside*. So
  standing on the plot reads like standing in the building. task-567 (generate
  interiors from type) gives the interior its own descriptions; naming the plot
  ("the inn front") is a prose call that belongs with it.
- **`link_islands` still rescues a sealed room.** A building that is deliberately
  walled in still gets a rescue way. Deciding when a *sealed* thing should stay
  unreachable is task-525's storey/terrain decision plus task-564, not this one:
  here a building with no sides is simply a building with no doors.
- **No room vocabulary yet** (`classroom`, `hallway`, `stairway` compile as
  unknown-id places with a warning), so a real floor plan still needs it.
