# Character Inspector Enhancements

## Problem

Two related gaps in character data persistence and inspection:

1. **Description not round-tripped through scenario save/load.** The `description` field (set per-character in files like `jake.json`) is accepted by the inspector's "Save" button, but the backend's `api_update_player` never stores it, `to_dict()` never serializes it, and `load_from_dict` never restores it. So any character description edits are lost on scenario save, and the descriptions from imported character files never make it into the scenario file at all.

2. **Stats and skills not visible or editable.** The inspector panel shows vitals, personality, appearance, emotions, inventory, and relationships — but not the character's core D&D-style stats (STR/DEX/CON/INT/WIS/CHA) or skills (Athletics, Perception, etc.). There is no way to view or edit them through the UI. The backend also has no handler to update them.

## Scope

Three files, small surgical changes:

| File | Change |
|------|--------|
| `app.py` | Add `description`, `stats`, `skills` to `api_update_player`'s generic field handler |
| `virtual_world_engine.py` | Add `description` to `to_dict()` player serialization and `load_from_dict()` player restoration |
| `static/js/inspector.js` | Add editable stats grid and editable skills list to `showAgent()` |

## Detailed Design

### 1. Backend — `app.py:api_update_player`

Insert three handlers in the generic field block (after line 784):

```python
if "description" in data:
    p.description = data["description"]
if "stats" in data:
    p.stats = data["stats"]
if "skills" in data:
    p.skills = data["skills"]
```

This is a straightforward extension of the existing pattern — every other character field follows this same structure.

### 2. Serialization — `virtual_world_engine.py`

**`to_dict()` (line 3078):** Add `"description": getattr(p, 'description', '')` to the player serialization dict, alongside the existing `"personality"` field.

**`load_from_dict()` (line 3184):** Add `p.description = pdata.get("description", "")` to restore it on load.

### 3. Frontend — `inspector.js:showAgent()`

Add two new collapsible/inline sections between the vitals display and the Personality section:

**Stats section:** A compact 2x3 or 3x2 grid of number inputs, one per stat (STR, DEX, CON, INT, WIS, CHA). Each input fires `ApiClient.updateCharacter(charName, { stats: updatedStats })` on change, sending the full stats object.

**Skills section:** A list of editable skill rows (name + rank number). Each row has a number input for the rank and a remove button. An "Add Skill" dropdown/input at the bottom allows adding new skills. Skills also auto-save via `ApiClient.updateCharacter(charName, { skills: updatedSkills })` on any change.

Both sections use the existing `ApiClient.updateCharacter()` pattern already established for personality, description, and emotion.

## Files Not Changed

All other inspector sections (vitals, personality, appearance, inventory, relationships, timeline, memories, behaviors, nudges, manual commands, import/export) remain untouched.
