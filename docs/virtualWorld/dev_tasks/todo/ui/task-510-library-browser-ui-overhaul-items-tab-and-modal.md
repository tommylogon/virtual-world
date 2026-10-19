---
type: task
status: todo
area: ui
priority: medium
wiki: "[[UI Reference/Rendering & UI Modules]]"
---

# task-510: Library browser UI overhaul (items tab and modal)

**Filed:** 2026-09-24
**Related:** 509, 508, 506

## What

Modernize the Library Browser's **items pane**. It is the primary authoring surface
for the library items, and it is currently a fixed 800px modal built almost
entirely out of inline styles, with a 300px scrolling list and a 240px editor —
it does not scale and it does not help the author find what matters.

> **Counted 2026-10-02:** `GET /api/library/items` returns **1,999** items —
> 480 tagged food, 362 tools, 151 containers, 803 with triggers. The 505 in this
> task (and in the acceptance text below) was accurate when filed on 2026-09-24
> and is now roughly 4× stale, in the direction that hurts every sizing and
> virtualization requirement listed here.
>
> **Mockup:** `docs/design/mockups/library-browser-react.html` — a self-contained
> React design of the items pane (type chip bar with live counts, quality
> presets, multi-select bulk bar, resizable split, keyboard + states). Verified
> in a browser; it is a design artifact, not application code.

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
- **A list that scales to 505+ items.** (Now 1,999 — see the note above.) Virtualize
  or page the list; search, sort and selection stay responsive. Sticky
  search/sort/filter header.
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

## Steps to verify

- `node tools/unit/run.cjs`, `npm run lint`, `npm run typecheck`,
  `node --check` on changed modules, and `python tools/js_module_index.py --check`
  (any new JS module needs its `@module`/`@contributes` header).
- Manual: open the library over 505 items — scroll/search/filter stay smooth,
  a filtered "No triggers" view is one click, and the placement flow still works.
  (Re-measure against 1,999 items, not 505.)

## Also surfaced by the audit, not yet ticketed

Counted from the same response while designing the mockup — each of these is a
data-layer finding, not a UI one:

- **294 of 1,999 items (15%) repeat a tag.** `acorn_coffee` is
  `drink,drink,nut,forage`; `adze` is `tool,tool,metal,wooden`. Any tag filter,
  tag badge or tag count built on this data must dedupe first, or the counts
  disagree with the list they claim to describe.
- **3 items have no description at all**, which is why an explicit
  "missing description" filter is a real authoring pass rather than a nicety.
- **Every filter is single-select except the presets.** Type and quality compose;
  the mockup keeps that composition rather than adding a query language.

## Why

TODO

## How

TODO

## Acceptance

- [ ] TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: 📚 Library Browser → Items tab. The item list and editor share a resizable split; type chips, quality presets, multi-select bulk actions, and the existing placement flow belong on this surface.

Current availability: The task's 2026-10-02 count measured 1,999 items; the React mockup is a design artifact, not application code. The items-pane overhaul remains planned.

Live steps when available:
1. Open the Items tab with the current 1,999-item library, resize the split, then search for a known item by display name and ID.
   - expected: the list remains responsive while scrolling/filtering, the row result and detail editor stay synchronized, and neither pane is clipped at a narrow window width.
2. Use the type chips to filter to food, then select “No triggers”.
   - expected: counts update against the filtered 1,999-item library and the no-trigger filter is reachable in one click.
3. Select several items and use one bulk action; then open an item and inspect its quality controls.
   - expected: the multi-select bar names the selected count, the quality presets apply to the intended items, and the editor shows the selected record.
4. Place one library item into a scratch world and return to the Library Browser.
   - expected: the existing placement workflow still resolves the chosen item and the library record itself is not mutated by placement.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.
