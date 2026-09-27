---
type: task
status: review
area: world
priority: high
---

# task-560: Author-set names on painted cells

**Filed:** 2026-09-27
**Related:** task-496 task-540 task-561 task-526

## Goal

Every painted place is named by the compiler alone: `<label> (<scope> x,y)`. A
19-location town is 19 coordinate names, so painted towns and interiors cannot be
authored — a building is "Building 3,4" forever, and `go inn` has nothing to
match. Add a per-cell name the author sets, preferred by the compiler for the
place's display name, with the uniqueness guarantee intact.

## Acceptance

- [x] **A `names` map on the scope record, not a fourth paint layer.** A name is
      *metadata about* a cell, so it lives beside `layers`: there is no name
      vocabulary, the eraser must not wipe it, and "clear this cell" must not
      silently unname a place. `world_grid.set_name` / `name_at`, and
      `normalise_grid` drops an unparseable cell key or a blank name (a bad save
      costs one name, not the map).
- [x] **An empty name removes the entry**, and the container goes with the last
      one, so an unnamed scope loads byte-identically to one that never had names.
- [x] **`POST /api/world/scopes/<id>/grid/name`** — `{x, y, name}`, its own undo
      step, and the grid payload carries `names` back. Rejects a non-integer cell
      and a non-string name.
- [x] **The compiler prefers it.** `_place_name` takes the author name, falling
      back to the generated form. A name repeated *inside one scope* also falls
      back, so no single area offers two exits with the same name — which is all
      `go <name>` needs, since `NameMatching.resolve_exit` collects the current
      area's exits first. Two scopes may reuse a name, exactly as two
      hand-authored areas may: ids stay the authoritative key.
- [x] **A merged region takes a name from *any* of its cells**, not just the
      anchor. Naming the middle of a High Street is the natural thing to do, and
      making the author know that the anchor is the top-left-most cell would be a
      rule with no purpose. Two different names in one region: the first wins.
- [x] **Authorable in the painter**: a name field in the cell inspector
      (task-540's panel), the name leading the hover readout, and
      `cellInfo`/`cellName` exposed on the grid model.
- [x] **Tests.** `tests/test_world_compile.py` (the name wins, the repeated-name
      fallback, a region taking a name from its middle, metadata-not-paint, a bad
      name costing one name), `tests/test_world_grid_routes.py` (round trip,
      clearing, paint-and-name independently, nonsense rejected).

## Verified

Through the real app (Flask test client, temp data dir, so the author's scenario
is untouched) — a 6×4 town grid with a road and a tavern and a temple, the tavern
named:

```
names on the record  : {'1,1': 'The Stag Inn'}
  (0,1)  Road (Downtown 0,1)     storey=0 surface='dirt'  tags=['road']
  (1,1)  The Stag Inn            storey=0 surface='dirt'
        tags=['building','settlement','commercial','food','drink']
  (2,1)  Temple (Downtown 2,1)   storey=0 surface='stone'
        tags=['building','settlement','religious','worship']
ways minted: 2
```

Note the tags: that is task-566's hook already in place — a place a character
could seek a bed or a meal in is identifiable from its node.

## Not here

- **The sim does not use names yet.** Nothing asks "where is an inn"; that is
  task-566. A painted town is addressable, not yet inhabited by intent.
- **Interiors name the same way**, so a room is nameable now — but a 2×2 classroom
  merging into one place names the whole region, which is task-564's business.
- `deep_woods_2` still carries its stale id (task-565).
