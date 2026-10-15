---
type: task
status: done
area: ui
priority: high
---

# task-630: Command input advertises 'Tab completes' but does not complete

**Filed:** 2026-09-30
**Related:** 

## What

#command-input placeholder promises 'Tab completes'; it does not.

## Acceptance

- TODO

## Why

TODO

## How

TODO

## Steps to verify

1. Select a controlled character in a room with two visible targets sharing a prefix; type `examine <prefix>` in `#command-input`.
   - expected: Tab inserts the first matching target without submitting the command.
   - observed: the current `main.ts` contains the Tab/API autocomplete handler; this card records no live browser result or actual target names.
2. Press Tab again and then Shift+Tab.
   - expected: suggestions cycle forward and backward while preserving the verb.
   - observed: not recorded in this card.
3. Submit the selected command and compare it with the event stream.
   - expected: only the chosen target is examined; cycling suggestions alone does not consume a turn or mutate the world.
   - observed: not recorded in this card.
4. Repeat after switching the controlled character.
   - expected: suggestions match that character's available targets; the `selectedAgent` context noted in `main.ts` must be checked live rather than assumed.
   - observed: not recorded in this card.
## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Main `#command-input` field → type a verb, a space, and a target prefix → press Tab; Shift+Tab cycles backward through matching targets.

Current availability: `main.ts` contains a Tab handler that requests autocomplete options and inserts the first result, then cycles them. Its comment says the selected-agent context is null on this path; this card contains no live observation showing which actor's target list the endpoint returns.

Live steps when available:
1. Select a controlled character in a room with two visible targets sharing a prefix, focus `#command-input`, and type `examine <prefix>` without pressing Enter.
   - expected: Tab inserts the first matching target and the command remains uncommitted.
2. Press Tab again, then Shift+Tab.
   - expected: Tab advances to the next matching target, Shift+Tab returns to the previous one, and the input retains the `examine` verb.
3. Press Enter only after choosing a target and inspect the event stream.
   - expected: exactly the chosen target is examined; cycling suggestions alone has not consumed a turn or changed world state.
4. Repeat after switching the controlled character to a room with different visible targets.
   - expected: suggestions match the newly controlled actor's available targets; if the active context remains null, record that as a remaining issue instead of treating the placeholder claim as verified.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.
