---
group: Trigger System
wiki: "[[Rules Engine/Triggers & Effects]]"
---

# Task 114: Trigger Editor — Nested Rule Tree Conditions + Flow Reorder

**Status**: Done  
**Priority**: High  
**Filed**: 2026-07-29  
**Updated**: 2026-07-31  

---

## Summary

Rework the TriggerEditor (form-based) to:
1. **Reorder flow**: Trigger Type → **Conditions** → Effects → Messages (was: Trigger → Effects → Conditions → Messages)
2. **Nested rule tree for conditions**: Replace flat conditions list + single AND/OR toggle with a recursive tree builder supporting grouped boolean logic like `(A AND B) OR (C AND D)`
3. **Fix TriggerGraph z-index bug**: Right-click context menu renders behind the canvas

---

## Backend Changes

### Bug Fix: condition singular never evaluated

`_execute_triggers` reads `conditions` (plural) but serialization stores `condition` (singular). Most library item conditions are dead code.

**Fix**: Add fallback lookup in `_execute_triggers` — if `conditions` (plural) is empty/absent, check `condition` (singular) and wrap it in a list.

### Unify condition evaluation

Two separate evaluators exist:
- `_evaluate_trigger_condition` — flat list, item context (has_item, skill_check, etc.)
- `_evaluate_conditions` — tree format, NPC context (eq, in_area, proximity, etc.)

**Fix**: Make `_execute_triggers` detect tree format (dict with `"operator"` key) and dispatch to `_evaluate_conditions`. Add missing item-trigger condition types to `_evaluate_conditions` (skill_check, temperature_below/above, uses_reached/above, has_trait).

### New condition data format

```json
// Tree format (new)
{
  "conditions": {
    "operator": "and",
    "conditions": [
      { "type": "has_item", "value": "Brass Key" },
      {
        "operator": "or",
        "conditions": [
          { "type": "skill_check", "skill": "Athletics", "dc": 10 },
          { "type": "state_equals", "target": "door_south", "value": "open" }
        ]
      }
    ]
  }
}
```

Backward compat: flat conditions array + conditions_logic still supported.

### Files to touch

| File | Change |
|------|--------|
| `engine/trigger_system.py` | Add singular fallback, tree detection, merge condition types |
| `engine/serialization.py` | Probably no change (stores what it gets) |

---

## Frontend Changes

### Flow reorder

Current: Trigger Type → Effects → Conditions → Messages
New: **Trigger Type → Conditions → Effects → Messages**

The natural language flow: "WHEN [trigger] IF [conditions] THEN [effects]"

### Nested rule tree UI

Replace the flat conditions section with a visual rule tree builder:

```
🧩 Conditions
  WHEN ALL of these are true:
  ┌─────────────────────────────────────┐
  │ AND │ [skill_check ▼]               │
  │     │ Skill: [Athletics] DC: [10]  ✕│
  ├─────────────────────────────────────┤
  │ AND │ [group ▼] [+ group -]         │
  │     │ ┌─────────────────────────┐    │
  │     │ OR │ [has_item ▼]         │    │
  │     │    │ Value: [key]        ✕│    │
  │     │ ├─────────────────────────┤    │
  │     │ OR │ [state_equals ▼]     │    │
  │     │    │ Target: [door]       │    │
  │     │    │ Value: [open]       ✕│    │
  │     │ └─────────────────────────┘    │
  └─────────────────────────────────────┘
  [+ Add Condition] [+ Add Group]
```

#### UI elements:
- **AND/OR pill** at start of each row — toggleable, determines logic between this and previous sibling
- **Condition row** — type dropdown + params (same as current)
- **Group row** — visual bracket/indent containing child conditions, same AND/OR logic
- **➕ Add Condition** — adds a leaf row
- **➕ Add Group** — adds a nested sub-group
- **Group/ungroup** — maybe a button to wrap selected? Or just manual grouping via "Add Group"
- **✕ Remove** on each row (same as current)

#### Visual design:
- Groups indented with left border/bracket
- Operator pills placed between rows (not on them)
- Color: pink accent for conditions (same as current)

### Data flow

Collect data builds nested tree:
```javascript
{
  conditions: {
    operator: "and",
    conditions: [
      { type: "skill_check", skill: "Athletics", dc: 10 },
      {
        operator: "or",
        conditions: [
          { type: "has_item", value: "key" },
          { type: "has_item", value: "crowbar" }
        ]
      }
    ]
  }
}
```

Initial data loading: parse tree format and render recursively.

### TriggerGraph z-index fix

The context menu in `trigger-graph.js` has a z-index lower than the canvas overlay. Find the menu element and bump its z-index above the overlay.

---

## Implementation Order

1. Fix TriggerGraph z-index (2 lines, separate concern)
2. Backend: condition evaluation unification (safest first, verify existing tests pass)
3. Frontend: TriggerEditor rework (biggest piece)
4. Test: verify with existing triggers + new nested conditions

---

## Files to touch

| File | Change |
|------|--------|
| `static/js/shared/trigger-graph.js` | Fix z-index on context menu |
| `engine/trigger_system.py` | Unify condition evaluation |
| `static/js/shared/trigger-editor.js` | Major rework — flow reorder, nested rule tree |
| `static/css/main.css` | Maybe add rule tree styles |

---

## Verification

1. Open Inspector → Add Trigger → verify conditions section has nested builder
2. Build `(has_item key AND skill_check) OR (state_equals door open)` — confirm tree renders right
3. Save trigger → reload → confirm conditions load correctly
4. Check existing triggers in world still fire correctly (backward compat)
5. Right-click in TriggerGraph → menu visible above canvas

---

## Hotfix 2026-07-29: Lost Trigger Effects

**Bug**: `_extractTriggersFromEdges` in `item-library.js` read `edgeProperties.effects` which was `undefined` for old-format triggers stored in graph edges. Fell back to `[]`, saving empty effects arrays.

**Root cause**: The sync-to-library function didn't handle the legacy trigger format (`effect_type` + `effect_params`). Old triggers stored in graph edges before the TriggerEditor rework had no `effects` array.

**Fix**: `_extractTriggersFromEdges` now detects old format and converts:
```javascript
const effects = edgeProperties.effects?.length > 0
    ? edgeProperties.effects
    : (edgeProperties.effect_type
        ? [{ type: edgeProperties.effect_type, params: edgeProperties.effect_params || {} }]
        : []);
```
Also converts flat conditions array → tree format for consistency.

**Restored**: 56 library items had their trigger effects recovered from git history HEAD~1 via a Python migration script.

**Prevention**: The conversion now happens each time triggers are extracted from graph edges, so old-format items synced to library will automatically upgrade to the new format.

---

## Implementation Summary (2026-07-31)

All items implemented and verified:

| Item | Status | Location |
|------|--------|----------|
| Flow reorder (Trigger → Conditions → Effects → Messages) | ✅ | `trigger-editor.js:98` (conditions before effects) |
| Nested rule tree UI | ✅ | `trigger-editor.js:316-638` — `_loadConditionTree()`, `_renderConditionGroup()`, `_collectConditionGroup()` |
| Singular condition fallback | ✅ | `trigger_system.py:1146-1153` |
| Tree format detection | ✅ | `trigger_system.py:1173-1183` |
| Unified condition evaluator | ✅ | `trigger_system.py:337` — `_evaluate_conditions()` handles both tree and flat |
| TriggerGraph z-index fix | ✅ | `trigger-graph.js:522` — context menu z-index:10001 > modal z-index:9999 |