---
type: task
status: todo
area: refactor
priority: low
wiki: "[[Triggers]]"
---

# task-901: Split trigger definition converters out of the canvas module

**Filed:** 2026-10-22
**Related:** bug-567, task-900

<!-- deps:start -->
**Related:** [[bug-567-trigger-graph-editor-reads-and-writes-the-legacy-edge-store]], [[task-900-materialize-trigger-writes-three-homes-and-documents-one]]
<!-- deps:end -->

## What

The four pure converters (`triggerToGraph`, `compileToEngine`, `triggerDefFromEdge`, `triggersFromGraphEdges`) live inside the same 2900-line IIFE as the canvas, camera, viewport store and blueprint browser in `static/js/shared/trigger-graph.ts`. Because of that, the only way to test them is the browser-ish vm harness, and the same condition list is normalised three times in one round trip: `triggerDefFromEdge` wraps leaves into `{operator: 'and'}`, `triggerToGraph` flattens it again with `_treeIsFlat` and `_flattenConditions`, and `_conditionToGraphProps` accepts a third shape. Each function has its own idea of "flat".

## Why

Three normalisations of one shape is how a condition silently disappears. The converters are the part of the editor that must be provably correct, and they are the part with the least isolation. Every store-boundary fix in this area has to reason about the canvas to change a data function.

## How

Move the converters into a pure `static/js/shared/trigger-def.ts` with no DOM access, exporting one `normalizeConditions()` used by both directions and type-only imports for the node and wire shapes. Keep `trigger-graph.ts` as the canvas and viewport layer and re-export the moved functions on `TriggerGraph` so existing call sites and `globals.d.ts` keep working. Add unit tests for triggerToGraph/compileToTriggers round trips, including a fan-out, a NOT group and an empty definition.

## Browser UI and intended live verification

Intended UI home: Inspector > any item > Triggers > Graph

Current availability: Open http://localhost:4444 after the split; the editor must behave identically.

Live steps when available:
1. Open the Graph editor for a defined trigger and confirm the nodes, wires and fields render
2. Save and reopen, confirming the definition is unchanged
3. Draw a second effect from one condition output and confirm both effects compile

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Follow the intended live path in Browser UI and intended live verification when that surface is available.
   - expected: TODO
   - observed: TODO
2. Record the browser surface and interaction actually used (for example: navigate, click, hover, type, expand, or scroll to the bottom).
   - expected: TODO
   - observed: TODO
3. Run the targeted regression test for the mechanism.
   - expected: TODO
   - observed: TODO

## Acceptance

- [ ] trigger-def.ts has no document, window, Lit or canvas reference
- [ ] One normalisation function is the only place a condition tree is converted
- [ ] Round-trip tests cover a flat AND, an OR group, a NOT group, fan-out and an empty definition
- [ ] TriggerGraph.triggerToGraph and TriggerGraph.compileToTriggers still resolve for existing callers
- [ ] python tools/ts_convert.py check and node tools/unit/run.cjs pass

## Files

- `static/js/shared/trigger-def.ts`
- `static/js/shared/trigger-graph.ts`
- `static/js/types/globals.d.ts`
- `tools/unit/test_trigger_graph.js`
