---
group: Tech Debt & Testing
---
# Task 151: Flavor Text Interaction Polish

**Filed**: 2026-07-31  
**Priority**: Medium  
**Status**: Done  

---

## Summary

Polish the interaction layer so that attempts to interact with objects that only exist in descriptive text (flavor text) produce in-character narrative responses instead of technical "not found" errors. Also improves the WITNESSED prompt section.

---

## Changes

### 1. Descriptive-target fallback for "use X on Y" ✅
**File**: `engine/item_actions.py` — `_descriptive_target_failure()`

When a use-on-target doesn't match a real item/exit, the system now scans the area description, item descriptions, and way descriptions for the target phrase. If found, it returns an in-character failure:

> "You try to use the multitool on chandelier, but it doesn't budge — it's part of the scenery, not something you can interact with."

The attempt is logged as a turn event so other characters in the room can witness it.

### 2. Descriptive-target fallback for "examine X" ✅
**File**: `engine/item_actions.py` — `_describe_flavor_target()`

When examining an object that only appears in descriptive text, the system pulls the surrounding sentence and returns it as flavor text:

> "You examine marble floor. A grand entrance hall with a black-and-white marble floor..."

### 3. Deduplicate WITNESSED entries ✅
**File**: `static/js/agent/prompt-builder.js`

A speech line heard from another room is no longer shown twice — once as a local event (`[Kayla] said: ...`) and once as heard speech (`[Heard] Kayla said: ...`). Deduplication uses a `(speaker, text)` key.

### 4. Always render WITNESSED header ✅
**File**: `static/js/agent/prompt-builder.js`

The `=== WITNESSED ===` header now always appears in the prompt. When nothing has happened, it shows a placeholder: "Nothing unusual happened while you were looking."

### 5. Log failed interactions as turn events ✅
**File**: `engine/item_actions.py`

Failed use-on-target attempts are recorded via `record_turn_event` so other characters in the room can witness the attempt.

### 6. Removed debug logging ✅
**Files**: `static/js/agent/prompt-builder.js`, `static/js/agent-engine.js`

The `[WITNESSED DEBUG]` and `[AGENT DEBUG]` console logs added during the WITNESSED debugging session were removed.

---

## Tests

Added `tests/test_descriptive_targets.py` (6 tests):
- Flavor target match returns narrative sentence
- Multi-word flavor match (marble floor) works
- Unknown target returns None
- Empty target returns None
- Use-on-flavor-target gives narrative failure + logs turn event
- Use-on-unknown-target returns None

**Result**: 40 tests passing (sound + engine + descriptive targets)

---

## Files Modified

1. `engine/item_actions.py` — added `_descriptive_target_failure()`, `_describe_flavor_target()`
2. `static/js/agent/prompt-builder.js` — dedupe WITNESSED, always render header, remove debug logs
3. `static/js/agent-engine.js` — remove debug logs
4. `tests/test_descriptive_targets.py` — new test file

---

## Related

- Task 149: Sound Propagation System
- Task 150: Prompt Builder Bug Fixes
