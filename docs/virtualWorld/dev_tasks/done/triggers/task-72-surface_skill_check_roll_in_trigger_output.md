# Surface Skill Check Roll in Trigger Output

**Filed**: 2026-07-19
**Priority**: Medium
**Status**: Done — verified 2026-08-03. Option A implemented: `_last_skill_check_msg` set in the skill_check condition paths (engine/trigger_system.py:287, 579) and appended to trigger outputs then reset (`:1252-1254`).

## Summary

When a trigger condition is of type `skill_check`, the roll result message (e.g., `"[Skill Check] Investigation vs DC 14 (medium): roll=15 + 2 = 17 => success"`) is discarded by `_evaluate_trigger_condition`. The player sees the `success_message` or `fail_message` from the trigger but never sees the actual dice roll.

## Current State

`virtual_world_engine.py:1131-1135`:

```python
elif ctype == "skill_check":
    skill = condition.get("skill", "Athletics")
    dc = int(condition.get("dc", 10))
    success, total, msg = self.skill_check(skill, dc)
    return success  # ← msg discarded!
```

`skill_check()` at line 3940-3943 generates the message and writes it to `self.add_log_entry()`, but `_evaluate_trigger_condition` only returns the boolean `success`. The caller (`_execute_triggers`) has no way to surface the roll.

Additionally, when the condition fails and the trigger's `fail_message` is shown (lines 1298-1301, 1308-1311), the roll still isn't included in the output.

## Fix

### Option A: Store the roll message on the world instance

Add a `self._last_skill_check_msg` attribute that `skill_check()` sets and `_execute_triggers()` appends to outputs:

```python
# In skill_check:
self._last_skill_check_msg = message
return (success, total, message)

# In _execute_triggers, after evaluating conditions:
if ctype == "skill_check" and self._last_skill_check_msg:
    outputs.append(self._last_skill_check_msg)
```

Drawback: stateful, could be stale if multiple skill checks run.

### Option B: Change return type of `_evaluate_trigger_condition`

Return a tuple `(success, msg)` instead of bool. Update callers at lines 1294 and 1306 to handle the tuple.

This is cleaner but requires updating all condition evaluation callers.

### Option C: Surface through trigger effect params

Instead of the engine adding the roll message, configure the trigger's `fail_message` and `success_message` to include `{roll_result}` template variables. But the engine doesn't pass the roll as a template variable.

**Recommendation**: Option A for simplicity. Store `self._last_skill_check_msg` and append it to trigger outputs when the condition type is `skill_check`.

## Edge Cases

- Multiple skill check conditions in one trigger: only the last roll is surfaced
- Skill check in nested conditions (AND/OR): will surface per evaluation
- Skill check passes and trigger has `success_message`: roll message should appear before the success message

## Files

- `virtual_world_engine.py:1131-1135` — `_evaluate_trigger_condition`
- `virtual_world_engine.py:3920-3943` — `skill_check()`
