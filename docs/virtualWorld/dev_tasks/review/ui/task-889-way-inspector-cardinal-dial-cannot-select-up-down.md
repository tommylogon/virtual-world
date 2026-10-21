---
type: task
status: review
area: ui
priority: medium
wiki: "[[World Building/Ways]]"
---

# task-889: Way inspector cardinal dial cannot select up/down

**Filed:** 2026-10-20
**Related:** 

## What

The way inspector's radial cardinal dial offered only the eight horizontal headings, so `up` and `down` - cardinals the engine already carries, the map layout already offsets, and the area inspector's badge already renders - could not be selected or displayed. A vertical way (a stairway, a sloping tunnel) showed a compass with nothing lit on it, and clicking any button silently overwrote its `down` with a horizontal heading.

The fix adds a two-button vertical column beside the dial: an up arrow and a down arrow, in their own axis rather than as two more points on the circle, because a vertical move is not a bearing. The existing opposite-cardinal auto-fill (a stairway's other side becomes the reverse) and the map layout's two-row vertical offset both already worked and now have a control to drive them.

## Why

The engine treats `up` and `down` as first-class cardinals: `engine/facing.py` keeps them deliberately off the rotation ring ('up' stays literal, so climbing a ladder does not leave a character facing north), `engine/effect_handlers/ways.py` has the up/down opposite pair, `static/js/graph/layout-engine.ts` offsets them by two rows so a cellar reads below its hall, and `static/js/graph/overlays.ts` labels them U and D in the cardinal overlay. The area inspector's way badge (task-240) already shows them - its own acceptance criteria say 'up/down is shown for the vertical exit'.

The dial was the one place that could not reach any of that. An author authoring a stairway had no control for its cardinal at all, and a way that already had `down` authored in the scenario data displayed as though it had no cardinal at all.

## How

`static/js/inspector/way-view.ts`:

1. Add a `VERTICAL_COMPASS` list (`up` with an up arrow, `down` with a down arrow) next to the existing `RADIAL_COMPASS`.
2. Render it as a separate column to the right of the dial, inside the same 130px-tall widget, so a vertical way is visibly a different axis from a bearing.
3. The column starts at x=146, not x=130: the dial's own buttons overrun their 130px box by 8px on every side (the N button's top edge is at y=-8), so a column at x=130 clipped the E button. Measured after the fix: zero intersecting button pairs, in both the side-A and side-B widgets.
4. The buttons reuse the `compass-radial-btn` class so the existing `_selectCompassDirection` handler repaints the selection across the whole widget, and carry an extra `compass-vertical-btn` class so they can be found and styled independently.

No engine change was needed. The opposite-cardinal maps in `way-view.ts` and `way-view-connections.ts` already had `up: 'down', down: 'up'`, and the map layout already had the vertical offsets.

## Browser UI and intended live verification

Intended UI home: Graph view -> select a way node -> the Inspector's Connections section -> the 'Cardinal for map layout' pad, or the 'Cardinal (A->B) for map layout' pad.

Current availability: Implemented and wired. Verified live in the browser on a real vertical way ('tunnel to mines' in the Kraktooth goblin camp): side A rendered `down` highlighted and side B rendered `up` highlighted; clicking `up` persisted `up` on one edge and auto-filled `down` on the other.

Live steps when available:
1. Open the graph, select a way whose connection cardinal is `up` or `down` (the Kraktooth goblin camp has 'tunnel to mines', cardinal `down` from the side tunnels and `up` from the mine access).
2. expected: the vertical column beside the dial shows the matching up or down button highlighted, and no horizontal button is lit.
3. Click the other vertical button.
4. expected: the new cardinal is persisted, and the opposite side of the same way takes the reverse cardinal automatically.
5. Click a horizontal heading such as north.
6. expected: the horizontal button highlights and the vertical buttons un-highlight; the opposite side takes the matching reverse heading.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Related

- `task-240` - the area inspector's way badge, whose acceptance criteria already
  say "up/down is shown for the vertical exit"
- `task-890` - the shared cardinal-to-glyph map, which the area badge and the
  graph's Cardinal overlay both read. This card's dial is the third surface
  that shows a cardinal.

## Steps to verify

1. Render the compass widget and count the offered cardinals.
   - expected: the eight horizontal headings, the clear button, and `up` and
     `down`.
   - observed: PASSES. Live probe of `InspectorWayView._renderCompassSelector`
     in the browser returned 11 buttons - north, northeast, east, southeast,
     south, southwest, west, northwest, "" (clear), up, down. Before the change
     it returned 9, with no up and no down.
2. Open a way whose connection cardinal is `up` or `down` and read the dial.
   - expected: the matching vertical button is highlighted and no horizontal
     button is lit.
   - observed: PASSES. On `way_side_to_mine` ("tunnel to mines" in the Kraktooth
     goblin camp), the side-A widget highlighted `down` and the side-B widget
     highlighted `up`; the highlighted-button query returned exactly
     ["down", "up"] across the two widgets, and no horizontal button carried
     the selection.
3. Click a vertical button and read the persisted graph.
   - expected: the cardinal is written to the edge, and the opposite side of
     the same way takes the reverse cardinal.
   - observed: PASSES. Clicking `up` on side A called
     `InspectorWayView._updateCardinal('area_side_tunnels', 'way_side_to_mine',
     'area_mine_access', 'up')`, which issued two `updateEdge` calls: `up` on
     the `area_side_tunnels` edge and `down` on the `area_mine_access` edge.
     Re-reading `GET /api/state` afterwards showed exactly those two values.
4. Check the button geometry for overlap.
   - expected: no two buttons intersect, in either widget.
   - observed: PASSES. Measured every button's rect against every other in both
     the side-A and side-B widgets: the overlap list was empty in both. This is
     why the column starts at x=146 - at x=130 the E button (which spans
     x=102..138) would have been clipped by the column.
5. Confirm the horizontal headings and the clear button are unchanged.
   - expected: the eight-way dial and the clear button behave as before.
   - observed: PASSES. The radial dial and the clear button are rendered from
     the same `RADIAL_COMPASS` list as before, and the clear button still
     takes the red style when no cardinal is set. Only the widget's total
     width changed (130px -> 230px), to make room for the column.
6. Run the gates.
   - expected: `npm run build:ts`, `npm run typecheck` and
     `node tools/unit/run.cjs` green.
   - observed: PASSES for all three. `build:ts` and `typecheck` report no
     errors; the unit runner reports 781 passed, 0 failed (57 test files).
     `python tools/ts_convert.py check` still reports two failures, and
     neither is from this change: `lint` fails on
     `static/js/agent/action-verbs.generated.js` (an untracked generated file
     from another lane - `git ls-files` matches 0 files for it, and it is
     referenced by `globals.d.ts` and `templates/index.html`), and
     `module:check` fails on `static/js/ui/play-mode.js` missing the
     `@module`/`@contributes` contract (committed in 2a7e3dd0, task-885).
     This card's own file lints clean on its own:
     `eslint static/js/inspector/way-view.js` exits 0.

## Acceptance

- [x] The way inspector's cardinal dial shows a vertical column with an up and a down button, beside the eight-way dial rather than on it.
- [x] A way whose cardinal is `up` or `down` renders that button highlighted on the correct side.
- [x] Clicking `up` on one side sets the opposite side to `down` automatically, via the existing opposite-cardinal auto-fill.
- [x] No two buttons in the widget overlap, in either the side-A or side-B compass.
- [x] The eight horizontal headings and the clear button still behave exactly as before.
- [x] `npm run build:ts`, `npm run typecheck` and `node tools/unit/run.cjs` are green.

## Files

- `static/js/inspector/way-view.ts`
- `static/js/inspector/way-view.js`
- `docs/virtualWorld/World Building/Ways.md`
