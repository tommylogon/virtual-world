# Task-238: Click a Parse Error to Inspect the Raw Response

**Status:** In Review — implemented as part of the event-stream v2 work (task-340).

## Goal

Surface raw LLM response text in a clickable way when parsing fails.

## Implemented

- `static/js/stream/stream-raw-llm.js` — `logParseError(charName, phase, errMsg, raw)`:
  renders a clickable `⚠ parse error` bubble with a `🔍 view raw response` link; the
  raw payload expands inline (monospace, scrollable, escaped).
- Consecutive parse-error count + **payload export** (`parse_errors_<char>_<phase>.txt`
  download) when a session accumulates errors.
- Raw-response ring buffer + token meters; collapsed LLM chips for request/response
  payloads (click to expand).
- Wired from the agent parse-failure paths (reaction/structure parse errors) in
  event-stream.js + task-340's stream module.

## Status

Part of task-340's stream v2 refactor; verified in the event stream (bubble + expand +
export). The original audit question of which surfaces hit parse errors is answered by
the stream logging path (agent `_parseReaction`/`_normalizeStructuredAction`).
