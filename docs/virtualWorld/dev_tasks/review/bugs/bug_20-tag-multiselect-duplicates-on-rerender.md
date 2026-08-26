# Bug 20 — Tag multiselect duplicates on every inspector re-render

**Status:** In Review — fixed 2026-08-23, pending browser E2E

## Symptoms

Every add/remove of a tag in the item inspector appended another full
TagMultiselect widget inside `#tag-multiselect-container-<nodeId>` (5 stacked,
empty copies observed in the DOM dump). Adding tags had the same effect since
both paths fire `onChange` → `api.updateNode` → `worldState.fetch()` → re-render.

## Root cause

`static/js/shared/tag-multiselect.js` mixed two rendering worlds:

1. `_build()` called `window.Lit.render(empty, container)` to clear the
   container — but lit-html only clears content between its own comment
   markers.
2. The widget `wrapper` was then added via `container.appendChild(...)`,
   landing AFTER lit's end marker, outside lit's managed region.

So every rebuild kept the old wrapper and appended a fresh one. `destroy()`
had the same flaw (lit-render empty leaves the imperative wrapper behind) and
was never called by most call sites anyway (`IV._tagMs` was simply overwritten).

## Fix

`tag-multiselect.js`:

- `_build()` now wipes all container children imperatively
  (`while (container.firstChild) removeChild(...)`) before appending —
  guarantees exactly one widget per container regardless of rebuild count.
- `destroy()` uses the same wipe so it actually removes the widget.

Fix is in the shared component, covering all call sites at once:
item-view, way-view, area-view, agent-view, memory-view, create-modal,
library-browser, trigger-editor, item-library. `trigger-editor` additionally
guards with `container.__condTagMulti`, so no behavior change there.

## Verification

- `node --check static/js/shared/tag-multiselect.js` — OK.
- Browser E2E pending: select item → remove a tag → confirm exactly one
  selector remains; add a tag → same; switch between nodes → no stacking.

## Files touched

- `virtual_world/static/js/shared/tag-multiselect.js`
