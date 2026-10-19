---
type: task
status: done
area: graph
priority: medium
---

# task-377: duplicate-room-and-item

**Filed**: 2026-08-30
**Status**: In review (single-write backend endpoint and UI actions complete).
**Source**: docs/virtualWorld/Scenario Workflows & UI Audit.md - P3 - Duplicate room (with items/contents/triggers) and duplicate item (with contents).

## Notes

See the audit doc for the full section and sequencing notes. Reuse existing machinery where noted; the guardrails are: CLI-free, undo-safe, and no new storage formats unless the audit says so.

> Hardening follow-up: the clone recursion walks a PRE-INDEXED original container tree (never live edges - parent edges previously looked like contents and re-discovered clones forever), with a shared visited set (cycles) and a 200-node cap; duplicate pushes an undo snapshot BEFORE mutating. tests: cycle guard + snapshot tests in tests/test_duplicate.py.

## What

Duplicate room (with contained items, sub-contents, and triggers) and duplicate item (with contents and triggers), plus character duplication. Handled with single-write backend `/api/graph/duplicate` and client UI buttons in Area Inspector, Item Inspector, and canvas context menu.

## Why

Re-authoring similar rooms, items, or characters from scratch was tedious and slow. Duplication copies definitions and internal structures while assigning fresh IDs and preserving placement. The single-write backend endpoint eliminates client-side roundtrip lag.

## How

- Backend route `/api/graph/duplicate` handles single-write duplication with deep containment recursion, cycle guards, and pre-push undo snapshot.
- Frontend `ApiClient.duplicateNode` invokes `/api/graph/duplicate` and updates world state.
- Graph canvas context menu and Area/Item Inspector panels wire the duplicate action directly to `graphManager._duplicateNode()`.

## Browser UI and intended live verification

Intended UI home: Graph canvas duplicate action for an area or item, with the existing Area/Item Inspector for the selected result.

Current availability: Implemented in UI via Area Inspector, Item Inspector, and context menu; backed by `/api/graph/duplicate`.

Live steps:

1. In a scratch copy, select an area with contents and duplicate it; repeat for an item with contents.
   - expected: A distinct copy is created with intended contents and triggers, without recursively cloning parent edges.

2. Undo the duplication and watch the graph/event feedback during the operation.
   - expected: One undo restores the prior state.

## Steps to verify

1. Duplicate an area with items and triggers via `/api/graph/duplicate` or Area Inspector.
   - expected: Clones area, contained items, sub-items, and attached triggers with unique IDs.
   - observed: Verified by test_duplicate_area_clones_items_contents_and_triggers in tests/test_duplicate.py (11 tests pass).
2. Duplicate an item on a surface or in a container.
   - expected: Cloned item remains on the same surface/parent without duplicating the parent area.
   - observed: Verified by test_duplicate_item_on_surface_keeps_same_parent and test_duplicate_item_keeps_placement_and_contents in tests/test_duplicate.py.
3. Revert duplication.
   - expected: Single undo restores prior state.
   - observed: Verified by test_duplicate_pushes_undo_snapshot in tests/test_duplicate.py.

## Acceptance

- [x] Duplicating an area clones its contained items, sub-items, and triggers.
- [x] Duplicating an item preserves parent placement and clones internal contents.
- [x] Single-write endpoint prevents runaway client-side fetch lag.
- [x] Operation is covered by undo snapshots.
- [x] 11 unit tests in tests/test_duplicate.py pass.

## Files

- `routes/graph.py`
- `static/js/graph-manager.ts`
- `static/js/api.ts`
- `static/js/graph/context-menu.ts`
- `static/js/inspector/area-view.ts`
- `static/js/inspector/item-view.ts`
- `tests/test_duplicate.py`
