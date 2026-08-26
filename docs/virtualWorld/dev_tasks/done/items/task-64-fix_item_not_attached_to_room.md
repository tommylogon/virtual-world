# BUG: New Item Not Attached to Selected Area

**Filed**: 2026-07-15
**Priority**: High
**Status**: Done — verified 2026-08-03. `api.createItem` (static/js/api.js:106) sends the `area` field; backend `build_item_legacy` (routes/graph.py:229) resolves the area node by name — including the non-standard-ID fallback loop (routes/graph.py:111-113) — and attaches the item via a `location` edge (migrated to `in` by `normalize_edges`).

---

## Summary

When creating a new item via the "Add New Item" modal with a target room selected, the item is not always placed in the selected room. The user reports creating a "leather chair" intended for the "living room", but the item did not appear in that room.

## Current State

In `main.js:openCreateModal()` (line 396-407), the item form includes a target room selector:

```html
<label>Target Area</label>
<select id="item-room">${roomOptions}</select>
```

On submit (line 448-449), the room value is collected:

```js
result = {
  room: document.getElementById('item-room')?.value,
  name: ...
};
```

Then passed to `api.createItem(data)` in `addItemViaGraph()` (line 202-208):

```js
function addItemViaGraph() {
  openCreateModal('item', async (data) => {
    if (!data.name) { alert('Item name required'); return; }
    const res = await api.createItem(data);
    // ...
  });
}
```

### Investigation Needed

1. **Check `api.createItem()` in `api.js`** — Does the API call pass the room to the backend?
2. **Check the backend endpoint** in `app.py` — Does `createItem` correctly attach the item to the specified room via graph edges?
3. **Check if the room parameter is being dropped** somewhere in the chain.

### Possible Root Causes

- The `room` field is collected but not sent in the API payload (field name mismatch)
- The backend creates the item node but doesn't create the `location`/`contains` edge to the room
- The backend expects a different field name (e.g., `area_id` vs `room`)
- The room name doesn't match the graph node's room name (case sensitivity, spaces)

## Proposed Fix

1. Add logging/debug to trace the data flow: form → JS object → API call → backend
2. Fix any field name mismatches
3. Ensure the backend creates the item-in-room edge
4. Verify the room lookup matches the graph's room ID normalization

## Files Affected

- `static/js/api.js` — verify `createItem()` payload structure
- `app.py` — verify backend `createItem` endpoint
- `static/js/main.js` — verify the data object construction
