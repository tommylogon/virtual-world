---
type: task
status: done
area: ui
priority: medium
---

# Task-238: Click a Parse Error to Inspect the Raw Response

**Status:** In Review — implemented as part of the event-stream v2 work (task-340).

## What

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

## Why

TODO

## How

TODO

## Steps to verify

1. Enable Manual Response mode, send malformed JSON for one agent response,
   and locate that turn's parse-error bubble in the Event Stream.
   - expected: a visible parse-error bubble appears in the affected turn card.
   - observed: task-340's stream-v2 record says the parse-error bubble and
     inline raw expansion were verified; this card has no fresh browser run.
2. Click “view raw response”, then use the parse-error export control after
   the session has accumulated errors.
   - expected: the escaped raw payload expands inline and the exported file
     contains the failed response and turn/phase context.

## Browser UI and intended live verification

Intended UI home: Game view → Event Stream → affected agent turn → ⚠ parse
error → 🔍 view raw response.

Current availability: `logParseError` renders the parse-error bubble, inline
raw response, consecutive-error count, and payload export. The card says this
was verified as part of task-340's stream-v2 work; this backfill did not repeat
the live run.

Live steps when available:
1. Turn on Manual Response mode, paste malformed JSON as the response for one
   agent call, and find the call's turn card in Event Stream.
   - expected: the card exposes a clickable parse-error bubble tied to that
     character and phase.
2. Click the raw-response link, scroll within the expanded payload, and use
   the parse-error export after producing a second failure.
   - expected: the full raw text is readable without breaking stream layout,
     and the export includes both failures in the session streak.

This section defines intended access and live acceptance. It is not a claim
that planned UI exists or works today.

## Acceptance

- [ ] TODO

## Files

- TODO
