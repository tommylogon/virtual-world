---
group: Trigger System
wiki: "[[Rules Engine/Triggers & Effects]]"
---

# Multi-Effect / Multi-Condition Triggers

**Filed**: 2026-07-17
**Priority**: High
**Status**: In Review — implemented (code-verified 2026-08-11). `effects`/`conditions` arrays supported with backward compat (single `effect_type`/`condition`); editor formats hint at `main.js:313`; `has_items`, `state_equals`, `consume_item`, `set_state` in trigger engine.

---

## Summary

Triggers currently support one `effect_type` + `effect_params` and one `condition`. To support recipes (lighting a fireplace needs: consume kindling + set_state + set_environment + message), triggers need arrays of both effects and conditions.

## Current Format

```json
{
  "trigger_type": "on_use",
  "condition": { "type": "has_item", "value": "kindling" },
  "effect_type": "message",
  "effect_params": { "message": "..." }
}
```

## Proposed Format

```json
{
  "trigger_type": "on_use",
  "conditions": [
    { "type": "has_items", "value": ["kindling", "tinderbox"] },
    { "type": "state_equals", "target": "fireplace", "value": "off" }
  ],
  "failure_message": "You need kindling and a tinderbox to light the fireplace.",
  "effects": [
    { "type": "message", "text": "You arrange the kindling..." },
    { "type": "set_state", "target": "fireplace", "value": "on" },
    { "type": "consume_item", "item": "kindling" },
    { "type": "set_environment", "params": { "temperature": 22, "light": 80, "noise": "crackling fire", "smell": "woodsmoke" } }
  ]
}
```

## Requirements

### Format
- `effects` array → executed in order, all effects run
- `conditions` array → ALL must pass for trigger to fire (AND logic)
- `failure_message` → shown when conditions fail, can reference missing items
- Backward compatible: if `effects` absent, use `effect_type`/`effect_params`
- Backward compatible: if `conditions` absent, use single `condition`

### New Condition Types
- `has_items` — checks player carries ALL listed items (via graph edges, NOT `self.player.inventory`)
  - Similar to existing `has_item` but takes an array and uses correct inventory source
  - Fix the existing `has_item` bug simultaneously (it reads dead `self.player.inventory` list instead of graph)
- `state_equals` — checks `current_state` on a target node (exists but may need polish)

### New Effect Types
- `set_state` — set `current_state` on a target node (e.g. `"on"`, `"lit"`, `"open"`)
- `consume_item` — decrement uses or remove item from player inventory
- `message` — display text to player (already exists as effect_type but needs to work as array entry)

### New Trigger Types (if needed)
- `on_state_enter` / `on_state_exit` — fires when a node's state changes TO/FROM a value (from stateful_continuous_triggers card)

## Execution Logic

In `_execute_triggers()`:
1. Collect all triggers matching the event (e.g. `on_use`)
2. For each trigger, evaluate ALL conditions
3. If all pass, execute ALL effects in order
4. If conditions fail and `failure_message` exists, show it

## Engine Changes

- `virtual_world_engine.py` — `_execute_triggers()` format parsing, new condition/effect dispatch
- `static/js/item-library.js` — trigger editor UI for array of effects
- `world_template.json` — migrate the fireplace triggers once format is stable

## Dependencies

- Prerequisite for: fireplace_lighting_recipe, way_trigger_events, heat_propagation