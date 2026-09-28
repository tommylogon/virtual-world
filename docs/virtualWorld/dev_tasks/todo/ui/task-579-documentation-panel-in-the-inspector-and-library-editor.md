---
type: task
status: todo
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

## Acceptance

- Selecting a node with a `docs` link shows the page title, summary, and a working open
  action; selecting one without shows the "no page yet" state.
- The panel appears for every node type without per-view edits.
- The resolver is called once per selection, not per render.
- An empty result never produces an error toast, a console exception, or a broken
  layout.
- `node tools/unit/run.cjs` covers the empty state and the populated state.
- New module: `@module` / `@contributes` header, a script tag in `templates/index.html`,
  a line in `tools/unit/run.cjs`, and `python tools/js_module_index.py --check` clean.
- `npm run lint` and `npm run typecheck` clean.

## Non-goals

- Editing documentation from inside the editor. Authoring prose is a different tool and
  this panel is a doorway to it, not a replacement for it.
- Search across the corpus (see task-578's non-goals).
