---
type: bug
status: inprogress
area: ui
priority: medium
---

# bug-546: WorldPainter placed-area names never render: the draw gate compares the constant CELL (22) against 26, so it is always false

**Filed:** 2026-10-11
**Related:** task-540

## What

Placed areas draw their marker but **never their name**, at any zoom. Found by
reading the draw path (a model review pointed at it; confirmed in code).

`editor.ts:2753`, inside `_drawFeatures`:

```
if (CELL >= 26) {  … ctx.fillText(name …) }
```

`CELL` is the module constant `22` (`editor.ts:394`, "base px per cell at
scale 1"). So the comparison is a constant `22 >= 26` → **always false**, and the
name branch never runs. The adjacent comment states the intent — "A name is worth
showing when the cell is big enough to hold one; at 1x the map is a mosaic" — so
the gate was meant to test the **on-screen** cell size, not the base constant.

## Why

An author zoomed into a scope with placed areas sees house markers with no names,
and cannot tell which area is which without opening the inspector — the exact
thing the label was added for (task-540).

## How

Gate on the scaled cell size, not the base constant:

```
const onScreen = CELL * (state.stage ? state.stage.scaleX() : 1);
if (onScreen >= 26) { … }
```

Keep the marker itself always drawn; only the name is gated. Check other call
sites that intend "big enough to label" for the same constant-vs-scaled mistake.

## Browser UI and intended live verification

Intended UI home: Build → WorldPainter → painted scope in Map mode, with placed-area labels visible.

Current availability: The label gate compares a constant cell value; scaled on-screen-size behavior remains to be verified after the fix.

Live steps when available:

1. Open a scope with placed areas and zoom until a cell is at least 26 screen pixels.
   - expected: Area names appear when the scaled cell reaches the label threshold.

2. Zoom back to mosaic scale.
   - expected: Names hide below threshold while area markers remain drawn.

This section defines the intended access point and acceptance path. It is not a claim that the UI or complete behavior exists or works today; Current availability records the present state, and these steps describe how to verify the intended behavior when it is available.
## Steps to verify

1. Open a scope with placed areas; zoom in past ~1.2× (so cells exceed 26px).
   - expected: names appear once the on-screen cell is ≥26px; stay hidden when zoomed out to a mosaic.
   - observed: TODO

## Acceptance

- [ ] Placed-area names draw when the on-screen cell is big enough, and stay hidden when it is not.
- [ ] The gate uses the scaled cell size, not the constant `CELL`.

## Files

- `static/js/worldpainter/editor.ts` — `_drawFeatures` (`:2729`, gate `:2753`), const `CELL` (`:394`).
- `static/js/worldpainter/editor.js` — emitted; rebuild with `npm run build:ts`.
