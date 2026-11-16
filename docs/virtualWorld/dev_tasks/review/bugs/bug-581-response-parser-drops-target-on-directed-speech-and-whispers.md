---
type: bug
status: review
area: bugs
priority: high
wiki: "[[Gameplay/Turn Queue & Human Turns]]"
related: [task-933, task-728]
---

# bug-581: ResponseParser.parseReaction and parseResultReaction drop target on directed speech and whispers

**Filed:** 2026-11-09
**Related:** task-933, task-728

<!-- deps:start -->
**Related:** [[task-933-character-controller-selector-and-director-turn-composer]], [[task-728-directed-control-mode-a-director-reviews-and-edits-an-llm-character-s-turn-before-it-acts]]
<!-- deps:end -->

## What

`ResponseParser.parseReaction()` and `ResponseParser.parseResultReaction()` in `static/js/agent/response-parser.ts` do not extract or return the `target` field (`p.speech_target` or `p.target` for directed speech/whispers), even though both `AgentEngine.stepCharacter` (`line 1132`) and `AgentEngine.draftTurnForCharacter` (`line 796`) read `parsed.target`.

As a result, when an LLM emits a directed whisper or speech (`{"speech": "...", "volume": "whisper", "target": "kayla jenkins"}`), `ResponseParser` silently drops `target`, so the `#htc-say-target` chip (`to kayla jenkins ×`) in the Human Turn Composer never renders on LLM drafts and autonomous directed whispers lose their target recipient.

## Why

`ActionNormalizer.normalizeStructuredAction(p)` consumes `p.target` for physical actions, while `ResponseParser.parseReaction()` omitted `target` from its returned `ParsedReaction` object.

## How

1. In `static/js/agent/response-parser.ts`:
   - Add `target?: string | null` to `ParsedReaction`.
   - Add helper `extractSpeechTarget(p)` that returns `p.speech_target` if present, or `p.target` when `p.speech` / `p.whisper` is present (and `p.action` is either empty/wait or `p.item` already supplied the physical object).
   - Include `target: extractSpeechTarget(p)` in the return objects of both `parseReaction()` and `parseResultReaction()`.

## Steps to verify

1. Run `node tools/unit/run.cjs test_directed_mode`.
   - expected: `ResponseParser.parseReaction` preserves `target` on directed speech/whispers.

## Acceptance

- [x] `ResponseParser.parseReaction` and `parseResultReaction` return `target` for directed speech/whispers.
- [x] `#htc-say-target` chip renders when the Director LLM drafts a targeted line.
- [x] Zero em-dashes in code or task files.

## Files

- `static/js/agent/response-parser.ts`
- `tools/unit/test_directed_mode.js`
