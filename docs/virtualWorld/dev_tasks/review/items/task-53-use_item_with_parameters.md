---
group: Items & Crafting
wiki: "[[Items & Inventory/Items Overview]]"
---

# Use Item with Parameters (Text/Message Passing)

**Filed**: 2026-07-15
**Priority**: Medium
**Status**: In Review — implemented (code-verified 2026-08-11). `use_item_on(item, target, params=params)` at `routes/action.py:305`; `set_description` effect at `engine/effects.py:988`; `{params}` usable in effect values.

---

## Summary

Items should support parameterized use: "use pen on paper 'i wrote this'" writes text on the paper. "use phone text miki 'hi miki'" sends a message to Miki's phone. This enables item-to-item communication, writing systems, and complex interactive items.

## Current State

### Command parsing (`app.py:186-202`)

The `use` command already handles `"use [item] on [target] '[params]'"` pattern:

```python
elif cmd.startswith("use "):
    use_str = cmd[4:].strip()
    if " on " in use_str:
        parts = use_str.split(" on ", 1)
        # Check for quoted params: use pen on paper "i wrote this"
        quote_match = re.match(r'^(.+?)\s+"(.+)"$', rest)
```

### Engine (`virtual_world_engine.py:1758+`)

`use_item_on()` already accepts `params` and passes it to triggers. But there's no generic mechanism for items to use params meaningfully.

### Trigger system

`on_use_on` triggers can check target_name but have no access to the params text.

## Proposed Design

### Phase 1: Params in trigger context

When `use_item_on()` fires `on_use_on` triggers, pass the `params` text into the trigger context so conditions and effects can reference it.

New condition type: `params_match` — checks if params match a pattern.

New effect type: `set_description` — changes a node's description (e.g., paper now has "i wrote this" as its description).

### Phase 2: Built-in param effects

| Item | "use [item] on [target] '[text]'" | Effect |
|------|-----------------------------------|--------|
| pen | paper "Hello World" | Paper description becomes "Hello World" |
| phone | phone "Call Miki" | Notify Miki's player |
| radio | radio "tune 98.7" | Change room noise |
| note | note "Remember milk" | Note description changes |

### Phase 3: Custom param triggers

Allow triggers to reference `{params}` in effect messages:
- message: `"You write '{params}' on the paper."`
- set_description: updates target's description to params

### Example trigger config for a pen

```json
{
  "trigger_type": "on_use_on",
  "effect_type": "set_description",
  "effect_params": {
    "message": "You write '{params}' on the paper.",
    "target_property": "description",
    "value": "{params}"
  }
}
```

## Audit

**Status**: Ready to test
**How to test**:
- Create a "pen" item with `on_use_on` trigger: effect_type `set_description`, value `"{params}"`, target the paper item ID.
- In-game: `use pen on paper "Hello World"`. Verify the paper's description changes to "Hello World".
- Create a trigger with a message containing `{params}` (e.g. `"You write '{params}' on the paper."`). Verify the message renders the params text.

## Files Affected

- `virtual_world_engine.py` — pass params to trigger context, add set_description effect
- `static/js/item-library.js` — add set_description effect type, params variable support
