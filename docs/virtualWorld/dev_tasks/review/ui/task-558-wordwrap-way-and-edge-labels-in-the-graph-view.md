---
type: task
status: review
area: ui
priority: low
---

# task-558: Wordwrap way and edge labels in the graph view

**Filed:** 2026-09-27
**Related:** task-530

## Goal

Wrap long way/edge labels to a max width, and fix the single-line edge-length
math so wrapped labels still get room. Also pin the unpinned vis-network CDN
version.

Unrelated to the climate design work; the substance is below.

## Measured (2026-09-27) — the graph draws labels on canvas, and sizes edges for one line

The graph view is **vis-network**, which draws edge labels on a canvas. There
is no HTML and no wordwrap option in the app today: a search for
`measureText` / `textPath` / `foreignObject` across `static/js` finds one hit,
and it is an unrelated sprite-sheet routine
(`static/js/inspector/sprite-sheet.js:258`).

Two places have to change together, or wrapped labels will collide:

**1. The label width.** `static/js/graph/network-manager.js:482` sets `label`
and `:492` sets `font`. vis-network already supports the wrapping option we
want — a `widthConstraint` number that breaks label lines on spaces to stay
under a maximum width. It is a per-edge or global option, so it drops straight
into `buildEdgeConfig`.

**2. The edge length, which assumes a single line.**
`static/js/graph/network-manager.js:471-472`:

```js
const labelLength = String(edgeLabel || '').length;
edgeLength = Math.min(130, Math.max(45, 35 + labelLength * 3.2));
```

A 60-character way name on one line is what this number was tuned for. Once the
label wraps to three lines it needs vertical room, and the same character count
in three lines is a *shorter* edge than the formula expects. This is the actual
work in the task; the `widthConstraint` itself is one line.

**The worst offender is `unlocks` edges** (`:404-409`), which put a whole
`properties.description` on the label — arbitrary length, author-written prose.
Wrap it to about three lines and keep the rest behind the hover tooltip that
already exists (`WayAuthoring.buildEdgeTooltipForVis`, `:427-432`).

## Way *nodes* are a different animal

Way nodes are nodes, not edges, so `nodes.widthConstraint` grows the node box —
which collides with the map layout's fixed margins and the `mapSizeScale()` font
math at `:155-158`. Leave way-node names to the existing label-LOD policy
(`_nodeLabelPolicy`, `:633`) and the tooltip. **Wrap edges only.**

## Pin the library

`templates/index.html:22` loads vis-network **unpinned** from unpkg:

```html
<script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
```

Latest is currently 10.1.2 while this code was written against the 9.x API, so
the app's graph is running on whatever unpkg serves today. Pin an explicit
version and confirm `widthConstraint` exists in the pinned build before relying
on it. This is a latent breakage risk independent of the wordwrap.

## Acceptance

## Acceptance

- [x] **Long way labels wrap instead of stretching or clipping**:
      `widthConstraint: { maximum: EDGE_LABEL_WRAP }` on every edge — edges only.
- [x] **The edge length is computed from the wrapped line count**, not the raw
      character count. `_labelEdgeLength()` wraps the label *the same way vis will,
      at the same width*, then sizes from the widest line plus a line of height
      per extra line, so wrapped labels do not overlap nodes or each other.
- [x] **Short labels are unaffected**: "west" is one line and gets the same length
      as before, because the character estimate is kept and only the line count is
      new.
- [x] **The worst offender is fixed**: an `unlocks` edge carries a whole
      `properties.description` on its label, so it is now cut to whole sentences
      and at most three lines (`_firstSentence`). The full text stays on the hover
      tooltip that already existed.
- [x] **Full text remains reachable on hover.**
- [x] **vis-network is pinned** to `9.1.9` in `templates/index.html`, with a
      comment saying to bump it deliberately and check the graph view when doing
      so. 9.1.9 is the 9.x line this code was written against and it supports
      `widthConstraint`.
- [x] `node tools/unit/run.cjs` passes — 368 passed, with the 13 pre-existing
      `test_plan_tracker.js` failures unchanged.
- [x] **Way nodes were deliberately not touched.** They are nodes, not edges;
      `nodes.widthConstraint` grows the node box, which collides with the map
      layout's fixed margins and the `mapSizeScale()` font math. Way names keep
      the existing label-LOD policy (`_nodeLabelPolicy`) and the tooltip.

## Notes

- A single word longer than the wrap width (a URL, a long id) is left as one line
  rather than cut mid-word: there is nothing to break on, and half an id is
  useless where half a sentence is merely annoying.
