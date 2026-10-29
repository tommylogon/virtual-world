---
type: task
status: review
area: ui
priority: medium
wiki: "[[UI Reference/Rendering & UI Modules]]"
---

# task-751: Replace native alert/confirm/prompt popups with a promise-based in-app dialog

**Filed:** 2026-10-09
**Related:** bug-533 (silent no-op), shared/diff-modal

## What

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

## How

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

## Resolution (2026-10-09)

Built the reusable module and piloted it; the 48-site bulk migration remains.

- `static/js/shared/dialog.ts` → publishes `window.Dialog` (also `VW.dialog` via
  `main.ts`). Promise-based `alert(opts)`, `confirm(opts) → boolean`,
  `prompt({fields}) → Record<string,string>|null`. One overlay, focus-trapped:
  `Esc` and backdrop cancel, `Enter` submits, `Tab` cycles in the card.
  Registered: script tag in `templates/index.html`, `@module/@contributes/@docs`,
  `js_module_index --write`.
- **Blueprint pilot:** `trigger-graph._saveBlueprint` now opens one
  `dialog.prompt` with name + description (was two native `prompt()`s), the
  toolbar button is relabelled **💾 Save to library**, and the success/failure
  `alert()`s became `toastInfo`/`toastError`.
- Guard: `tools/unit/test_dialog.js` (API surface, dismissal rules, and that the
  blueprint save routes through `dialog.prompt`).

## Acceptance

- [x] `VW.dialog` exists (confirm / prompt / alert), promise-based, focus-trapped,
      `Esc`/`Enter`/backdrop handled, and covered by unit tests.
- [x] The blueprint save uses it: one modal with name + description; the toolbar
      button makes clear it saves to the library.
- [ ] **Not met:** ~48 native `alert`/`confirm`/`prompt` call sites across ~20 files
      remain to migrate (`graph-manager.ts`, `library-browser.ts`, `trigger-graph.ts`,
      `ui/saveload-view.ts`, ...). The module is ready; this is the mechanical bulk pass.
- [x] The pilot's success/failure `alert()`s became toasts, not modals.
- [x] `build:ts`, `typecheck`, `js_module_index --check` clean; unit passes (636).

## Why

TODO

## Browser UI and intended live verification

Intended UI home: Shared in-app dialog at existing alert/confirm/prompt call sites; use blueprint save as the representative path.

Current availability: The reusable dialog and blueprint flow exist; many native popup call sites remain to migrate.

Live steps when available:

1. Open blueprint save and test confirm, cancel, Escape, Enter, and backdrop behavior.
   - expected: One themed dialog collects fields, traps focus, returns the documented promise result, and preserves cancellation.

2. Trigger a representative migrated alert/confirm and inspect focus after closing.
   - expected: No browser-native popup appears and focus returns to the invoking control.

This section defines the intended access point and acceptance path. It is not a claim that the UI or complete behavior exists or works today; Current availability records the present state, and these steps describe how to verify the intended behavior when it is available.
## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO

## Audit note (2026-10-16)

Moved from inprogress back to todo: it was not being worked. No uncommitted changes in the working tree or in any of the eight git worktrees touch this card's files, and nobody is editing it. 4 of 5 acceptance boxes checked. static/js/shared/dialog.ts and the blueprint pilot are committed (c5034257, 2026-10-09). The open box is the bulk migration of about 48 native alert/confirm/prompt call sites, and nothing has touched it since.
