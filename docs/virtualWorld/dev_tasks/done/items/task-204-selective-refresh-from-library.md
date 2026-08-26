---
group: Library
---

# Selective Refresh from Library (Items + Ways)

**Filed**: 2026-08-10
**Priority**: Medium
**Status**: In Review — implemented 2026-08-10. 838 tests pass, 0 regressions.

---

## Problem

`refresh-from-library` blindly overwrote all unlocked properties and wiped all triggers. For items, the frontend didn't even show a preview — it just called the endpoint and refreshed. This made it impossible to use library refresh when a placed item/way had custom triggers you wanted to keep.

## Fix

**Backend**:
- `routes/library_routes.py` — new `POST /api/ways/<node_id>/refresh-from-library` endpoint. Accepts `{sections: [...]}` and only touches those fields + respects `locked_fields`. Without `sections`, does legacy blind refresh.
- `routes/items_registry.py` — updated existing item refresh endpoint to accept optional `sections` for selective refresh. Without `sections`, behaves exactly as before (backward compat).

**Frontend**:
- `static/js/api.js` — added `ApiClient.refreshWayFromLibrary(nodeId, sections)`; updated `refreshFromLibrary(nodeId, sections)` to send body.
- `static/js/inspector/way-view.js` — added `InspectorWayView._refreshFromLibrary()`. Loads library entry, builds current node payload, shows `DiffModal`, POSTs selected sections. Added "🔄 Refresh from Library" button to way inspector footer.
- `static/js/inspector/item-view.js` — replaced blind `_refreshFromLibrary` with DiffModal flow. Loads library entry, shows section-by-section comparison, POSTs selected sections.

**Way inspector tabs**: also added tab layout (Info | Behavior | Connections | Tags & More | Triggers) + Parameters section in Info tab.

## Verification

- 5 new tests in `tests/test_library_refresh.py`: selective way refresh, missing library entry, selective item refresh, blind item refresh, blind way refresh.
- Full suite: 838 passed, 11 pre-existing give-item failures, 0 regressions.
