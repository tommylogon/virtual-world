---
type: task
status: done
area: ui
priority: low
---

# task-627: Outline panel: hierarchical scope tree rendered as a flat option list

**Filed:** 2026-09-30
**Related:** 

## Goal

The scope tree is hierarchical but the select's option list is flat, losing the structure the tree has.

## Acceptance

- [x] The scope picker nests depth-1+ scopes in real `<optgroup>` elements
- [x] No option text carries leading non-breaking spaces
- [x] A shallower sibling closes the deeper branch
- [x] Multiple roots each become their own top-level option
- [x] Zero / undefined / null scope lists are tolerated
- [x] Covered by unit tests that need no scenario loaded
- [x] Visually confirmed in the browser against a synthetic 5-scope tree

## Resolution (2026-09-30)

The claim was correct and is now fixed. `graph-manager.js` was rendering the
hierarchy as a flat list with the depth expressed as invisible padding:

    opt.textContent = `${'\u00A0'.repeat((scope.depth || 0) * 2)}${scope.name}`

so a player had to count non-breaking characters to tell a zone from a sub-zone.

**Fixed** by extracting the nesting into a new module,
`static/js/shared/scope-options.js` (`window.ScopeOptions.populate`), which
renders real `<optgroup>` nesting using a stack of open groups: scopes arrive
parent-before-child (task-531 keeps `parent_id` for exactly this), so popping
back to the requested depth and appending into it is sufficient.

**Verified in the browser** against a synthetic tree, because the world loaded at
the time has ZERO world-scopes (`/api/world/scopes` returns `scopes: []`, and
the picker correctly offers only "Whole world"). Rendering into a real DOM and
screenshotting gives:

    Whole world
    Root
    Zones
      Zone A
      Sub-zones
        Sub-zone A1
        Sub-zone A2
      Zone B

**8 unit tests** in `tools/unit/test_scope_options.js` cover the regression
(depth-1 nests; no nbsp in any option text), the shape (depth 2 inside depth 1;
a shallower sibling closes the deeper branch; multiple roots; every scope
reachable exactly once), and degenerate inputs (zero, undefined, null, missing
depth).

Two notes for whoever picks up adjacent work:

- The helper had to be its own module rather than a method on `GraphManager`.
  Loading `graph-manager.js` into the unit sandbox broke **12** existing tests
  (`test_relative_layout`, `test_graph_background`, `test_graph_event_handlers`),
  because constructing the manager perturbs the shared sandbox. A 25-line pure
  function is the right seam anyway.
- A new browser-global module needs its `<script>` tag in
  `templates/index.html`. The unit runner loads modules itself, so the 8 tests
  passed while the page still had `window.ScopeOptions` undefined — the tests
  could not catch the missing tag, and only loading the real page did.

- TODO
