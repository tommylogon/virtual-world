# Trigger Enhancements — adjust_vital, Multi-Effect, and UX Improvements

## Problem

The trigger system is functional but limited: only one effect and one condition per trigger, no way to adjust arbitrary vitals (Bladder, Hunger, Sanity, etc.), no template variable substitution, and the trigger editor for items lacks success/fail message fields and a searchable condition value picker. AI-generated items also don't include triggers.

## Scope

Six focused changes across three files. No new files needed.

| Feature | Files | Complexity |
|---------|-------|------------|
| 1. `adjust_vital` effect | `virtual_world_engine.py`, `item-library.js` | Small |
| 2. Multi-effect/multi-condition arrays | `virtual_world_engine.py`, `item-library.js` | Large |
| 3. Split message → success/fail in editor | `item-library.js` | Small |
| 4. has_item dropdown as searchable input | `item-library.js` | Small |
| 5. `_render_template()` + context expansion | `virtual_world_engine.py` | Medium |
| 6. AI trigger generation | `main.js` | Small |

## Detailed Design

### 1. `adjust_vital` effect type

New effect in `_execute_triggers()`:

```
effect_type: "adjust_vital"
effect_params: {
  stat: "Bladder" | any vital name,
  amount: -30 | positive or negative integer,
  target: "self" | character name,
  message: "You feel relieved."
}
```

- Adds `amount` to the specified vital (supports negative values for reduction)
- Clamps to 0-100 (HP uses Max_HP as upper bound)
- Target "self" uses active player, other targets look up by player name
- Added to `EFFECT_TYPES` in the engine and to `ItemLibrary.EFFECT_TYPES` in the frontend, with `stat` (text) + `amount` (number) + `target` (dropdown) params in the trigger editor

### 2. Multi-effect / multi-condition arrays

Backward-compatible format change. `_execute_triggers()` checks for arrays first, falls back to single values:

```python
effects = trigger_edge.properties.get("effects", None)
if effects is None:
    effects = [{ "type": effect_type, "params": effect_params }]
conditions = trigger_edge.properties.get("conditions", None)
if conditions is None:
    conditions = [condition] if condition else []
```

Execution logic:
- ALL conditions must pass (AND logic)
- If any condition fails and `failure_message` exists, show it and skip effects
- If all pass, execute ALL effects in order

Frontend trigger editor:
- Single effect row becomes list with "Add Effect" button
- Single condition row becomes list with "Add Condition" button
- Each row independently configurable (type dropdown + params)
- "Failure Message" text field shown when conditions > 0

### 3. Success/Fail messages

Engine already supports `success_message` and `fail_message` in `effect_params`. Frontend change only: split the single "Message" input into two fields ("✅ Success Message" / "❌ Fail Message") that appear when a condition is set. Both stored as `effect_params.success_message` and `effect_params.fail_message`.

### 4. has_item dropdown as searchable input

Replace the `<select id="trigger-cond-extra">` in `item-library.js` with `<input list="...">` + `<datalist>` populated with all graph items and library items. Same pattern already used for `on_use_on` target selection in the trigger editor.

### 5. `_render_template()` and context expansion

New method on `VirtualWorld`:

```python
def _render_template(self, text, context):
    """Replace {variable} placeholders with values from context dict."""
    if not text or "{param:" in text:
        # Custom params via item properties
        item_params = context.get("item_params", {})
        text = re.sub(r"\{param:(\w+)\}", lambda m: str(item_params.get(m.group(1), m.group(0))), text)
    for key, value in context.items():
        text = text.replace("{" + key + "}", str(value))
    return text
```

Context built in `_execute_triggers()` and passed through to message rendering calls. Context includes: `game_time`, `time_ticks`, `turn_number`, `player_name`, `area_name`, `item_name`, `item_state`, `player_hp`, `player_energy`, `room_light`, `room_temp`, `room_smell`, plus custom `item_params`.

### 6. AI-generated triggers

In `main.js:generateWithAI()`, extend the format hint:

```javascript
const formatHint = '{"name":"...","description":"...","actions":"examine,take,use","uses":1,"weight":0.5,"hidden":false,"triggers":[{"trigger_type":"on_use","effect_type":"message","effect_params":{"message":"..."}}]}';
```

After AI response, parse the `triggers` array and populate the triggers JSON textarea (`item-triggers-json`).

## Files Not Changed

- Way inspector trigger UI is already present (`_buildTriggersHtml` is called in `_showDoor`)
- `on_state_enter`/`on_state_exit` trigger types already implemented in engine and frontend
- Skill check condition type already implemented
- `app.py` — no changes needed
