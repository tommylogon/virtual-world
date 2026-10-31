---
type: task
status: todo
area: refactor
priority: medium
wiki: "[[World Building/Graph System|Graph System]]"
related: [task-23, task-357, task-886]
blocked_by: []
---

# task-895: Retire unlocks edges and trigger graph representation

**Filed:** 2026-10-21
**Updated:** 2026-10-31
**Related:** task-23, task-357, task-886
**Blocked by:** none (unblocked; task-886 completed)

<!-- deps:start -->
**Related:** [[task-23-remove_locked_with]], [[task-357-structure-save-load-connected-areas]], [[task-886-refactor-triggers-from-graph-nodes-to-node-property-arrays]]
<!-- deps:end -->

## What

Retire `unlocks` graph edges and the obsolete `logic_trigger` node plus `triggers` edge representation.
Keep trigger definitions as `owner.properties["triggers"]` data and keep trigger effects such as
`unlock_way` as executable behavior. **`unlock_way` stays.**

STATUS UPDATE (2026-10-31): Task-886 has landed. Load-time migration `_migrate_triggers_from_nodes_to_properties`
is active in `engine/serialization.py:98-120`. This card is now UNBLOCKED and owns the removal of
legacy constants, runtime fallback paths, and frontend edge-authoring choices.

## Why

Task-886 moved trigger definitions off `logic_trigger` graph nodes and `triggers` edges into the
owning node's `properties["triggers"]`. However, legacy definitions and edge authoring choices still
remain in the codebase:
- `graph.py:934-935` still declares `EDGE_UNLOCKS = "unlocks"` and `EDGE_TRIGGERS = "triggers"`.
- `engine/items/use_actions.py:228-232` still checks for `EDGE_UNLOCKS` edges on item use.
- `static/js/graph/edge-types.ts` still lists `'unlocks'` and `'triggers'` in `EdgeTypes.ALL` (lines 30-31),
  offers them in `validForSource` (line 58), and validates them in `validTargets` (lines 85-86).
- `tests/test_world_scopes.py` still creates `EDGE_UNLOCKS` edges.

Current scenario and library graph data contains zero `unlocks` edges. Graph edge authoring should
not offer `unlocks` or `triggers`, and the simulation runtime should not maintain dead edge pathways.

## How

1. **Remove graph edge constants**:
   - Retire `EDGE_UNLOCKS` and `EDGE_TRIGGERS` from `graph.py` (move to legacy compatibility dictionary if needed for migration).
2. **Remove runtime readers**:
   - Clean up `engine/items/use_actions.py` to remove the `EDGE_UNLOCKS` query; ensure unlocking uses `on_use_on` triggers with the `unlock_way` effect.
3. **Remove frontend authoring options**:
   - Remove `'unlocks'` and `'triggers'` from `static/js/graph/edge-types.ts` (`EdgeTypes.ALL`, `validForSource`, and `validTargets`). Rebuild TypeScript (`npm run build:ts`).
4. **Preserve legacy load migration**:
   - Retain `_migrate_triggers_from_nodes_to_properties` in `engine/serialization.py` to convert old saves on load.
   - For any legacy `unlocks` edge in an old save, convert it to an `on_use_on` trigger with `unlock_way`.
5. **Update tests and docs**:
   - Update `tests/test_world_scopes.py` and trigger authoring tests to use property-based triggers.
   - Verify `tests/test_trigger_system.py` and `tests/test_trigger_migration.py`.

## Browser UI and intended live verification

Intended UI home: Graph view edge authoring and item use in a scenario with a locked way.

Current availability: Task-886 implemented property-based trigger storage and execution. The graph editor still exposes `unlocks` and `triggers` in `static/js/graph/edge-types.ts`.

Live steps when available:
1. Open an item in the graph editor and inspect its edge choices.
   - expected: neither `unlocks` nor `triggers` is offered as a graph edge type.
   - observed: currently `unlocks` and `triggers` are listed in `EdgeTypes.validForSource`.
2. Configure an `on_use_on` trigger on a key item with an `unlock_way` effect, then use the key on its locked way.
   - expected: the way unlocks through the owner's trigger property with no graph edge created.
3. Load a legacy save containing an old `triggers` edge or `unlocks` edge.
   - expected: the migration converts them to properties on load, and no legacy edges exist in the live graph.

## Steps to verify

1. Search production source and generated frontend output for `EDGE_UNLOCKS`, `EDGE_TRIGGERS`, and edge authoring for `unlocks`:
   - expected: no active graph authoring or runtime path uses those graph edges; legacy serialization migration is the only reader of old edge payloads; `unlock_way` remains as a trigger effect.
   - observed: `graph.py:934-935`, `engine/items/use_actions.py`, and `edge-types.ts` still retain active entries.
2. Load a legacy graph payload containing a trigger node/edge and an item-to-way `unlocks` edge:
   - expected: triggers migrate to node properties; legacy nodes and edges are discarded from the active graph.
3. Run focused tests:
   - expected: `python -m pytest tests/test_trigger_migration.py tests/test_trigger_system.py tests/test_world_scopes.py` passes cleanly.

## Acceptance

- [ ] No production authoring surface offers `unlocks` or `triggers` as graph edge types.
- [ ] No active runtime path reads `unlocks` or `triggers` as graph edges; `unlock_way` effect remains fully functional.
- [ ] Old saved trigger nodes/edges migrate into owner properties before activation and are stripped from the active graph.
- [ ] `tests/test_world_scopes.py` and legacy edge tests are updated to property-based triggers.
- [ ] Generated JavaScript matches TypeScript (`npm run build:ts`), and contract check passes.

## Files

- `graph.py` - retire `EDGE_UNLOCKS` and `EDGE_TRIGGERS`
- `engine/items/use_actions.py` - remove legacy edge reader
- `static/js/graph/edge-types.ts` - remove `unlocks` and `triggers`
- `engine/serialization.py` - retain migration on load
- `tests/test_world_scopes.py` - update edge references
- `docs/virtualWorld/World Building/Graph System.md`

## Reconnaissance (2026-10-31)
- Measured: Task-886 is completed and landed in `engine/serialization.py:98-120`. `EDGE_UNLOCKS` has 1 hit in `graph.py`, 2 in `use_actions.py`, and 2 in `test_world_scopes.py`. `EDGE_TRIGGERS` has 7 in `graph.py` and scattered migration/test hits. `edge-types.ts` still offers both edge types in `validForSource`.
- Verdict: UNBLOCKED and ready to execute. Status remains todo.
