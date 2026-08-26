# Bug-18: Graph Toolbar Overflows Off-Screen on Smaller Windows

**Status:** In Review — implemented 2026-08-16 in `static/css/style.css`: `.editor-toolbar` got `overflow-x: auto` (thin scrollbar) + `max-width: 100%`, and `.toolbar-group` now `flex-wrap: wrap` so wide groups flow to multiple lines. Browser re-check pending.
**Area:** UI — graph editor toolbar
**Observed:** `toolbar for graph overflows out of screen on smaller screens`

## Repro (live markup)

The toolbar is one `.editor-toolbar` with several `.toolbar-group` rows. The
middle group is very wide — 11 controls in a row:

```html
<div class="toolbar-group">
    <button id="btn-physics">⏸ Physics</button>
    <button id="btn-cardinal">🗺️ Map</button>
    <button>⊞ Fit</button>
    <input id="graph-search" class="graph-search" type="text" placeholder="🔍 Search nodes...">
    <button>📖 Legend</button>
    <button>🏷️ Tags</button>
    <button id="btn-edge-labels">🏷 Labels</button>
    <button id="btn-triggers">🔩 Triggers</button>
    <button id="btn-items">📦 Items</button>
    <button class="view-toggle">🔮 Graph</button>
    <div class="toolbar-dropdown"><button>📊 Overlays ▾</button>...</div>
    <button>🖨️ Print</button>
</div>
```

## Root cause

`static/css/style.css`

```css
.editor-toolbar {
    display: flex; gap: 6px; flex-shrink: 0;
    flex-wrap: wrap;            /* already present */
}
.toolbar-group { display: flex; align-items: center; gap: 4px; }
.toolbar-btn   { white-space: nowrap; }
```

`flex-wrap: wrap` only wraps *whole groups*. The groups themselves are `flex`
rows whose buttons are `white-space: nowrap` and cannot shrink, so any single
`toolbar-group` wider than the screen overflows past the right edge — the big
middle group is clearly it.

## Fix options

1. **Scroll strip (simplest):** allow inner groups to scroll when too wide —
   `overflow-x: auto` on `.editor-toolbar` (buttons stay reachable, one row).
2. **Wrap within groups:** make `.toolbar-group` also `flex-wrap: wrap` so the
   buttons inside a wide group flow to multiple lines (uses vertical space but
   everything is visible).
3. **Shrinkable search input:** give `.graph-search` a `min-width: 0` +
   `flex: 0 1 auto` so it can shrink instead of forcing the row wide.

Verify the toggle buttons (physics, cardinal, items, triggers, legend, labels,
overlays) remain usable at common small widths (~1024px, ~1280px) either way.