---
type: task
status: review
area: ui
priority: medium
---

# task-541: WorldPainter area picker: this scope's areas, and what is placed here

**Filed:** 2026-09-27
**Related:** task-528, task-539, task-540
**Status:** implemented 2026-09-27, in review

## Goal

Once membership is edited on the node (task-539), the place tool's dropdown should
just answer "which areas belong to the scope I am painting?". It used to list
**every** unplaced hand-authored area in the whole world
(`_unplaced_areas`, `routes/world_grid_ops.py`), so the goblin camp's rooms showed
up in the world map's picker as if they belonged there.

## Acceptance

- [x] The payload carries each candidate's **owning scope** — `scope_id` *and*
      `scope_name`, so the "elsewhere" group can name the scope it belongs to
      instead of showing a bare id.
- [x] `gridModel.areaGroups(payload, selectedId)` returns up to three groups, in
      order: **On this grid** (with each cell), **This scope, not placed**, and
      **Elsewhere in the world**. The editor renders them as `<optgroup>`s;
      `placeableAreas` is the flattened view of the same list.
- [x] An area with **no** scope counts as this scope's — it belongs to nobody, so
      any map may claim it.
- [x] An area already on this grid is never listed twice, even if the server also
      offers it as a candidate.
- [x] The "elsewhere" heading says picking one moves it here, because that is a
      membership change (task-539) and must not read as a placement.
- [x] A picked area is never dropped from the picker, so it can still be moved.
- [x] Unit-tested: the parent map's picker does not list a child scope's rooms as
      its own, the camp's own map does, an unowned area appears on both, a placed
      area appears once, and an unknown selected id stays selectable.
- [x] Verified live: on the goblin camp grid the picker shows
      `On this grid (2)` → Animal Pens (11,7), Sleeping Halls (2,3) and
      `This scope, not placed (29)` → the camp's rooms, with no "elsewhere" group
      (every unplaced area already belongs to that scope).

## Note

The old flat "📍 name (x,y)" chip row for already-placed areas is gone: those areas
are now the first optgroup, with their cell, so the same information is in one
place instead of two.
