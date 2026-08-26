# Auto-Add New Items to Library

**Filed**: 2026-07-15
**Priority**: Low
**Status**: Done — verified 2026-08-03 (re-checked after being flagged NOT_DONE; the frontend auto-save was missed in the first audit).

---

## Summary

When a new item is created via the graph toolbar create modal, it is automatically added to the item library for reuse in other areas.

## Implementation (Option A — auto-save on creation) ✅

1. `static/js/main.js:131` — `addItemViaGraph()` creates the world item via `api.createItem(data)`.
2. `static/js/main.js:138-141` — on success it derives a library id (`name.toLowerCase().replace(/[^a-z0-9_]+/g, '_')`) and calls `api.saveLibraryItem({ id: libId, name, description, actions, uses, weight, hidden, equip_slots, tags })` (fire-and-forget `.catch(() => {})`).
3. `static/js/api.js:182-189` — `saveLibraryItem` POSTs to `/api/registry/items`.
4. `routes/items_registry.py:31-45` — `registry_items_post` upserts the item into the `items.json` registry (persisted to `data/library/items/`).

So the create-modal flow auto-adds to the library — the item becomes reusable in other areas without manual "Sync to Library".

## Caveats (recorded, not blocking)

- **Auto-save only fires on the create-modal path** (`addItemViaGraph`). Items created via raw API calls or the inspector don't auto-save — but the modal is the primary creation surface, matching the task's Option A scope.
- **No fuzzy-match/merge**: the "Ideally a fuzzy match... merge/cancel" bonus was never built. `saveLibraryItem` blindly upserts by name-derived id, overwriting a same-id entry. That's a separate enhancement idea, not part of the core fix.
- Manual sync buttons still exist as a belt-and-suspenders path ("📋 Sync to Library", right-click "📚 Save to Library").
