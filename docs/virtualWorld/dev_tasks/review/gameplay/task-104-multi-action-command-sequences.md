---
group: Agent AI & Behavior
wiki: "[[Items & Inventory/Items Overview]]"
---
# Task 104: Multi-Action Command Sequences

**Status**: todo
**Priority**: Low
**Filed**: 2026-07-24

## Summary

Allow characters to queue up a sequence of commands that execute in order, enabling macro-actions like "use key on door, go north, look" as one atomic operation. Useful for both player convenience and NPC multi-step behaviors. BUT not sure if i really want this or not. might tie into a action point system downt he line


## What Already Exists

- `/api/action` processes one command at a time
- Agent engine sends one action per turn
- Turn queue handles step-by-step execution
- NPC behaviors have an `actions` array

## Implementation

### Frontend
- Command input allows `;` or `→` separated sequences: `use key on door; go north; look`
- A sequence builder UI (optional) with drag-and-drop reordering
- Visual feedback showing sequence progress ("Step 2/3: going north...")

### Backend
- `/api/action/sequence` endpoint — accepts array of commands, executes in order
- Each command in sequence gets its own response event
- If one command fails, the sequence stops with a clear error
- State is passed between commands (e.g., after taking an item, use it in next step)

### Edge Cases
- **Failed command mid-sequence**: "You used the key. The door is locked. Sequence stopped."
- **Character state changes**: If "go north" moves the character, subsequent "examine" works in the new room
- **Very long sequences**: Cap at 10 commands (configurable)
- **Multi-character**: Only valid for the acting character's commands

## Files Affected

- `routes/action.py` — `/api/action/sequence` endpoint
- `virtual_world_engine.py` — sequence execution loop
- `static/js/agent-engine.js` — sequence parsing
- `static/js/ui-controller.js` — sequence UI feedback
- `static/js/event-stream.js` — sequence step events

## Tests
- Sequence of 3 commands executes in order
- Failed command stops sequence with error message
- State passes between commands (move then look)
- Empty sequence returns error
- Single command in sequence = normal /api/action