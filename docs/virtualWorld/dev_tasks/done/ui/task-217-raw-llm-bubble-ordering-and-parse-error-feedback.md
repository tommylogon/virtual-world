---
type: task
status: done
area: ui
priority: medium
---

# Task 217 — Raw LLM bubble ordering + parse error feedback

## Status

In Review — implemented 2026-08-12, then folded into task-340's stream v2
(2026-08-24); the parse-error expansion UX now lives in
`static/js/stream/stream-raw-llm.js` (logParseError + view-raw + streak export).

## What

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

## Steps to verify

- Full suite green at implementation (1010-ish); stream v2 tests + `node --check`
  all touched files. Browser verification is live under task-340's E2E pending.

## Why

TODO

## How

TODO

## Acceptance

- [ ] TODO

## Browser UI and intended live verification

Intended UI home: Game view → Event Stream → expand an agent turn card; use
Manual Response mode to provide a malformed response for the parse-error path.

Current availability: Raw request/response bubbles and parse-error expansion
are implemented in the stream modules. This card says the later task-340
browser E2E owns the live stream check; no independent browser observation is
recorded here.

Live steps when available:
1. Run an agent turn with the raw LLM display enabled and expand its turn card.
   - expected: the raw request/response bubbles appear inside that turn card
     before the parsed action/result content; stream filters still include the
     nested bubbles.
2. In Manual Response mode, return malformed JSON for one agent call, then
   click the parse-error bubble's raw-response control.
   - expected: the parse failure is visible in the stream, the malformed text
     can be inspected, and the affected turn remains identifiable.
3. Use the stream's parse-error filter and export the error streak.
   - expected: the same failed turn remains discoverable in the filtered view
     and the exported streak includes its raw response evidence.

This section defines intended access and live acceptance. It is not a claim
that planned UI exists or works today.
