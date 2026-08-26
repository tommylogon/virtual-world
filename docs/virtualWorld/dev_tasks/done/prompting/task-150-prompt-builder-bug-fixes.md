---
group: Tech Debt & Testing
---
# Task 150: Prompt Builder Bug Fixes

**Filed**: 2026-07-31  
**Priority**: High  
**Status**: Done  

---

## Summary

Fix 6 confirmed bugs in the prompt-builder.js and agent pipeline that prevent cross-room awareness, cause duplicate inventory, and break memory parsing.

---

## Bugs Fixed

### P0-1: WITNESSED header empty rendering ✅
**Problem**: Filter happened after length check, causing empty `=== WITNESSED ===` header when all events belonged to the character.

**Fix**: Filter before length check in `prompt-builder.js:542-549`

### P0-2: Duplicate inventory items ✅
**Problem**: `getInventory(charName, ['carrying', 'equipped', 'carried_by'])` returned duplicates because equipped items satisfied multiple edge types.

**Fix**: Deduplicate by item ID in `world-state.js:128-142` (source-level fix benefits all callers)

### P1-1: Memory parser separator mismatch ✅
**Problem**: Parser looked for colon (`:`) but action memories used arrow (` → `) separator, so Investigation Notes never rendered.

**Fix**: Try arrow first, then colon for backward compatibility. Strip leading emoji/icon from action part. `prompt-builder.js:195-222`

### P1-2: Unify memory-passing pattern ✅
**Problem**: `buildResultReactionPrompt` called `buildMemoryContext` internally while sibling functions received it as a parameter, causing potential inconsistency.

**Fix**: Added `memoryNL` parameter to function signature, removed internal call. Updated caller in `agent-engine.js:361`.

### P2-1: First-turn observe wording ✅
**Problem**: Hardcoded "Based on what has happened this turn" even when nothing happened (first turn).

**Fix**: Conditional wording based on `lastResult` existence in `prompt-builder.js:729-747`

---

## Files Modified

1. `static/js/agent/prompt-builder.js`
   - Fixed WITNESSED filter order (line 542-549)
   - Fixed memory parser to handle arrow separator (line 195-222)
   - Added memoryNL parameter to buildResultReactionPrompt (line 793)
   - Fixed first-turn observe wording (line 729-747)

2. `static/js/world-state.js`
   - Deduplicate inventory by item ID (line 128-142)

3. `static/js/agent-engine.js`
   - Pass memoryNL to buildResultReactionPrompt (line 361)

---

## Testing

- ✅ All 21 sound propagation tests pass
- Manual testing needed:
  - Verify no empty WITNESSED headers
  - Verify no duplicate inventory items
  - Verify Investigation Notes appears after examining items
  - Verify cross-room hearing works (characters hear speech from adjacent rooms)
  - Verify first-turn observe prompt uses appropriate wording

---

## Related

- Task 149: Sound Propagation System (provides the data that feeds into WITNESSED)
- Agent pipeline architecture (prompt-builder.js, agent-engine.js, world-state.js)
