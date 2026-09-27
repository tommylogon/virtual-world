---
type: task
status: review
area: world
priority: medium
---

# task-535: Promote a graph selection into a new child scope with a gateway

**Filed:** 2026-09-27
**Related:** task-528 task-495 task-397

## Goal

The deferred half of task-528: take a selection of area nodes and make them a NEW child scope, placed on a cell of a parent scope's painted grid, with a gateway way and an entry area so it is walkable. Needs (a) a public helper to create a child scope record from existing area nodes (nothing in engine/ does this today - handle_create_scope only makes an empty record), (b) a gateway whose provenance is NOT the parent scope's, because world_compile._gateway is private and stamps properties.generated.scope_id = parent, which would make ungenerate(parent) delete the hand-authored gateway, and (c) entry_area_id/entry_area_name bookkeeping so the scope has an entry point. Placement of an EXISTING area onto a cell (task-528) is done; this is about creating a new scope out of a selection.

## Acceptance

## Acceptance

- [x] **(a) A public helper creates a child scope from existing area nodes**:
      `world_scopes.promote_to_scope(manifest, graph, scope_id=, name=,
      area_ids=, parent_id=, cell=, entry_area_id=, mode=, enter=, leave=)`.
      Nothing in `engine/` did this before; `handle_create_scope` still only makes
      an empty record.
- [x] **The areas move with everything attached** — names, items, character
      placements and their ways stay put, because the *nodes* move scope rather
      than being recreated. Membership moves at both ends: the node's
      `world_scope_id` and the manifest's `area_ids` mirror.
- [x] **The painted cell marker is cleared** on the way in, because inside a
      promoted scope the position is hand-authored canvas space — left in place,
      the layout engine would read engine units as canvas pixels.
- [x] **(b) The gateway's provenance is NOT the parent's.** It carries no
      `generated` block at all, so `Ungenerate` on the parent cannot delete a
      gateway the author made by promoting something. **Checked**: ungenerate the
      parent and the promoted gateway is still there.
- [x] `(c) entry_area_id` / `entry_area_name` are set, and the entry is a
      *choice*: the author's `entry_area_id`, else the first selected area **by
      id** — deterministic, and not "top-left-most" as the compiler picks, because
      a promoted selection has no painted anchor to be top-left-most of.
- [x] **Every refusal happens before anything mutates.** Empty selection,
      duplicate id, an id that is not an area, an entry outside the selection, a
      cell off the grid, a cell that is not a painted place, an unknown parent —
      all checked up front, because a half-created scope whose areas have already
      moved is worse than no promotion.
- [x] **One undoable step**: `POST /api/world/promote` moves the areas, creates
      the record, writes the placement and mints the gateway together, and a
      refusal pops the snapshot it pushed so nothing dangles in the undo stack.
- [x] **The scope is `baked`** — authored, not compiled — so Generate on it
      refuses with a reason instead of replacing a hand-drawn interior with
      regions, and `ungenerate_scope` refuses a baked scope for the same reason.
- [x] **`ungenerate_scope` no longer deletes hand-authored ways.** A *compiled*
      gateway still dies with the scope it points at; an author's own is kept and
      reported in the new `kept_ways` field, because Ungenerate is the undo of a
      Generate and the author never ran one.
- [x] UI: the cell panel offers "🪜 Make this a scope…" on an inspected area.
      The graph view's **multi**-select is not wired (vis runs
      `multiselect: false`), so this is the one-area case; the helper takes a
      list and the multi-select is the follow-up.

## Notes

- **`world_grid.place` gained a third overlap mode, `gateway`**, because
  promotion legitimately needs a cell to hold both a hand-placed area and a
  child scope — the area becomes the **doorstep**. `forbid` and `displace` still
  refuse (a collision is a mistake; sharing the cell deliberately is not), and
  the compiler now *reports* a hand-gated placement instead of silently minting
  nothing, which is the failure this whole task was filed about.
