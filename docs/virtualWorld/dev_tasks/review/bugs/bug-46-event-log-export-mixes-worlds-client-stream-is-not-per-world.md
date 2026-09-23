---
type: bug
status: review
area: bugs
priority: medium
---

# bug-46: Event log export mixes worlds (client stream is not per-world)

**Filed:** 2026-09-23
**Related:** 

## Goal

Reported: 'something went pretty wrong? im in world_template, but it seems to have soaked on goblin camp?' The world was fine (data/autosave.json is world_template: Kaelen Voss/Lyrie/rat, 19 areas, _scenario_name world_template; its game_log has zero Krikka entries). The exported event log is the CLIENT event stream (WorldExport.exportEventLog writes the visible stream; docs/virtualWorld/UI & Settings/Event Log Export.md), which main.js restores from IndexedDB at startup (line 806) and re-saves every 5s (line 839). It was only cleared when a scenario was opened through the scenario manager, so any other world change (server restart auto-loading a different world, save load) left the previous world's bubbles in place - and an export then mixed worlds. Fixed: StreamPersistence now stamps the persisted stream with the world key (_scenario_name, falling back to scenario_source / body dataset) and drops the stored log when the world differs, on both persist and restore. Verified live: persist in world_template kept 86 entries; switching to kraktooth_goblin_camp cleared to 0; a stale log from another world was not restored; the same world kept its entries.

## Acceptance

- TODO
