---
type: task
status: done
area: refactor
priority: medium
wiki: "[[World Building/Graph System|Graph System]]"
related: [task-23, task-357, task-886]
blocked_by: []
---

# task-895: Retire unlocks edges and trigger graph representation

**Filed:** 2026-10-21
**Completed:** 2026-10-31
**Related:** task-23, task-357, task-886
**Blocked by:** none (unblocked; task-886 completed)

<!-- deps:start -->
**Related:** [[task-23-remove_locked_with]], [[task-357-structure-save-load-connected-areas]], [[task-886-refactor-triggers-from-graph-nodes-to-node-property-arrays]]
<!-- deps:end -->

## What

Retire `unlocks` graph edges and the obsolete `logic_trigger` node plus `triggers` edge representation.
Keep trigger definitions as `owner.properties["triggers"]` data and keep trigger effects such as
`unlock_way` as executable behavior. **`unlock_way` stays.**

STATUS UPDATE (2026-10-31): Completed. `EDGE_UNLOCKS` and `EDGE_TRIGGERS` are retired from active edge definitions.
`engine/items/use_actions.py` legacy edge reader removed. Frontend edge-authoring choices and context-menu trigger
edge creation options removed. `_migrate_unlocks_edges_to_triggers` added to `engine/serialization.py`.
`graph.py` node trigger indexing implemented so `get_trigger_sources` supports property triggers natively.

## Why

Task-886 moved trigger definitions off `logic_trigger` graph nodes and `triggers` edges into the
owning node's `properties["triggers"]`. However, legacy definitions and edge authoring choices still
remained in the codebase:
- `graph.py` declared `EDGE_UNLOCKS = "unlocks"` and `EDGE_TRIGGERS = "triggers"`.
- `engine/items/use_actions.py` checked for `EDGE_UNLOCKS` edges on item use.
- `static/js/graph/edge-types.ts` listed `'unlocks'` and `'triggers'` in `EdgeTypes.ALL` and `validForSource`.
- `tests/test_world_scopes.py` created `EDGE_UNLOCKS` edges.

Current scenario and library graph data contains zero `unlocks` edges. Graph edge authoring should
not offer `unlocks` or `triggers`, and the simulation runtime should not maintain dead edge pathways.

## How

1. **Remove graph edge constants**:
   - Retired active `EDGE_UNLOCKS` and `EDGE_TRIGGERS` from `graph.py` (moved to legacy compatibility section).
2. **Remove runtime readers**:
   - Cleaned up `engine/items/use_actions.py` to remove the `EDGE_UNLOCKS` query; way unlocking uses `on_use_on` triggers with the `unlock_way` effect.
3. **Remove frontend authoring options**:
   - Removed `'unlocks'` and `'triggers'` from `static/js/graph/edge-types.ts` and trigger edge creation actions from `static/js/graph/context-menu.ts`. Rebuilt TypeScript (`npm run build:ts`).
4. **Preserve legacy load migration**:
   - Retained `_migrate_triggers_from_nodes_to_properties` in `engine/serialization.py` to convert old saves on load.
   - Added `_migrate_unlocks_edges_to_triggers` in `engine/serialization.py` to convert legacy `unlocks` edges to `on_use_on` triggers with `unlock_way`.
5. **Update tests and docs**:
   - Updated `tests/test_world_scopes.py` and `tests/test_trigger_migration.py`.
   - Updated `docs/virtualWorld/World Building/Graph System.md`.

## Browser UI and intended live verification

Intended UI home: Graph view edge authoring and item use in a scenario with a locked way.

Current availability: Property-based trigger storage and execution is active. Special edge authoring no longer offers `unlocks` or `triggers`.

Live steps:
1. Open an item in the graph editor and inspect its edge choices.
   - expected: neither `unlocks` nor `triggers` is offered as a graph edge type.
   - observed: verified; neither is listed in `EdgeTypes.validForSource`.
2. Configure an `on_use_on` trigger on a key item with an `unlock_way` effect, then use the key on its locked way.
   - expected: the way unlocks through the owner's trigger property with no graph edge created.
   - observed: verified via `tests/test_item_actions.py` and `tests/test_trigger_system.py`.
3. Load a legacy save containing an old `triggers` edge or `unlocks` edge.
   - expected: the migration converts them to properties on load, and no legacy edges exist in the live graph.
   - observed: verified via `tests/test_trigger_migration.py`.

## Steps to verify

1. Search production source and generated frontend output for active `EDGE_UNLOCKS` and `EDGE_TRIGGERS`:
   - expected: no active graph authoring or runtime path uses those graph edges; legacy serialization migration converts old edge payloads.
   - observed: verified; active constants retired, frontend menus stripped, serialization handles migration.
2. Load a legacy graph payload containing a trigger node/edge and an item-to-way `unlocks` edge:
   - expected: triggers migrate to node properties; legacy nodes and edges are discarded from the active graph.
   - observed: verified via `test_legacy_unlocks_edge_migrates_to_on_use_on_trigger`.
3. Run focused tests:
   - expected: `python -m pytest tests/test_trigger_migration.py tests/test_trigger_system.py tests/test_world_scopes.py tests/test_item_actions.py` passes cleanly.
   - observed: 42 + 163 + 77 tests passing.

## Acceptance

- [x] No production authoring surface offers `unlocks` or `triggers` as graph edge types.
- [x] No active runtime path reads `unlocks` or `triggers` as graph edges; `unlock_way` effect remains fully functional.
- [x] Old saved trigger nodes/edges migrate into owner properties before activation and are stripped from the active graph.
- [x] `tests/test_world_scopes.py` and legacy edge tests are updated to property-based triggers.
- [x] Generated JavaScript matches TypeScript (`npm run build:ts`), and contract check passes.

## Files

- `graph.py` - retire `EDGE_UNLOCKS` and `EDGE_TRIGGERS` from active set; index node property triggers
- `engine/items/use_actions.py` - remove legacy edge reader
- `static/js/graph/edge-types.ts`, `static/js/graph/edge-types.js` - remove `unlocks` and `triggers`
- `static/js/graph/context-menu.ts`, `static/js/graph/context-menu.js` - remove trigger edge creation actions
- `engine/serialization.py` - add legacy unlocks edge migration on load
- `tests/test_world_scopes.py` - update edge references
- `tests/test_trigger_migration.py` - add migration and index tests
- `docs/virtualWorld/World Building/Graph System.md` - document property-based triggers

## Reconnaissance (2026-10-31)
- Measured: All acceptance criteria met. Edge constants retired to legacy block. Serialization migrates old edges. Node property triggers indexed natively.
- Verdict: COMPLETED.
