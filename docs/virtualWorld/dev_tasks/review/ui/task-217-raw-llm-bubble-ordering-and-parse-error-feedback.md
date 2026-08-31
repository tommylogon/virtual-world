# Task 217 — Raw LLM bubble ordering + parse error feedback

## Status
In Review — implemented 2026-08-12, then folded into task-340's stream v2
(2026-08-24); the parse-error expansion UX now lives in
`static/js/stream/stream-raw-llm.js` (logParseError + view-raw + streak export).

## Summary
Two UI/UX improvements for the event stream:

1. **Raw LLM bubbles move inside turn cards, before parsed content**
   `logRawLLM`/`logRawLLMRequest` append inside the turn-card body, ordered before
   parsed content; filter recursion into `.turn-card-body`.
2. **Parse failures surface visually** — parsers return a `parseError` string;
   agent-engine emits a visible error bubble; raw response inspectable (task-238
   click-to-expand lives in the same module).

## Files
- `static/js/event-stream.js` (+ `stream/stream-raw-llm.js` after the split)
- `static/js/agent-engine.js`
- `static/js/shared/json-utils.js` (`repairJSON`)

## Verification
- Full suite green at implementation (1010-ish); stream v2 tests + `node --check`
  all touched files. Browser verification is live under task-340's E2E pending.
