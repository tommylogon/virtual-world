---
group: UI Refactor
wiki: "[[UI & Settings/Inspector Panels]]"
---

# lit-html Inspector Conversion

**Priority**: Medium
**Status**: In Review — implemented 2026-08-13 (all views route through `InspectorPanel`; static checks pass; pending browser E2E)

---

## Summary

All inspector views (`#inspector-panel`) previously used vanilla JS `innerHTML` template literals with inline event handlers. This was fragile: mixing rendering approaches caused DOM state conflicts, escaping was manual and error-prone, and re-rendering destroyed/recreated the entire panel DOM on every update.

A proof-of-concept with `lit-html` (ES module + import map) was attempted for the edge inspector, but it failed because:
1. The module loaded asynchronously while other inspectors write to the same panel synchronously
2. lit-html's internal comment placeholders leaked into the DOM on re-render
3. `panel.innerHTML = ''` to clear state broke lit-html's diffing

## Goal

Convert all inspector views to a consistent rendering approach, chosen as **Option A (all lit-html)** with a classic-script bootstrap:

- Vendored `lit-html` under `static/js/vendor/lit-html/`
- `static/js/shared/lit-bootstrap.js` — deferred ES-module bootstrap that exposes `window.Lit` (`html`, `render`, `nothing`, `unsafeHTML`, directives) at call time, so classic scripts keep working
- `static/js/inspector/panel.js` — `InspectorPanel`, the SINGLE render entrypoint for `#inspector-panel`. No other file writes `panel.innerHTML` directly.
- Views render lit `TemplateResult`s via `window.Lit.html` and hand them to `InspectorPanel.render()`
- Inline `onclick`/`onchange` replaced with `@click`/`@change`/`?selected` bindings where views were fully converted
- lit auto-escaping replaces most manual `esc()` calls in converted views

### Converted fully to lit TemplateResults

- `inspector/helpers.js` — `graphGravityControl`, `renderLockToggle`, `renderAliasesSection` return TemplateResults
- `inspector/trigger-helpers.js` — `buildTriggersHtml` / `buildContentsHtml`
- `inspector/lore-view.js` — list + modal
- `inspector/memory-view.js` — edit modal (section builder stays string for agent-view)
- `inspector/behaviors-view.js` — editor modal + action cards
- `inspector/area-view.js` — full view
- `inspector/item-view.js` — full view (Choices.js equip-slot select still re-init'd post-render)
- `inspector/way-view.js` — full view incl. reconnect/connections section (fixed latent bugs: lock-toggle was `[object Object]`, connection "View from" textareas were missing their opening tags)
- `graph/edge-inspector.js` — full view; added `renderEdgeInspector` export so `graph-manager._showEdgeInspector` dispatches to the lit version (it was previously dead code falling through to the innerHTML fallback)
- `graph-manager.js` — `_showEdgeInspector` fallback renders a lit template through `InspectorPanel` instead of `panel.innerHTML`
- `inspector.js` — `hide()`/empty/fallback branches render through `InspectorPanel`

### agent-view.js (largest, 1461 lines)

Kept as a single string template (48 inline handlers) but rendered through `InspectorPanel.render()` wrapped in `lit-html`'s `unsafeHTML` directive, so `InspectorPanel` stays the sole owner of the panel while lit never diffs against string content. Two helper TemplateResults (`graphGravityControl`, `renderAliasesSection`) that can't be string-concatenated are rendered into placeholder `<div>`s via a deferred-render queue (`_deferredGravityControl`/`_deferredAliasesSection`) after the panel render.

### paperdoll-view.js

Left as string output (consumed by agent-view's string template) — a prior session's edit had stripped its `esc()` calls on the assumption of full lit rendering; those were restored because agent-view emits them through `unsafeHTML`, where manual escaping is still required.

## Verification

Static (done):
- `node --check` passes on all converted inspector/graph files
- `rg "panel.innerHTML"` shows no writers outside `InspectorPanel` itself

Pending browser E2E (user):
1. Click every node type in graph → inspector updates correctly
2. Click another node → previous content fully replaced, no stale DOM
3. All buttons/inputs work (edit, delete, add, save)
4. No `<!--?lit$...$-->` placeholders in DOM
5. Agent view tabs switch, paperdoll/inventory/memory/behaviors/lore still interactive
6. Edge inspector from graph context menu renders and edits properties

## Files

- `virtual_world/static/js/vendor/lit-html/**` — vendored lit-html
- `virtual_world/static/js/shared/lit-bootstrap.js` — deferred `window.Lit` bootstrap
- `virtual_world/static/js/inspector/panel.js` — single panel render owner
- `virtual_world/static/js/inspector/helpers.js`
- `virtual_world/static/js/inspector/trigger-helpers.js`
- `virtual_world/static/js/inspector/lore-view.js`
- `virtual_world/static/js/inspector/memory-view.js`
- `virtual_world/static/js/inspector/behaviors-view.js`
- `virtual_world/static/js/inspector/paperdoll-view.js`
- `virtual_world/static/js/inspector/area-view.js`
- `virtual_world/static/js/inspector/item-view.js`
- `virtual_world/static/js/inspector/way-view.js`
- `virtual_world/static/js/inspector/agent-view.js`
- `virtual_world/static/js/inspector.js`
- `virtual_world/static/js/graph/edge-inspector.js`
- `virtual_world/static/js/graph-manager.js`
- `virtual_world/templates/index.html` — script load order (panel.js after helpers, lit-bootstrap as deferred module)
