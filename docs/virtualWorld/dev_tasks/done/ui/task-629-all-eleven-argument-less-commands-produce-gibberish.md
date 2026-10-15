---
type: task
status: done
area: ui
priority: high
---

# task-629: All eleven argument-less commands produce gibberish

**Filed:** 2026-09-30
**Related:** 

## What

Invoking a verb with no target returns nonsensical prose for every one of the eleven verbs tested. Only three remaining verbs produce anything sensible at all.

## Acceptance

- TODO

## Why

TODO

## How

TODO

## Steps to verify

1. Recover the exact eleven verb spellings from the original regression fixture or commit, load a scratch scenario, and enter each verb without a target in the command input.
   - expected: every reply gives a useful missing-target explanation or choices; no bare verb produces gibberish or silently executes another action.
   - observed: This card does not record the verb spellings or a browser result; a faithful replay cannot be claimed until the original input list is recovered.
2. Compare `/api/state`, tick, and action slots before and after each bare verb.
   - expected: asking for a target does not move the actor, consume a slot, advance time, or write a memory.
   - observed: not recorded in this card.
3. Add a valid target to each verb that requires one and repeat.
   - expected: the targeted form follows the normal engine action path and produces its ordinary result.
   - observed: not recorded in this card.
## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Main command input → enter a verb with no target → read the command result in the event stream. The response must explain the missing target or show useful choices without performing an action.

Current availability: This card is filed under done but its body does not name any of the eleven verbs, record their expected replies, or provide evidence. The exact eleven input strings are not available in the card, so a faithful replay needs the original regression fixture or commit evidence before it can be called verified.

Live steps when available:
1. Load a scratch scenario, select the actor used by the original repro, and record `/api/state` and the current tick.
   - expected: a clean before-state is available for checking that a bare verb has no side effects.
2. Enter each of the eleven exact no-target verb strings from the original regression fixture and record the event-stream reply.
   - expected: each reply names the missing argument or offers the relevant choices in ordinary prose; none returns gibberish or silently executes a different action.
3. Compare state and tick after each input.
   - expected: a request for an argument does not move the actor, consume an action slot, advance time, or write a memory.
4. Add a valid target to each command that asks for one and repeat.
   - expected: the valid form reaches the normal engine action path and produces its ordinary result.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.
