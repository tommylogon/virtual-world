---
group: Trigger System
wiki: "[[World Building/Doors & Connections]]"
---

# Cross-Entity Trigger Effects (Target Any Node)

**Filed**: 2026-07-17 (updated 2026-07-21)
**Priority**: High
**Status**: Complete — Move to Review

---

## Summary

Triggers need to target and modify arbitrary nodes (items, ways, areas, characters) — not just the trigger's source node or current room. Already proven: `front_way` `on_open` → `set_state` on `item_fireplace` works. This card expands to a full cross-entity effect system.

## Complete

### Effects
| Effect | Params | Engine | Frontend | Notes |
|--------|--------|--------|----------|-------|
| `set_state` | `node_id`, `state` | ✅ | ✅ | Targets any node |
| `set_hidden` | `node_id`, `hidden` (bool) | ✅ | ✅ | `{ node_id: "item_spellbook", hidden: false }` |
| `adjust_uses` | `node_id`, `delta` (int) | ✅ | ✅ | `{ node_id: "item_lockbox", delta: -1 }` |
| `set_environment` (cross-room) | `node_id`, `light`, `temp`, `noise`, `smell`, `air` | ✅ | ✅ | Target any room |
| `set_description` | `target`, `value` | ✅ | ✅ | Replace full description |
| `append_description` | `target`, `text` | ✅ | ✅ | NEW — appends text with `\n` separator |
| `end_scenario` / `restart_scenario` | — | ✅ | ✅ | Stop/restart game |
| `rename` | `new_name`, `node_id` | ✅ | ✅ | Rename items |
| `unlock_way` | `way_id` | ✅ | ✅ | |
| `spawn_item` / `remove_item` | `item_id` | ✅ | ✅ | |
| `drain` | `amount`, `stat` | ✅ | ✅ | |

### Conditions
| Condition | Engine | Frontend | Notes |
|-----------|--------|----------|-------|
| `has_item` | ✅ | ✅ | Searchable from all world + library items |
| `state_equals` | ✅ | ✅ | NEW: target field in UI — `{ target: "item_fireplace", value: "lit" }` or just `{ value: "lit" }` for trigger source |
| `random_chance` | ✅ | ✅ | |
| `skill_check` | ✅ | ✅ | |
| `uses_reached` | ✅ | ✅ | |

### UI
- ✅ Trigger editor works on items, ways, any node (node-type-agnostic)
- ✅ Cross-entity effect targeting with node name datalist (items + areas + ways)
- ✅ Locked state/checkbox in item inspector + library editor
- ✅ Cancel Step button (aborts LLM)
- ✅ Removed legacy unlock UI

### Template
- ✅ Front door → fireplace snuffing wired (on_open + state_equals + set_state + set_environment)
- ✅ Desk unlock → spellbook reveal (on_use + has_item + set_state + set_hidden)

## Use Cases

### 1. Desk unlock → reveal spellbook (Study)
Trigger: `on_use` on `item_desk`, condition: `has_item: "brass_key"`
Effects:
- `set_state` → `node_id: "item_desk", state: "open"`
- `set_hidden` → `node_id: "item_Spellbook ", hidden: false`
- `message` → "The lock clicks open. Inside you see a dusty spellbook."

### 2. Front door open → snuffs fireplace (DONE)
Trigger: `on_open` on `way_front`, condition: `state_equals: "item_fireplace" = "lit"`
Effects:
- `set_state` → `node_id: "item_fireplace", state: "unlit"`
- `set_environment` → `node_id: "area_living_area", temperature: -5, noise: "wind howling", smell: "cold air"`
- `message` → "A blast of freezing wind roars through the open door, snuffing out the fire!"

### 3. Lockbox with limited uses
Trigger: `on_use` on `item_lockbox`
Effects:
- `adjust_uses` → `node_id: "item_lockbox", delta: -1`
- `spawn_item` → `item_id: "gold_coin"`

## Verification

### 1. `append_description` effect
1. Open an item's trigger editor (e.g. a note/paper item)
2. Add effect type: **Append to Description** (`append_description`)
3. Set Target Node to the item's own ID (or another item)
4. Set Text to Append: `"\nSomeone has written in this book."`
5. Save the trigger
6. In the game, fire the trigger (e.g. `use` or `examine`)
7. Examine the target item — its description should now include the appended text

### 2. `state_equals` with cross-entity target
1. Open any item's trigger editor
2. Add condition type: **Node state equals** (`state_equals`)
3. You should see a **Target node** input (optional) plus the **Value** input
4. Set Target to `item_fireplace` and Value to `lit`
5. Save — this condition now checks the fireplace's state, not the trigger source
6. (The front door → fireplace example in the template already uses this)

### 3. Existing cross-entity effects still work
- `set_state` with `node_id` targeting a different node
- `set_environment` with `node_id` targeting a different room
- `set_hidden` to reveal/hide items anywhere

## Files Changed (this batch — 2026-07-21)

- `virtual_world_engine.py` — added `append_description` effect handler
- `static/js/inspector.js` — `state_equals` target field in condition editor + `append_description` effect UI
- `static/js/item-library.js` — `state_equals` target field + `append_description` effect type + node datalists
- `static/js/main.js` — `append_description` in AI prompt
- `static/js/prompt-docs.js` — docs for `append_description` + updated `state_equals`
- `dev_tasks/inprogress/task-15-way_trigger_events.md` — updated status to complete

### Previous batches (2026-07-20)
- `virtual_world_engine.py` — `set_hidden`, `adjust_uses`, `end_scenario`, `restart_scenario` effects
- `static/js/inspector.js` — has_item search, locked state/checkbox, removed unlock UI
- `static/js/item-library.js` — has_item search, locked checkbox, new effect types
- `static/js/agent-engine.js` — cancel step, scenario_ended detection, abort controller
- `static/js/ui-controller.js` — cancel button visibility
- `static/js/main.js` — `cancelStep()` global
- `static/js/api.js` — `resetWorld()` method
- `static/js/graph-manager.js` — removed unlock context menu
- `static/js/prompt-docs.js` — new effect docs
- `app.py` — scenario_ended flags in API responses
- `templates/index.html` — cancel button
- `world_template.json` — locked state handling
