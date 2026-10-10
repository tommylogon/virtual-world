---
type: bug
status: todo
area: graph
priority: medium
---

# bug-540: NL staging tray labels spawn/attach/detach/connect ops '(no property change - will no-op)', which is false

**Filed:** 2026-10-10
**Related:** 

## What

In the NL editor staging tray, every staged op that is not an update_node / create_node / delete / library_* / bulk op renders '(no property change - will no-op)'. Observed live 2026-10-10 in scenario labs: 16 spawn_library_item ops each showed that string, though a spawn plainly adds a node. Root: static/js/nl-editor/diff.ts opDiff() returns {kind:'other', changes:[]} for any op type it does not model (spawn_library_item, attach, detach, connect_areas, populate_area, create_trigger, ...), and summaryLines() maps empty changes to that string. It is display-only - Apply still runs the ops, since nothing filters on the label - but it is alarming and hides what the op will do. Fix: give each op type a real one-line summary (e.g. '+ spawn glass_beaker into Task 1', '+ attach glass_vial -> player_Bob (carrying)', '+ connect A-B via Oak Door') and reserve '(no-op)' for a patch that genuinely changes nothing. Related task-461 (the apply-time diff), which modelled property changes and no-op PATCHES but not these op kinds.

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
