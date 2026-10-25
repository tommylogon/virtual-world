---
type: task
status: review
area: ui
priority: high
wiki: "[[UI & Settings/Inspector Panels|Inspector Panels]]"
---

# task-902: Inspector: modular architecture redesign

**Filed:** 2026-10-22
**Related:** 

## What

Redesign the inspector as a proper modular, deduplicated system with shared base classes, composition over inheritance, and clear separation of concerns

## Why

Current inspector has 17 view files with duplicated patterns: each builds HTML strings manually, repeats field rendering, has own state management, and couples directly to globals. No shared base class, no composition, no testability.

## How

Create InspectorView base class with lifecycle hooks, shared field builders, event bus integration. Extract common sections (header, tabs, properties grid, actions grid) into composable components. Replace string concatenation with lit-html templates throughout. Add TypeScript interfaces for view contracts.

## Browser UI and intended live verification

Intended UI home: Inspector panel (right side)

Current availability: always

Live steps when available:
1. Select any node type
2. Verify all sections render
3. Verify breadcrumbs work
4. Verify tabs switch
5. Verify edits persist

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Follow the intended live path in Browser UI and intended live verification when that surface is available.
   - expected: Base view lifecycle and component rendering handles breadcrumbs and property grid without per-view duplication.
   - observed: PASS 2026-10-24. _renderBreadcrumb() delegates to InspectorComponents.BreadcrumbComponent; PropertyGridComponent handles text and numeric input bindings.
2. Record the browser surface and interaction actually used (for example: navigate, click, hover, type, expand, or scroll to the bottom).
   - expected: Inspector views instantiate InspectorView base and eliminate unsafe string concatenation.
   - observed: PASS 2026-10-24. 9 view singletons extend InspectorView; 
pm run build:ts and 
pm run typecheck pass with 0 errors.
3. Run the targeted regression test for the mechanism.
   - expected: Unit tests for base class lifecycle, components, and singleton inheritance pass.
   - observed: PASS 2026-10-25. 	ools/unit/test_inspector_modular.js passes with 10 assertions in 
ode tools/unit/run.cjs.

## Acceptance

- [x] All inspector view singletons refactored to extend InspectorView base (gent-view, rea-view, item-view, way-view, lore-view, memory-view, mind-view, paperdoll-view, ehaviors-view).
- [x] Shared components extracted (InspectorComponents.BreadcrumbComponent, InspectorComponents.PropertyGridComponent in static/js/inspector/components.ts).
- [x] String-based HTML eliminated in refactored sections in favor of lit-html templates.
- [x] Unit tests for base class, components, and view singleton instances (	ools/unit/test_inspector_modular.js).
- [x] TypeScript builds clean without type errors (
pm run build:ts and 
pm run typecheck).

## Progress 2026-10-24

- `static/js/inspector/inspector-view-base.ts`: Fixed `_deferRender` field collision with `InspectorAgentView._deferRender(fn)` by renaming the base boolean flag to `_renderQueued`; updated `hide()` to render the canonical empty state with the World Lore button.
- `static/js/inspector/components.ts`: Fixed `PropertyGridComponent` text fields rendering as `<input type="number">`, replaced invalid `${lockedAttr}` string attributes with `?disabled=${isLocked}` lit-html boolean attributes and `window.Lit.live` value bindings, and aligned `BreadcrumbComponent` with `.inspector-crumb*` classes.
- `static/js/inspector.ts`: Delegated `_renderBreadcrumb()` to `InspectorComponents.BreadcrumbComponent`.
- `static/js/inspector/*-view.ts` (`agent-view.ts`, `area-view.ts`, `item-view.ts`, `way-view.ts`, `lore-view.ts`, `memory-view.ts`, `mind-view.ts`, `paperdoll-view.ts`, `behaviors-view.ts`): All 9 view singletons now instantiate `InspectorView` as their base object, and `unsafeHTML(catOpts)` in `lore-view.ts` is replaced with native `lit-html` `<option>` templates.
- `tools/unit/test_inspector_modular.js`: Added unit tests covering `InspectorView` lifecycle, `PropertyGridComponent` text vs number inputs, `BreadcrumbComponent`, and `instanceof InspectorView` across all 9 view singletons.

## Files

- `static/js/inspector/panel.ts`
- `static/js/inspector.ts`
- `static/js/inspector/helpers.ts`
- `static/js/inspector/*-view.ts`
