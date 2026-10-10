---
type: task
status: review
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

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO
