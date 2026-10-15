---
type: task
status: todo
area: ui
priority: medium
---

# task-682: Scene chips leak snake_case node ids as display names

**Filed:** 2026-10-04
**Related:** 

## What

Things you can see renders raw node ids for items whose name is an id: coat_rack, calling_cards, protein_bar, vase (ok) while neighbouring chips read denim cut-offs. The You strip shows energy drinkbroken -- the item name and its broken state concatenated with no separator. scene_snapshot emits describe_item_quantity(node) and build_item_quantity_label joins name+state; both need a display-name resolution layer plus a separator. Check whether the id is already available as a display_name/label property before adding a second resolution path.

## Acceptance

- TODO

## Browser UI and intended live verification

Intended UI home: Human Turn Composer → scene snapshot → People and Things chips, plus the controlled character's You strip.

Current availability: The card records raw item IDs (`coat_rack`, `calling_cards`, `protein_bar`, `vase`) in Things and the joined text `energy drinkbroken` in the You strip; the name/separator fix is planned.

Live steps when available:
1. Load the repro scene, open the human-turn composer, and inspect Things for coat rack, calling cards, protein bar, and vase.
   - expected: each chip uses its authored display name rather than an ID fallback when that name exists; `vase` remains readable if its authored name is already “vase”.
2. Inspect the controlled character's You strip while carrying the broken energy drink.
   - expected: the item name and broken state have a visible separator, reading as “energy drink — broken” (or the chosen state format), not `energy drinkbroken`.
3. Select each chip and compare its visible label with the item record's `name`/`display_name` fields.
   - expected: scene snapshot and You strip resolve from the existing display-name field; they do not add a second name-resolution source.

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
