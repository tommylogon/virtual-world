---
type: task
status: todo
area: library
priority: low
wiki: "[[Library System/Library System Overview]]"
---

# task-684: matches and candlestick carry light triggers in the save but not in the library entry

**Filed:** 2026-10-04
**Related:** 

## What

The live save authors on_light / on_toggle_off / on_toggle_on triggers on item_matches, item_candle_stub and item_candlestick, but their library entries under data/library/items carry no triggers, so re-importing any of them from the library drops the authored lighting behaviour and the node falls back to a plain dim light_source. The missing toggleable tag has been added to all three (both places). Sync the trigger definitions themselves, or state that the save is the authoring surface for these and the library is deliberately trigger-free.

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

Intended UI home: Library Browser → choose `item_matches`, `item_candle_stub`, or `item_candlestick` → place/import into a scenario → inspect the item's triggers and operate it in the game view.

Current availability: the saved scenario contains `on_light`, `on_toggle_off`, and `on_toggle_on` for these items, while the corresponding library entries lack them. The card leaves open whether the library or save is the authoring surface; resolve that before deciding which data should be copied.

Live steps when available:
1. In a scratch scenario, place each of the three items from the Library Browser and inspect its trigger list before interaction.
   - expected: each imported item has the same authored lighting/toggle behavior as its canonical library definition; no trigger disappears on import.
2. Light the matches, then toggle the candle stub and candlestick off and on using their normal item actions.
   - expected: the correct `on_light`/`on_toggle_off`/`on_toggle_on` event fires for the operated item and the lighting state updates accordingly.
3. Save the scenario, reload it, and compare the item trigger records with the library entry.
   - expected: behavior survives save/reload and re-import; the chosen authoring source is explicit and there is no conflicting duplicate trigger set.

This section is not a claim that planned UI exists or works today.
