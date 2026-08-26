---
group: Items
---

# Fix: Duplicating an Item Loses Its Triggers (case-mismatched edge ids)

**Filed**: 2026-08-09  
**Priority**: High  
**Status**: In Review — implemented 2026-08-09, verified via Playwright UI repro (orphan count 0), UI smoke 25/25.

---

## Summary

Duplicating an item (graph context menu → 📋 Duplicate) silently lost all edges — including trigger edges — whenever the new name contained uppercase letters.

Root cause: `GraphNodeOps.duplicateNode` (`static/js/graph/node-operations.js`) computed the new node id in the caller's case (`item_Button_18_-_2`) and used that string as the source for every copied edge, but the backend lowercases node ids on create (`routes/graph.py:32` `create_node`: `.lower()`). Result: node `item_button_18_-_2` with edges pointing from `item_Button_18_-_2` — orphaned edges, and the duplicate appeared to have zero triggers.

Secondary effect: `remove_node` cleans edges under the exact id, so deleting the broken duplicate left the mixed-case orphan edges behind permanently.

## Reproduction

- Duplicate an item, name it with any capital letter → duplicate node exists but the inspector shows no Triggers/edges; `/api/graph/edges` contains orphaned edges under the mixed-case source id.
- Reproduced live: `item_coffee_grinder_dup_UI_test` (all 4 trigger edges orphaned under `item_coffee_grinder_dup_UI_test`); same pattern visible in the user's world for `item_Button_18_-_2` (in + triggers), `item_Jumpsuit_2`, `item_Button_7`.

## Fix

- `static/js/graph/node-operations.js`:
  - `duplicateNode`: generated `newId` is now `.toLowerCase()` before the existence check, node creation, and `_copyEdges` — matches the backend's create_node convention (ids always lowercase, see AGENTS.md memory `node_ids_lowercase_generated`).
  - `_copyEdges`: the recursive item-copy `copyId` is also `.toLowerCase()` for the same reason.
- Character duplication path is untouched (player ids like `player_John_doe` are not lowercased by `createCharacter`).

## Verification

- Playwright UI repro with an uppercase name ("Coffee Grinder Dup Case Test"): node `item_coffee_grinder_dup_case_test` got all 4 trigger edges + `on` edge, **0 orphaned** edges.
- Clean duplicate (lowercase name): 5 edges incl. 4 triggers, as before.
- `node --check` clean; `tools/test_ui.cjs` 25/25 passed.
- Live cleanup: removed 30 orphan/test edges and the duplicate test nodes; the user's bug orphans (`item_Button_18_-_2`, `item_Jumpsuit_2`, `item_Button_7`) are cleared. Legacy mixed-case ids (Task 3 panels/areas, `area_Task_18_-_Room_4`) were left untouched — unrelated and pre-existing.

## Files Changed

- `static/js/graph/node-operations.js` — lowercase generated ids in `duplicateNode` + `_copyEdges`
