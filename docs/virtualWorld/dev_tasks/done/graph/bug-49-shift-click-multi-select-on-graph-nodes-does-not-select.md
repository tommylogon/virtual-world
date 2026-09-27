---
type: bug
status: done
area: graph
priority: medium
---

# bug-49: Shift-click multi-select on graph nodes does not select

**Filed:** 2026-09-27
**Related:** task-539, task-378
**Fixed:** 2026-09-27

## Symptom

Shift-clicking a node in the graph neither selected it nor opened the inspector —
it behaved exactly like a plain click, so no bulk selection bar ever appeared and
there was no way to act on several nodes at once (e.g. reassign a whole interior
to a scope, task-539).

## Cause

`params.event.shiftKey` in `static/js/graph/event-handlers.js:onClick` is
**always `undefined`**. vis-network does not hand the DOM event to the click
handler: `params.event` is vis's own pointer wrapper (Hammer), and that wrapper
proxies the geometry the context menu needs (`clientX`/`clientY`, which is why the
right-click menu has always been positioned correctly) but **not** the keyboard
state. The real `PointerEvent` is at `params.event.srcEvent`.

So the guard `if (params.event?.shiftKey && …)` was never true: the code fell
through to the plain-click branch, which opened the inspector. Nothing was broken
in the selection bookkeeping itself — `_toggleBulkSelect` and the action bar work
once they are reached.

## Fix

- `GraphEventHandlers.modifiers(params)` unwraps the event once, handling all three
  shapes vis/hammer can pass: the wrapper (read `srcEvent`), a bare DOM event, and
  an array of either. `onClick` uses it for the shift test. The reason is
  documented in the JSDoc so the next reader does not "simplify" it back.
- Unit-tested in `tools/unit/test_graph_event_handlers.js` (6 tests): the real
  wrapper shape, the two other shapes, a plain click still opening the inspector,
  shift-click toggling without opening it, a pending connection still winning, and
  an empty-canvas click still clearing the selection. `event-handlers.js` is now
  loaded in the Node sandbox (`tools/unit/run.cjs`).
- Since the point of a selection is what you can do with it, the bulk bar also
  gained the one action this bug was blocking: a **🗺️ Scope** picker
  (`graphManager._fillBulkScopes` / `_bulkScope`, task-539) that moves the whole
  selection into one scope in a single request — one undo step — and reports the
  route's refusal if the selection mixes in generated areas.

## Verified

Live, on the goblin camp: shift-clicking three areas gave "3 selected — " with all
three in `_bulkSelection`; the scope picker listed all five scopes; choosing the
camp moved all three to `deep_woods_2` in one request, cleared the selection and
removed the bar. Shift-clicking the same node twice deselects it. The three test
areas were put back the way they were found.
