---
type: task
status: inprogress
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
   - expected: TODO
   - observed: TODO
2. Record the browser surface and interaction actually used (for example: navigate, click, hover, type, expand, or scroll to the bottom).
   - expected: TODO
   - observed: TODO
3. Run the targeted regression test for the mechanism.
   - expected: TODO
   - observed: TODO

## Acceptance

All 17 view files refactored to extend InspectorView base; shared components extracted; string-based HTML eliminated; unit tests for base class and components; new view can be added in <50 lines

## Files

- `static/js/inspector/panel.ts`
- `static/js/inspector.ts`
- `static/js/inspector/helpers.ts`
- `static/js/inspector/*-view.ts`
