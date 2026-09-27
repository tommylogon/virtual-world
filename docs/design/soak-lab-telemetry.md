# Soak Lab — telemetry and the space-time view

Two systems, added by task-542 / 543 / 544, that exist so a long run can answer
**"who did what, why, where"** — and, in particular, *"did those two ever share a
room?"*

- [`docs/design/lived-log-format.md`](lived-log-format.md) — the per-character
  objective record, renamed from `trace`, and the boundary that keeps it apart
  from telemetry.
- `engine/soak_telemetry.py` — the **run-owned** measurement store.
- `static/js/soak/soak-spacetime.js` — the space-time swimlane renderer.
- `/api/soak/runs/<id>/telemetry` (+ `?events=1`, and `telemetry.jsonl`).

## Two stores, deliberately not one

|  | `lived_log` | soak telemetry |
|---|---|---|
| scope | per **character** | per **run** |
| stored | **in the save**, on the player | **out of the save**, on the run |
| grain | salience-filtered, runs collapsed | complete, every move |
| test applied | "would a person remember this" | "measure exactly this" |
| lifetime | ~200 entries, rolled up | the whole run, then archived |
| consumer | LLM summarisation on promote/demote | dashboard, export, benchmark |
| if it leaks | an LLM "remembers" a life it never lived | the benchmark becomes fiction |

The rollup that makes the lived log *good* for memory is exactly what destroys it
for measurement, so they cannot be one store. The rule, stated once so it cannot
be "optimised" away:

> **Telemetry is never written to a `lived_log`, and the `lived_log` is never
> the dashboard's data source.**

The space-time view is drawn from telemetry **only**. This is not a style
preference: the lived log is capped at 200 salience-filtered entries per
character, so it can describe one character's afternoon but it cannot say where a
camp's twenty-three goblins were on day two.

## How the two share a decision without sharing a store

A background decision needs the same `(character, tick, kind, what, why, area)`
tuple written twice — lossy here for memory, lossless there for measurement — and
duplicating ~20 call sites guarantees they drift. Instead `engine.lived_log.record`
*fans out* to an active recorder through `engine.soak_telemetry.active_recorder`,
the same shape as a logging handler.

Three properties keep the boundary honest, and all three are asserted by tests
rather than trusted:

1. **One way.** The tap fires on the write path, *before* any rollup can collapse
   the entry, so a lossy store can never become the source of a lossless one.
2. **Off by default.** `active_recorder()` is `None` outside a soak, so the
   normal game pays one identity check per record. A recorder that raises is
   swallowed: a measurement failure is not a game failure.
3. **Refuses the wrong vocabulary.** See below.

## Presence intervals, not per-tick samples

Occupancy is knowable only if you record *where a character was between two
moves* — one line per area change:

```json
{"type": "presence", "character": "Jake", "area": "Storehouse",
 "from_tick": 41200, "to_tick": 41480}
```

The cost is therefore bounded by **moves**, not ticks, and the same records render
at any zoom. Per-tick sampling cannot do that: a 7-day soak at 1 min/tick is
10,080 samples per character on the tick axis, and any stored subsample is a
permanent loss of resolution.

A character who stands still for six hours produces **one** interval and no
further events, which is the whole point: presence is *state*, and only a state
change is worth writing down. Every character is seeded with an interval at tick 0
by the runner, so "never moved" and "was nowhere" stay distinguishable.

## The `why` vocabulary is measured, not remembered

Every event carries the reason tag that decided it, grouped by prefix. The
accepted prefixes were **measured against the code** with
`tools/why_vocabulary.py`, not copied from a design document — the first draft
came from task-543's prose and was wrong within a single run, missing
`traversal:`, `forage:` and `schedule:` entirely. The recorder's rejection counter
is what surfaced it, which is the argument for keeping the counter.

- **Rejected** tags are counted and surfaced in the UI, never silently accepted:
  silently accepting an unknown tag is how a vocabulary rots. A bad tag must not
  be fatal to the run that produced it.
- **`llm:` is excluded structurally**, not by frequency. A soak makes no LLM
  calls by construction, so an LLM reason is impossible rather than rare.
- **Unattributed events are counted, not ranked.** Most of them are the
  mechanical cost-application entry `apply_action` writes for every verb. Counting
  that as a "decision" would drag every real rule's share down, so the ranked
  shares add up to the *decided* total and the omitted volume is reported beside
  them ("4,740 decided, 3,324 with no rule").

## The space-time view

Time on x, area lanes on y, one bar per presence interval. Two overlapping bars
in the same lane is a collision, and surfacing that is the reason the view exists
— a heatmap shows where the world is busy but aggregates characters away, and an
average Energy line hides the one character collapsing while the mean stays flat.

Everything above the renderers is a **pure function**, unit-tested in
`tools/unit/test_soak_spacetime.js`. That is not tidiness: lane assignment, greedy
row packing, overlap detection and windowing are the parts that can be *wrong* in
ways a screenshot will not reveal. An off-by-one in the window silently drops a
character's whole afternoon, and a mis-packing row packer turns two people in a
room into two people who appear never to meet.

### Non-obvious rendering decisions

- **Drawn at 1 layout unit = 1 px; the box scrolls.** An SVG given a `max-height`
  is scaled down to fit, and because a viewBox scales *uniformly* that squeezes
  the time axis too. Eighteen lanes of stacked bands then collapse into a block
  of colour that still looks like a chart. This is why the swimlane has its own
  box class: `.soak-chart-tall .soak-chart { max-height: 340px }` is a
  pre-existing rule for the overview vitals chart and silently applies to any
  chart in that box.
- **The default window is 6 game-hours, not the whole run.** Three days of 23
  goblins is 2,700 bands; six hours is 258 and stays readable. "Full run" is one
  click away for when the mass itself is the finding. Past ~900 intervals the view
  says so rather than pretending to be legible — a cramped view is worse than an
  absent one, because it looks like it answered the question.
- **Condition ribbons are quiet, and skip ambient states.** `awake` and `busy` are
  excluded server-side: they describe a baseline, not an incident, and ribboning
  them turns the chart into a solid orange field in which a real illness loses its
  contrast. The ribbon marks the incident; the band carries the data.
- **Missing layout fields are silent.** A `paddingTop` absent from the layout
  object becomes an `undefined`/`NaN` SVG attribute, which the browser *drops*
  without error — the grid lines and death rules simply do not appear. Both the
  field set and the rendered output are asserted.
- **A gap means unknown, not empty.** The integrity check surfaces gaps and
  overlaps so a hole in the data cannot be misread as "nobody was here".

## Reading a real run

Kraktooth goblin camp, 3 days (4,320 ticks at 1 min/tick), 23 characters, all
background, seed 1234, started from the dashboard's own scenario and horizon
controls:

- 1,665 presence intervals and 6,422 events — no gaps, no overlaps, and **zero
  rejected `why` tags**, which is what "the vocabulary matches the engine" looks
  like.
- `needs` drove 82% of decided actions, `social` 16%, `traversal` and `forage`
  under 1% each.
- The busiest room by shared occupancy was **Waste Disposal** at 45,844 shared
  ticks across five pairs — a single question the average-vitals charts cannot
  ask, let alone answer.
- The `why`-over-time stack shows a large burst in the first ~45 minutes as the
  whole cast's starting vitals collapse at once, then a settled baseline. A flat
  ranked bar chart would show `needs 82%` and lose the burst entirely.
- 23 alive, 0 dead over three days with baked decay rates — no casualty finding
  to investigate, which is itself the result.

### Drilling into one character

Click any name in the legend — or any pair in the "who shared a room" table — to
isolate that character. Click again, or "Show everyone", to go back.

The reason this exists: with twenty-three goblins the question is almost never
"where was everyone", it is "what did *this one* do all day". That question is
unreadable in the full view, where one character's bands are spread across
eighteen lanes interleaved with everybody else's, and finding them by colour
across a crowded chart is exactly the visual search this view is meant to remove.

Two decisions that are not obvious, and both were wrong in the first version:

- **The area axis is pruned to the rooms that character actually visited.**
  Keeping all eighteen drew fourteen empty rails, which is worse than useless: an
  empty rail reads as "they were nowhere" for a room they simply never entered,
  and it pushes the lanes you came to read off the screen. Relative order is
  preserved among the kept lanes, so the sequence of rooms is still legible.
- **The collision list is computed from the *unfiltered* intervals and then
  narrowed by who is in the pair.** Filtering the other people out of the input
  made an isolated character collide with nobody — precisely backwards, since the
  reason to drill in is to find out who they were *with*. So the chart narrows
  and the company list does not. See `ST.collisionsFor`.

A stale selection (a name that matched nobody, e.g. after switching runs) renders
the "no presence recorded" state rather than a field of empty rails, and is
dropped automatically on the next draw.

### Clickable legend entries

The legend is the cheapest possible drill-down: it is already a list of every
character, it is already colour-coded to match the bands, and it is already on
screen. Making it a list of buttons costs one delegated listener and no new
state beyond a single `ui.stCharacter` — which is deliberately **not** part of the
run config, because it is a view choice and must not leak into a saved run or a
comparison.

## Two page-level bugs this view surfaced

Both were pre-existing shell problems that only became visible because the
swimlane is the tallest content in the lab. Neither is specific to this view, so
they are worth knowing about before the next tall pane is added.

1. **The page could not scroll.** The shared app shell sets
   `html, body { height: 100%; overflow: hidden }` for its fixed three-column
   editor layout, and the Soak page inherits it. That is correct for the editor —
   its panels each own a scrollbar — but wrong here: the Soak page is an ordinary
   scrolling document whose sidebar merely *sticks*. Anything taller than the
   viewport was cut off with no way to reach the bottom.

   It has to be undone on **both** `html` and `body`, and the `html` half is the
   one that bites: `html` is the viewport-propagation root, so its `overflow` is
   what the viewport uses, and a `body` override is *ignored* while `html` still
   says `hidden`. Fixing only `body` left the page just as unscrollable, which is
   why it looked fixed and was not. `html.soak-doc` comes from
   `templates/soak.html`.

2. **A wide child stretched the whole grid column.** A flex item defaults to
   `min-width: auto`, so one wide descendant widened the card, then the pane, then
   the grid track — and the page ended up wider than the viewport with the
   left-hand side unreachable. `.soak-pane > *` and `.soak-row-2 > *` now carry
   `min-width: 0`, which lets the card shrink to its column and lets the child's
   own `overflow-x: auto` do its job.

There is also a *nested* scroll trap worth naming, because the fix is to avoid it
rather than work around it: the swimlane originally had `max-height: 640px;
overflow: auto` inside a page that did not scroll. A scroll area inside a
non-scrolling area is exactly the "I can only see part of it and I cannot work out
how to scroll" report. The swimlane now takes its natural height and the page
does the scrolling; the box only guards the horizontal axis.
