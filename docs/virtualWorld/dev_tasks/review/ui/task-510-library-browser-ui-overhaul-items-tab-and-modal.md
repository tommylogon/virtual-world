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
entirely out of inline styles, with a 300px scrolling list and a 240px editor -
it does not scale and it does not help the author find what matters.

> **Counted 2026-10-02:** `GET /api/library/items` returns **1,999** items -
> 480 tagged food, 362 tools, 151 containers, 803 with triggers. The 505 in this
> task (and in the acceptance text below) was accurate when filed on 2026-09-24
> and is now roughly 4× stale, in the direction that hurts every sizing and
> virtualization requirement listed here.
>
> **Mockup:** `docs/design/mockups/library-browser-react.html` - a self-contained
> React design of the items pane (type chip bar with live counts, quality
> presets, multi-select bulk bar, resizable split, keyboard + states). Verified
> in a browser; it is a design artifact, not application code.

## Evidence

- `templates/index.html:483-527` - `width:800px` modal; every control carries
  inline `style=` (search, sort, list cap `max-height:300px`, editor
  `min-width:240px`); eight flat tabs share the header; the list is a plain
  `#item-lib-list` div, not paginated or virtualized.
- `static/js/item-library.js:109-190` - `renderList` builds rows and badges with
  inline styles (`:155-186`); filtering is a substring match over name/description/
  tags only (`:114-120`); sort is name/type/recent only (`:123-128`).
- `_getItemType` (`:81-97`) already knows a type taxonomy that the UI never
  surfaces as a filter.
- There is **no CSS for the library** - `static/css/` holds only `style.css` and
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
- **A list that scales to 505+ items.** (Now 1,999 - see the note above.) Virtualize
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
  - visual consistency only, no rework.

## Steps to verify

- `node tools/unit/run.cjs`, `npm run lint`, `npm run typecheck`,
  `node --check` on changed modules, and `python tools/js_module_index.py --check`
  (any new JS module needs its `@module`/`@contributes` header).
- Manual: open the library over 505 items - scroll/search/filter stay smooth,
  a filtered "No triggers" view is one click, and the placement flow still works.
  (Re-measure against 1,999 items, not 505.)

## Also surfaced by the audit, not yet ticketed

Counted from the same response while designing the mockup - each of these is a
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

The Library Browser is the authoring surface for 2,208 item records, and it is
still the shape it had when the library held a few hundred. Everything is
inline-styled into a fixed 800px modal, the list is a plain div with a
`max-height:300px` cap and no pagination, and eight flat tabs share one header
strip. The list is a substring match over name, description and tags; the type
taxonomy that `_getItemType` already knows is never surfaced as a filter.

That is not a cosmetic complaint. The two data facts the card measured are
what make it a real gap: 294 items repeat a tag, so any count or badge built on
the raw tag list disagrees with the list it claims to describe, and 3 items have
no description at all, so "find me the undescribed items" is a genuine
authoring pass that the current filter cannot express. An author with 2,208
records and no way to filter by type, no way to see which records still need
descriptions, and a list that renders every row at once is the bottleneck.

## How

Four changes, in the order they unblock each other:

1. **Move the inline styles into a stylesheet.** The library's controls carry
   inline `style=` attributes and the `item-lib-*` / `library-modal` classes
   appear in no stylesheet at all. Extract them to `static/css/style.css` or a
   new `static/css/library.css`, using the existing design tokens (`--bg-*`,
   `--border`, `--text-*`). The element ids (`item-lib-list`, `item-lib-editor`,
   `item-lib-search`, `lib-sort`, `lib-item-count`, `place-items-btn`) must be
   preserved - the items pane deliberately reuses the item-library ids for
   backward compatibility.
2. **Make the modal scale.** Widen and/or make the 800px modal resizable, let
   the list fill the available height instead of capping at 300px, and make the
   list/editor split resizable so the editor is not pinned at 240px.
3. **Make the list scale.** Virtualize or paginate: 2,208 rows with inline
   row styles is a rendering cost on every filter keystroke.
4. **Expose the taxonomy the code already has.** `_getItemType` knows the item
   type taxonomy; surface it as a filter alongside the existing type/quality
   composition, and add a "missing description" filter for the 3 undescribed
   items. Any tag count or badge must dedupe the repeated tags first, or the
   numbers will not match the list.

The composition rule is deliberate: every filter stays single-select except the
existing presets, and type/quality keep composing. This is a query language
that is not wanted.

## Acceptance

- [ ] The library's inline `style=` attributes are gone from
      `templates/index.html` and `static/js/item-library.ts`; the rules live in
      a stylesheet and use the existing design tokens.
- [ ] The modal is wider or resizable, the list fills the available height
      rather than `max-height:300px`, and the list/editor split is resizable.
- [ ] The list virtualizes or paginates and stays responsive while filtering
      2,208 items.
- [ ] The item type taxonomy from `_getItemType` is exposed as a filter, and
      type and quality still compose.
- [ ] A "missing description" filter surfaces the 3 undescribed items.
- [ ] Every tag count and badge dedupes repeated tags, so a count matches the
      list it describes.
- [ ] The existing element ids (`item-lib-list`, `item-lib-editor`,
      `item-lib-search`, `lib-sort`, `lib-item-count`, `place-items-btn`) and
      the placement flow still work.

## Files

- `templates/index.html` - the modal markup and its inline styles (`:887` is the
  `width:800px` container; the tab strip and controls are in the same block)
- `static/js/item-library.ts` - `renderList` and the row/badge building, the
  filter and sort logic, `_getItemType` (the taxonomy to surface)
- `static/css/style.css` (or a new `static/css/library.css`) - where the
  extracted rules go; `library-modal` and `item-lib-*` currently have no rules
  anywhere

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

## Reconnaissance (2026-10-20) - still valid

Re-checked on 2026-10-20. The items pane is still the fixed 800px inline-styled modal:

- `templates/index.html:887` still reads `<div class="modal-content" style="width:800px;">`.
- `data/library/items` now holds 2,209 JSON files (was 1,999 at the 2026-10-02 count) - the sizing/virtualization pressure grew.
- No `static/css/library.css` exists; `static/css/` holds only `style.css` and `soak.css`.

Verdict: card accurate; item count drifted upward (2,209 vs 1,999). Kept in todo.
