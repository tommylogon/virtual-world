---
type: task
status: todo
area: refactor
priority: high
wiki: "[[UI & Settings/Inspector Panels|Inspector Panels]]"
---

# task-904: Shared component library: extract reusable UI primitives and state primitives

**Filed:** 2026-10-23
**Related:** task-902, task-854, task-893

## What

Extract shared UI component library and state primitives to eliminate duplication across Viwo inspector panels and between Viwo and The Commons.

## Why

Viwo and The Commons duplicate core UI and state primitives:
1. Inspector views (`item-view.ts`, `area-view.ts`, `agent-view.ts`, `way-view.ts`) each copy-paste 40-70 lines of identical node identity markup (badge, name input, generated-node check, lowercase rename, sync ID button, library sync, and node deletion).
2. The Commons (`templates/commons.html`, `static/js/commons/`) duplicates dialogs, collapsible drawer sections, status badges, and shortcut handling already present in Viwo.
Extracting these into presentational components in `static/js/inspector/components.ts` and `static/js/shared/components/` eliminates duplication, enforces consistent contracts, and prevents brittle domain-coupled widgets.

## How

1. **Phase 1: Inspector Component Decomposition (High ROI)**
   - Extract `InspectorNodeHeader` into `static/js/inspector/components.ts`: standardizes badge, editable name, generated-node guard, lowercase rename, sync ID button, and close handler.
   - Extract `InspectorDangerZone` into `static/js/inspector/components.ts`: standardizes node deletion button, confirm modal, and dispatch.
   - Wire `InspectorNodeHeader` and `InspectorDangerZone` into `item-view.ts`, `area-view.ts`, `way-view.ts`, and `agent-view.ts`.
2. **Phase 2: Viwo and Commons Shared UI Primitives**
   - Extract `CollapsibleSection` and `StatusBadge` into `static/js/shared/components/`.
   - Extract `ModalDialog` with dark-mode styling, Escape-key handling, and backdrop dismissal.
   - Wire shared primitives into both the Viwo Agents left-panel tab and The Commons drawer (`/commons`).
3. **Phase 3: State & API Contracts**
   - Extract `ShortcutRegistry`, `Observable`, and `PersistedConfig` to `static/js/shared/state/`.
   - Update imports and ensure clean TypeScript build (`npm run build:ts`).

## Browser UI and intended live verification

Intended UI home: Right-panel Inspector tabs (Item, Area, Character, Way) and Left-panel Agents tab / The Commons drawer

Current availability: always (Inspector panels and The Commons are currently live in the app)

Live steps when available:
1. Click on an item, area, character, or way node on the graph canvas or from the outline list
   - expected: Inspector panel opens with the standardized InspectorNodeHeader showing type badge, editable name, generated-node indicator or rename field, and sync ID button without layout breakage.
2. Edit the name or click the sync ID button on the inspector header
   - expected: Graph node updates name or ID, state persists across reload, and graph label synchronizes.
3. Click the delete node button in the inspector danger zone
   - expected: Confirmation prompt appears and confirming cleanly deletes the node from graph canvas and worldState.
4. In The Commons (/commons), open a character drawer
   - expected: Character drawer renders collapsible sections and status presence badges using the shared presentational primitives.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Follow the intended live path in Browser UI and intended live verification when that surface is available.
   - expected: Inspector views render unified InspectorNodeHeader and DangerZone widgets with functional rename, sync-ID, and delete operations across all 4 entity types.
   - observed: Planned; to be tested upon implementation.
2. Record the browser surface and interaction actually used (for example: navigate, click, hover, type, expand, or scroll to the bottom).
   - expected: Inspecting item, area, way, and character nodes displays identical header controls without console errors or regressions.
   - observed: Planned; to be tested upon implementation.
3. Run the targeted regression test for the mechanism.
   - expected: Unit tests in tools/unit/test_inspector_modular.js and tools/unit/test_commons_drawer.js pass with 0 failures, and npm run build:ts compiles with 0 errors.
   - observed: Planned; to be tested upon implementation.

## Acceptance

- [ ] `static/js/inspector/components.ts` exports `InspectorNodeHeader` and `InspectorDangerZone`.
- [ ] `item-view.ts`, `area-view.ts`, `way-view.ts`, and `agent-view.ts` delegate node header and deletion markup to the shared inspector components.
- [ ] `static/js/shared/components/` hosts reusable presentational primitives (`CollapsibleSection`, `StatusBadge`).
- [ ] The Commons drawer and Viwo panels import and use the shared components with consistent styling.
- [ ] `npm run build:ts` and `npm run typecheck` pass with 0 errors.
- [ ] Existing unit tests pass cleanly.

## Files

- `static/js/inspector/components.ts`
- `static/js/inspector/item-view.ts`
- `static/js/inspector/area-view.ts`
- `static/js/inspector/way-view.ts`
- `static/js/inspector/agent-view.ts`
- `static/js/shared/components/`
- `static/css/commons.css`
- `templates/commons.html`
- `static/js/commons/commons-ui.js`
- `tools/unit/test_inspector_modular.js`
