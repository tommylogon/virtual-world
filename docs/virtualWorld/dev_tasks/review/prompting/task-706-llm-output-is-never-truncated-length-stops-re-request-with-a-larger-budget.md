---
type: task
status: review
area: prompting
priority: high
---

# task-706: LLM output is never truncated: length stops re-request with a larger budget

**Filed:** 2026-10-05
**Related:** task-700

## Goal

A length stop from the provider re-requests with a doubled budget instead of handing a fragment to the caller.

## Acceptance

- **Wired:** the runtime path reaches it. Every `llmClient.chat()` call goes
  through the escalation — there is no opt-in and no second client to bypass it.
- A Chat Completions `finish_reason: 'length'` and a Responses API
  `incomplete_details.reason: 'max_output_tokens'` (or `status: 'incomplete'`)
  are both detected. A `stop` / `tool_calls` / missing signal is not.
- A length stop re-requests with 2x the CALLER's cap, up to 3 retries, clamped
  at 32768.
- An answer still truncated after the budget is **reported** to the event
  stream with its tail, not returned silently.
- A provider that omits the stop reason never triggers a spurious retry (the
  old `_truncationReason` had to distinguish this from a length stop).
- Streaming does not paint a second overlapping stream over the partial text
  already on screen: `onChunk` is suppressed once the retry budget is in play.

## Why this is the layer

`max_tokens` is a hard cap at the provider. Every caller was receiving a
silently cut-off string with no way to tell it from a complete one — the plan
phase turned a half-written JSON plan into **no plan** and logged nothing. The
16 `max_tokens` call sites cannot each defend themselves, and `config.maxTokens`
plus per-call caps means there is no single number to raise. So the fix belongs
where the truncation happens.

## Implementation

`static/js/llm-client.ts`:

- `_truncationReason(completion, isResponses)` — the provider's own stop signal.
- `_nextTokenBudget(base, retry)` — doubling from `base`, clamped.
- `_warnTruncated(label, budget, content)` — the last-resort event-stream line.
- `_handleStream(..., info?)` — records the finish reason off the final SSE chunk.
- In `chat()`: `effectiveMaxTokens` is what goes on the wire, escalating on a
  length stop via `continue`.

## Two defects this change itself introduced, and what caught them

1. **Truncation retries shared the transport-retry counter.** Three length stops
   exhausted `maxRetries` and the call threw "LLM request failed after retries"
   having never failed at transport. Transport and truncation now have separate
   budgets (`maxIterations = maxRetries + MAX_TRUNCATION_RETRIES`).
   *Caught by:* the unit test that stubs four consecutive length stops.
2. **The escalation compounded.** `_nextTokenBudget` was handed the previously
   escalated budget instead of the caller's cap: 300 -> 600 -> 2400 -> 19200.
   On a local model that is one very long doomed generation instead of three
   quick ones. *Caught by:* the live browser run, not the unit tests — the
   helper-only tests could not see how the caller used the return value. Fixed
   to 300 -> 600 -> 1200 -> 2400, and pinned by a test that asserts the whole
   sequence.

## Evidence

Unit: `tools/unit/test_llm_truncation.js`, 9 tests. Gate green
(`python tools/ts_convert.py check`), 610 unit tests passing.

Live (browser, real loaded `window.llmClient`, stubbed provider), 2026-10-04:

| Scenario | Result |
|---|---|
| provider always length-stops | budgets requested `300,600,1200,2400`, no throw |
| first response cut, second complete | caller received `{"steps":[{"act":"go","target":"west passage"}]}` |

## Known remaining gap

`task-700`'s `_salvageTypedSteps` is now a second line of defence rather than the
primary fix, and stays: it also covers a provider that returns cut-off text
**without** a stop reason (some local proxies), which no amount of budget
escalation can detect.
