# Bug 4: Initiative list shows "ACTING" on first character before any turn is taken

**Filed**: 2026-07-23
**Priority**: High
**Status**: Fixed

## Summary

Before clicking "Step" or "Start", the first character in the initiative list shows `▶️ Kaelen Voss ⚡ ACTING`. No turn has been taken yet — the character is "up next", not "acting".

## Root Cause

`TurnQueue.initialize()` sets `currentTurnIndex = 0`. The `_renderInitiative()` function in `ui-controller.js` treats any character at `currentTurnIndex` as "current" and displays "⚡ ACTING" regardless of whether any turns have actually been processed.

When `currentTurnIndex = 0` and `turnNumber = 0`, the character at index 0 hasn't had their turn yet — they're the next character up. The UI shouldn't show "ACTING" until `step()` has actually started processing them.

## Fix

In `_renderInitiative()` (`ui-controller.js:176`), change the status text for the current character when `agent.turnNumber === 0` (no full rounds completed) and no characters have been processed yet:

```
const statusStr = isCurrent
  ? (agent.turnNumber === 0 ? 'up next' : (isNpc ? 'ACTING...' : '⚡ ACTING'))
  : (isDone ? 'done' : 'waiting');
```

## File

`static/js/ui-controller.js:176`

---
_Audited 2026-08-03 � duplicate file consolidated into this record._
