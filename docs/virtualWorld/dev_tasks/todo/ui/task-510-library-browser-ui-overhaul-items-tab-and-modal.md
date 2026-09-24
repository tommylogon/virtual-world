---
type: task
status: todo
area: ui
priority: medium
---

# task-510: Library browser UI overhaul (items tab and modal)

**Filed:** 2026-09-24
**Related:** 509, 508, 506

## Goal

Modernize the Library Browser's **items pane**. It is the primary authoring surface
for 505 library items, and it is currently a fixed 800px modal built almost
entirely out of inline styles, with a 300px scrolling list and a 240px editor —
it does not scale and it does not help the author find what matters.

## Evidence

- `templates/index.html:483-527` — `width:800px` modal; every control carries
  inline `style=` (search, sort, list cap `max-height:300px`, editor
  `min-width:240px`); eight flat tabs share the header; the list is a plain
  `#item-lib-list` div, not paginated or virtualized.
- `static/js/item-library.js:109-190` — `renderList` builds rows and badges with
  inline styles (`:155-186`); filtering is a substring match over name/description/
  tags only (`:114-120`); sort is name/type/recent only (`:123-128`).
- `_getItemType` (`:81-97`) already knows a type taxonomy that the UI never
  surfaces as a filter.
- There is **no CSS for the library** — `static/css/` holds only `style.css` and
  `soak.css` (linked at `templates/index.html:23-26`), and `library-modal` /
  `item-lib-*` appear in no stylesheet.
- The items pane deliberately reuses the item-library IDs for backward
  compatibility (`templates/index.html:500`), so IDs/classes must be preserved.

## Design / Acceptance

- **Stylesheets, not inline.** Move the library's inline styles into
  `static/css/style.css` (or a new `static/css/library.css` linked in
  `templates/index.html`), keeping the existing element ids (`item-lib-list`,
  `item-lib-editor`, `item-lib-search`, `lib-sort`, `lib-item-count`,
  `place-items-btn`) and reusing design tokens (`--bg-*`, `--border`, `--text-*`).
- **A layout that scales.** Wider and/or resizable modal, a list that fills the
  available height instead of `max-height:300px`, and a resizable split between
  list and editor so the editor is not pinned at 240px.
- **A list that scales to 505+ items.** Virtualize or page the list; search,
  sort and selection stay responsive. Sticky search/sort/filter header.
- **Filtering that helps authoring**, not just substring search:
  - by type (reuse `_getItemType`),
  - by tag,
  - and presets that tie into the current work: `No triggers`, `Edible/drinkable`,
    `Has contents`, `Missing depletion` (once task-508 defines it).
- **Multi-select bulk bar** (shared with task-509): "N selected" with bulk actions,
  visible without entering the placement flow.
- **Better rows**: consistent type icon + colour, trigger/contents/uses badges,
  hover/selected/focus states all in CSS, and a readable name/description
  hierarchy.
- **Keyboard + states**: ↑/↓ to move, Enter to open, Escape to close, visible focus
  rings; explicit empty, loading and error states.
- **Accessibility**: labels on the search/sort controls, `role="listbox"`/`option`
  or an equivalent pattern for the list, focus trap while the modal is open.
- **No regressions**: `openForRoom` placement, `📌 Place in Area`
  (`place-items-btn`), `📋 Sync to Library`, and the other library tabs behave
  exactly as before.

## Non-goals

- Rewriting the item editor's logic or the trigger/contents editors.
- Changing the library data model or the backend.
- The other tabs (characters, areas, traits, conditions, behaviours, tags, ways)
  — visual consistency only, no rework.

## Verification

- `node tools/unit/run.cjs`, `npm run lint`, `npm run typecheck`,
  `node --check` on changed modules, and `python tools/js_module_index.py --check`
  (any new JS module needs its `@module`/`@contributes` header).
- Manual: open the library over 505 items — scroll/search/filter stay smooth,
  a filtered "No triggers" view is one click, and the placement flow still works.
