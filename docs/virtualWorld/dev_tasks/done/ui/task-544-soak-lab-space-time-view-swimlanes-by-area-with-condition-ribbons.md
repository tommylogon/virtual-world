---
type: task
status: done
area: ui
priority: low
wiki: "[[UI Reference/Rendering & UI Modules]]"
---

# task-544: Soak lab space-time view - swimlanes by area, with condition ribbons

**Filed:** 2026-09-27
**Related:** task-543 (the data), task-542 (naming/boundary)

## What

Answer the question a line chart cannot: **did those two ever share a room?**

## Why not lines or a plain heatmap

The Soak Lab already has `renderLineChart`, `renderDonut`, `renderBarChart`,
`renderVerticalBars` and a histogram, and the line charts are all **vitals over
time**. Those answer "is the average holding up", which is the least interesting
question in a soak:

- An average Energy line is close to useless. It hides the exact thing a soak
  exists to catch - one character collapsing while the mean stays flat.
- A time × area **heatmap** shows where the world is busy, which is genuinely
  useful, but it is strictly less informative than swimlanes: it aggregates
  characters away, so it cannot show *who* was where or reveal a meeting.

## The view

**A space-time swimlane diagram.** x = time, y = area ordered spatially, one band
per character.

- Each character's band is drawn per presence interval, so a long stay is a long
  bar and a commute is a short one. Built from task-543's intervals, so it renders
  at any zoom from the same records.
- **Overlapping bands in the same area-lane are a collision** - two characters in
  one room. That is the thing the view exists to surface, and it is invisible in
  every chart currently in the lab.
- **Deaths** marked on the band at the tick they occurred, with cause.
- **Condition ribbons** beneath each character: a second, thinner strip per
  character showing condition state over time (hungry / tired / sick / injured).
  This is what replaces the average line - you see *who* was suffering and when,
  not that the mean moved 2 points.
- **Churn is legible**: a character oscillating between two lanes shows a
  zigzag, which reads instantly as a behavioural problem.

Companion panels, cheap from the same data:

- **`why` breakdown - the core panel, not an extra.** `why` is what makes a soak
  answerable: it is the only field that says *which rule drove the behaviour*, and
  the whole request is "who did what why where". Render it as a ranked
  distribution of `why` values, grouped by prefix so the nine background rules
  compete against each other on one axis - and stacked over time, so you can see
  a rule start dominating. Without it the view answers "who was where" but not
  "what decided it".
- **Action composition** - a stacked bar or donut of action `kind` per character,
  and/or a stacked area over time. Answers "what are they spending their time on".
  Note this is coarser than the `why` breakdown: `kind` is *what*, `why` is
  *why*, and the second is the one worth ranking.
- **Occupancy heatmap** - time × area, as a compact overview for a long run. Keep
  it as the zoomed-out companion to the swimlanes, not instead of them.

## Implementation notes

- Draw on the existing dependency-free SVG helpers in `static/js/soak/soak-charts.js`
  (it already has line/bar/vertical-bar/donut plus a `histogram` and a
  `niceTicks`/`scaleFor` helper). A swimlane is rectangles and one axis, so it
  fits that house style - no charting dependency needed, and no `Chart.js` in the
  app's runtime path.
- The lane axis needs an **area ordering that is stable across a run**, ideally
  spatial (from the graph layout) with rooms alphabetised as a fallback. An
  alphabetical axis puts a camp's storehouse and longhouse far apart and destroys
  the spatial read.
- Render lazily and windowed: a 30-day run is tens of thousands of intervals.
  Aggregate to the visible time range and only draw what fits.
- The existing lab polls; follow whatever cadence the vitals charts use rather
  than introducing a second polling path.

## Acceptance

- [x] A run with recorded telemetry renders swimlanes: area lanes on the y axis,
      time on the x, one band per character from its presence intervals.
- [x] Two characters present in the same area at the same time are visually
      distinguishable as an overlap.
- [x] Deaths appear on the band at the correct tick with their cause.
- [x] Condition ribbons render beneath each band, and a per-character collapse is
      identifiable without reading a number.
- [x] A 30-day run renders without freezing - windowed or aggregated, with the
      visible range only.
- [x] The lane ordering is spatial where a layout exists, and stable across
      refreshes.
- [x] A run with no telemetry shows a clear empty state, not an empty axis.
- [x] Pure-JS unit tests for the geometry (lane assignment, overlap detection,
      windowing), in the existing `tools/unit/test_*.js` style.
- [x] `node tools/unit/run.cjs` green, `npm run lint` and `npm run typecheck` clean.
- [x] Per the standing rule, documented in the user guide / technical docs.

## Non-goals

- Capturing the data - task-543. This task renders what exists and shows an empty
  state until then.
- Replacing the existing vitals charts. They answer a different question and
  should stay.
- A graph-view or node-link visualisation of the same data. The space-time
  diagram is the one that answers the question; a force graph would not.
- Interactivity beyond hover and zoom. Resist building a general analysis tool
  here - pick one question and answer it well.

## Why

The Soak Lab's existing charts all answer "is the average holding up", which is
the least interesting question a soak can ask. The question a soak actually
exists to answer is "who was where, when, and what decided it", and no chart
before this one could show it: a heatmap aggregates characters away, so it can
never reveal that two characters shared a room.

## How

Pure geometry in `static/js/soak/soak-spacetime.ts`, drawn by the existing
dependency-free SVG helpers, wired into the Soak Lab as a Space-Time tab
(`soak-ui.ts` `renderSpacetime`, selected via `[data-pane="spacetime"]`).
Geometry and windowing are the parts that can be wrong in ways a screenshot will
not reveal, so they are pure functions with unit tests.

## Browser UI and intended live verification

Intended UI home: Soak Lab → Space-Time view.

Current availability: the swimlane view, condition ribbons, why breakdown,
occupancy heatmap and collisions table are implemented and wired to the
telemetry payload, and the geometry is unit-tested. What is not demonstrated
here is a live browser run against a 30-day soak, which is the one acceptance
item that needs a real run rather than a fixture.

Live steps when available:

1. Open a recorded soak run in the space-time view and inspect area lanes and character timelines.
   - expected: Each character’s presence occupies the correct area lane and time interval.

2. Inspect two co-present characters and a condition change.
   - expected: Their intervals overlap in time and condition ribbons mark the corresponding periods.

3. Open a run whose telemetry was off, and one with no presence intervals.
   - expected: A clear empty state, not an empty axis.

4. Widen the time range to the whole run.
   - expected: The view stays responsive; if more than 900 intervals are visible the density guard warns.

This section defines the intended access point and acceptance path. Current availability records the present state.
## Steps to verify

1. `node tools/unit/run.cjs` includes `test_soak_spacetime.js`.
   - expected: the geometry test file runs and every case passes.
   - observed: 62 cases in `test_soak_spacetime.js` pass; the suite reports 780 passed, 0 failed (57 test files).
2. The Space-Time tab is reachable and renders.
   - expected: the pane is selected and `renderSpacetime()` draws swimlanes.
   - observed: `static/js/soak/soak-ui.ts:1326` dispatches `case 'spacetime': renderSpacetime(); break;`; the pane is bound at line 937 via `[data-pane="spacetime"]`; `bindSpacetime()` is called at line 1505.
3. The module is a pure geometry layer, so its behaviour is testable without a browser.
   - expected: lane order, windowing, row packing, collision detection and the why-over-time bucketing are all pure functions.
   - observed: `soak-spacetime.ts` exports `laneOrder`, `clipToWindow`, `packRows`, `findCollisions`, `collisionsByArea`, `buildLayout`, `whyOverTime`, `renderSwimlanes`, `renderHeatmap`, `filterCharacter`, `collisionsFor`; 62 cases cover them.
4. A 30-day run renders without freezing.
   - expected: windowed or aggregated, with the visible range only.
   - observed: NOT demonstrated live. The mechanism is in place (`clipToWindow` plus `buildLayout` windowing, with a 900-interval density guard at `soak-ui.ts:687` and a 6-hour default window), and the unit tests pin the windowing, but no 30-day run was rendered in a browser here. This is the one acceptance item resting on mechanism rather than observation.

## Files

- `static/js/soak/soak-spacetime.ts` (and emitted `.js`) - pure geometry and renderers
- `static/js/soak/soak-ui.ts` - the Space-Time tab, `renderSpacetime`, density guard, integrity alerts
- `tools/unit/test_soak_spacetime.js` - 62 geometry cases
- `docs/virtualWorld/UI & Settings/Soak Lab.md` - the feature page

## Reconnaissance (2026-10-20) - verdict: FIXED

Newer work (commits in the soak lane) implemented the space-time swimlane view that this card asked for.

- `static/js/soak/soak-spacetime.ts` (and emitted `.js`) exists: 34,566 bytes, declares `@module soak-spacetime` and `@contributes pure lane/row/overlap geometry, the swimlane renderer, the occupancy heatmap and the why-over-time stack`.
- It is wired into `static/js/soak/soak-ui.ts` line 1326 (`case 'spacetime': renderSpacetime(); break;`) and the tab pane is selected at line 937 (`[data-pane="spacetime"]`).
- Pure-JS geometry tests exist: `tools/unit/test_soak_spacetime.js` (26,532 bytes).
- Companion panels (occupancy heatmap, why-over-time stack, action composition) are present in the module.

Evidence counts: 1 spacetime module, 1 wired render call site, 1 geometry test file. Card moved to done.
