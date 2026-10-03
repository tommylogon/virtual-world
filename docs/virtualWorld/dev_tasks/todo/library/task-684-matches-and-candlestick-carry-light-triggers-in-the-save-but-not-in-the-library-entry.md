---
type: task
status: todo
area: library
priority: low
---

# task-684: matches and candlestick carry light triggers in the save but not in the library entry

**Filed:** 2026-10-04
**Related:** 

## Goal

The live save authors on_light / on_toggle_off / on_toggle_on triggers on item_matches, item_candle_stub and item_candlestick, but their library entries under data/library/items carry no triggers, so re-importing any of them from the library drops the authored lighting behaviour and the node falls back to a plain dim light_source. The missing toggleable tag has been added to all three (both places). Sync the trigger definitions themselves, or state that the save is the authoring surface for these and the library is deliberately trigger-free.

## Acceptance

- TODO
