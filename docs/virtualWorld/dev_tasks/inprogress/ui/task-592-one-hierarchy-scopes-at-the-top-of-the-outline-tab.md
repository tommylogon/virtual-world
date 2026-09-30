---
type: task
status: inprogress
area: ui
priority: medium
related: [task-397, task-398, task-528, task-531, task-574]
---

# task-592: One hierarchy: scopes at the top of the Outline tab

**Filed:** 2026-09-29
**Related:** task-397, task-398, task-528, task-531, task-574

## Goal

One tree in one place: **world → scope → area**, in the Outline tab, so there is a
single place to navigate the world and the "not built" signal sits next to the areas
it explains.

## The problem, precisely

The scope tree (`static/js/graph/scope-tree.js`, task-397 step 4) and the Outline tab
(`static/js/graph/tree-view.js`) are **not** duplicates, and it is worth saying why
before changing anything:

- The Outline tab is a tree of **areas** in the loaded state — descriptions, exits,
  items, who is present, temperature/light/air — read from `worldState.areas`.
  `tree-view.js` contains **zero** references to scopes: it cannot tell you
  `goblin camp` exists, let alone that it has never been generated.
- The scope tree is a tree of **scopes** from `GET /api/world/scopes?flat=1` —
  ids, states, area/item/character counts, parent and depth. It is the only thing
  that reports `unmade`.

Different subjects, different endpoints, disjoint data. The problem is everything
*around* that:

1. **Scope navigation is in three places**: the `Loaded world scope` dropdown, the
   `scope-breadcrumb` (task-531), and the scope tree. Three routes to one place, and
   **none of them in the left sidebar** — which is where navigation lives in this app
   and where a reader looks first.
2. **Two collapsible trees with counts, on screen at once**, on different subjects,
   in different halves of the UI. They look like the same widget, so a reader has to
   learn which one to trust. That is a real cost even though nothing is duplicated.
3. **The diagnosis and the fix are in different windows.** The scope tree is the
   only thing that says a scope is *not built*; the only thing that can build one is
   ⚙ Generate in the WorldPainter. The panel that names the problem offers no way to
   act on it, and — deliberately, per `scope-tree.js`'s own rule — no Generate
   button, because "a card that offered one would be a promise the graph cannot
   keep". That rule is right and stays; what changes is that the scope rows move
   next to the areas, so "this scope is empty" is read in the same breath as the
   areas of the scope that is not.

## Decisions taken

- **The scope tree becomes the top level of the Outline tab**, above the existing
  area list, indented as its parent. One hierarchy, in the one panel that already
  holds a hierarchy.
- **A scope row loads that scope** — the same call the graph's scope tree row makes
  today (`graphManager.setScopeFilter`), so behaviour is unchanged and the graph
  keeps working exactly as it does.
- **The area list follows the loaded scope.** It already does (it reads
  `worldState.areas`, which is whatever is loaded), so this needs no new plumbing.
- **No Generate button on a scope row.** Carried over from `scope-tree.js`'s rule.
  What a row *may* offer is the honest "open in WorldPainter" jump — which is the
  fix for point 3 and does not break the rule, because the WorldPainter is where
  generation lives and the link says exactly that.

## Decisions still open — need an answer before the UI is drawn

1. **Does the `Loaded world scope` dropdown survive?** It is the third route to the
   same place. Removing it makes the tree the only navigator; keeping it is a hedge
   for someone who does not know the tree is there. *My recommendation: keep it
   for now and delete it in a follow-up once the tree is in place and used* —
   removing a navigation surface and adding one in the same change means an author
   who learned the old one has nothing, and there is no undo for muscle memory.
2. **What does the graph keep?** The breadcrumb answers "where am I" and the tree
   answers "what else is there", which is a real split worth keeping — so the
   proposal is: breadcrumb stays in the graph, the scope **tree** moves out. If the
   graph is showing the whole world with no scope loaded, the breadcrumb has nothing
   to say, and the graph would then have *no* scope affordance at all; that is
   acceptable because "show whole world" is a graph-local view, not a place in the
   world.

## Acceptance

- [ ] The Outline tab shows **world → scope → area** in one tree: the scope rows
      first, each with its state and counts, and the area rows nested under the scope
      that holds them (so an area is never listed under a scope it is not in).
- [ ] Clicking a scope row loads that scope into the graph, and the area rows update
      to that scope's areas. Loading a scope with **no** areas says so on the row
      rather than rendering an empty section that looks broken.
- [ ] The scope tree is **not** also rendered at the bottom of the graph. One place.
- [ ] An unmade scope says so on its row, and the row offers **"open in
      WorldPainter"** for that scope — the honest jump, with no Generate button and
      no promise the graph cannot keep.
- [ ] `tools/unit/test_graph_scope_tree.js` still passes: `buildTree`,
      `visibleRows`, `toggleCollapsed` and `rowLabel` stay pure and unit-tested, and
      the panel becomes a thin render over them as its docstring already claims.
- [ ] The unit rule "every non-DOM rule lives in a pure function and is unit-tested"
      holds for the new nesting: the world→scope→area fold is a pure function with a
      test, not DOM assembly.
- [ ] Areas that belong to **no** scope (a hand-authored world) still appear, under
      a plainly-labelled fallback row — never silently dropped.

## Notes

- The pure rules already exist and are already tested; this is mostly a **placement**
  change plus one new pure function (the fold), which is why the estimate is small
  even though it touches three files.
- `copyOutlineTree()` currently copies areas only. It should copy the **whole**
  hierarchy once scopes are in the panel, or the clipboard will silently lose the
  top two levels of the world.
- Point 3 is the one worth remembering: the app currently tells you a scope is
  unbuilt in one window and expects you to know which of two buttons in another
  window fixes it. Nothing in the UI connects them, and that is a bigger usability
  hole than the visual duplication this task is named after.
