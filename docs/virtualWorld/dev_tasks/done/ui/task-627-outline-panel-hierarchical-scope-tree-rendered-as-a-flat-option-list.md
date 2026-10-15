---
type: task
status: done
area: ui
priority: low
---

# task-627: Outline panel: hierarchical scope tree rendered as a flat option list

**Filed:** 2026-09-30
**Related:** 

## What

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

## Why

TODO

## How

TODO

## Steps to verify

1. Render a synthetic five-scope tree into the graph scope picker.
   - expected: depth-1+ scopes appear in real nested optgroups; a shallower sibling closes the deeper branch; multiple roots stay separate.
   - observed: live browser DOM and screenshot show Root → Zones → Zone A → Sub-zones → Sub-zone A1/A2, then Zone B; the second root remains separate.
2. Inspect all option text and test zero, undefined, and null scope lists.
   - expected: no non-breaking-space indentation; each scope is reachable once; empty inputs do not throw.
   - observed: eight scope-options unit tests pass, and the browser on a zero-scope world correctly offered only “Whole world”.
## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Graph workspace → scope picker → nested scope options. The picker uses real option groups; it is not a second scope tree or a whitespace-indented list.

Current availability: The card records a browser pass using a synthetic five-scope tree because the loaded world had zero scopes; the picker correctly offered only “Whole world” for that world.

Live steps when available:
1. Open the scope picker with a synthetic tree containing two roots, a depth-1 child, two depth-2 children, then a shallower sibling.
   - expected: “Root” and each other root appear at the top level; `Zone A` is inside a real `optgroup`, its two sub-zones are nested under their own group, and the later `Zone B` closes the deeper branch.
2. Inspect each option's text and parent element in the open picker.
   - expected: no option begins with non-breaking-space indentation; each scope appears once in its correct group.
3. Replace the scope list with empty, undefined, and null inputs.
   - expected: the picker remains usable and offers “Whole world” without throwing.
4. Load a world with no scopes and open the picker.
   - expected: only “Whole world” is available; no synthetic scope is presented as world data.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.
