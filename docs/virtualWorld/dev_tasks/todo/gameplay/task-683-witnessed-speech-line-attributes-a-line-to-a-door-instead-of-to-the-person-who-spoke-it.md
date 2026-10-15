---
type: task
status: todo
area: gameplay
priority: medium
---

# task-683: WITNESSED speech line attributes a line to a door instead of to the person who spoke it

**Filed:** 2026-10-04
**Related:** 

## What

As Jake in the foyer the panel shows: [Heard from the library_door_back -> to you] a woman's voice said: elena!! the bookcase ... The direction is a door node, not a speaker, so the line reads as if the door talked. A character standing in earshot should be attributed the way any other agent would perceive it. Reporter has not yet pinned the expectation (speaker named vs anonymous voice with a correct origin), so confirm the intended rendering before implementing, and trace which layer supplies the Heard from value (sound propagation vs the prompt builder) rather than patching the rendered string.

## Acceptance

- TODO

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Human Turn/room view → event stream → inspect the witnessed-speech line for the listening character. Attribution must describe the audible speaker or an anonymous voice from the correct direction; a door node must not appear as the speaker.

Current availability: the card records a live line attributed to `library_door_back`, but the reporter has not decided whether the correct output names Elena or says “a woman's voice.” That semantic choice must be confirmed before the expected line is fixed.

Live steps when available:
1. Place a listener in the foyer and Elena in the library, separated by `library_door_back`; have Elena say `elena!! the bookcase` while the listener cannot see her.
   - expected: the event line attributes the words to Elena if she is recognized, or to an anonymous woman's voice if she is not; it identifies the sound origin/direction without saying the door spoke.
2. Repeat with Elena visible and recognized, then with an unknown speaker behind the same way.
   - expected: the attribution changes according to the listener's knowledge, not the way-node display name; the exact named/anonymous wording follows the decision recorded in this card.
3. Compare the event stream with the room's sound/perception output and the prompt context for the listener.
   - expected: each layer reports the same speaker identity or anonymity and correct sound origin; no real name is leaked to an unacquainted listener.

This section is not a claim that planned UI exists or works today.
