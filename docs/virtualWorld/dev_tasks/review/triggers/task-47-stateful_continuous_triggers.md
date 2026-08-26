---
group: Trigger System
wiki: "[[Rules Engine/Triggers & Effects]]"
---

# Stateful Continuous Triggers (While State = X → Effect)

**Filed**: 2026-07-15
**Priority**: High
**Status**: In Review — implemented (code-verified 2026-08-11). `on_state_enter`/`on_state_exit` trigger types (`engine/trigger_system.py:40-41/1759/2002`, fired on state change at `engine/effects.py:478-487`); `on_tick` + `state_equals` pattern documented in Audit below.

---

## Summary

Triggers currently fire once on an event (on_use, on_take, on_tick). There is no "while state = X" continuous trigger pattern. Examples:
- Fireplace state = "lit" → room temperature increases while lit
- Flashlight/torch state = "on" → room light = 70 while on
- Character is in room → sound propagates to adjacent room

## Current State

### `_execute_triggers()` (`virtual_world_engine.py:875-1012`)

Triggers are event-driven:
- `on_use`, `on_take`, `on_examine`, etc. fire once when the action happens
- `on_tick` fires once per tick but has no state-based gating baked in

### `set_state` effect

The existing `set_state` effect (`virtual_world_engine.py:978-985`) can change `current_state` on any node. But there's no mechanism to say "while state is X, apply effect Y."

### Working around it

A player could create an `on_tick` trigger with a `state_equals` condition like:
- trigger_type: on_tick
- condition: { type: "state_equals", value: "fireplace=lit" }
- effect: set_environment { temperature: 30 }

But this relies on the item having the right `current_state` and the on_tick system processing it. This works for simple cases but has no cleanup when state changes back.

## Proposed Change

### Phase 1: Add `while_state` condition support

The condition system already has `state_equals`. We need to ensure:
1. Items can have their `current_state` checked in conditions
2. `on_tick` triggers fire reliably for state-based checks
3. A "while state = X" trigger pattern is documented and usable

This is mostly already possible but not documented or exposed in the UI:

```
trigger_type: on_tick
condition: { type: "state_equals", value: "lit" }
effect: { type: "set_environment", params: { temperature: 30 } }
```

### Phase 2: `on_state_enter` / `on_state_exit` triggers

Add new trigger types:
- `on_state_enter` — fires when an item's state changes TO a specific value (e.g., fireplace lit → start warming)
- `on_state_exit` — fires when an item's state changes FROM a specific value (e.g., fireplace extinguished → stop warming)

These would require the state change code to detect transitions and fire relevant triggers.

### Phase 3: UI support

In the trigger editor (`item-library.js`), add:
- Conditional state selection dropdown (target node + expected state)
- Better documentation for state-based trigger patterns

## Example Use Cases

| Item | State | Effect |
|------|-------|--------|
| fireplace | lit → on_state_enter | temperature += 10 |
| fireplace | lit → on_state_exit | temperature -= 10 |
| flashlight | on → on_tick + state_equals=on | current_area.light = 70 |
| torch | on → on_tick + state_equals=on | current_area.light = 60 |
| radio | on → on_tick + state_equals=on | room noise = "music" |

## Audit

**Status**: Ready to test
**How to test**:
- Create an item with `current_state` (e.g. a fireplace with state "unlit"). Add an `on_state_enter` trigger: state="lit" → effect `set_environment` temperature=30. Add an `on_state_exit` trigger: state="unlit" → effect `set_environment` temperature=21.
- Use the item to toggle state between lit/unlit. Verify room temperature changes accordingly.
- Check the trigger editor in Item Library — verify `on_state_enter` and `on_state_exit` appear in the trigger type dropdown, with a "Target State" input field.

## Files Affected

- `virtual_world_engine.py` — add on_state_enter/on_state_exit trigger types, detect state transitions
- `static/js/item-library.js` — add new trigger types to UI