---
type: task
status: done
area: ui
priority: medium
---

# task-631: Turn-mode dropdown caption is static and wrong for four of five modes

**Filed:** 2026-09-30
**Related:** 

## What

Selecting any turn mode leaves the caption reading 'Characters act one at a time' (the Sequential description). The agent list IS correctly ordered by initiative; only the caption is wrong.

## Acceptance

- TODO

## Why

TODO

## How

TODO

## Steps to verify

1. In Agent controls, select Sequential, Random, Initiative, Simultaneous, and Simultaneous per room in turn.
   - expected: captions read respectively “Characters act one at a time”; “Characters act in a shuffled order, reshuffled each round”; “Each character rolls d20 + DEX; highest acts first”; “Independent 5–120 second cooldowns, jittered per character”; and “Rooms resolve independently; order within a room”.
   - observed: `config.ts` contains all five mode-specific descriptions; this card has no browser observation of the dropdown after each selection.
2. Reload with each mode selected.
   - expected: the selected mode and its matching caption restore together.
   - observed: not recorded in this card.
## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Agent controls → Turn-Based Mode checkbox and Turn mode dropdown (`#agent-turn-order`) → descriptive caption immediately below the checkbox.

Current availability: `config.ts` contains mode-specific descriptions for sequential, random, initiative, simultaneous, and simultaneous-per-room. This card does not record a live browser observation of all five selected modes.

Live steps when available:
1. Open Agent controls and select each mode in `#agent-turn-order`, reading the caption after every selection.
   - expected: Sequential says “Characters act one at a time”; Random says “Characters act in a shuffled order, reshuffled each round”; Initiative says “Each character rolls d20 + DEX; highest acts first”; Simultaneous describes independent 5–120 second cooldowns; Simultaneous per room says rooms resolve independently with order within a room.
2. Switch between sequential and simultaneous-per-room while watching the Turn Order controls.
   - expected: the caption updates immediately and the mode's supported controls update without changing the separate initiative ordering data.
3. Reload with each mode selected in turn.
   - expected: the saved mode is restored and its matching caption appears, never the static sequential caption for another mode.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.
