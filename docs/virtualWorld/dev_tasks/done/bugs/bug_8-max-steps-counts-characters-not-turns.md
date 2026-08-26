---
wiki: "[[Characters/NPC Behavior System]]"
---

# Bug 8: "Max turns" input counts individual character steps, not full turns

**Filed**: 2026-07-23
**Priority**: Medium
**Status**: Fixed

## Summary

The "Max turns" input in settings actually counts individual character steps (actions) rather than full turns (rounds where all characters act once). A value of 10 stops after 10 individual character actions, not 10 full rounds.

## Root Cause

The counting logic in `agent-engine.js:465-468` increments the counter on each character step rather than tracking completed rounds. The label `title="Max turns before auto-stop"` is misleading.

## Fix

Two options taken:
1. Relabeled the input to "Max Steps (character actions)" to match actual behavior
2. Updated the title attribute accordingly

## Files

- `templates/index.html:52` — `title="Max turns before auto-stop"`
- `static/js/agent-engine.js:465-468` — step counting loop

## Verification

### Manual Test Steps:
1. Open the game in browser at http://127.0.0.1:4444
2. Open Settings → Behavior & Automation tab
3. Find the "Max Steps" or "Max Turns" input field
4. **Expected**: The label/title clearly indicates it counts "steps" (individual actions) not "turns" (full rounds)
5. Set max steps to 2, run agents — should stop after ~2 character actions
6. The count behavior should match what the label says

---
_Audited 2026-08-03 � duplicate file consolidated into this record._
