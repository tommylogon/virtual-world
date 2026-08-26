# Task 219: Prompt Builder Shared Fragment Extraction

**Status**: Done — implemented 2026-08-13, verified via `tools/test_llm.cjs` (16/19, 3 pre-existing LLM endpoint failures unrelated to prompt output).

**Priority**: Medium
**Filed**: 2026-08-13

---

## Summary

The prompt builder had already been split from a monolithic `prompt-builder.js` into 6 modules (helpers, character-state, memory-context, room-context, system-prompt, turn-prompts). However, `turn-prompts.js` still contained large inline strings duplicated across phases: emote rules, memory instructions, ghost/dead flavor text, JSON schema examples, and plan guidance.

This task extracts those shared fragments into two new registries so they become a single source of truth.

---

## What was implemented

**New files:**
- `static/js/agent/prompt-builder/context-sections.js` — shared context-fragment registry with `buildContextBlock()` and `buildPlanGuide()`
- `static/js/agent/prompt-builder/schema-fragments.js` — shared instructional text + JSON schema fragments with `buildJsonExample()`

**Modified files:**
- `static/js/agent/prompt-builder/turn-prompts.js` — refactored to use `PromptBuilder.buildContextBlock()`, `PromptBuilder.buildPlanGuide()`, `PromptBuilder.EMOTE_RULES_*`, `PromptBuilder.MEMORY_INSTRUCTION_*`, and `PromptBuilder.buildJsonExample()`
- `static/js/agent/prompt-builder/system-prompt.js` — last emote-rules bullet now uses `PromptBuilder.EMOTE_RULES_SYSTEM` from `schema-fragments.js`
- `templates/index.html` — added script tags for `context-sections.js` and `schema-fragments.js` (load before system-prompt.js and turn-prompts.js)
- `static/js/agent/prompt-builder/index.js` — updated manifest to document 8 files

**Flags preserved from Claude's review:**
1. `includeMemory` in reaction prompt builds `memoryInstruction` but never inserts it — preserved as commented-out line (would change model behavior if uncommented)
2. `MEMORY_INSTRUCTION_REACTION` vs `MEMORY_INSTRUCTION_REACT` differ by "of the room" — kept as two named constants, marked `FLAG:` in comments

---

## Verification

- `node --check` passes on all 8 prompt-builder files
- `tools/test_llm.cjs`: 16/19 passed (3 failures are pre-existing LLM endpoint routing issues, unrelated to prompt text)
- External call sites (`agent-engine.js`, `plan-manager.js`) untouched — same exported function signatures

---

## Files touched

- `static/js/agent/prompt-builder/context-sections.js` — new
- `static/js/agent/prompt-builder/schema-fragments.js` — new
- `static/js/agent/prompt-builder/turn-prompts.js` — refactored
- `static/js/agent/prompt-builder/system-prompt.js` — uses `EMOTE_RULES_SYSTEM`
- `static/js/agent/prompt-builder/index.js` — updated manifest
- `templates/index.html` — added 2 script tags
- `docs/virtualWorld/dev_tasks/dev_Task_sequence.md` — bumped to 219
