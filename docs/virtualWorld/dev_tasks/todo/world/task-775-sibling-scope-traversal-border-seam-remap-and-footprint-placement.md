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
feature occupies an **area** of parent cells (a footprint) rather than one — so
walking from one wilderness chunk to the next goes edge-to-edge, without
returning to the world scope.

## Why

- Feature entry currently has no spatial anchor for *where inside* the child you
  arrive; a footprint fixes that (you arrive at the edge you crossed from).
- Two adjacent chunks currently have border areas that **lead nowhere** — no way
  joins a painted edge cell of one to the facing cell of its neighbour.

## The model (ratified)

- Scopes are **chunks placed on a parent grid**; each chunk is its own scope with
  its own grid. Placement uses the existing child-scope-at-a-cell model
  (`place_feature`, `properties.cell`, `feature_layer`) — a footprint extends
  "one cell" to "an area of cells".
- **The world scope is a placement / overview surface, not a navigation
  surface.** You navigate *inside chunk scopes*, and adjacent chunks join
  **directly at their facing edges**. You never go up to the world scope to
  travel between neighbours.
- **Consequence — no time dilation.** Because the world scope is never a travel
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
  surface — "this exit leads nowhere; paint the facing cell or remove the road")
  and the world treats it as a dead end (a road stopping at the map edge).

**Open fork (pick one):**
- **Strict** — connect only where **both** facing cells are passable; the author
  aligns the road across the seam. Predictable; requires painting both sides.
- **Forgiving** — a passable cell on one side **snaps** to the nearest passable
  cell on the other. Easier to author; the connection point may not be exactly
  where painted.

**Leaning (author, 2026-10-11): do not ship empty 1-cell borders.** So the rule
stays strict (honest world), but the painter *aids* authoring: when a road is
painted into an empty facing edge, offer to paint the matching cell on the other
side (or warn), so seams do not get left dangling. Record the choice here before
implementation.

## Non-goals

- **task-401 is a distinct angle** — the *settlement* case (a town with four
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

- `docs/design/notebook-notes.md` — source sketches (Pages 6, 8).
- `engine/world_grid.py`, `routes/world_grid_ops.py` — footprint placement, seam adjacency.
- `engine/world_index.py` (task-583) — gateway ways across the seam.
- `engine/promotion.py` — fidelity reconciliation (if boundaries auto-switch scope).
