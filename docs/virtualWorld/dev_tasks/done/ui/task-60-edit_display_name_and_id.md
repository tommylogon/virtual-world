# Edit Display Name and ID for Rooms, Items, Doors

**Filed**: 2026-07-15
**Priority**: Medium
**Status**: Done — verified 2026-08-03. Editable node IDs on all inspectors (InspectorHelpers.renameNode, static/js/inspector/helpers.js:150) + backend rename with edge/trigger-param migration (routes/graph.py).

---

## Summary

Users can edit the display name of areas, items, and ways in the inspector panel, but the underlying IDs are not editable. This means renaming something can create inconsistencies or require destructive recreate workflows. Id's are also not editable in the library or the seperate modals for creatig new enteties.

## Current State

### Area Inspector (`inspector.js:_showRoom()` line 455)
The room name is editable via an inline `<input>` that calls `api.updateNode(nodeId, {name: this.value})`. The room's node ID (used in graph edges, API calls, etc.) is not editable.

### Item Inspector (`inspector.js:_showItem()` line 644)
The item display name is editable via an `<input>` that calls `_updateItemProp(escId, 'name', this.value)`. The item node ID is not editable.

### Way Inspector (`inspector.js:_showDoor()` — need to verify)
Same pattern: display name editable, ID not.

## Proposed Change

Add an editable ID field to each inspector, alongside the display name:

### Pattern for all three inspectors

Under the header (or in a Properties section), show:

```
ID: [editable input with current ID]   (changes: lowecase, no spaces)
Name: [editable display name]
```

### When ID changes:

1. Update the node's ID in the graph database
2. Update all edges referencing the old ID to point to the new ID
3. Refresh the graph view

### Backend API

Either:
- **Option A**: Add an `api.updateNodeId(nodeId, newId)` endpoint
- **Option B**: Have the existing `api.updateNode(nodeId, data)` accept a new `id` field and handle the migration server-side

Recommended: Option A, to keep concerns separated and make the migration explicit.

### UX considerations

- Enforce lowercase, no spaces for IDs (with inline validation)
- Show a warning if the new ID conflicts with an existing node
- Auto-update the inspector view after ID change

## Files Affected

- `static/js/inspector.js` — add editable ID field to room/item/door inspectors
- `app.py` — add `updateNodeId` API endpoint or extend `updateNode`
- `static/js/api.js` — add `updateNodeId()` method
