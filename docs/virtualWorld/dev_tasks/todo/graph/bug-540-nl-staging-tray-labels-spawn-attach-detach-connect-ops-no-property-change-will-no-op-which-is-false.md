---
type: bug
status: todo
area: graph
priority: medium
wiki: "[[World Building/World Structure & Graph Representation]]"
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

## Browser UI and intended live verification

Intended UI home: NL editor → stage a `spawn_library_item`, `attach`, `detach`, or `connect_areas` operation → inspect that operation's summary in the staging tray before Apply.

Current availability: the card records a live case where 16 `spawn_library_item` rows were labeled “no property change - will no-op” even though Apply still spawned items. The misleading label is a display defect; the operations currently execute.

Live steps when available:
1. In scenario `labs`, stage one `spawn_library_item`, one `attach`, one `detach`, and one `connect_areas` operation. Count the tray rows and read each row's summary.
   - expected: each row describes its actual effect and relevant source/target; none is labeled as a no-op merely because `opDiff()` does not model its properties.
2. Apply the batch and inspect the graph and containment/connection edges.
   - expected: each displayed summary corresponds to the operation that ran; spawned nodes and changed edges are visible.
3. Stage an unsupported or invalid operation and inspect its row before Apply.
   - expected: the UI identifies an actual validation failure or unknown operation explicitly; it does not reuse the empty-property-diff label for an operation that will execute.

This section is not a claim that planned UI exists or works today.
