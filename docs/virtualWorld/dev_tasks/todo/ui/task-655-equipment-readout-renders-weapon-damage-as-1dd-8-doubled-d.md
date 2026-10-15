---
type: task
status: todo
area: ui
priority: low
---

# task-655: Equipment readout renders weapon damage as '1dd+8' (doubled d)

**Filed:** 2026-09-30
**Related:** 

## What

The character inspector's Equipment section shows the Rusty Hatchet as '1dd+8 piercing'. The item's damage in the graph data is 1d6, so the doubled 'd' is either a display bug or a doubled parser token in that readout. Only visible by reading the Equipment section in the inspector. Found while walking all 26 inspector sections for task-654.

## Acceptance

- TODO

## Browser UI and intended live verification

Intended UI home: Select the character carrying Rusty Hatchet → Inspector → Inventory/Equipment section → equipped weapon detail.

Current availability: The card records a visible `1dd+8 piercing` readout while the underlying Rusty Hatchet damage is `1d6`; the display correction is planned and no fix is claimed here.

Live steps when available:
1. Load the scenario used for the Rusty Hatchet repro, select its carrier, and open the full Equipment section in the character inspector.
   - expected: Rusty Hatchet shows its source damage as `1d6 piercing`, with no doubled `d` and no unexplained `+8` unless the item's actual damage modifiers supply it.
2. Open the item's graph properties and compare the damage fields with the Equipment readout.
   - expected: the displayed expression is derived from the same item damage record and any explicit modifier is shown once.
3. Inspect a second weapon with a different damage die.
   - expected: its readout uses that weapon's own die and modifier; the formatting correction does not hard-code Rusty Hatchet.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

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
