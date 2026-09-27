---
type: task
status: review
area: world
priority: high
---

# task-539: Reassign an area to a scope (membership only) + a scope picker on the node

**Filed:** 2026-09-27
**Related:** task-528, task-535, task-540, task-541
**Status:** implemented 2026-09-27, in review
**Author's design (2026-09-27):** membership is one field, so it should be edited
where membership is visible — click the area node, pick its scope from a dropdown,
done. No separate bulk-move flow; the WorldPainter then only has to list the areas
of the scope you are painting (task-541).

## Problem

`world_scope_id` *is* scope membership — the scope views read nothing else
(`world_scopes.own_area_ids` / `area_ids_in_scope`, and `project_subgraph`'s "a
`way` whose both endpoints are included"). But today the only way to change it is
`POST /api/world/scopes/<id>/grid/place_area` (`routes/world_grid_ops.py`), which
needs a **painted cell** and writes `cell`/`x`/`y` too. For a child scope's
*interior* that is the wrong tool: rooms should belong to the camp scope, not be
parked as cells on the world's grid (which is also why they kept showing up in
the world scope's own view).

`PATCH /api/graph/node/<id>` with `{"properties": {"world_scope_id": ...}}`
*would* work, but it writes only the node. The manifest mirror
(`scope["area_ids"]`, maintained by `_set_area_membership`) would desync, so scope
counts and `area_ids_in_scope` would disagree with the graph. It is also not one
undo step with the rest.

## Acceptance

- [x] `POST /api/world/scopes/<scope_id>/areas` with `{"add": [ids], "remove": [ids]}`
      (lists, so a multi-selection moves in one call) sets
      `properties.world_scope_id`, updates **both** scope records' `area_ids`,
      leaves `cell`/`x`/`y` of a *target*-scope placement alone, and is **one undo
      step**. The rules live in `world_scopes.assign_area_membership`, which the
      place route now shares, so there is one implementation of "move".
- [x] Moving an area away from a scope drops it from that scope's
      `area_placements` and clears the node's `cell`/`x`/`y` — otherwise the old
      grid keeps reserving a cell for an area that is no longer a member. A cell
      it holds in the *target* scope is kept, so re-assigning it there is a no-op.
- [x] Refuses generated areas (with the same explanation `handle_place_area`
      gives), non-areas and unknown ids — and validates **before** the snapshot, so
      a refusal leaves no junk undo entry and no half-applied move.
- [x] `remove` clears the scope *and* the cell (the area then belongs to nobody
      and is free to be placed anywhere).
- [x] An **area-node scope picker** in the inspector: a 🗺️ Scope section with a
      `<select>` of the scope list from `GET /api/world/scopes?flat=1`
      (depth-indented), a "— no scope —" option, and an orphan option so a scope
      id with no record still shows as the current value instead of the select
      lying. Nothing in the inspector fetched scopes before.
- [x] The same section shows the map placement ("cell (x,y)" + *open in
      WorldPainter*), so membership and position read as one fact.
- [x] Removing via the "— no scope —" option posts to the area's *current* scope
      (an empty scope id would build `/api/world/scopes//areas`); a failure
      restores the previous selection.
- [x] After moving, the parent's own-level view no longer lists the areas and the
      child's does.
- [x] Tests (`tests/test_world_grid_routes.py`, +7): membership without a cell,
      one undo step for a whole selection (asserted through a real
      `POST /api/undo`), cell release on leaving, target-cell kept, remove clears
      both, the three refusals, and the candidate `scope_name`.

## Verified live

Created a throwaway `zz_camp` scope and three areas, then moved two of them with
`POST /api/world/scopes/zz_camp/areas`:
`zz_tent=assigned, zz_pit=assigned`; the camp's subgraph then listed
`area_animal_pens, area_murk_lake, area_sleeping_halls, zz_pit, zz_tent` and
`world`'s subgraph no longer contained the moved areas. All three refusal paths
answered with their intended message. Through the UI: picking "goblin camp"
(`deep_woods_2`) in the node's Scope dropdown put `area_training_pit` into the
camp's own level, and "— no scope —" put it back. Test data was removed again and
the world left as it was found.

## Not done here

- The task-535 half (turning a *selection* into a new child scope) is untouched.
  A multi-selection can now be moved into an *existing* scope (see below), but
  making a new child scope out of a selection is still task-535.
