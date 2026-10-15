---
type: bug
status: inprogress
area: ui
priority: high
---

# bug-526: Sync World to Library 'Sync All' ignores the active tab and generated entities, and silently overwrites

**Filed:** 2026-10-07
**Related:** task-724

## What

Sync All must respect the active tab filter, warn before overwriting, and offer to skip procedurally generated entities. Today it filters only by status (new/diff), so pressing it on the Items tab silently creates/overwrites every item, way, area and character; generated areas (nodes carrying 'cell') have no opt-out, and generated items/ways have no provenance marker at all.

## Measured (2026-10-07)

`static/js/world-sync.ts:263`:

```js
async syncAll() {
    const pending = this.entities.filter(e => e.status === 'new' || e.status === 'diff');
```

The filter is by **status only**, not by the active tab. `openEntityByIndex`
respects the tab (`e.type === this.filter`); `syncAll` does not. So pressing
**Sync All** while on the Items tab creates/overwrites **items, ways, areas and
characters** alike. The docstring confirms it silently overwrites matched library
entries — no DiffModal, no confirm. At the time of the report the dialog read
**633 new / 167 differ**, i.e. one click would push all of them across all types.

## Generated-entity provenance

- **Areas** carry `cell` (+ `world_scope_id`) in `properties` — the grid cell the
  painter compiled. Skipping generated areas is a property check.
- **Items** (e.g. `bush_of_berries_deep_forest_1`) and **ways**
  (`way_cooking_to_storage`) carry **no** provenance marker; `x,y` exists on
  authored nodes too, so it cannot distinguish. Ignoring generated items/ways
  needs a marker (`source: "worldpainter"` or equivalent) stamped in
  `engine/world_compile.py` / `engine/world/spawner.py` at generation time.

## Goal

- `syncAll()` scopes to the active tab (or the "All" tab syncs all, explicitly).
- A confirmation before a cross-type / high-count batch, and no silent overwrite.
- An opt-out (filter) for procedurally generated entities; add the missing
  items/ways provenance marker.

## Acceptance

- [ ] `Sync All` on the Items tab touches only items.
- [ ] A batch that would overwrite existing library entries asks first.
- [ ] Generated areas (`cell` present) can be excluded; items/ways gain a
      provenance marker and can be excluded too.
- [ ] `npm run build:ts` and `node tools/unit/run.cjs` pass; a unit test covers
      the tab-scoped filter and the generated exclusion.

## Implemented (2026-10-07)

`static/js/world-sync.ts`: `syncAll()` now filters by the active tab
(`this.filter`) and skips entities flagged `generated`; `SyncEntity` gains a
`generated` flag, `_collect` marks areas whose node carries a grid `cell`,
`_buildArea/_buildItem/_buildWay` set it (items/ways also match a future
`source: "worldpainter"` marker), and a "generated" badge renders in the list.
The toast reports how many generated entries were skipped. `npm run build:ts`
clean; unit runner 618 passed.

Still open: a confirmation before overwriting existing library entries (a custom
modal is needed — native `confirm` is against convention), and stamping the
`source: "worldpainter"` marker on generated items/ways at generation time.

## Browser UI and intended live verification

Intended UI home: Build → Library → Sync World to Library, using the active category and review/apply flow.

Current availability: Item grouping is partly implemented; active-tab scoping, generated-entity handling, and overwrite confirmation remain open.

Live steps when available:

1. Open Sync World to Library on Items and preview a batch.
   - expected: Only items are included; generated entities are excluded by default and instances collapse to one review row.

2. Toggle excluded rows, inspect a diff, and attempt an overwrite.
   - expected: The diff is reviewable and overwrite requires confirmation; apply/undo reports the batch result.

This section defines the intended access point and acceptance path. It is not a claim that the UI or complete behavior exists or works today; Current availability records the present state, and these steps describe how to verify the intended behavior when it is available.
## Steps to verify

- expected: Sync All scopes to the active tab and skips generated entities, AND asks before overwriting.
- observed (2026-10-10, review): the card's own Implementation note says the overwrite confirmation ('native confirm is against convention') and the source:'worldpainter' provenance marker are STILL OPEN. Tab-scope + generated badge shipped; not ready to close.

## Why

TODO

## How

TODO

## Files

- TODO
