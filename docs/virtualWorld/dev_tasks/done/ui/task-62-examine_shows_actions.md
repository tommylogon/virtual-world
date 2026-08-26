# Examine Enhancement — Show Available Actions When Examining an Object

**Filed**: 2026-07-17
**Priority**: Medium
**Status**: Done — verified 2026-08-03. Examine appends "Available actions:" via _get_available_actions (engine/item_actions.py:200-205). Phase 3 (clickable action buttons) was optional and not implemented.

---

## Summary

When a player examines an object, the result should include not only the object's description but also a list of **available actions** the player can perform on it. This helps players discover what they can do with items without trial-and-error guessing.

For example:
```
> examine grandfather_clock

An old grandfather clock ticks steadily in the corner. It is tall with an intricately carved wooden face.

Available actions:
  [examine] Look at the clock closely
  [open] Open the glass door
  [use key] Insert a key (requires: brass_key)
  [toggle] Toggle the chime
```

## Current State

### Examine result (`virtual_world_engine.py:1326`)

The `get_item_desc()` method returns:
1. Item description from `item_node.properties.description`
2. Optional skill check results
3. Trigger outputs (from `on_examine` triggers)
4. Container contents (if any)

No action hints are included.

### Item actions property

Items have an `actions` list (e.g., `["examine"]`) and `action_costs` in their properties. But these are used by the engine for validation, not surfaced to the player.

### Available actions per item

An item's available actions depend on:
- The item's `actions` list (statically defined)
- The item's `current_state` (e.g., a closed container can be "open", an open one can be "close")
- The player's inventory (e.g., "use key" is available only if the player has a matching key)
- The item's triggers (e.g., `on_toggle_on`/`on_toggle_off` implies toggle is available)
- Area conditions (light level, player state)

## Proposed Design

### Phase 1: Determine available actions in the backend

Add a method `_get_available_actions(item_node, player)` that returns a list of action descriptors:

```python
[
    {"action": "examine", "label": "Look at the clock closely", "enabled": True},
    {"action": "open", "label": "Open the glass door", "enabled": False, "reason": "It's already open"},
    {"action": "use brass_key", "label": "Insert a key", "enabled": True},
    {"action": "toggle", "label": "Toggle the chime", "enabled": True},
]
```

Rules for determining available actions:
- `examine` — always available (it's the current action)
- `take` — available if item is in room and not too heavy
- `drop` — available if item is carried
- `open`/`close` — available if item has openable state and isn't already in that state
- `use` — available if item has triggers for `on_use` or `on_use_on`
- `use [target]` — available if player has a matching item in inventory and target has relevant triggers
- `toggle` — available if item has `on_toggle_on`/`on_toggle_off` triggers
- `eat`/`drink` — available if item has food/drink tags

### Phase 2: Append to examine output

Modify `get_item_desc()` to append available actions:

```python
desc += "\n\nAvailable actions:"
for action in actions:
    status = "" if action["enabled"] else f" ({action['reason']})"
    desc += f"\n  [{action['action']}] {action['label']}{status}"
```

### Phase 3: (Future) Make actions clickable in the frontend

In the examine output displayed in the event stream, render actions as clickable buttons that populate the command input. This would require changes to the event stream rendering in `static/js/event-stream.js`.

## Files Affected

- `virtual_world_engine.py` — `get_item_desc()`, new `_get_available_actions()`
- `static/js/event-stream.js` — (optional) render clickable action buttons in examine output
- `world_template.json` — add action metadata for template items
