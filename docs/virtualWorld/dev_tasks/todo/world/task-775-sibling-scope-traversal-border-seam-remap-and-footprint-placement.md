---
type: task
status: todo
area: world
priority: medium
---

# task-775: Sibling-scope traversal: border seam remap and footprint placement

**Filed:** 2026-10-11
**Related:** task-401, task-399, task-419
**Source:** `docs/design/notebook-notes.md` Pages 6 and 8; reworked 2026-10-11 after the chunk demo (two `example chunk wilderness` scopes placed at adjacent world cells, each its own `8×7` grid).

## What

Define how **adjacent sibling chunks connect at their shared border**, and how a
feature occupies an **area** of parent cells (a footprint) rather than one - so
walking from one wilderness chunk to the next goes edge-to-edge, without
returning to the world scope.

## Why

- Feature entry currently has no spatial anchor for *where inside* the child you
  arrive; a footprint fixes that (you arrive at the edge you crossed from).
- Two adjacent chunks currently have border areas that **lead nowhere** - no way
  joins a painted edge cell of one to the facing cell of its neighbour.

## The model (ratified)

- Scopes are **chunks placed on a parent grid**; each chunk is its own scope with
  its own grid. Placement uses the existing child-scope-at-a-cell model
  (`place_feature`, `properties.cell`, `feature_layer`) - a footprint extends
  "one cell" to "an area of cells".
- **The world scope is a placement / overview surface, not a navigation
  surface.** You navigate *inside chunk scopes*, and adjacent chunks join
  **directly at their facing edges**. You never go up to the world scope to
  travel between neighbours.
- **Consequence - no time dilation.** Because the world scope is never a travel
  surface for a chunk, a town occupying 1 world cell is not a distance anyone
  walks; `1 cell = 1 turn = 1 minute` (`grid-model.routeStats`) holds only within
  whichever chunk you are in. There is no world-cell-vs-town-cell comparison to
  reconcile. (The earlier "time dilation is a problem" framing is **retracted**;
  it only applied to a model where you cross the town *on* the world map.)

## The seam rule (the core work)

A seam is **per passable edge cell**, not "the whole edge connects":

- Only a **passable** edge cell (a painted road / open ground) forms an exit;
  unpainted edge cells are wall, exactly like any interior unpainted cell. A
  south border with 1 road painted of 30 gives **exactly one** south transition.
- It reuses the compiler's existing 8-neighbour adjacency, applied **across the
  scope boundary**: a passable edge cell of chunk A that faces a passable edge
  cell of chunk B becomes one **gateway way** (task-401's mechanism; do not build
  a second).
- **Unequal resolutions map by position.** The edge lengths may differ (A `8`
  wide, B `12`), so each passable A-edge cell maps to the facing B-edge cell at
  the same **fraction along the edge**, and connects only if that cell is
  passable.
- **A passable cell facing an empty cell "leads nowhere."** Do not silently drop
  it or teleport: the painter **flags** it (reuse the `blockers` / preflight
  surface - "this exit leads nowhere; paint the facing cell or remove the road")
  and the world treats it as a dead end (a road stopping at the map edge).

**Open fork (pick one):**
- **Strict** - connect only where **both** facing cells are passable; the author
  aligns the road across the seam. Predictable; requires painting both sides.
- **Forgiving** - a passable cell on one side **snaps** to the nearest passable
  cell on the other. Easier to author; the connection point may not be exactly
  where painted.

**Leaning (author, 2026-10-11): do not ship empty 1-cell borders.** So the rule
stays strict (honest world), but the painter *aids* authoring: when a road is
painted into an empty facing edge, offer to paint the matching cell on the other
side (or warn), so seams do not get left dangling. Record the choice here before
implementation.

## Investigation (2026-10-18): most of this exists, and three rules need correcting

Read against the current code. Full write-up, with diagrams:
`docs/design/sibling-scope-traversal.md`.

**Already there:**

- A boundary-seam pass exists (`engine/world_compile.py:2054`, task-528): the id is
  `_way_id(scope, a, b)` = `way_{scope}_{a}_{b}`, an 8-neighbour scan, **one way
  per region pair** (`emitted_pairs`), overridable (`boundary_overrides`), reported
  (`boundary_ways` / `boundary_suppressed`). It is **intra-scope**; this card is
  largely "run the same pass across the border".
- The gateway shape is reusable as-is. Any `way` carrying `target_area_id` +
  `target_scope_id` is indexed as a gateway (`engine/world/index.py:129`), and
  `engine/movement.py:645` loads the destination scope before resolving it.
  Cross-scope movement is already demonstrated by `tests/test_chunk_lifecycle.py`.
- The preflight advice surface exists (`engine/world_compile.py:1172`, exposed as
  `blockers` in the grid payload at `routes/world_grid_ops.py:279`), so the "leads
  nowhere" flag is a payload item, not new UI machinery.

**Three corrections:**

1. **"Per passable edge cell" contradicts the rule it says to reuse.** The compiler
   mints one way per region pair. Under a literal per-cell reading, a fully painted
   seam mints N parallel ways between the same two areas. Passability should be
   tested **per facing cell pair**; minting stays **one per region pair**.
2. **"Passable" is already defined, and it is not "painted".** `is_place(cell)`
   (`engine/world_compile.py:1250`) is painted AND place-kind; a wall, void, window
   or door on the border is painted and not passable. The "1 road of 30" example
   also only holds if the other 29 border cells are unpainted. A chunk whose
   interior paint reaches the border has a fully passable border. That is the real
   authoring rule, and the aid should teach it.
3. **The seam must target the facing edge cell's area, not the child's entry.**
   Gateways currently target the child's `entry_area_id`
   (`engine/world_compile.py:2336`), which is why "you arrive at the edge you
   crossed from" is not true today. `_gateway(...)` already takes the entry area as
   a parameter, so this is a caller decision, not new machinery, and it fixes the
   sibling case with no footprint required.

**The one gap with no precedent to copy: ownership.** `world_scope_id` is
single-valued (`engine/world/index.py:46`); `_gateway_id(parent, child)` is one way
per pair; and the existing "whoever compiles second" arbitration is
**parent-mediated** (`engine/world_compile.py:2287-2291`, `2357`). Siblings have no
parent-child order. Because the card's premise is that the world is not a travel
surface, the seam must still cross while the world scope is evicted, which argues
against owning it on the world. `_way_id` also bakes in one scope id and cannot
name a way spanning two scopes.

**Unequal resolutions.** The fraction mapping is non-bijective in both directions
(a shorter edge maps two cells onto one; a longer edge has cells that map from
nothing), and the two directional maps can disagree. Define the seam as **one
pairing computed once**, not two independent directional maps.

**Movement is one path for every controller (corrected 2026-10-18).** A human, an
LLM agent, a simple NPC and a backsim character all move through
`movement.move_to_area`; the BFS in `engine/npc_behaviors.py:812` / `:873` and
`engine/timeskip.py:653` is the *knowledge* layer, not a second movement model. So
load-before-you-move (`engine/movement.py:645`) is not agent-specific and a minted
seam way is routable and costable for free. The only remaining gap is *route
computation* into an evicted scope (the BFS reads loaded graph edges), which is
task-583's index work. Two adjacent findings, not part of this card: the soak-tier
hazard roll (`engine/traversal.py`) reaches the backsim and timeskip but not the
human/LLM command path (**task-863**), and the slasher bypasses `move_to_area`
entirely (`engine/npc_behaviors.py:800`; legacy, not wanted, **task-864**).

## Proposed decisions (not ratified)

1. **Strict**, per the author's leaning, and for a second reason: forgiving makes
   the flag dead. If any passable cell snaps to the nearest passable cell, nothing
   ever leads nowhere, so the preflight item the card wants can never fire. The
   aid's flavour (warn, or offer to mirror) is separate, and whether it may write
   into the neighbour's grid is the author's call.
2. **Seam owner: to be decided**, but it must not depend on the world scope being
   loaded.
3. **Split the multi-cell footprint out of this card.** The card already says the
   settlement-gate angle (task-401) is a distinct problem, and for adjacent
   wilderness siblings the seam needs only the facing-area target, not a footprint.
   Footprints drag `placements` / `occupant_at` / `area_placement_at` /
   `feature_layer` / `_gateway_id` off their single-cell assumption, which is the
   settlement case.

## Non-goals

- **task-401 is a distinct angle** - the *settlement* case (a town with four
  gates; each gate is an area you exit the settlement through), i.e.
  intra-settlement gateways. This card is the *wilderness sibling* case: two
  adjacent chunks joined along their shared border. Both use a boundary way, but
  they are different problems; do not collapse them.
- **Variable cell size *within* one scope is out of scope.** The grid is uniform
  everywhere (`CELL = 22` renderer, integer coords, 8-neighbour adjacency,
  one-cell-one-area compile). Resolution may differ **per scope**, never per cell.
- Reconciliation with **fidelity** (task-399 `activate_scope`) is required if
  crossing a boundary auto-switches scope; decide whether scope becomes a
  streamed chunk of a continuous world.

## Steps to verify

1. Two adjacent chunks, a road painted across the seam on both sides.
   - expected: walking out A's east edge arrives at B's facing west-edge cell.
   - observed: TODO
2. Same, but B's facing edge is empty.
   - expected: the painter flags "exit leads nowhere"; the world makes it a dead end, not a teleport.
   - observed: TODO
3. Chunks of different widths; a road at ~50% of A's edge.
   - expected: it maps to ~50% of B's edge (proportional), connecting only if that cell is passable.
   - observed: TODO

## Acceptance

- [ ] Feature placement supports a footprint (multiple parent cells), reusing the child-scope-at-a-cell model.
- [ ] The seam is per passable edge cell; it reuses the compiler's adjacency and task-401's gateway ways.
- [ ] Unequal resolutions map by position (proportional), connecting only when both facing cells are passable.
- [ ] "Leads nowhere" is flagged by the painter and treated as a dead end, never a silent drop.
- [ ] The strict-vs-forgiving fork is decided here, with the no-empty-borders aid specified.
- [ ] The settlement-gate angle (task-401) is not conflated with the wilderness-sibling case.
- [ ] Variable cell size within a scope is explicitly out of scope.

## Files

- `docs/design/notebook-notes.md` - source sketches (Pages 6, 8).
- `docs/design/sibling-scope-traversal.md` - current state vs target state, the three-way comparison and the open decisions.
- `engine/world_grid.py`, `routes/world_grid_ops.py` - footprint placement, seam adjacency.
- `engine/world/index.py` (task-583) - gateway ways across the seam.
- `engine/promotion.py` - fidelity reconciliation (if boundaries auto-switch scope).

## Browser UI and intended live verification

Intended UI home: WorldPainter → choose two adjacent sibling scopes → inspect their shared border cells and child-scope footprints → compile and traverse the generated gateway ways in the game view.

Current availability: the card defines seam mapping, passable edge cells, unequal grid resolutions, and multi-cell footprints, but the strict-vs-forgiving rule is still undecided. These traversal and placement rules are not claimed as implemented.

Live steps when available:
1. Paint a child feature with a footprint spanning multiple parent cells; inspect the parent grid before applying it.
   - expected: every occupied parent cell is visible and the child scope is represented once with the selected footprint.
2. Create sibling scopes at unequal resolutions and inspect each facing border cell.
   - expected: proportional position mapping pairs corresponding cells; a gateway is generated only where both facing cells are passable.
3. Attempt traversal across each generated border gateway from both scopes.
   - expected: traversal crosses directly into the sibling chunk and does not return through the world scope; impassable seams remain closed.
4. Paint a border that leads nowhere and inspect the WorldPainter warning and game result.
   - expected: the painter flags the dead end explicitly and the game treats it as a dead end, not a silently dropped connection.
5. Repeat around a settlement gate.
   - expected: the settlement-gate rule from task-401 remains separate from wilderness sibling traversal; variable cell size within one scope remains unsupported.

This section is not a claim that sibling-scope traversal or footprints are implemented today.
