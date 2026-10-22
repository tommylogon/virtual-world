---
type: task
status: todo
area: refactor
priority: medium
wiki: "[[World Building/Graph System|Graph System]]"
related: [task-23, task-357, task-886]
blocked_by: [task-886]
---

# task-895: Retire unlocks edges and trigger graph representation

**Filed:** 2026-10-21
**Related:** task-23, task-357, task-886
**Blocked by:** task-886

<!-- deps:start -->
**Blocked by:** [[task-886-refactor-triggers-from-graph-nodes-to-node-property-arrays]]
**Related:** [[task-23-remove_locked_with]], [[task-357-structure-save-load-connected-areas]], [[task-886-refactor-triggers-from-graph-nodes-to-node-property-arrays]]
<!-- deps:end -->

## What

Retire `unlocks` graph edges and the old `logic_trigger` node plus `triggers` edge representation. Keep trigger definitions as `owner.properties["triggers"]` data and keep trigger effects such as `unlock_way` as executable behavior. **`unlock_way` stays.** This is follow-up cleanup after task-886 migrates legacy trigger graph nodes and edges into owner properties.

## Why

The graph editor still offers `unlocks` for item-to-way edges and `engine/items/use_actions.py` still executes that edge directly, even though structure serialization classifies it as obsolete and current scenario/library graph data contains zero such edges. Separately, task-886 is moving trigger definitions off `logic_trigger` graph nodes and `triggers` edges into the owning node's `properties["triggers"]`. Its migration must land before removing legacy edge readers and writers. The authored graph data survey found 886 `triggers` edges across scenario files and 107 in library room data; these are migration inputs, not a reason to retain the edge type.

## How

Complete task-886 first and retain its load-time migration for old trigger nodes and edges. Then trace every `unlocks` and `triggers` graph-edge reader, writer, validator, renderer, copy path, serializer, and documentation reference.
Remove both edge types from the canonical graph constants and type registry, editor edge creation, rendering, copying, and runtime edge readers. Keep trigger authoring and execution against the owning node's `properties["triggers"]` array. Remove `logic_trigger` as a graph node type from normal runtime and authoring paths. Do not remove trigger definitions, trigger execution, or the `unlock_way` effect.
On legacy load, migrate trigger node/edge payloads into owner properties before the graph becomes active, then discard those legacy nodes and edges. For legacy `unlocks` edges, preserve their item-to-way behavior by converting them to an `on_use_on` trigger using `unlock_way`, or emit a clear migration diagnostic and discard only when safe conversion is impossible. Do not silently change behavior.
Keep `unlock_way` as a trigger effect and verify a key item unlocks a way through an owner-property trigger after all graph-edge paths are removed.
Update graph, trigger, and item documentation to describe triggers as owner-node data and way unlocking as an effect, then add focused regressions for both legacy migrations and current property-based execution.

## Browser UI and intended live verification

Intended UI home: Graph view edge authoring and item use in a scenario with a locked way

Current availability: The current editor exposes edge types through the item node's special-edge controls; trigger editing is available on item and way inspectors.

Live steps when available:
1. Open an item in the graph editor and inspect its special edge choices.
   - expected: neither `unlocks` nor `triggers` is offered as a graph edge; trigger authoring edits the selected owner's trigger property list.
   - observed: `unlocks` is still offered by the item edge registry, and trigger helper code still creates graph nodes and edges.
2. Configure an `on_use_on` trigger on a key item with an `unlock_way` effect, then use the key on its locked way.
   - expected: the way unlocks through the owner's trigger property and normal event output, with no trigger or unlock graph edge.
   - observed: task-886 implements property-based trigger execution, but legacy edge creation/fallback remains; live browser interaction is pending this cleanup.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Search production source and generated frontend output for `EDGE_UNLOCKS`, `EDGE_TRIGGERS`, `unlocks` graph-edge handling, and `logic_trigger` graph-node creation.
   - expected: no active graph authoring/runtime path uses those graph concepts; legacy serialization migration is the only accepted reader of old edge payloads; `unlock_way` remains as an effect.
   - observed: not yet run; current source still has an unlock edge registry/runtime reader and trigger edge/node creation and fallback paths.
2. Load a legacy graph payload containing a trigger node/edge and an item-to-way `unlocks` edge.
   - expected: trigger definitions are migrated to owner properties, legacy trigger nodes/edges are absent from the active graph, and the old unlock relation is converted or reported with the documented diagnostic.
   - observed: task-886 provides trigger migration; no unlock edges were found in the current scenario/library survey. Combined legacy migration behavior is not yet verified.
3. In the browser, inspect item trigger authoring, then use a key on a locked way with an owner-property `on_use_on` trigger containing `unlock_way`.
   - expected: trigger authoring edits node properties directly, and the way unlocks with no trigger or unlock graph edge.
   - observed: task-886 reports property-based trigger authoring and execution; this browser flow has not been verified after legacy edge cleanup.
4. Run focused legacy-load, trigger-authoring, and item-trigger regression tests.
   - expected: old payload migration and current property-based trigger execution pass without graph trigger or unlock edges.
   - observed: not yet run; this is pending implementation.

## Acceptance

- [ ] No production authoring surface offers `unlocks` or `triggers` as graph edge types, and no active runtime path reads them as graph edges.
- [ ] Old saved trigger nodes/edges migrate into owner properties before activation and are absent from the active graph.
- [ ] Old saved `unlocks` edges are converted to equivalent property-based trigger behavior or discarded with a clear diagnostic when safe conversion is impossible.
- [ ] Trigger authoring and execution use the owning node's `properties["triggers"]`; `unlock_way` still unlocks its target through normal item use.
- [ ] Generated JavaScript matches TypeScript, graph/trigger/item documentation describes the property-based model, and focused regressions cover migration and retained behavior.

## Files

- `graph.py`
- `engine/items/use_actions.py`
- `engine/serialization.py`, `engine/serialization_legacy.py`, `engine/serialization_template.py`
- `engine/trigger_system.py`, `engine/triggers/execution.py`, `engine/triggers/materialize.py`, `engine/triggers/ui.py`
- `engine/structures.py`
- `static/js/graph/edge-types.ts and generated edge-types.js`
- `static/js/graph/node-operations.ts and generated node-operations.js`
- `static/js/graph/network-manager.ts and generated network-manager.js`
- `static/js/inspector/trigger-helpers.ts`, `static/js/inspector.ts`
- `data/scenarios and saved graph loading/migration code, if needed for legacy edge handling`
- `tests for item use, trigger authoring, and legacy graph loading`
- `docs/virtualWorld/World Building/Graph System.md`
- `docs/virtualWorld/Rules Engine/Triggers & Effects.md`
- `docs/virtualWorld/Items & Inventory/Items Overview.md`
