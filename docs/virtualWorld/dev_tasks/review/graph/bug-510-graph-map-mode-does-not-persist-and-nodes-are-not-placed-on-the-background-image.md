---
type: bug
status: review
area: graph
priority: high
---

# bug-510: Graph map mode does not persist, and nodes are not placed on the background image

**Filed:** 2026-09-30
**Related:** 

## Goal

Two defects in one area. (1) Selecting map mode for the graph does not save - the choice is lost on reload or re-render. (2) Nodes are not correctly placed or spaced relative to the background image, so they must be nudged by hand every time the map is loaded. Determine whether the placement is a stored coordinate that is being lost, a projection/scale mismatch between node coordinates and image pixels, or a layout pass that is not reading the map's coordinate space at all.

## Acceptance

- TODO

## Fix / findings — 2026-10-02 (port 4471, Playwright)

### (1) Map mode did not persist — fixed

Root cause: the Map layout lived only in `graphManager._cardinalLayout`, a
runtime boolean. `config.graphLayoutMode` persisted **Levels** ('free'/'levels')
but there was no key at all for Map, so a reload (and any full re-init) dropped
straight back to Graph — exactly what the audit noted ("there is no key for
layout mode").

- `config.js` now loads/saves `graphCardinalLayout` (`graph_cardinal_layout`),
  separate from `graphLayoutMode` because `activeLayout()` treats them as
  independent axes.
- `graph-manager.js` initialises `_cardinalLayout` from config (constructor and
  again in `init()`, after `config._initPromise`), and `_persistCardinalLayout()`
  is called whenever the choice actually changes — `toggleCardinalLayout()` and
  the `setViewMode('graph')` clear.

Live proof (real click on `#layout-segment [data-layout="map"]`):

| step | `activeLayout()` | `config.graphCardinalLayout` | `storage` | Map tab `aria-selected` |
|---|---|---|---|---|
| before | graph | false | "false" | false |
| after click | map | true | "true" | true |
| after reload | **map** | true | "true" | **true** |

### (2) Nodes not on the background image — does not reproduce as filed

Measured on the current tree: the two background layers carry rects in graph
units, and **236 of 238 placed nodes fall inside an image rect**. The two
outliers are one area 193px below layer 0 (`Dark Cave`, y=1284 vs bottom 1090)
and one logic-trigger 32px above its top edge (`on_examine → message`) — i.e.
nodes the layout engine placed relative to their holder, not a whole-canvas
projection failure. The old audit picture (a node pile "below and to the left"
of a single map band, four images at four scales) no longer matches: Map mode
composes the layers side by side and the nodes share their frame.

So the placement half is a **retraction with measurement**, not a fix I made.
The audit also noted `graph_background.positions` is still empty (0 entries) and
layout is stored in `node.properties.x/y`; that two-stores question is a design
decision, filed separately, and not resolved here.

Gates: `node tools/unit/run.cjs` 485 passed; `npm run lint`, `npm run
typecheck` clean.
