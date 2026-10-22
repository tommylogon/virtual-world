---
type: bug
status: review
area: triggers
priority: high
wiki: "[[Triggers]]"
---

# bug-567: Trigger graph editor reads and writes the legacy edge store

**Filed:** 2026-10-22
**Related:** bug-566

<!-- deps:start -->
**Related:** [[bug-566-load-crashes-when-properties-triggers-is-an-object]]
<!-- deps:end -->

## What

Every trigger surface in the editor still reads and writes the retired representation. `_getNodeTriggerData` calls `triggersFromGraphEdges`, which filters `edge.type === 'triggers'` only, so a node whose rules live in `properties.triggers` shows zero (measured: a node with two property triggers and no edges returns 0). The Graph editor then opens a blank default `on_use` and saves by creating a `logic_trigger` node plus a `triggers` edge, never touching the property array. Suggest/Apply does the same (`_applyTriggerDiff`, `createTriggerOnNode`). The item library reads the same edge-only path when it builds a world-to-library payload. And `compileToEngine` returns only `{trigger_type, effects, conditions, fail_message}`, so a graph save drops `id`, `once`, `fired`, `cooldown` and `success_message` (probe: those five keys absent from the compiled result).

## Why

One store is read by some surfaces and written by others, which produces four user-visible symptoms from one defect: an empty trigger list, an edit that does not appear, accepted suggestions that vanish until a reload, and a library save that writes `triggers: []`. Each graph save also silently resets trigger state. Until the property array is the only read and write target, the migration can never finish and every new feature has to know about both stores.

## How

Make `properties.triggers` authoritative in the editor and treat legacy edges as a read-only fallback. Extend `triggersFromGraphEdges(edges, nodes, sourceId)` to read the source node's property array first, dedupe legacy edges by id, and carry each entry's `id` plus passthrough fields. Add `triggerDefFromProperty(entry)`. Add `triggersToGraph(defs)` (one trigger block per definition, stacked vertically, each root carrying its `id`, `once`, `fired`, `cooldown`, `name`, `success_message`) and `compileToTriggers(graph)` (trace every root, carry the passthrough fields); keep `compileToEngine(graph)` as the first-root wrapper the form editor uses. In `trigger-helpers._openGraphEditor`, load all definitions and persist the compiled list back into the array by id, merging over the existing entry so unknown keys survive. Rewrite `_applyTriggerDiff` and `createTriggerOnNode` to update the array in one call (delete legacy edge targets only for rules being removed). Keep `item-library._extractTriggersFromEdges` working through the extended reader, and switch its Graph button to the same all-definitions graph.

## Browser UI and intended live verification

Intended UI home: Inspector > item_water_bottle > Triggers > Graph

Current availability: Open the app on http://localhost:4444, load the mansion scenario, select item_water_bottle in the graph, then open the Triggers section.

Live steps when available:
1. Count the trigger cards in the Triggers section and write the number down
2. Click Graph and confirm the canvas shows one trigger root per card, not a blank on_use node
3. Edit a condition, save, and confirm the card count and the condition text changed without a reload
4. Reopen Graph and confirm the edit is still there
5. Click Suggest, accept one row, and confirm the new trigger appears in the list immediately

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Open the Triggers section for a node whose rules are in the property store.
   - expected: one card per stored definition, including a node whose `properties.triggers` holds the wrapped library shape.
   - observed: live on http://localhost:4444 (301-node world), `inv_elena vance_water_bottle` holds the wrapped shape and renders 5 cards, matching the 5 entries `TriggerGraph.triggersFromGraphEdges` returns. Before the change the same node read 0 through the edge-only path.
2. Click Graph on that node and count the trigger roots.
   - expected: one root per definition, each carrying its id, never a single blank `on_use`.
   - observed: the canvas held 14 nodes: roots `t0_n0` through `t4_n0` (5 roots), each block carrying its conditions and effects below it.
3. Press Apply without editing and confirm the property array survives.
   - expected: same count, same ids, no new `logic_trigger` node, no new `triggers` edge.
   - observed: server `/api/state` after Apply returned `shape: list, count: 5`, the original 5 ids, effects `[2,1,1,1,1]`, 9 `logic_trigger` nodes and 8 `triggers` edges, unchanged from before the save. The wrapped shape was normalised to a list by the write.
4. Build a world-to-library payload for the same node.
   - expected: the payload carries the property triggers instead of `[]`.
   - observed: `itemLib._buildWorldItemPayload(id).payload.triggers.length === 5`, first entry effects length 2.
5. Click Suggest and read the diff.
   - expected: types already present in the property array are reported as covered, not missing.
   - observed: the modal listed ON_EXAMINE, ON_DRINK, ON_TAKE and ON_DROP as "Already covered" and said "No changes to apply". The accept-write half was not exercised live because the heuristic plan had nothing to add for this node; that path uses the same single `updateNode` write verified in step 3, but it is not separately demonstrated.
6. Run the targeted gates.
   - expected: build and typecheck pass; the trigger unit tests pass.
   - observed: `python tools/ts_convert.py check` reports build:ts ok, typecheck ok, header survival ok; `node tools/unit/run.cjs` reports 820 passed, 1 failed, the single failure being the pre-existing `test_plan_grounding.js :: carried items satisfy use/take even when absent from the area`. The three untouched gate failures (`action-verbs.generated.js` lint, `play-mode.js`/`source-version.js` module headers, `main.js` `window.narrationUI` guard) reproduce without this change: none of those files is modified.

7. Run the consume content guard, which previously never read the property store.
   - expected: no consume trigger hand-spends a charge the engine already spends.
   - observed: the guard was extended to normalise the wrapped library shape and to read definitions inside `properties.triggers`. On the working copy it then reported `trigger_inv_elena_vance_water_bottle_on_use_1784402362_4 ['on_use','on_drink'] -> ['adjust_uses']`: one trigger carrying both verb types plus the on_use rule's manual charge spend, which double-spends on both verbs because `use` and consume each decrement `uses` in the engine. The hand-written `adjust_uses` effect was removed from that trigger in `data/scenarios/mansion.json` and `data/library/items/inv_elena_vance_water_bottle.json`, leaving `adjust_vital` (-30 thirst) and the authored messages. The trigger is not present in `HEAD:data/scenarios/mansion.json`; the merged form is working-copy data produced by the editor's save path this card fixes.
8. Re-run the targeted suites after the data repair.
   - expected: pass.
   - observed: `python -m pytest tests/test_consume_contract.py tests/test_trigger_system.py tests/test_use_trigger_guard.py tests/test_trigger_migration.py tests/test_trigger_materialize.py` reports 182 passed.

## Acceptance

- [x] A node with two property triggers and zero edges opens the Graph editor with two trigger roots and no blank default
- [x] Saving the graph writes both definitions back into properties.triggers and preserves id, once, fired, cooldown, name and success_message
- [ ] Accepting suggestions updates the trigger list without a reload and creates no logic_trigger nodes for a node that had none (read half verified: the diff reports existing types as covered; the accept-write half was not exercised live)
- [x] Building a world-to-library payload for a node with property triggers returns those triggers instead of []
- [x] A legacy edge with no property entry still opens, and its definition is migrated into the array on save
- [x] python tools/ts_convert.py check passes build:ts, typecheck and header survival, and the trigger unit tests pass (820 passed, 1 failed). The gate as a whole still reports lint, module:check and window-guard failures on files this card does not touch (`action-verbs.generated.js`, `ui/play-mode.js`, `ui/source-version.js`, `main.js` `window.narrationUI`), and the one unit failure is the pre-existing `test_plan_grounding.js :: carried items satisfy use/take even when absent from the area`.

## Files

- `static/js/shared/trigger-graph.ts`
- `static/js/inspector/trigger-helpers.ts`
- `static/js/inspector.ts`
- `static/js/shared/trigger-editor.ts`
- `static/js/item-library.ts`
- `tools/unit/test_trigger_graph.js`
- `tools/unit/test_trigger_representations.js`
- `tests/test_consume_contract.py`
- `data/scenarios/mansion.json`
- `data/library/items/inv_elena_vance_water_bottle.json`
