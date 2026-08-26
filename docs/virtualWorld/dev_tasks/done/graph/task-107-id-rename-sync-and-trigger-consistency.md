---
type: task
status: done
area: graph
priority: medium
created: 2026-07-26
implemented: 2026-07-26
wiki: "[[World Building/Graph System]]"
---

# ID Rename Sync + Trigger Consistency

---

## Summary

When renaming an entity, the node ID should optionally sync with the new name. And when it does, any trigger effect params that reference the old ID must be updated too — otherwise triggers silently break.

---

## Current State

Two decoupled inputs in the inspector (every entity type: room, item, door, character):

- **Name** — free-text display name, updates via `PATCH /api/graph/node/<id>` (just changes `node.name`)
- **ID** — small editable text field showing `item_rusty_key`, calls `renameNode(oldId, newId)` on change, which hits `POST /api/graph/node/<id>/rename`

`rename_node` in `routes/graph.py:97` handles the ID change:
1. Creates a new `Node` with same type/name/properties but new ID
2. Scans all edges — any with `edge.source == old_id` or `edge.target == old_id` gets updated to new ID
3. Deletes old node

### The gap

Step 2 only updates **edge source/target** fields. But trigger effects store node IDs as string-valued **effect parameters** inside the trigger node's `properties` dict:

| Effect | Param | Example |
|--------|-------|--------|
| `spawn_item` | `item_id` | `item_rusty_key` |
| `remove_item` | `item_id` | `item_rusty_key` |
| `set_state` | `node_id` | `way_kitchen_west` |
| `set_environment` | `node_id` | `area_cellar` |
| `unlock_way` | `way_id` | `way_kitchen_west` |

These are just strings nested in `trigger_node.properties["actions"][N]["item_id"]`. The rename has no idea they exist — they become dead references.

---

## Proposed Solution

### 1. "Sync ID from Name" button

Add a button in the inspector next to the manual ID field. When clicked:

1. Normalize the display name into an ID: `.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '')`
2. Prefix with the node type: `{type}_` (e.g. `item_`, `area_`, `way_`, `player_`)
3. If the generated ID matches the current ID, do nothing
4. If it's different, call `renameNode` with the new ID
5. After rename completes, call a new **scan triggers** step

Don't make this automatic on name change — keep it a button. Reasons:
- Name changes during typing would spam renames
- Sometimes you want a stable ID even after rename (triggers reference it)
- Rename is a heavyweight graph operation

### 2. Trigger param scan after rename

After `renameNode` succeeds, scan every `logic_trigger` node in the graph:

```python
def update_trigger_references(graph, old_id, new_id):
    for node in graph.nodes.values():
        if node.type != "logic_trigger":
            continue
        actions = node.properties.get("actions", [])
        changed = False
        for action in actions:
            for param_key in ("item_id", "node_id", "way_id"):
                if action.get(param_key) == old_id:
                    action[param_key] = new_id
                    changed = True
        if changed:
            node.updated = time.time()
```

Run this server-side as part of the rename flow (not a separate API call — piggyback on the existing endpoint).

### 3. Where to add

- **Backend**: Extend `routes/graph.py:rename_node` to call `update_trigger_references()` after the edge update
- **Frontend**: Add a "🔄 Sync ID" button in each inspector view that has the ID field already:
  - `inspector/area-view.js` (line 121 area)
  - `inspector/item-view.js` (line 129 area)
  - `inspector/way-view.js` (line 60 area)
  - `inspector/agent-view.js` (add one — character panel currently may not show ID)

---

## Files Changed

| File | Change |
|------|--------|
| `routes/graph.py` | Extended `rename_node` to scan all `logic_trigger` nodes and update `item_id`/`node_id`/`way_id` effect params that reference the old ID |
| `inspector/area-view.js` | Added 🔄 Sync ID button next to ID field |
| `inspector/item-view.js` | Same |
| `inspector/way-view.js` | Same |
| `inspector/agent-view.js` | Added editable name field, Node ID display with inline edit, and 🔄 Sync ID button |
| `inspector/helpers.js` | Added `InspectorHelpers.syncIdFromName(nodeId, displayName)` — derives `{prefix}_{sanitized}` from display name, no-ops if match, calls `renameNode` |

---

## Implementation Notes

- `syncIdFromName` extracts the prefix (`item_`, `area_`, `way_`, `player_`) from the current node ID, normalizes the display name, and only calls rename if the generated ID differs
- Duplicate protection is handled by the existing backend 409 response — `renameNode` shows the error in the event stream
- The trigger param scan runs inline in `rename_node` after the edge update, not as a separate API call

---

## Edge Cases

- **Duplicate generated ID**: If `item_sword` already exists and you rename "Sword" → the generated ID `item_sword` conflicts. Current API returns 409. The button should show an error message and not change anything.
- **No-op**: If the normalized ID matches the current ID, button does nothing (name change didn't affect the sanitized form).
- **Trigger on the renamed node itself**: If the renamed item has its own triggers (e.g. `item_rusty_key` with an `on_take` trigger), those trigger edges reference the old ID. The edge-update step in `rename_node` already handles this — trigger edges are just `Edge(source=item_id, target=trigger_node_id, type="triggers")`, so they get updated.
- **Characters**: Player characters are referenced by **name** in the `players` dict, not by node ID. Renaming the player node ID shouldn't break player logic, but player node IDs are largely unused. Low risk.

---

## Test Plan

1. Rename "Rusty Key" to "Golden Key" → ID changes from `item_rusty_key` to `item_golden_key`
2. Verify trigger edge from `item_golden_key` to its `logic_trigger` still exists
3. Verify trigger effect params (e.g. `spawn_item` with `item_id: item_rusty_key`) got updated to `item_golden_key`
4. Verify the item still works (take/use triggers fire normally)
5. Test rename to same ID as another node → 409 error shown properly
6. Test name change that normalizes to same ID → no-op, no error
