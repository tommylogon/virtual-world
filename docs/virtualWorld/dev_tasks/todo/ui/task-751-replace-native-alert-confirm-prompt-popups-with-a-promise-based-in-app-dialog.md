---
type: task
status: todo
area: ui
priority: medium
---

# task-751: Replace native alert/confirm/prompt popups with a promise-based in-app dialog

**Filed:** 2026-10-09
**Related:** bug-533 (silent no-op), shared/diff-modal

## Goal

Native `alert()` / `confirm()` / `prompt()` popups are used throughout the front
end. They ignore the app's theme and focus management, look nothing like the rest
of the UI, and are the same blocking string-returning API everywhere. Replace them
with one reusable, promise-based in-app dialog.

This was triggered by the blueprint save flow: `trigger-graph._saveBlueprint`
(`shared/trigger-graph.ts:2108-2122`) fires **two** `prompt()` calls in a row
(name, then description), and the toolbar button is labelled "💾 Blueprint" so it
is not even obvious it saves. A two-field modal fixes both problems at once.

Inventory (TS sources; the generated `.js` doubles each). Counts are approximate —
some `prompt(` matches in `agent/prompt-builder/*` are identifiers, not popups, so
triage per site:

| Kind | Count | Notes |
|---|---|---|
| `confirm()` | 19 | boolean guard, maps 1:1 to `dialog.confirm` |
| `prompt()` | 20 | needs a small form modal (fields + validate) |
| `alert()` | 9 | maps to `toast(...)` in most cases, `dialog.alert` otherwise |

Heaviest files: `shared/trigger-graph.ts` (16), `graph-manager.ts` (10),
`library-browser.ts` (8), `ui/saveload-view.ts` (4), then
`graph/context-menu.ts`, `graph/graph-background.ts`, `graph/node-operations.ts`,
`inspector/agent-view.ts`, `inspector/area-view.ts`, `ui/scenario-manager.ts`,
`ui/scenario-wizard.ts`, `ui/changes-panel.ts`, `item-library.ts`,
`nl-editor/ui.ts`, `agent-lens.ts`, `inspector/memory-view.ts`,
`inspector/lore-view.ts`, `inspector/helpers.ts`, `inspector/behaviors-view.ts`,
`shared/diff-modal.ts`, `main.ts`, `config.ts`.

## Design

A single `shared/dialog.ts` module, promise-based, modelled on `DiffModal.show`
(same overlay + Lit + `null`-on-cancel contract that already fits the codebase):

- `dialog.confirm({ title, message, confirmLabel?, cancelLabel?, danger? })`
  → `Promise<boolean>`
- `dialog.prompt({ title, fields: [{ key, label, value?, placeholder?, type? }], confirmLabel? })`
  → `Promise<Record<string,string> | null>`
- `dialog.alert({ title, message })` → `Promise<void>`

Focus-trapped; `Esc` cancels, `Enter` submits, backdrop click cancels. Publish as
`VW.dialog`. `alert()` calls that are just "it worked" messages become
`toastInfo`/`toastError` (`ui-helpers.ts`) — do not open a modal for those.

## Plan

1. Build `shared/dialog.ts` (+ `@module`/`@contributes` headers, script tag,
   `js_module_index`), pilot it on the blueprint save (name + description in one
   modal) and relabel the toolbar button so "save" is obvious.
2. Migrate `confirm()` → `dialog.confirm` (19), then `prompt()` → `dialog.prompt`
   (20, per-file), then the true `alert()`s (9; most → toast).
3. One `build:ts` per batch; `typecheck` + unit.

## Acceptance

- [ ] `VW.dialog` exists (confirm / prompt / alert), promise-based, focus-trapped,
      `Esc`/`Enter`/backdrop handled, and is covered by unit tests.
- [ ] The blueprint save uses it: one modal with name + description; the toolbar
      button makes clear it saves to the library.
- [ ] No native `alert`/`confirm`/`prompt` remains in the migrated surfaces
      (tracked to zero in TS sources).
- [ ] Non-blocking "success/failure" `alert()`s became toasts, not modals.
- [ ] `build:ts`, `typecheck`, `js_module_index --check` clean; unit passes.
