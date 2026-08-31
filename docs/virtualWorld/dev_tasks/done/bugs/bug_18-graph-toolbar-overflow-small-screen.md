# Bug-18: Graph Toolbar Overflows Off-Screen on Smaller Windows

**Status:** Done — confirmed by Tommy 2026-08-30.
**Area:** UI â€” graph editor toolbar
**Observed:** `toolbar for graph overflows out of screen on smaller screens`

## Repro (live markup)

The toolbar is one `.editor-toolbar` with several `.toolbar-group` rows. The
middle group is very wide â€” 11 controls in a row:

```html
<div class="toolbar-group">
    <button id="btn-physics">â¸ Physics</button>
    <button id="btn-cardinal">ðŸ—ºï¸ Map</button>
    <button>âŠž Fit</button>
    <input id="graph-search" class="graph-search" type="text" placeholder="ðŸ” Search nodes...">
    <button>ðŸ“– Legend</button>
    <button>ðŸ·ï¸ Tags</button>
    <button id="btn-edge-labels">ðŸ· Labels</button>
    <button id="btn-triggers">ðŸ”© Triggers</button>
    <button id="btn-items">ðŸ“¦ Items</button>
    <button class="view-toggle">ðŸ”® Graph</button>
    <div class="toolbar-dropdown"><button>ðŸ“Š Overlays â–¾</button>...</div>
    <button>ðŸ–¨ï¸ Print</button>
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
`toolbar-group` wider than the screen overflows past the right edge â€” the big
middle group is clearly it.

## Fix options

1. **Scroll strip (simplest):** allow inner groups to scroll when too wide â€”
   `overflow-x: auto` on `.editor-toolbar` (buttons stay reachable, one row).
2. **Wrap within groups:** make `.toolbar-group` also `flex-wrap: wrap` so the
   buttons inside a wide group flow to multiple lines (uses vertical space but
   everything is visible).
3. **Shrinkable search input:** give `.graph-search` a `min-width: 0` +
   `flex: 0 1 auto` so it can shrink instead of forcing the row wide.

Verify the toggle buttons (physics, cardinal, items, triggers, legend, labels,
overlays) remain usable at common small widths (~1024px, ~1280px) either way.
