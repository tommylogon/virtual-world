---
type: task
status: review
area: ui
priority: medium
wiki: "[[World Building/Ways]]"
---

# task-890: Cardinal overlay reads the way node instead of the edge and labels every way '?'

**Filed:** 2026-10-20
**Related:** 

## What

The two surfaces that show a way's cardinal disagreed, and the graph's Cardinal overlay was reading the wrong object entirely.

The area inspector's exit badge drew a generic compass plus the raw word (`🧭 down`). The graph's Cardinal overlay drew a per-direction glyph (`⬆N`) from a map that was written inline in the overlay - but it read `node.properties.cardinal`, and a way's cardinal lives on its *connection edge*, not on the way node. In the Kraktooth camp 5030 edges carry a cardinal and 0 way nodes do, so the overlay found nothing and labelled every single way with `?`. It looked wired and produced a placeholder.

The fix puts one cardinal-to-glyph map in `WayAuthoring` (which already owns the shared way-authoring helpers and is used by way-view, area-view and network-manager), adds a `wayCardinal()` reader that looks where the cardinal actually lives, and points both surfaces at it.

## Why

The overlay is the map view's cardinal display. If it says `?` on every way, the map carries no direction information at all and the feature is inert - the exact 'exists but is not wired' failure the repo rules call out. It was not obvious: the overlay function ran, coloured the nodes, and produced a label, so it looked like it worked.

The badge and the overlay also had two different visual languages for the same fact, which is worse than either alone: an author comparing the area inspector to the map could not tell whether `🧭 down` and `⬆N` meant the same thing.

The cardinal vocabulary is wider than the eight headings. The data uses twelve values: the eight horizontal, `up`/`down`, `in`/`out` for scope gateways (written by `engine/world_compile.py`), and `upstream`/`downstream`. A map that only knew eight would render the other four as raw text.

## How

1. `static/js/inspector/way-authoring.ts` gains `CARDINAL_ICON` (one map of all twelve cardinals to a glyph), `cardinalIcon(cardinal)` (the glyph, falling back to the raw word for an unknown value so an authored cardinal is never hidden), and `wayCardinal(wayId)` (the way's cardinal, read from its connection edges, falling back to the edge's `direction` when that is itself a heading - the same fallback `engine/facing.py`'s `edge_cardinal()` and `graph/layout-engine.ts` already use).
2. `static/js/inspector/area-view.ts` renders the badge from `WayAuthoring.cardinalIcon(...)` instead of the raw word.
3. `static/js/graph/overlays.ts` reads the cardinal through `WayAuthoring.wayCardinal(node.id)` instead of `node.properties.cardinal`, and uses the shared glyph.

The vertical pair gets its own arrows (`⤒U` / `⤓D`) rather than borrowing the north and south ones, because a vertical move is not a bearing. The scope-gateway pair gets `↘IN` / `↗OUT`.

No engine change was needed.

## Browser UI and intended live verification

Intended UI home: Graph view -> the Cardinal overlay toggle in the graph toolbar (labels every way). Area view -> select an area -> the EXITS list, where each exit carries the cardinal badge.

Current availability: Implemented and wired. Verified live in the browser on the Kraktooth goblin camp: the Cardinal overlay labels all 23 ways with a real glyph (0 `?`, 0 raw words), including `⤓D` on the two vertical ways and `↘IN`/`↗OUT` on the scope gateway. The area inspector's EXITS list for 'Camp Entrance' reads `🧭 ⤓D` (downward passage), `🧭 ↘IN` (into camp) and `🧭 ⬇S` (south trail).

Live steps when available:
1. Open the graph, switch on the Cardinal overlay, and read the way labels.
2. expected: each way shows a direction glyph (for example `⬆N`, `➡E`, `⤓D`) above its name, and no way shows `?`.
3. Open an area that has a vertical exit, and read its EXITS list.
4. expected: the vertical exit's badge shows the vertical arrow glyph and the other exits show their own heading glyphs, all in the same visual language as the overlay.
5. Open a scope gateway's area and read its EXITS list.
6. expected: the gateway's badge shows the `in` / `out` glyph rather than the raw word.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Confirm the overlay was reading the wrong object.
   - expected: the cardinal is on the connection edge, not the way node.
   - observed: CONFIRMED. Live count against `GET /api/state` in the Kraktooth
     goblin camp: **5030** edges carry `properties.cardinal` and **0** way
     nodes do. The overlay's read (`nodeData.properties.cardinal`) therefore
     found nothing.
2. Confirm the overlay's output was a placeholder.
   - expected: every way labelled `?`.
   - observed: CONFIRMED. Calling `GraphOverlays.applyCardinalOverlay()` in
     the browser labelled all **23** ways with `?` - the label head query
     returned exactly `{"?": 23}`.
3. Re-run the overlay after the fix.
   - expected: real glyphs, and no `?` on a way that has a cardinal.
   - observed: PASSES. The same call now labels all 23 ways with a glyph:
     `⬆N` x3, `➡E` x7, `⬅W` x2, `⬇S` x2, `⤓D` x3, `⬈NE` x1, `⬉NW` x1,
     `⬊SE` x1, `⬋SW` x1, `↘IN` x1, `↗OUT` x1. The `?` count is **0** and the
     raw-word count is **0**.
4. Confirm the area badge uses the same glyph.
   - expected: the badge and the overlay agree.
   - observed: PASSES. The EXITS list of 'Camp Entrance' reads
     `🧭 ⤓D` (downward passage), `🧭 ↘IN` (into camp) and `🧭 ⬇S`
     (south trail), each with the matching `title` attribute
     ("Map cardinal: down" and so on). The `⤓D` on the vertical exit is the
     same glyph the overlay gives that way.
5. Confirm the cardinal vocabulary is complete.
   - expected: every cardinal the data actually uses has a glyph.
   - observed: PASSES. Counting `properties.cardinal` across the camp's edges
     gives twelve distinct values: the eight horizontal headings, `up` x2,
     `down` x2, `in` x1, `out` x1, `upstream` x1, `downstream` x1. All twelve
     are in `CARDINAL_ICON`, which is why no way falls through to a raw word.
6. Confirm the direction fallback matches the engine.
   - expected: a way with no `cardinal` but a heading-like `direction` still
     reads as that heading.
   - observed: PASSES, and it matters: 4 ways have a `direction` but no
     `cardinal`. Three of them ('Nursery Passage' with `north`/`south`,
     'Shaman Passage' with `east`/`west`, 'Tunnel Opening' with `east`/`west`)
     went from `?` to a real glyph once the fallback was added. The fourth,
     'Hide-Curtained Alcove', has `direction: "out"` on both edges and no
     `cardinal`; it is the one way that still shows `?`, which is correct -
     `out` there is a prose direction, not a heading.
7. Confirm the `?` case is still honest.
   - expected: a way with neither a cardinal nor a heading-like direction
     keeps `?`, so the World Issues validator's `way_missing_cardinal` check
     still has something to report.
   - observed: PASSES. The fallback only accepts a `direction` that is itself
     one of the known cardinals; a prose direction is left off, so the `?`
     survives rather than being papered over with a guess.
8. Run the gates.
   - expected: `npm run build:ts`, `npm run typecheck` and
     `node tools/unit/run.cjs` green, and the three changed files lint clean.
   - observed: PASSES for all four. `build:ts` and `typecheck` report no
     errors; the unit runner reports 781 passed, 0 failed (57 test files);
     `eslint` on `way-authoring.js`, `area-view.js` and `overlays.js` exits 0.
     `python tools/ts_convert.py check` still reports two failures and neither
     is from this change: `lint` fails on
     `static/js/agent/action-verbs.generated.js` (an untracked generated file
     from another lane) and `module:check` fails on `static/js/ui/play-mode.js`
     missing the `@module`/`@contributes` contract (committed in 2a7e3dd0,
     task-885). `python tools/feature_index.py --check` reports
     "Feature check OK (78 rows, every Docs note resolves)".

## Acceptance

- [x] The graph's Cardinal overlay labels each way with its cardinal glyph instead of `?`.
- [x] The area inspector's exit badge and the Cardinal overlay use the same glyph for the same cardinal.
- [x] A way whose cardinal is `up` or `down` gets a vertical glyph distinct from the north and south ones.
- [x] A scope gateway's `in` / `out` cardinal gets a glyph rather than a raw word.
- [x] A way with no cardinal and no cardinal-like direction keeps `?`, which is the honest answer and what the World Issues validator's `way_missing_cardinal` check reports.
- [x] `npm run build:ts`, `npm run typecheck` and `node tools/unit/run.cjs` are green, and the three changed files lint clean.

## Files

- `static/js/inspector/way-authoring.ts`
- `static/js/inspector/way-authoring.js`
- `static/js/inspector/area-view.ts`
- `static/js/inspector/area-view.js`
- `static/js/graph/overlays.ts`
- `static/js/graph/overlays.js`
- `docs/virtualWorld/World Building/Ways.md`
