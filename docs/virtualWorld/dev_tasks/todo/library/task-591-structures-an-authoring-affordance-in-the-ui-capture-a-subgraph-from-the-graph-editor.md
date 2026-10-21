---
type: task
status: todo
area: library
priority: high
related: [task-357, task-291]
wiki: "[[Library System/Library System Overview]]"
---

# task-591: Structures - an authoring affordance (capture a subgraph from the graph editor)

**Filed:** 2026-09-29
**Related:** task-357, task-291

<!-- deps:start -->
**Related:** [[task-357-structure-save-load-connected-areas]], [[task-291-unified-library-api-and-data-driven-catalogs]]
<!-- deps:end -->

## What

**Surviving scope, after the 2026-10-20 re-measurement.** The engine, the five
routes, the capture dialog and the browse / materialize / delete browser all
landed with task-357 (commit `f2c34acb`, 2026-09-22). What did **not** land is
the thing this card was filed for: a way in from the **live** graph editor.

- The `📦 Save as Structure…` item was added to `GraphManager._showContextMenu`
  (`static/js/graph-manager.ts:796`, the item at `:814`), a method with **zero
  call sites**. The live right-click path is
  `static/js/graph/network-manager.ts:244` → `GraphEventHandlers.onContext`
  (`static/js/graph/event-handlers.ts:127`) → `GraphContextMenu.showContextMenu`
  (`static/js/graph/context-menu.ts:27`), and its area branch
  (`context-menu.ts:38-47`) carries no structure item and `ctxAction` has no
  `save_structure` case. So `VW.structures.openSaveDialog` is unreachable from
  the running UI.
- No template has ever been committed. `data/library/structures/` does not exist
  on disk, `git ls-files data/library/structures` returns 0 files, and
  `git log --all --diff-filter=A -- "data/library/structures/*"` is empty.

So the remaining work is: put the capture affordance on the live context menu
(or give the author another live route into `openSaveDialog`), and commit a
first real template so the library is not empty on `master`.

## Verified state (2026-09-29, re-measured 2026-10-20)

- **Engine, complete.** `collect_structure` (`engine/structures.py:153`) captures from a live graph with a fixpoint that pulls in items reachable through area / surface / container and any residents inside. `materialize_structure` (`:310`, was `:309`) instantiates it, remapping every reference (`_remap_refs:73`, `_unique_id:94`, `_deterministic_suffix:89`) so two instances cannot collide. `summarize_structure` (`:292`, was `:291`) reports `{areas, ways, items, residents}`.
- **API, complete.** `/api/structures` (list), `/preview`, `/save`, `/<id>/materialize`, `/<id>` (delete). Registered in `routes/structures.py:16-34`, handlers in `routes/structures_ops.py`.
- **Storage, already per-entry.** `save_registry` writes `data/library/structures/<id>.json` (`routes/helpers.py:304-319`, via `_registry_subdir` at `:272-277`) - no shape decision is outstanding here, contrary to what a first reading of `STRUCTURES_REGISTRY = "structures.json"` suggests.
- **UI, present but the capture entry point is dead.** `static/js/structures.ts` (255 lines, `structures.js` until the 2026-10-02 TypeScript conversion) holds the save dialog and the browse / materialize / delete browser. It is live for browsing: `templates/index.html:210` puts `📦 Structures` in the top menu and calls `VW.structures.openBrowseDialog()`, and `templates/index.html:1485` loads the script. The **capture** route is not live: the `📦 Save as Structure…` item lives in `GraphManager._showContextMenu` (`static/js/graph-manager.ts:796`, item at `:814`), which has zero call sites. The library browser still has no structures pane: the `LibraryTab` union (`static/js/library-browser.ts:64`) lists 11 tabs and the refresh list (`:334`) renders 10, with `structures` in neither.
- **No content.** `data/library/structures/` does not exist on disk, `git ls-files data/library/structures` returns 0 files, and `git log --all --diff-filter=A -- "data/library/structures/*"` is empty: no structure has ever been committed, so `list` returns nothing and `materialize` can only ever 404.

## The gap

Capture is the interesting direction and it needs the graph editor: the author has a subgraph in front of them - a tavern with its tap room, a shrine with its courtyard, a bandit camp - and wants it reusable. Today the only way to get one is to hand-build the JSON, which is the thing the library exists to stop.

## Open questions

1. **Where does capture start?** A context-menu action on selected area nodes in the graph canvas, or a button in the area inspector that captures the area and everything reachable? The engine's boundary rule (no far-side area node, or far side outside the selection) is the interesting part and the UI has to express it before the author presses the button, not after.
2. **Preview before saving.** `/api/structures/preview` exists. Does the flow show `{areas, ways, items, residents}` and the boundary before it writes, given that `save_registry` never deletes and a wrong capture lingers?
3. **Which pane?** A `structures` library pane would make them browsable, but triggers set the precedent that a type used only by one tool needs no pane - the trigger graph editor's blueprint picker. Structures is captured in the graph editor, so a picker there may be the honest answer.
4. **Does `task-357` already own part of this?** It is in review and covers capture + materialize end to end. If its acceptance is met by the engine alone, this task is the UI half; if it never claimed a UI affordance, say so in its file rather than leaving two tasks implying the same work.

**Answered 2026-10-20.** task-357 claims the UI affordance explicitly: its card
lists "**UI** - `static/js/structures.js` - Save dialog (name, include
items/residents, live preview of counts + boundary exits) and a Structures
browser with Materialize/Delete" and "Area right-click menu gains `📦 Save as
Structure…`". It implemented the dialog and the browser, but the right-click
item went into a method that is not on the live path, so the half it claimed is
the half that did not land. Questions 1 to 3 were answered by the
implementation: capture starts from an area node's context menu (question 1),
the preview runs before the write (question 2), and the picker is a top-menu
`📦 Structures` browser rather than a library pane (question 3) - the
`structures` registry type is in `REGISTRY_TYPES`
(`routes/library_ops.py:27`), but the library browser has no structures tab
(`static/js/library-browser.ts:64`, `:334`).

## Acceptance

Met by task-357 (commit `f2c34acb`, 2026-09-22), re-verified 2026-10-20:

- [x] The capture writes one `data/library/structures/<id>.json` file per
      template, and `save_registry` is the only write path
      (`routes/structures_ops.py:86` → `routes/helpers.py:304-319`).
- [x] The preview runs **before** anything is written, and shows the
      `{areas, ways, items, residents}` summary plus the boundary-exit count:
      `openSaveDialog` calls `runPreview()` on open
      (`static/js/structures.ts:189`) and renders the counts at `:161-164`;
      `Save` is a separate button at `:176`.
- [x] A structure can be materialized twice into the same world with **no id
      collision**, proved by a test that exercises `_deterministic_suffix`
      (`engine/structures.py:89`): `tests/test_structures.py::test_collision_remaps_ids_but_keeps_names`
      materializes into the *same* world, so `_unique_id` (`:94`) fires.
      14 tests in `tests/test_structures.py`.
      *Correction:* the original wording asked for the ids **and the names** to
      differ. task-357 settled the opposite on purpose - a collision remaps
      ids only and never renames a node (`engine/structures.py:14-18`) - and the
      test asserts two areas both called "Hall". The criterion was wrong as
      written; the wiring-stays-intact half is what the test proves.
- [x] Deleting a template from the UI removes the file via `delete_registry_entry`
      and leaves existing materialized instances in the world alone: the `🗑`
      button in the Structures browser (`static/js/structures.ts:232-235`) calls
      `DELETE /api/structures/<id>` → `delete_registry_entry`
      (`routes/helpers.py:322-333`), which unlinks one file and touches nothing
      in the world.

Still open:

- [ ] **An author can capture a subgraph from the live graph editor.** The
      `📦 Save as Structure…` item must exist on the live right-click path
      (`static/js/graph/context-menu.ts`, the area branch at `:38-47`) and
      `ctxAction` must handle `save_structure` by calling
      `VW.structures.openSaveDialog(nodeId, name)`. Today the item is only in
      `GraphManager._showContextMenu`, which nothing calls.
- [ ] **A first real template is captured and committed**, so
      `data/library/structures/` is not empty on `master`.
- [ ] The preview **names** the boundary exits (which ways, and where they
      lead) instead of only counting them. `POST /api/structures/preview`
      already returns the detail (`routes/structures_ops.py:63`); the dialog
      shows only the number (`static/js/structures.ts:164`).

## Why

A structure template is only worth having if an author can *make* one without
hand-writing JSON. The engine, the routes and the dialog already exist, so the
gap is one click on the wrong code path plus one committed example: without
them the feature is a curl script that ships a backend nobody can reach.

## How

1. Move the capture item onto the live menu. `static/js/graph/context-menu.ts`
   owns the area branch (`showContextMenu`, `:38-47`); add the
   `📦 Save as Structure…` row there and a `save_structure` case in
   `ctxAction` (`:92`) that calls `VW.structures.openSaveDialog(nodeId, name)`.
   The item already exists in `GraphManager._showContextMenu`
   (`static/js/graph-manager.ts:796-814`, handler at `:874-875`); either move
   it or make that method a thin delegate, so there is one menu, not two.
2. Make the preview name the boundary. `POST /api/structures/preview` returns
   `boundary_exits` as a list of `{way, area, direction, name}`
   (`routes/structures_ops.py:63`, built in `engine/structures.py:202-208`);
   render the names, not just the count.
3. Capture a first template in a scratch world (two connected areas, their way,
   an item, a resident), save it, and commit
   `data/library/structures/<id>.json` so `master` is not empty.

## Steps to verify

1. Right-click an area node in the graph canvas.
   - expected: the context menu shows `📦 Save as Structure…`.
   - observed: (2026-10-20) the live menu does NOT show it. The item is in
     `GraphManager._showContextMenu` (`static/js/graph-manager.ts:814`), which
     has zero call sites; the live path is `network-manager.ts:244` →
     `GraphEventHandlers.onContext` → `GraphContextMenu.showContextMenu`
     (`static/js/graph/context-menu.ts:38-47`).
2. With the item live, open it and read the preview before pressing Save.
   - expected: the `{areas, ways, items, residents}` summary and the boundary
     exits are shown, and no file exists yet.
   - observed: (2026-10-20) the dialog's preview is correct and runs on open
     (`static/js/structures.ts:161-164`, `:189`); it is unreachable from the UI.
3. Save, then browse `📦 Structures` from the top menu.
   - expected: one `data/library/structures/<id>.json` entry appears and its
     summary matches the capture.
   - observed: (2026-10-20) the browse / materialize / delete half is live from
     `templates/index.html:210`; there is no captured template to list, because
     `git ls-files data/library/structures` returns 0 files.
4. Materialize the template twice into the same world and inspect both
   instances.
   - expected: both instances keep their internal wiring, and their ids differ.
   - observed: (2026-10-20) proved by
     `tests/test_structures.py::test_collision_remaps_ids_but_keeps_names`,
     which materializes into the same world.

## Files

- `static/js/graph/context-menu.ts` (the live menu - the capture item belongs here)
- `static/js/graph-manager.ts` (the dead `_showContextMenu` copy)
- `static/js/structures.ts` (the capture dialog and the Structures browser)
- `engine/structures.py` (capture, summarize, materialize)
- `routes/structures_ops.py`, `routes/structures.py` (the five endpoints)
- `tests/test_structures.py` (14 tests)
- `data/library/structures/` (to be created: the first committed template)

## Browser UI and intended live verification

Intended UI home: Graph editor → select the intended area/way/item/resident subgraph → **Capture Structure** → review the boundary and `{areas, ways, items, residents}` summary → Apply to the Structures library.

Current availability: re-measured 2026-10-20, the backend endpoints, the capture
dialog and the Structures browser exist. The **capture affordance is not
reachable from the graph editor** (the menu item sits in an uncalled method),
and `data/library/structures/` has never held a committed template, so the
browse dialog has nothing to list.

Live steps when available:
1. In a scratch world, right-click the root area node and invoke **Save as Structure…**.
   - expected: a preview shows exactly the captured residents and internal edges, names the boundary connections, and writes no file before Apply.
2. Apply the capture, then open `📦 Structures` from the top menu and preview the new template.
   - expected: one `data/library/structures/<id>.json` entry appears and its preview matches the captured areas, ways, items, and residents.
3. Materialize the template twice into the same world and inspect both instances in the graph.
   - expected: both instances retain internal wiring but have distinct IDs; their display names stay the same (a collision remaps ids only, by design).
4. Delete the template from the Structures browser, then inspect the two materialized instances.
   - expected: only the template file is removed; both world instances remain unchanged.

This section is not a claim that planned UI exists or works today.

## Reconnaissance (2026-10-20) - partly done, still open

Re-checked on 2026-10-20 against the code, not the card. The newer work that
touches this feature is **task-357** (commit `f2c34acb`, 2026-09-22), whose card
lists the UI as implemented. The code agrees with the card about the dialog and
the browser, and disagrees with it about the right-click menu.

What landed (task-357):

- `static/js/structures.ts` exists, 255 lines, 34 matches for "structure".
  `openSaveDialog` (`:122`) and `openBrowseDialog` (`:193`).
- The browse half is **live**: `templates/index.html:210` renders
  `📦 Structures` in the top menu calling `VW.structures.openBrowseDialog()`;
  `templates/index.html:1485` loads `/static/js/structures.js`;
  `static/js/main.ts:95` publishes `VW.structures`.
- The capture half is **dead**: `📦 Save as Structure…` is at
  `static/js/graph-manager.ts:814` inside `GraphManager._showContextMenu`
  (`:796`), whose only repo-wide references are its own definition
  (`graph-manager.ts:796`, `graph-manager.js:716`). The live right-click path
  is `static/js/graph/network-manager.ts:244`
  (`network.on("oncontext", ...)`) → `static/js/graph/event-handlers.ts:127`
  → `static/js/graph/context-menu.ts:27`, and that module contains **0**
  matches for "structure" and no `save_structure` case in `ctxAction` (`:92`).
  So `VW.structures.openSaveDialog` has no live caller.
- Backend and tests: `routes/structures.py` registers the five endpoints,
  `routes/structures_ops.py` holds the handlers, `tests/test_structures.py`
  has 14 tests including the same-world collision test.

Evidence counts: 1 capture dialog module, 1 live browse entry point
(`templates/index.html:210`), 1 dead capture entry point
(`graph-manager.ts:814`), 0 structure matches in the live context menu, 14
structure tests, 0 committed templates
(`git ls-files data/library/structures` = 0; `git log --all --diff-filter=A --
"data/library/structures/*"` is empty).

Facts that drifted since the card was written:

- "Nothing in `static/` or `templates/` mentions a structure template" was
  already false when the card was filed on 2026-09-29: `static/js/structures.js`
  was created on 2026-09-22 and is present in the tree at the filing commit
  `347d539f`. The card's *conclusion* (capture is not reachable from the graph
  editor) still holds, for a different reason.
- `materialize_structure` moved `:309` → `:310`; `summarize_structure` moved
  `:291` → `:292`. The other cited lines (`collect_structure:153`,
  `_remap_refs:73`, `_unique_id:94`, `_deterministic_suffix:89`) are unchanged.
- The library browser has 11 tab types and renders 10, not the eight the card
  lists, and still has no structures tab.

Verdict: PARTLY_DONE. Four of the five original acceptance criteria are met
(the write path, the pre-write preview, the collision-free double
materialization with its test, and the delete-from-UI). The card is kept in
todo with its scope rewritten to what is left: the live capture entry point,
the first committed template, and naming the boundary exits.
