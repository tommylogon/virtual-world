---
type: bug
status: review
area: ui
priority: medium
wiki: "[[Triggers]]"
---

# bug-569: Trigger card reports only the first effect and condition

**Filed:** 2026-10-22
**Related:** bug-567

<!-- deps:start -->
**Related:** [[bug-567-trigger-graph-editor-reads-and-writes-the-legacy-edge-store]]
<!-- deps:end -->

## What

The trigger card in the inspector renders only the first effect and the first condition. `buildTriggersHtml` computes `firstEff = effectsList[0]`, prints it as `Effect: ...`, then reads `conditionsList[0]` for the condition line. A trigger with three effects reads as if it had one, and an AND of two conditions reads as if it had one. Measured on HEAD mansion.json: 12 trigger definitions have more than one effect (9 in the live world). The card is the only view that lists every trigger on a node, so it is the surface that must not under-report.

## Why

The inspector is where a designer checks what a node actually does. A card that shows one of three effects makes a correct trigger look wrong and an incomplete one look complete. It also hides the effect that will run last, which is usually the visible message.

## How

Build the effect summary from the whole list: join effect labels with a count when there is more than one, and keep the detailed suffix for a single effect. Do the same for conditions (`2 conditions: uses_above, has_item`). Use the definition already merged by `triggerDefFromEdge`; no new data path.

## Browser UI and intended live verification

Intended UI home: Inspector > item_unlabeled_vial > Triggers

Current availability: Open http://localhost:4444, load the mansion scenario, and select item_unlabeled_vial in the graph.

Live steps when available:
1. Count the effects in the JSON definition of the vial's on_use trigger and write the number down
2. Open the Triggers section and confirm the card names every effect, not just the first
3. Select a single-effect item and confirm its card is unchanged

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Open the Triggers section on an item with a multi-effect trigger and compare the card to the JSON.
   - expected: the card names every effect, and the count matches the definition.
   - observed: `item_granola_bar` holds two definitions with effect counts `[1, 2]`. Its card read `Effect: adjust_vital (hunger -25)` for the single-effect trigger and `Effect: 2 effects: adjust_vital (Hunger -25) · message` for the two-effect one. The single-effect card kept its detailed suffix.
2. Open a trigger with two flattened conditions.
   - expected: both leaves are named, with the operator.
   - observed: no authored trigger in the live world has more than one condition, so the renderer was driven directly: the `item_unlabeled_vial` node's client-side `properties.triggers` was temporarily set to one `on_use` trigger with `{operator: 'and', conditions: [uses_above=0, has_trait=goblin]}`, the inspector was re-rendered, and the card read `Conditions (and): uses_above=0 · has_trait=goblin`. The client copy was restored immediately; nothing was sent to the server.
3. Open a trigger whose conditions are an empty object.
   - expected: the card renders with no condition line.
   - observed: the water bottle's `on_take` and `on_drop` definitions carry `conditions: {}` and rendered their effect and message with no condition line.
4. Run the front-end gate.
   - expected: build and typecheck pass.
   - observed: `python tools/ts_convert.py check` reports build:ts ok, typecheck ok, header survival ok.

## Acceptance

- [x] A trigger with two effects shows both on its card
- [x] A trigger with a single effect keeps its current detailed suffix (damage amount, vital delta, and so on)
- [x] A trigger with two flattened conditions shows both
- [x] The card still renders for a trigger whose conditions are an empty object
- [x] Live check on an item with a multi-effect trigger shows the same count as the JSON definition

## Files

- `static/js/inspector/trigger-helpers.ts`
