---
group: Refactor
---

# Split prompt-builder.js into prompt-builder/ Module

**Filed**: 2026-08-09
**Priority**: Medium
**Status**: In Review — implemented 2026-08-09, node harness: all 21 public exports present (28 keys total incl. cross-file helpers), buildRoomContext/buildReactionPrompt/buildCharacterSystemPrompt smoke tests pass, full suite 787 passed (only the 11 pre-existing give-item fixture failures).

---

## Summary

`static/js/agent/prompt-builder.js` was a ~1240-line IIFE doing at least five distinct jobs (helpers, character state, memory context, room context, system prompt, turn prompts). It referenced all globals (`worldState`, `config`, `events`, `VW`, `ApiClient`, `narrationUI`, `EventBus`) at call time rather than closing over module-local state, so the split was mechanical with no closure-capture risk.

## Changes

Split into `static/js/agent/prompt-builder/`:

- **`helpers.js`** — leaf utilities: `lightToLevel`, `stripLeadingArticle`, `indefiniteArticle`, `buildRelationMap`, `anonymousName`, `voiceLabel`, `hasPlan`, `secondPersonDesc`, `describeActivity`, `frameSelfSpeech`
- **`character-state.js`** — `buildEmotionContext`, `buildRelationshipContext`, `buildInsanityContext`, `buildTraitBehaviorContext`, `buildSizeContext`, `buildPerceivedState`, `describeVitals`, `buildPlanContext`
- **`memory-context.js`** — `buildMemoryContext` (async fetch + scoring + investigation notes)
- **`room-context.js`** — `buildCharacterPreamble`, `buildRoomContext`, `buildNarratedRoomContext`
- **`system-prompt.js`** — `buildCharacterSystemPrompt` (static ACTIONS table + rules)
- **`turn-prompts.js`** — `buildReactionPrompt`, `buildObservationPrompt`, `buildDecisionPrompt`, `buildResultReactionPrompt`, `buildDashFollowUpPrompt`
- **`index.js`** — module manifest (comment only)

**Pattern**: every file does `window.PromptBuilder = window.PromptBuilder || {};` then `Object.assign(window.PromptBuilder, {...})`. Internal cross-file calls use `PromptBuilder.<fn>(...)`. Nothing executes at load time, so script order between the split files is irrelevant — all six load before `agent-engine.js` in `index.html`.

**Flat public API preserved** — `PromptBuilder.buildRoomContext(...)` etc. — so `agent-engine.js` and `plan-manager.js` needed zero changes. The old `static/js/agent/prompt-builder.js` was deleted; `index.html` now loads the six files.

## Verification

- `node --check` on all six files passes.
- Node harness loads the files in shuffled order with stub globals: all 21 original exports present (28 keys total — 8 previously-internal helpers are now exposed on the namespace since cross-file calls need them; harmless, flat API intact).
- Smoke tests: `buildRoomContext` outputs `[Tick 0]` + preamble, `buildReactionPrompt` contains `=== START ===`, `buildCharacterSystemPrompt` contains the ACTIONS table + SPEECH & VOLUME.
- Full pytest suite: 787 passed, same 11 pre-existing give-item fixture failures — no regression.
- No stale references to the old `agent/prompt-builder.js` path remain.

## Notes

- The 8 extra namespace keys (`buildPerceivedState`, `buildRelationMap`, `buildSizeContext`, `buildTraitBehaviorContext`, `describeActivity`, `indefiniteArticle`, `stripLeadingArticle`, `secondPersonDesc`) are exposed because split files call each other across files. If a strictly-21-key surface is ever wanted, gate cross-file helpers behind the namespace but delete them from `Object.assign` after — not worth the ceremony now.
- Namespacing (`PromptBuilder.room.build(...)`) deliberately deferred; would touch every call site.
