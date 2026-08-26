# BUG: Area Item Lists Display Empty

**Filed**: 2026-07-15
**Priority**: High
**Status**: Done — area inspector renders items via worldState.getItemsInArea() (static/js/inspector/area-view.js:103-110). Audited 2026-08-03

---

## Summary

The room inspector shows "No items" even when the room has items. The item list in the room inspector is always empty regardless of actual room contents.

## Current State

In `inspector.js:_showRoom()` (line 588-592), the items rendering uses:

```js
const items = worldState.getItemsInArea(name);
```

This calls `worldState.getItemsInArea(name)` which presumably queries the graph for `contains` or `location` edges. If this function returns empty results despite items existing in the room, either:

1. The function's graph query is wrong (checking wrong edge type, wrong direction)
2. The world state hasn't been fetched/updated properly
3. The items are stored differently in `worldState.areas[name].items` vs graph edges

## Investigation Needed

1. Check `worldState.getItemsInArea()` — in `world-state.js`
2. Check `worldState.areas[name].items` — which items array is populated and when
3. Check if graph edges of type `contains`/`location` exist between areas and items

The room data structure (`worldState.areas`) may have items listed directly (from the API response `/api/state`), while `getItemsInArea()` queries the graph. These could be out of sync.

## Workaround / Quick Fix

If the room data already contains items in `worldState.areas[name].items`, the inspector should use that array rather than (or in addition to) the graph query.

```js
// Try both sources
const itemsFromGraph = worldState.getItemsInArea(name);
const itemsFromRoomData = (worldState.areas[name]?.items || []).map(i => i.name || i);
```

## Files Affected

- `static/js/inspector.js` — fix items rendering in `_showRoom()`
- `static/js/world-state.js` — may need to fix `getItemsInArea()` if that's the root cause
- `static/js/api.js` — verify that `/api/state` returns items correctly
