# Unified Sync World → Library

**Filed**: 2026-08-19
**Priority**: High
**Status**: In Review — core + nested sync + round-trip endpoint implemented 2026-08-19, pending browser E2E

---

## Background / Root cause

The toolbar **"📋 Sync to Library"** button used to call `addAllWorldItemsToLibrary()` →
`syncAllWorldItems()`. Commit `db090445` (2026-07-31) silently repurposed it to
`openLibraryBrowser()` (just opens the library modal, no sync). Later work added
per-tab sync buttons for items / characters / areas, but:

- the toolbar button was never re-wired,
- **ways have no world→library sync at all**,
- each sync runs as a modal-per-entity sequence (no unified list),
- nested items (a container's contents) are **not** synced as their own library
  entries, and the library entry only gets a stale `contents` id list,
- comparison used naive `JSON.stringify` (key-order sensitive) → false diffs.

## Goal

One **"Sync World to Library"** flow covering items, ways, areas, and characters:

1. **List view** of every world entity, each with a status badge:
   - `new` — no matching library entry → offer to add it
   - `diff` — matching entry exists with different values → click to review
   - `synced` — identical (skipped)
2. **Click an entity** → DiffModal with all properties as sections, per-section
   checkboxes. Actions: **Skip** / **Update** (merge checked sections into the
   existing entry) / **Create New** (save as new/duplicate entry).
3. **Nested items**: walk the real graph relations (`in`, `carrying`, `equipped`,
   container contents) recursively. Each contained item is synced as its **own**
   standalone library entry (so `box of cards` → `cards` exists in the library),
   and the parent's `contents` in the library entry holds those item definitions.
4. Both directions usable: world→library sync AND the library browser can
   sync/save to a nested `cards` entry.

## Implementation

- **Restore the toolbar button** → opens the new unified sync view.
- **`syncAllWorld()`** orchestrator + `worldSyncList` view (reuses DiffModal per entity).
- **Shared world→library payload builder per type**, extracted/reused. Ways need
  one (extract `way-view.js`'s builder). Items get the contents recursion.
- **Backend**: `POST /api/library/sync/from-world` returning computed per-entity
  diffs in one round-trip (fast list render); existing save endpoints do the writes.
- **Key-order-stable comparison** (`canonicalize`) so identical data isn't flagged.

## Done (core, 2026-08-19)

- **Restored** the toolbar "📋 Sync to Library" button → opens the unified sync view
  (no longer opens the library browser). "📚 Library" is the separate browser button.
- **New `static/js/world-sync.js`** (`WorldSync`): collects every world entity
  (items via graph nodes, ways via graph nodes, areas, characters) and renders a
  list with status badges — `new` (no match), `differs` (content differs), `synced ✓`.
  Match by `library_id` → slug → name.
- Filter tabs (All / Items / Ways / Areas / Characters) with counts summary.
- Clicking an entity routes to the existing single-entity DiffModal save flow:
  item → `itemLib.saveWorldItem`, way → `wayView._saveToLibrary`,
  area → `libraryBrowser.saveAreaByName`, character → new `saveCharacterByName`
  (added, no-prompt, reuses `_saveCharacterWithDiffModal`). Those flows already
  implement Skip (cancel) / Update (merge checked sections) / Create New (duplicate).
- **Key-order bug fixed everywhere**: added shared `canonicalizeJSON` + `jsonDeepEqual`
  to `shared/json-utils.js`, used by WorldSync status computation; `diff-modal.js`
  was already fixed earlier in the session (its own `canonicalize`).
- Modal HTML added to `index.html`; `world-sync.js` script included and registered
  on `VW.worldSync` in `main.js`.

## Verified

- Backend suite: **1018 passed, 1 skipped, 71 deselected**.
- `jsonDeepEqual`: key-order-insensitive deep equality confirmed via node check.
- Nested pipeline confirmed via node harness (box-of-cards): container embeds full
  recursive `contents` definitions; contained items that are their own graph nodes
  get a standalone sync entry AND are saved as their own library entries; cyclic
  container references are blocked (depth + seen guards).
- JS syntax clean on all edited files.
- **Pending**: browser E2E of the sync modal (toolbar button → list → click → DiffModal).

## Nested items (done 2026-08-19)

- **`ItemLibrary._buildWorldItemPayload(nodeId)`** (item-library.js): canonical
  recursive builder — a container's `contents` now embeds the **full definitions**
  (recursively) of contained items, not just `{id, name}` refs. Returns
  `{payload, nested}` with depth + cycle guards (`seen` set, max depth 8).
- **`ItemLibrary._saveNestedChildren(nestedIds)`**: after saving a container, each
  contained item that is its own graph node is also saved as its own standalone
  library entry (recursively). This is the box-of-cards case: `box_of_cards` embeds
  playing cards inside it AND `playing_cards` exists as a reusable library entry.
- Both `saveWorldItem` and `syncAllWorldItems` now route through
  `_buildWorldItemPayload` + `_saveNestedChildren`.
- **WorldSync** (`world-sync.js`) uses the shared builder, restores `library_id` for
  matching, and registers contained graph-node items as standalone entries in the
  list (`this._nested`), so the box AND its cards both appear with their own badges.
- The library browser can now also sync/save to the nested `playing_cards` entry
  (it's a standalone entry with full schema + DiffModal on save).

## Round-trip endpoint (done 2026-08-19)

- **`GET /api/library/all`** (library_routes.py) returns one or more registries in a
  single HTTP round-trip. Optional `?types=items,ways` narrows the set; default
  returns every `REGISTRY_TYPES` member.
- **`ApiClient.getLibraryTypes(types)`** (api.js) wraps it.
- **WorldSync.open()** now makes **one** request for items/ways/areas/characters
  instead of 4 parallel `getLibraryType` calls. Diff computation stays client-side
  (reuses the shared builders + `jsonDeepEqual`), so there's no builder drift between
  the server and the browser.
- Test: `test_library_all_returns_multiple_registries_in_one_round_trip` (subset +
  default). Suite: **8 passed** in `test_library_refresh.py`, **1018 passed** overall.

## Remaining (future)

- **Ways sync-all button** in the library Ways tab (WorldSync now covers ways from
  the unified view, but the tab itself still has no sync button).

## Order

1. Restore toolbar button → unified sync view (this task, in progress)
2. Build unified list with status badges
3. Wire per-entity DiffModal skip/update/create-new
4. Backend diff endpoint
5. Nested-item recursion (follow-up / separate task)

## Related

- `docs/virtualWorld/Library System/Library 2.0 - Unified Library Design.md` (Phase 2)
- `docs/virtualWorld/dev_tasks/done/items/task-95-idempotent-sync-to-library.md`
- `docs/virtualWorld/dev_tasks/done/items/task-127-library-diff-sync.md`
