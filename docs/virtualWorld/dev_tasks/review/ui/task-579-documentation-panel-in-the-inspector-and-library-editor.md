---
type: task
status: review
area: ui
priority: medium
blocked_by: [task-578]
---

# task-579: Documentation panel in the inspector and library editor

**Filed:** 2026-09-28
**Related:** task-575, task-521
**Blocked by:** task-578 (the resolver route)

## Goal

Surface the documentation covering the selected feature in the authoring UI, next to the
panels an author already sees.

## Why here and not earlier

The links already exist and are already checked — 152 of 179 JS modules carry an `@docs`
header, and `docs/design/js-module-index.md` is a generated Docs column. They are
invisible because nothing renders them, and this is the task that renders them. Adding a
panel before task-578 would mean shipping a panel that can only link to a hardcoded list.

## Placement

- **Inspector** — `static/js/inspector/panel.js` is the 78-line container; the views are
  the 15 files beside it. The panel belongs in the container, so every node type gets it,
  rather than being hand-added to 15 views.
- **Library editor** — `static/js/item-library.js`, next to the existing trigger-helper
  and validator affordances.
- Do not duplicate the help-center pattern wholesale. `static/js/ui/help-center.js` is
  tips and tours, aimed at a player or a first-time author; this is reference material for
  the thing currently selected. Reuse the modal and the seen-tracking if it fits, but they
  are not the same feature.

## Design

- Selecting a node or item calls the resolver once and renders the result. No polling, no
  re-fetch on every keystroke.
- **"No documentation" is a first-class state** and must render as a quiet, honest
  "this has no page yet", not an error or an empty box. Most of the 505 library items
  will be in that state at first.
- Render the page title, a one-line summary, and an open action. Do **not** inline the
  whole page body — the inspector is already dense, and a wall of markdown inside a
  property panel makes the panel unusable.
- In the inspector, resolve by the node's id (task-577). Where a node is a world object
  rather than a library node, resolve by the module that renders it, so an area still
  gets *something* useful.

## Resolution (2026-10-02)

- New `static/js/inspector/doc-panel.js` (`window.DocPanel`): pure view-model
  (`format`, `requestUrl`, `selectionForNode`) plus a DOM paint. It fetches the
  resolver once per selection and renders title / summary / open action, or the
  quiet "No documentation yet.".
- `inspector/panel.js` appends `DocPanel.section()` to **every** render, so all
  fifteen node views get it with no per-view edit.
- `inspector.js` reports the selection: a materialised node resolves by
  `properties.library_id`, otherwise by the view module that renders its type
  (`area-view`, `item-view`, `way-view`, `agent-view`); `hide()` resets it.
- `item-library.js` shows a resolution preview under its Documentation field for
  the selected entry id.
- Wired: script tag in `templates/index.html`, load line in `tools/unit/run.cjs`,
  module contract header, regenerated `js-module-index.md`.

## Acceptance

- [x] The panel is appended through `panel.js`, so it reaches every node type
      without per-view edits.
- [x] The resolver is called once per selection (`setSelection` -> one `_load`);
      `section()` only repaints from cached state.
- [x] An empty result renders the quiet empty state; a resolver failure is
      caught and shown as the same empty state (no toast, no throw).
- [x] `node tools/unit/run.cjs` covers the empty and populated states
      (`tools/unit/test_doc_panel.js`, 6 tests) — **491 passed**.
- [x] New module has the contract header; script tag, run.cjs line, and
      `python tools/js_module_index.py --check` clean (178 documented).
- [x] `npm run lint` and `npm run typecheck` clean.
- [~] **Live-browser pass pending.** The selection->title/summary/open behaviour
      is implemented and unit-tested but has not been exercised in a running
      browser in this worktree; task-579 must not be called done until it has.
      (`VW_PORT=4460 python app.py`, then select an item with a `docs` link.)

## Non-goals

- Editing documentation from inside the editor. Authoring prose is a different tool and
  this panel is a doorway to it, not a replacement for it.
- Search across the corpus (see task-578's non-goals).
