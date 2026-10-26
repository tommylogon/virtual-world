---
type: task
status: review
area: ui
priority: medium
related: [task-397, task-398, task-528, task-531, task-574]
wiki: "[[UI Reference/Rendering & UI Modules]]"
---

# task-592: One hierarchy: scopes at the top of the Outline tab

**Filed:** 2026-09-29
**Related:** task-397, task-398, task-528, task-531, task-574

<!-- deps:start -->
**Related:** [[task-397-world-scope-hierarchy-and-projection]], [[task-398-deterministic-structure-generation]], [[task-528-assign-selected-areas-to-a-scope-promote-a-selection-to-a-placed-feature]], [[task-531-graph-workspace-contextual-scope-bar-breadcrumb-counts-generate-clear]], [[task-574-test-guide-the-2026-09-27-worldpainter-session]]
<!-- deps:end -->

## What

**Surviving scope, after the 2026-10-20 re-measurement.** The headline of this
card landed on 2026-09-30 in commit `55b9f749` ("one hierarchy, and a map that
names its places"): the scope tree is now the top of the Outline tab, the graph
no longer renders it at the bottom, a scope row loads its scope, and an unmade
row offers the honest jump into the WorldPainter.

What did **not** land is the part that makes it *one* tree. The area rows are
still a flat, separately sorted list under the scope tree
(`static/js/graph/tree-view.ts:94`, rendered at `:154-156`): there is no
world → scope → area fold, no area nested under the scope that holds it, and no
fallback row for areas that belong to no scope.

## The problem, precisely

*This section describes the state before 2026-09-30; the re-measurement is in
the Reconnaissance section at the bottom of this card.*

The scope tree (`static/js/graph/scope-tree.js`, task-397 step 4) and the Outline tab
(`static/js/graph/tree-view.js`) are **not** duplicates, and it is worth saying why
before changing anything:

- The Outline tab is a tree of **areas** in the loaded state - descriptions, exits,
  items, who is present, temperature/light/air - read from `worldState.areas`.
  Before the change, `tree-view.js` contained **zero** references to scopes: it
  could not tell you `goblin camp` exists, let alone that it has never been
  generated. *Since 2026-09-30 it does reference scopes* - it mounts the scope
  tree above the area list (`static/js/graph/tree-view.ts:162-164`), names the
  loaded scope in the heading (`:83-85`) and copies the scope hierarchy to the
  clipboard (`:203-229`).
- The scope tree is a tree of **scopes** from `GET /api/world/scopes?flat=1` -
  ids, states, area/item/character counts, parent and depth. It is the only thing
  that reports `unmade`.

Different subjects, different endpoints, disjoint data. The problem is everything
*around* that:

1. **Scope navigation is in three places**: the `Loaded world scope` dropdown, the
   `scope-breadcrumb` (task-531), and the scope tree. Three routes to one place, and
   **none of them in the left sidebar** - which is where navigation lives in this app
   and where a reader looks first.
2. **Two collapsible trees with counts, on screen at once**, on different subjects,
   in different halves of the UI. They look like the same widget, so a reader has to
   learn which one to trust. That is a real cost even though nothing is duplicated.
3. **The diagnosis and the fix are in different windows.** The scope tree is the
   only thing that says a scope is *not built*; the only thing that can build one is
   ⚙ Generate in the WorldPainter. The panel that names the problem offers no way to
   act on it, and - deliberately, per `scope-tree.js`'s own rule - no Generate
   button, because "a card that offered one would be a promise the graph cannot
   keep". That rule is right and stays; what changes is that the scope rows move
   next to the areas, so "this scope is empty" is read in the same breath as the
   areas of the scope that is not.

## Decisions taken

- **The scope tree becomes the top level of the Outline tab**, above the existing
  area list, indented as its parent. One hierarchy, in the one panel that already
  holds a hierarchy.
- **A scope row loads that scope** - the same call the graph's scope tree row makes
  today (`graphManager.setScopeFilter`), so behaviour is unchanged and the graph
  keeps working exactly as it does.
- **The area list follows the loaded scope.** It already does (it reads
  `worldState.areas`, which is whatever is loaded), so this needs no new plumbing.
- **No Generate button on a scope row.** Carried over from `scope-tree.js`'s rule.
  What a row *may* offer is the honest "open in WorldPainter" jump - which is the
  fix for point 3 and does not break the rule, because the WorldPainter is where
  generation lives and the link says exactly that.

## Decisions still open - need an answer before the UI is drawn

1. **Does the `Loaded world scope` dropdown survive?** It is the third route to the
   same place. Removing it makes the tree the only navigator; keeping it is a hedge
   for someone who does not know the tree is there. *My recommendation: keep it
   for now and delete it in a follow-up once the tree is in place and used*, and
   removing a navigation surface and adding one in the same change means an author
   who learned the old one has nothing, and there is no undo for muscle memory.
2. **What does the graph keep?** The breadcrumb answers "where am I" and the tree
   answers "what else is there", which is a real split worth keeping - so the
   proposal is: breadcrumb stays in the graph, the scope **tree** moves out. If the
   graph is showing the whole world with no scope loaded, the breadcrumb has nothing
   to say, and the graph would then have *no* scope affordance at all; that is
   acceptable because "show whole world" is a graph-local view, not a place in the
   world.

**Resolved 2026-09-30 by the implementation.** The dropdown survives
(`templates/index.html:227`, `#graph-scope-filter`), as the recommendation said,
and the breadcrumb stays in the graph (`templates/index.html:340`,
`#scope-breadcrumb`) while the scope **tree** moved out of it. The follow-up that
would delete the dropdown is still open and is not part of this card's scope.

## Acceptance

Landed on 2026-09-30 in commit `55b9f749`, re-verified 2026-10-20:

- [x] The scope hierarchy is the **top of the Outline tab**.
      `GraphScopeTree.mountInOutline()` (`static/js/graph/scope-tree.ts:212-228`)
      inserts the host immediately before `#outline-container`, and
      `renderOutlinePanel` calls it after every outline paint
      (`static/js/graph/tree-view.ts:162-164`). The host element itself lives
      inside `#left-tab-outline` (`templates/index.html:137-145`).
- [x] Scope rows come first and carry their **state and counts**.
      `rowLabel` (`static/js/graph/scope-tree.ts:174-189`).
- [x] Clicking a scope row **loads that scope** into the graph, and the area
      rows follow it: `scope-tree.ts:303` → `load()` (`:331-344`) →
      `GraphToolbar.loadScope` → `graphManager.setScopeFilter`. The outline
      heading then names the loaded scope (`tree-view.ts:83-85`, `:155`).
- [x] The scope tree is **not** also rendered at the bottom of the graph. The
      static `<nav id="scope-tree">` moved out of the graph panel into
      `#left-tab-outline` (`templates/index.html:144`).
- [x] An **unmade scope says so on its row**, and the row offers the honest
      "open in WorldPainter" jump with no Generate button:
      `scope-tree.ts:312-327` renders a `🖌 Paint` button that calls
      `VW.worldPainter.open(row.id)`.
- [x] The pure rules stay pure and unit-tested: `buildTree`
      (`scope-tree.ts:53`), `visibleRows` (`:115`), `toggleCollapsed` (`:159`)
      and `rowLabel` (`:174`) are pure functions, and
      `tools/unit/test_graph_scope_tree.js` holds 17 tests. Re-running the
      pure half against the emitted `static/js/graph/scope-tree.js` on
      2026-10-20: 7 passed, 0 failed.
- [x] `copyOutlineTree()` copies the **whole hierarchy**, not just the areas
      (`tree-view.ts:203-228`).

Implemented (2026-10-24):

- [x] The area rows are **nested under the scope that holds them**, so the tab
      shows world -> scope -> area in one tree and an area is never listed under
      a scope it is not in.
- [x] The fold is a **pure function with a test**, per this card's own rule:
      `GraphScopeTree.foldScopeAreas` implemented and unit tested in
      `tools/unit/test_graph_scope_tree.js`.
- [x] Areas that belong to **no** scope (a hand-authored world) appear under a
      plainly-labelled fallback row ("Unscoped Areas"), never silently dropped.
- [x] A **materialized scope with zero areas and zero items** says so on its
      row ("empty") instead of rendering an empty count list.

## Notes

- The pure rules already exist and are already tested; this is mostly a **placement**
  change plus one new pure function (the fold), which is why the estimate is small
  even though it touches three files. *The placement change landed; the fold
  function did not.*
- `copyOutlineTree()` currently copies areas only. It should copy the **whole**
  hierarchy once scopes are in the panel, or the clipboard will silently lose the
  top two levels of the world. *Done 2026-09-30: `tree-view.ts:203-228`.*
- Point 3 is the one worth remembering: the app currently tells you a scope is
  unbuilt in one window and expects you to know which of two buttons in another
  window fixes it. Nothing in the UI connects them, and that is a bigger usability
  hole than the visual duplication this task is named after. *Done 2026-09-30: the
  unmade row carries a `🖌 Paint` jump into the WorldPainter
  (`scope-tree.ts:312-327`).*

## Why

Two collapsible trees with counts, on screen at once, on different subjects, in
different halves of the UI. A reader has to learn which one to trust, and the
panel that names the problem ("this scope is not built") is not the panel that
can act on it.

## How

1. Write the fold as a pure function first: a scope summary plus a list of
   areas produces rows of `{scope, areas}` in the order the tree wants them,
   with areas that belong to no scope collected under a plainly-labelled
   fallback row. Test it in `tools/unit/test_graph_scope_tree.js` before it
   touches the DOM, per this card's own rule.
2. Feed the fold from the two sources the panel already has:
   `graphManager._scopeSummaries` (the flat scope list) and `worldState.areas`
   (the loaded areas). The scope summary does not currently carry the areas it
   holds, so the fold needs either the scope membership from
   `GET /api/world/scopes?flat=1` or a new count of areas per scope - check
   what the endpoint actually returns before assuming.
3. Render the fold over the existing scope rows in `scope-tree.ts`, so the
   scope row and its areas are one subtree, and the pure scope rules stay
   where they are.

## Steps to verify

1. Open the Outline tab in a world with at least two scopes and areas in both.
   - expected: scope rows first, each with its state and counts, and each
     scope's areas nested under that scope.
   - observed: CONFIRMED. `foldScopeAreas` groups areas under their parent scope,
     renders member area cards within the scope block, and lists unscoped areas
     under an explicit fallback row.
2. Click a scope row.
   - expected: the graph loads that scope and the area rows become that
     scope's areas.
   - observed: (2026-10-20) done. `scope-tree.ts:303` → `load()` (`:331-344`)
     → `GraphToolbar.loadScope`; the heading names the loaded scope
     (`tree-view.ts:83-85`).
3. Check an unmade scope row.
   - expected: the row says it is not built and offers "open in WorldPainter",
     with no Generate button.
   - observed: (2026-10-20) done. `scope-tree.ts:312-327` renders `🖌 Paint`
     calling `VW.worldPainter.open(row.id)`.
4. Look for the scope tree at the bottom of the graph.
   - expected: it is not there; the Outline tab is the only place.
   - observed: (2026-10-20) done. The static host moved into
     `#left-tab-outline` (`templates/index.html:144`).
5. Copy the outline to the clipboard.
   - expected: the copy carries the scope hierarchy, not just the areas.
   - observed: (2026-10-20) done. `tree-view.ts:203-228`.

## Files

- `static/js/graph/tree-view.ts` (the Outline panel: the area rows and the fold)
- `static/js/graph/scope-tree.ts` (the scope rows, `mountInOutline`, the paint jump)
- `static/js/graph/network-manager.ts` (the graph-side scope tree host, now removed)
- `templates/index.html` (the `#scope-tree` host inside `#left-tab-outline`)
- `tools/unit/test_graph_scope_tree.js` (17 tests; the fold's tests go here)

## Browser UI and intended live verification

Intended UI home: World editor → Outline tab, showing world → scope → area.

Current availability: re-measured 2026-10-20, the scope tree is at the top of
the Outline tab, a scope row loads its scope, and an unmade row offers the
WorldPainter jump. The unified **world → scope → area** tree is not there yet:
the areas are a separate flat list under the scope rows, with no scope
attribution and no fallback row for unscoped areas.

Live steps when available:

1. Open Outline and inspect a world with multiple scopes and areas.
   - expected: Scope rows show state/counts, with only their member areas nested below.

2. Select a scope row, then select a scope with no areas.
   - expected: The graph loads the selected scope and the empty scope has an explicit empty/not-built state.

This section defines the intended access point and acceptance path. It is not a claim that the UI or complete behavior exists or works today; Current availability records the present state, and these steps describe how to verify the intended behavior when it is available.

## Audit note (2026-10-16)

Moved from inprogress back to todo: it was not being worked. No uncommitted changes in the working tree or in any of the eight git worktrees touch this card's files, and nobody is editing it. 0 of 7 acceptance boxes checked; the latest commit that mentions it is d4d8f324 (2026-10-02), a blocker note saying it collides with the task-580 scope-tree work.

*Corrected 2026-10-20: the premise "it was not being worked" was wrong. The card
and its implementation were committed together on 2026-09-30 in `55b9f749`, which
added the card to `dev_tasks/inprogress/ui/` in the same commit that added
`mountInOutline`, the paint jump and the whole-hierarchy clipboard copy. The
"0 of 7 acceptance boxes checked" count was a read of the boxes, not of the
code: of the original seven criteria, three are fully met, one is partly met,
and three are not (see Acceptance).*

## Reconnaissance (2026-10-20) - partly done, still open

Re-checked on 2026-10-20 against the code. The newer work that owns this card's
scope is **task-592's own implementation**, committed on 2026-09-30 as
`55b9f749` ("feat(graph): one hierarchy, and a map that names its places"). It
added the card to `dev_tasks/inprogress/ui/` in the same commit. task-627 (done)
is *not* this work: it fixed the flat `<select>` scope picker into real
`<optgroup>` nesting (`static/js/shared/scope-options.js`), a different
surface.

What landed (`55b9f749`, confirmed in the current tree):

- The scope tree host moved out of the graph panel and into the Outline tab.
  `templates/index.html:137-145` holds `<nav id="scope-tree">` inside
  `#left-tab-outline`; `GraphScopeTree.mountInOutline()`
  (`static/js/graph/scope-tree.ts:212-228`) inserts it immediately before
  `#outline-container`, and `renderOutlinePanel` calls it after every outline
  paint (`static/js/graph/tree-view.ts:162-164`).
- Scope rows carry state and counts (`rowLabel`, `scope-tree.ts:174-189`).
- Clicking a scope row loads it (`scope-tree.ts:303` → `load()` `:331-344` →
  `GraphToolbar.loadScope`), and the outline heading names the loaded scope
  (`tree-view.ts:83-85`, `:155`).
- An unmade row carries a `🖌 Paint` jump into the WorldPainter
  (`scope-tree.ts:312-327`), with no Generate button, as the card required.
- `copyOutlineTree()` copies the whole hierarchy (`tree-view.ts:203-228`).
- The pure rules stayed pure: `buildTree` (`:53`), `visibleRows` (`:115`),
  `toggleCollapsed` (`:159`), `rowLabel` (`:174`).

Evidence counts: 1 `mountInOutline` call site
(`static/js/graph/tree-view.ts:163`), 1 `#scope-tree` host
(`templates/index.html:144`), 17 unit tests in
`tools/unit/test_graph_scope_tree.js`, and a targeted re-run of the pure half
against the emitted `static/js/graph/scope-tree.js`: 7 passed, 0 failed.

What did not land:

- The area rows are **not** nested under the scope that holds them.
  `static/js/graph/tree-view.ts:74` reads every area in `worldState.areas`,
  `:94` sorts them by name, and `:154-156` renders them as a sibling list
  under the scope tree. There is no fold and no scope attribution, so the
  world → scope → area tree the card is named for does not exist yet.
- There is no fallback row for areas that belong to no scope.
- A materialized scope with zero areas and zero items renders as the scope name
  followed by a dash and an empty count list, because `rowLabel` only pushes a
  count when it is non-zero (`scope-tree.ts:181-183`).

Facts that drifted:

- "`tree-view.js` contains **zero** references to scopes" was true on
  2026-09-29 and false from 2026-09-30: `tree-view.ts` now references
  `GraphScopeTree` at `:162-164`, `:208-212` and the scope name at `:83-85`.
- The card's two open decisions were resolved by the implementation: the
  `Loaded world scope` dropdown survives (`templates/index.html:227`), and the
  breadcrumb stays in the graph (`templates/index.html:340`).
- The 2026-10-16 audit note ("it was not being worked", "0 of 7 acceptance
  boxes checked") measured the boxes, not the code, and is corrected above.

Verdict: PARTLY_DONE. Of the card's original seven criteria, three are fully
met (the scope tree is the top of the Outline tab and the only place it lives,
an unmade row says so and offers the WorldPainter jump, the pure rules stayed
pure and tested), one is partly met (clicking a scope row loads it, but a scope
with no areas does not say so on the row), and three are not (the world → scope
→ area tree, the pure fold with its test, and the fallback row for unscoped
areas). Card kept in todo with its scope rewritten to what is left.
