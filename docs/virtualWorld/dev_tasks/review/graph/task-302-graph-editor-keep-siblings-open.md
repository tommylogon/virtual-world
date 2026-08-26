---
group: Graph
---
# Graph Editor: Keep Siblings Open When Drilling In

**Filed**: 2026-08-19
**Priority**: Medium
**Status**: In Review — implemented 2026-08-20

## Implementation

Changed `revealItemsForNode()` in `static/js/graph/network-manager.js` to keep previously revealed items visible when drilling into a child node. `_revealedItemIds` is now a `Map<parentId, Set<childItemIds>>` instead of a flat Set. When clicking a new parent, the old parent's children are cleared; when drilling into a child of the current parent, siblings stay open. Empty click or toggling items back on still clears everything.

Also changed the default so items are hidden by default (`_showItems = false` in `graph-manager.js`, 📦 button starts inactive) per user preference.

## Verification

- JS syntax check passed (`node --check network-manager.js`)

---

## Idea

Graph editor optimization: when drilling into a parent node, keep its siblings open instead of hiding them.

Examples:
- Click an area → shows all items in that area. Click one of those items → currently hides the other items; want them to stay open.
- Same for clicking a character, or an item with items inside it.
- Default for "hide items unless clicking parent" should be **off**, not on.

## Notes

- Pure editor/UX optimization for the graph view (vis.js layout in the map editor).
- Complements `task-303` (hide areas with no characters) and `task-312` (graph search filter).

## Related

- `developer ideas.md` line 9
- Map editor code (`static/js/` graph/map editor modules)
