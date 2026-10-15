---
type: task
status: inprogress
area: ui
priority: low
---

# task-755: Trigger graph: auto-grow value textareas and stop the inspector triggers header overflowing

**Filed:** 2026-10-09
**Related:** 

## What

Trigger-graph value textareas are fixed rows=2 and scroll instead of growing with their content, and the inspector triggers-section header packs five buttons into one nowrap row that clips on a narrow panel. Make textareas grow to fit their value, and let the button row wrap.

## Acceptance

- [x] A trigger-graph value textarea grows to fit its content as it is typed (no inner scrollbar for a long message/instructions).
- [x] A textarea with an existing long value is sized on open and on every node re-render.
- [x] The inspector triggers header's five buttons wrap instead of clipping on a narrow panel (`flex-wrap` on the header and button row).
- [ ] Live: open the trigger graph, type a multi-line message, confirm the box grows; narrow the inspector and confirm the header buttons wrap.

## Notes

Implemented in `static/js/shared/trigger-graph.ts` (`_autoGrow` / `_sizeTextareas`,
delegated `input` listener on `#tg-canvas`, sizing after `_renderNode`) and
`static/js/inspector/trigger-helpers.ts` (wrap styles on the header row).
Rebuilt with `npm run build:ts`.

Gate: `ts_convert.py check` — build/typecheck/lint/unit/headers/window-guards all
ok; only the pre-existing `module:check` failure on `engine/activities_loader.py`
and `engine/effect_handlers/movement.py` remains (unrelated, py module headers).

Still unimplemented from the same recon: a left-to-right stacking-siblings graph
layout for the trigger graph — it needs a decision first, since condition
`output_yes`/`output_no` sockets are `side:'bottom'` and are compile-coupled.

## Why

TODO

## How

TODO

## Browser UI and intended live verification

Intended UI home: Trigger Graph value fields and Character/Area Inspector → Triggers section header.

Current availability: Textarea growth and wrapped inspector controls are partly implemented; remaining live acceptance is open.

Live steps when available:

1. Open Trigger Graph, type a multiline value, then reopen a node with a long saved value.
   - expected: The textarea grows to its content on input and render without an internal scrollbar.

2. Narrow the Inspector and inspect the Triggers header.
   - expected: Buttons wrap within the panel instead of clipping or forcing horizontal overflow.

This section defines the intended access point and acceptance path. It is not a claim that the UI or complete behavior exists or works today; Current availability records the present state, and these steps describe how to verify the intended behavior when it is available.
## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO
