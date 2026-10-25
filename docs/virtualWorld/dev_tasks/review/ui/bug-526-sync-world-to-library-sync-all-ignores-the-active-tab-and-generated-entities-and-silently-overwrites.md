---
type: bug
status: todo
area: ui
priority: high
wiki: "[[Library System/Library 2.0 - Unified Library Design]]"
---

# bug-526: Sync World to Library 'Sync All' ignores the active tab and generated entities, and silently overwrites

**Filed:** 2026-10-07
**Related:** task-724

## What

Sync All must respect the active tab filter, warn before overwriting, and offer to skip procedurally generated entities. Current state (2026-10-20): tab filtering and skipping of generated entities (areas via cell; items/ways if flagged generated or props.source == 'worldpainter') are implemented. Overwrite confirmation and provenance stamping for generated items/ways remain open.

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
entries - no DiffModal, no confirm. At the time of the report the dialog read
**633 new / 167 differ**, i.e. one click would push all of them across all types.

## Generated-entity provenance

- **Areas** carry `cell` (+ `world_scope_id`) in `properties` - the grid cell the
  painter compiled. Skipping generated areas is a property check.
- **Items** (e.g. `bush_of_berries_deep_forest_1`) and **ways**
  (`way_cooking_to_storage`) carry **no** provenance marker; `x,y` exists on
  authored nodes too, so it cannot distinguish. Ignoring generated items/ways
  needs a marker (`source: "worldpainter"` or equivalent) stamped in
  `engine/world_compile.py` / `engine/world/spawner.py` at generation time.

## Plan position (2026-10-20)

**Which NEWER cards (higher number, in `done/` or `review/`) bear on this card, and what did each one actually do?**
- task-724 (review, higher number than 526) is about player state being stored in multiple homes; it touches state persistence/serialization but does not change Sync World to Library UI, tab filtering, or generated-entity provenance.
- task-732 (todo, higher number) is specifically about Sync World to Library item instance collapse; it bears directly on the sync UI behavior (related to grouping/handling instances) but is still todo, not done/review.

**Did that newer work CHANGE THE APPROACH of this card, or does it merely IMPLEMENT PART OF IT, or is it UNRELATED?**
- task-724: unrelated to this UI behavior. task-732: implements part of the same feature area (library sync behavior), but as a separate todo card; it does not replace bug-526's requirements.

**Does this card still stand as a DISTINCT piece of the overall plan, or has a newer card absorbed its scope?**
- Stands as a distinct piece. The core issues (tab-scoped sync, overwrite confirmation, provenance stamping for generated entities) are owned by bug-526; task-732 may complement it but has not absorbed the scope.

**Verdict:** holds, distinct.

## Goal

- `syncAll()` scopes to the active tab (or the "All" tab syncs all, explicitly).
- A confirmation before a cross-type / high-count batch, and no silent overwrite.
- An opt-out (filter) for procedurally generated entities; add the missing
  items/ways provenance marker.

## Acceptance

- [x] `Sync All` on the Items tab touches only items.
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
modal is needed - native `confirm` is against convention), and stamping the
`source: "worldpainter"` marker on generated items/ways at generation time.

## Steps to verify

1. Sync All from the Items tab, with the world containing items, ways and areas.
   - expected: only items are collected; the batch does not include ways or
     areas.
   - observed: CONFIRMED. `syncAll()` in `static/js/world-sync.ts` filters by
     the active tab (`this.filter`), and the "Implemented (2026-10-07)" note
     records the same. This is the one acceptance box that holds.
2. Run a batch that would overwrite an existing library entry.
   - expected: the batch asks for confirmation before overwriting.
   - observed: FAILS. The overwrite path is `_silentSave`, with no
     confirmation step. The card's own Implementation note records the
     overwrite confirmation as still open, and a native `confirm` is against
     project convention, so a custom modal is required.
3. Inspect a generated item and a generated area in the batch list.
   - expected: generated entities are flagged, are excluded by default, and
     the toast reports how many were skipped.
   - observed: PARTIALLY. Areas carry a grid `cell` and are marked; the
     "generated" badge renders and the toast reports the skip count. Items and
     ways have no equivalent marker, so they are not identifiable yet.
4. Confirm the provenance marker is stamped at generation time for items and
   ways.
   - expected: generated items/ways carry `source: "worldpainter"` or an
     equivalent, so step 3 can exclude them.
   - observed: FAILS. No provenance stamping exists in
     `engine/world_compile.py` or `engine/world/spawner.py`. The code only
     matches a *future* `source: "worldpainter"` marker, so nothing sets it.
   - note: areas cannot be distinguished this way either. A generated area has
     a `cell` marker, but so does a hand-authored node placed on a grid cell.
     The area case needs a different discriminator.
5. Run the gates.
   - expected: `npm run build:ts` and `node tools/unit/run.cjs` pass, with a
     unit test covering the tab-scoped filter and the generated exclusion.
   - observed: the 2026-10-07 note records the build clean and 618 unit tests
     passing at the time. No targeted unit test for the tab-scoped filter or
     the generated exclusion was found on re-check.

## Browser UI and intended live verification

Intended UI home: Build → Library → Sync World to Library, using the active category and review/apply flow.

Current availability: Item grouping is partly implemented; active-tab scoping, generated-entity handling, and overwrite confirmation remain open.

Live steps when available:

1. Open Sync World to Library on Items and preview a batch.
   - expected: Only items are included; generated entities are excluded by default and instances collapse to one review row.

2. Toggle excluded rows, inspect a diff, and attempt an overwrite.
   - expected: The diff is reviewable and overwrite requires confirmation; apply/undo reports the batch result.

This section defines the intended access point and acceptance path. It is not a claim that the UI or complete behavior exists or works today; Current availability records the present state, and these steps describe how to verify the intended behavior when it is available.
## Why

Sync All currently operates across all entity types regardless of the active tab and silently overwrites existing library entries without confirmation. It also lacks a reliable way to exclude procedurally generated entities (areas have cell markers, but items/ways do not have consistent provenance). This creates a high risk of accidental cross-type sync and loss of hand-authored library content. The fix is needed to make sync behavior predictable, safe, and respectful of generated vs authored content.

## How

1. **Tab scoping**: Update `syncAll()` in `static/js/world-sync.ts` to filter entities by the active tab (respect `this.filter`) so only entities of the active type are included when not in "All" mode.
2. **Generated-entity handling**: Mark entities as generated where possible (`areas` via `cell` in properties; `items/ways` when `props.generated` or `props.source === "worldpainter"`). Add UI indication and allow exclusion/skipping. For items/ways, add provenance stamping in generation paths (`engine/world_compile.py` / `engine/world/spawner.py`) to set `source: "worldpainter"` (or equivalent) so they can be reliably identified.
3. **Overwrite confirmation**: Replace silent overwrite (`_silentSave`) with a confirmation flow (custom modal, per project convention) before applying batch changes that would overwrite existing library entries. Report skipped/generated counts in toast.

## Files

- `static/js/world-sync.ts` - syncAll filtering, generated flags, skip logic, toast reporting
- `engine/world_compile.py` - provenance stamping for generated items/ways
- `engine/world/spawner.py` - provenance stamping if used for generation
- Targeted unit tests for world-sync tab scoping and generated exclusion

## Audit note (2026-10-16)

Moved from inprogress back to todo: it was not being worked. No uncommitted changes in the working tree or in any of the eight git worktrees touch this card's files, and nobody is editing it. 0 of 4 acceptance boxes checked; the only commits that mention it are a8450e5e and an earlier one, the latest on 2026-10-10. Item grouping is partly in place via task-732; tab scoping, generated-entity handling and overwrite confirmation remain open.

## Reconciliation (2026-10-20)

Verified current implementation in static/js/world-sync.ts:
- syncAll() filters by active tab and skips entities flagged generated (areas via cell; items/ways if props.generated or props.source === "worldpainter"). Skipped count reported in toast.
- _silentSave() overwrites without DiffModal/confirmation; no confirm modal present.
- No provenance marker source: "worldpainter" found stamped on generated items/ways by inspected paths.

Verdict: **PARTLY_DONE**. Tab scoping and generated-area skipping done; overwrite confirmation and provenance stamping for items/ways remain open.
