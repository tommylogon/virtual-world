# Way Inspector: Target Editing & Direction Display

**Status**: Done — verified 2026-08-03. Connections + directions shown in the way inspector (static/js/inspector/way-view.js), Reconnect button wired to /api/graph/way/reconnect (routes/graph.py:431). Endpoint renamed from door/reconnect to way/reconnect.

**Priority**: Medium

## Summary

The door inspector (`_showDoor`) currently shows a door's name, state, description, tags, and triggers — but **doesn't show which rooms it connects to** or allow changing them. This makes it impossible to fix miswired doors from the UI.

## Requirements

- Show both connected rooms with their direction labels visible in the inspector
- Dropdown selectors to change which room each side connects to
- "Reconnect" button that calls `/api/graph/door/reconnect`
- Also add this to the door creation modal (`door_modal_more_properties.md` is a separate task)

## UI Mock

```
🚪 Way: Kitchen-swinging
Description: [...]

⚙️ Properties
  State: [open ▼]
  Pass Message: [...]
  Direction A: swinging door → Kitchen
  Direction B: enter → Living Area

🔗 Connections
  Side A: [Kitchen ▼]  direction: [swinging door ▼]
  Side B: [Living Area ▼]  direction: [enter ▼]
  [Reconnect]

[... triggers, unlock, delete]
```

## Implementation

In `_showDoor()`:
1. Query `worldState.graph.edges` for connection edges matching this door
2. Extract room node IDs and directions from the 4 edges
3. Resolve room names from node IDs
4. Display as read-only labels + editable dropdowns
5. "Reconnect" button calls `ApiClient.reconnectDoor(wayId, roomAId, roomBId)`

Need a new `reconnectDoor` method on the API client.

## Files Changed

- `static/js/inspector.js` — extend `_showDoor()` with connection display + target editing
- `static/js/api.js` — add `reconnectDoor()` method
