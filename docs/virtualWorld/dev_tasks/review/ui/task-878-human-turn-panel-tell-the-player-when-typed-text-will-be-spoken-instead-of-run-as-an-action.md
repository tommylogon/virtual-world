---
type: task
status: review
area: ui
priority: medium
wiki: "[[Gameplay/Turn Queue & Human Turns]]"
---

# task-878: Human turn panel: tell the player when typed text will be spoken instead of run as an action

**Filed:** 2026-10-19
**Related:** task-333, task-352, task-610

<!-- deps:start -->
**Related:** [[task-333-human-turn-panel-scene-first]], [[task-352-action-economy]], [[task-610-human-turn-modal-exposes-3-of-23-backend-character-to-character-actions]]
<!-- deps:end -->

## What

In the human turn composer, a typed line whose first word is not in the 58-entry VERBS list is sent as speech. Show the player that before they commit, instead of letting 'walk over to the counter' be said aloud by the character.

## Why

Verified in human-turn-composer.ts parseCmd: line 171 returns { speech: t } when the first word is not in VERBS, and buildPayload then sends it as p.speech with the current volume. 'walk' is not in VERBS ('go' and 'approach' are), so the intent becomes dialogue with no warning. The behavior is documented in the code comment ('Unknown verbs become speech') so this is a feedback gap, not a parser bug. Live reproduction in the browser is still to be done and recorded before closing.

## How

In the composer, on input in #htc-do, run parseCmd and, when the result has speech but no action, show a one-line hint under the field: the text will be said aloud, plus the closest known verbs. Leave parseCmd and the payload untouched. Keep the hint out of the way when the field is empty or starts with a volume word (scream, shout, whisper), which are deliberate speech.

## Browser UI and intended live verification

Intended UI home: Human turn modal, the 'do' row of the step composer

Current availability: Mis-spoken intent is live today; the hint is not built.

Live steps when available:
1. Open a human-controlled turn, type 'walk to the bar' in the do field. expected after fix: an inline hint. observed before fix: nothing, and Act makes the character say it.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Follow the intended live path in Browser UI and intended live verification when that surface is available.
   - expected: TODO
   - observed: TODO
2. Record the browser surface and interaction actually used (for example: navigate, click, hover, type, expand, or scroll to the bottom).
   - expected: TODO
   - observed: TODO
3. Run the targeted regression test for the mechanism.
   - expected: TODO
   - observed: TODO

## Acceptance

- [ ] Typing 'walk to the bar' in the do field shows a hint that it will be spoken, naming at least one real verb.
- [ ] Typing 'go north' or 'take sword' shows no hint.
- [ ] Typing 'whisper hello' shows no hint.
- [ ] Committed payloads are byte-identical to before for the same input.

## Files

- `static/js/agent/human-turn-composer.ts`
- `tools/unit/test_human_turn_composer.js (new; no composer test exists today)`
