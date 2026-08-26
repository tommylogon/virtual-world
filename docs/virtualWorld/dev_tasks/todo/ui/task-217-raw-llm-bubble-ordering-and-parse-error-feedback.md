# Task 217 — Raw LLM bubble ordering + parse error feedback

## Status
In Progress — implemented 2026-08-12, pending browser verification

## Summary
Two UI/UX improvements for the event stream:

1. **Raw LLM bubbles move inside turn cards, before parsed content**
   Currently `logRawLLMRequest` / `logRawLLM` append directly to `#event-stream`, outside the turn card, which visually drops them to the bottom of each bubble group. After this change they are treated as agent events and appended inside the turn-card body, appearing before inner_monologue / speech / action / result / reaction bubbles.

2. **Parse failures surface as system messages**
   `_parseReaction`, `_parseResultReaction`, and `_parseObservation` silently return `null` on JSON parse failure, causing the action to vanish. After this change the parsers return a `parseError` string on failure, and the agent-engine emits a visible `error-msg` bubble so the player can see what went wrong.

## Files changed
- `static/js/event-stream.js`
- `static/js/agent-engine.js`
- `static/js/shared/json-utils.js`

## Implementation notes

### event-stream.js
- `_addBubble`: remove `rawllm` from the non-agent-event list so it stays inside the turn card.
- `logRawLLMRequest` / `logRawLLM`: append inside `turn-card-body` when open, otherwise fall back to `streamEl`. Keep the existing `_trimStream`/autoscroll behaviour.
- `applyFilters`: recurse into `.turn-card-body` to filter rawllm/thought/speech/action/emote bubbles inside turn cards, not just top-level stream children.

### shared/json-utils.js
- `repairJSON(raw)`: new standalone helper — strips code fences, finds first `{`/last `}`, then repairs common LLM JSON failures: literal newlines/tabs in strings → escaped, non-ASCII chars → `\uXXXX`, trailing commas before `]`/}`, missing closing braces/brackets (brackets closed before braces).

### agent-engine.js
- `_parseObservation`, `_parseReaction`, `_parseResultReaction`: call `repairJSON()` before `JSON.parse`. On catch, return default fields + `parseError` instead of `null`.
- Call sites at lines ~254, ~381, ~414, ~639: destructure `parseError`; when truthy, `events.log(...)` with `'error-msg'`.

## Verification
- Trigger a malformed LLM response (e.g. send non-JSON text) and confirm a system error bubble appears instead of silent failure.
- Run a normal turn and confirm raw LLM request/response bubbles appear at the top of each turn card, before the phase/thought/speech/action bubbles.
