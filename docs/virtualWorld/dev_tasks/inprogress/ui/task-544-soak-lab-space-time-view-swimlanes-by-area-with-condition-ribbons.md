---
type: task
status: inprogress
area: ui
priority: low
---

# task-544: Soak lab space-time view — swimlanes by area, with condition ribbons

**Filed:** 2026-09-27
**Related:** task-543 (the data), task-542 (naming/boundary)

## Goal

Answer the question a line chart cannot: **did those two ever share a room?**

## Why not lines or a plain heatmap

The Soak Lab already has `renderLineChart`, `renderDonut`, `renderBarChart`,
`renderVerticalBars` and a histogram, and the line charts are all **vitals over
time**. Those answer "is the average holding up", which is the least interesting
question in a soak:

- An average Energy line is close to useless. It hides the exact thing a soak
  exists to catch — one character collapsing while the mean stays flat.
- A time × area **heatmap** shows where the world is busy, which is genuinely
  useful, but it is strictly less informative than swimlanes: it aggregates
  characters away, so it cannot show *who* was where or reveal a meeting.

## The view

**A space-time swimlane diagram.** x = time, y = area ordered spatially, one band
per character.

- Each character's band is drawn per presence interval, so a long stay is a long
  bar and a commute is a short one. Built from task-543's intervals, so it renders
  at any zoom from the same records.
- **Overlapping bands in the same area-lane are a collision** — two characters in
  one room. That is the thing the view exists to surface, and it is invisible in
  every chart currently in the lab.
- **Deaths** marked on the band at the tick they occurred, with cause.
- **Condition ribbons** beneath each character: a second, thinner strip per
  character showing condition state over time (hungry / tired / sick / injured).
  This is what replaces the average line — you see *who* was suffering and when,
  not that the mean moved 2 points.
- **Churn is legible**: a character oscillating between two lanes shows a
  zigzag, which reads instantly as a behavioural problem.

Companion panels, cheap from the same data:

- **`why` breakdown — the core panel, not an extra.** `why` is what makes a soak
  answerable: it is the only field that says *which rule drove the behaviour*, and
  the whole request is "who did what why where". Render it as a ranked
  distribution of `why` values, grouped by prefix so the nine background rules
  compete against each other on one axis — and stacked over time, so you can see
  a rule start dominating. Without it the view answers "who was where" but not
  "what decided it".
- **Action composition** — a stacked bar or donut of action `kind` per character,
  and/or a stacked area over time. Answers "what are they spending their time on".
  Note this is coarser than the `why` breakdown: `kind` is *what*, `why` is
  *why*, and the second is the one worth ranking.
- **Occupancy heatmap** — time × area, as a compact overview for a long run. Keep
  it as the zoomed-out companion to the swimlanes, not instead of them.

## Implementation notes

- Draw on the existing dependency-free SVG helpers in `static/js/soak/soak-charts.js`
  (it already has line/bar/vertical-bar/donut plus a `histogram` and a
  `niceTicks`/`scaleFor` helper). A swimlane is rectangles and one axis, so it
  fits that house style — no charting dependency needed, and no `Chart.js` in the
  app's runtime path.
- The lane axis needs an **area ordering that is stable across a run**, ideally
  spatial (from the graph layout) with rooms alphabetised as a fallback. An
  alphabetical axis puts a camp's storehouse and longhouse far apart and destroys
  the spatial read.
- Render lazily and windowed: a 30-day run is tens of thousands of intervals.
  Aggregate to the visible time range and only draw what fits.
- The existing lab polls; follow whatever cadence the vitals charts use rather
  than introducing a second polling path.

## Acceptance criteria

- [ ] A run with recorded telemetry renders swimlanes: area lanes on the y axis,
      time on the x, one band per character from its presence intervals.
- [ ] Two characters present in the same area at the same time are visually
      distinguishable as an overlap.
- [ ] Deaths appear on the band at the correct tick with their cause.
- [x] Condition ribbons render beneath each band, and a per-character collapse is
      identifiable without reading a number.
- [ ] A 30-day run renders without freezing — windowed or aggregated, with the
      visible range only.
- [ ] The lane ordering is spatial where a layout exists, and stable across
      refreshes.
- [ ] A run with no telemetry shows a clear empty state, not an empty axis.
- [ ] Pure-JS unit tests for the geometry (lane assignment, overlap detection,
      windowing), in the existing `tools/unit/test_*.js` style.
- [x] `node tools/unit/run.cjs` green, `npm run lint` and `npm run typecheck` clean.
- [ ] Per the standing rule, documented in the user guide / technical docs.

## Non-goals

- Capturing the data — task-543. This task renders what exists and shows an empty
  state until then.
- Replacing the existing vitals charts. They answer a different question and
  should stay.
- A graph-view or node-link visualisation of the same data. The space-time
  diagram is the one that answers the question; a force graph would not.
- Interactivity beyond hover and zoom. Resist building a general analysis tool
  here — pick one question and answer it well.
