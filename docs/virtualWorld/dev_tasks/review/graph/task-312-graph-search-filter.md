---
group: Graph
---
# Graph Search Filter (Hide Non-Matches)

**Filed**: 2026-08-19
**Priority**: Medium
**Status**: In Review — implemented 2026-08-20

## Implementation

Updated `GraphNetwork.applyFilter()` in `static/js/graph/network-manager.js` to truly hide non-matching nodes instead of dimming them. Non-matching nodes now get `opacity: 0.0` (fully invisible). Edges are also filtered: edges remain visible if at least one endpoint matches, and are hidden only when both endpoints are non-matching.

The search input already existed in the toolbar (`#graph-search`), so no HTML changes were needed.

## Verification

- JS syntax check passed (`node --check network-manager.js`)

---

## Idea

Graph search that hides non-matching nodes, showing only the matches.

## Notes

- Editor UX: type to search, non-matching nodes/edges fade or disappear, only matches (and optionally their connections) stay visible.
- Complements `task-302` (siblings stay open) and `task-303` (hide areas without characters) — all three reduce visual noise in the graph/map editor.

## Related

- `developer ideas.md` line 19
- Map editor code (`static/js/` graph/map editor modules), vis.js layout
