# Contextual Action Feedback — Smart Error Messages

**Filed**: 2026-07-20
**Priority**: High
**Status**: Done — verified 2026-08-03. `_contextual_failure` (engine/trigger_system.py:975) wired into take (item_actions.py:469), eat/drink (:767,:835), use (:946). The proposed weight/encumbrance check (item 4) was not implemented.

---

## Summary

When an action fails on an item (not found, wrong verb, impossible action), instead of
generic "can't do that" messages, return a first-person contextual reason explaining
*why* plus a list of what actions ARE valid for that item. This teaches the AI agent
what's possible and makes the world feel more alive.

## Problem

Currently, failing actions produce robotic messages:

| Action | Current message | Wanted |
|--------|----------------|--------|
| `eat rock` | "Unknown command" or generic ValueError | "I pause — that's a rock, not food. I could **examine** it." |
| `take curtains` | Generic "can't find it" or nothing | "I realize I have no need for the curtains. I could **examine** them." |
| `use book` (no triggers) | "nothing happens" | "I flip through the book but find nothing useful to do with it." |
| `eat coat` | Generic failure | "I stop myself — that's not something you eat." |

## Supported Actions (Simplified Set)

| Action | Maps To | Validation |
|--------|---------|------------|
| examine | examine | Always valid |
| take | take | Check `"take"` in item.actions |
| use | use | Check if triggers exist OR `"use"` in item.actions |
| open | open | Check `"open"` in item.actions or tags |
| close | close | Check item state is open |
| eat | use (flavor) | Check `"food"` tag or `"eat"` in actions |
| drink | use (flavor) | Check `"drink"` tag or `"drink"` in actions |
| read | examine (flavor) | Treat as examine |
| light | use (flavor) | Check for toggle/use triggers |
| activate | use (synonym) | Same as use |
| toggle | toggle | Check for on_toggle_on/off triggers |
| equip | equip | Check if equippable |
| unequip | equip | Check if equipped |
| break | break | Check if breakable |

## Implementation

### 1. Add `_contextual_failure()` to engine

A helper that generates a first-person failure reason:

```python
def _contextual_failure(self, actor, verb, target_name, available_actions):
    """Generate a first-person contextual failure message."""
    reasons = {
        "take": "I reach for the {item} but stop — I have no need for it.",
        "use": "I examine the {item} but can't figure out what to do with it.",
        "eat": "I pause — that's not food.",
        "drink": "That's not something you drink.",
        "open": "The {item} doesn't open.",
        "close": "The {item} isn't something you can close.",
        "break": "I don't think breaking the {item} would accomplish anything.",
    }
    msg = reasons.get(verb, "I try, but nothing useful happens.")
    msg = msg.format(item=target_name)

    # Append available actions
    valid = [a["label"] for a in available_actions if a["enabled"]]
    if valid:
        msg += f" I could {valid[0].lower()}" + (f" or {', '.join(v.lower() for v in valid[1:])}." if len(valid) > 1 else ".")
    return msg
```

### 2. Add validation in `take_item()`

Before attempting to take, check `"take" in item.actions`:

```python
if "take" not in item_data.get("actions", []):
    available = self._get_available_actions(item_id)
    return self._contextual_failure(actor, "take", item_name, available)
```

### 3. Add validation in `use_item()` / `use_item_on()`

Check if the item has `on_use`/`on_use_on` triggers or `"use"` in actions:

```python
# In use_item() or use_item_on(), after finding the item but before processing:
has_triggers = self._has_triggers_of_type(item_id, "on_use") or self._has_triggers_of_type(item_id, "on_use_on")
if "use" not in item_data.get("actions", []) and not has_triggers:
    # Also check for eat/drink tags for contextual message
    is_food = "food" in item_data.get("tags", [])
    is_drink = "drink" in item_data.get("tags", [])
    if is_food and verb == "eat":
        # Let it pass - it's food
        pass
    elif not has_triggers:
        available = self._get_available_actions(item_id)
        return self._contextual_failure(actor, "use", item_name, available)
```

### 4. Add weight/encumbrance check

Read `weight` from item properties, compare to player's strength stat:

```python
item_weight = item_data.get("weight", 0.1)
player_strength = self.players.get(actor, {}).get("strength", 10)  # or however strength is stored
if item_weight > player_strength * 2:  # arbitrary threshold
    available = self._get_available_actions(item_id)
    return f"I try to lift the {item_name} but it's far too heavy. {available_msg}"
```

### 5. Wire eat/drink into contextual path

Currently `eat` and `drink` are separate branches in app.py that call `use_item()`. Validate through the same path:

```
eat rock → use_item("rock") → check "food" tag → fail: "I pause — that's a rock, not food."
```

### 6. Update app.py error handling

The existing `ValueError` catch (line 497) already converts engine errors to output. Smart errors returned as strings (not exceptions) should flow through the same path. No app.py changes needed if engine returns contextual strings.

## How Agents Benefit

When an agent tries `eat rock` and gets:
```
"I pause — that's a rock, not food. I could **examine** it."
```

The agent's LLM learns:
- Rocks aren't food
- The action failed because the item category doesn't match
- Examine is available as an alternative

Over time, this teaches agents the game's physics and item grammar without hardcoded rules.

## Files Affected

- `virtual_world_engine.py` — `_contextual_failure()`, validation in `take_item()`, `use_item()`, `use_item_on()`
- `app.py` — possibly minor adjustments to how snake_case verbs map (read→examine, light→use, etc.)
