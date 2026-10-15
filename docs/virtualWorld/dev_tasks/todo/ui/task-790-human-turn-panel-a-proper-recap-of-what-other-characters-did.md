---
type: task
status: todo
area: ui
priority: medium
---

# task-790: Human turn panel: a proper recap of what other characters did

**Filed:** 2026-10-12
**Related:** task-333, task-334, task-679

## What

Replace the 260-char sentence-join recap with a real summary of what other characters said and did while it was not your turn.

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Acceptance

- [ ] TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Turn-based play → resolve the controlled character's human-turn prompt → Human Turn Panel's recap of the actors who took turns since that character last acted.

Current availability: The card describes the current recap as a sentence-join capped at 260 characters. A structured recap of other characters' speech and actions is planned and not claimed as available.

Live steps when available:
1. Load a turn-based scenario with the controlled character and at least two NPCs; let one NPC move and the other speak before the controlled character's next turn.
   - expected: the Human Turn Panel names both NPCs and separately summarizes the movement and spoken line that occurred while the player waited.
2. Add enough distinct actions and speech to exceed the old 260-character limit, then open the next human turn.
   - expected: the recap remains complete or provides an explicit expand affordance; later actors and their actions are not silently truncated.
3. Advance another turn with no NPC actions and open the panel.
   - expected: the recap says no other-character actions occurred instead of repeating stale content from the prior turn.
4. Compare the recap with the event stream for the same tick/turn interval.
   - expected: actor names and summarized actions correspond to events in that interval; the recap does not claim actions outside it.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.
