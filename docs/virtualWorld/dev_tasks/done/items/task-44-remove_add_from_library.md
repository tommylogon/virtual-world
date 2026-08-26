---
group: Items & Crafting
wiki: "[[Library System/Library System Overview]]"
---

# Remove "Add from Library" from Area Actions

**Filed**: 2026-07-15
**Priority**: Low
**Status**: In Review — implemented (code-verified 2026-08-11). "Add from Library" button gone from room inspector; replaced with hint text at `static/js/inspector/area-view.js:53`. 📚 Item Library toolbar button remains.

---

## Summary

The room inspector panel has an "Add from Library" button under Area Actions. This button duplicates functionality that already exists via the toolbar "Item Library" button (which also supports placing items in specific areas). The room-level action is redundant. we also already have a right click context menu to add items to a room directly

## Current State

In `inspector.js:_showRoom()` (line 552), the room inspector renders:

```html
<button class="btn btn-sm btn-yellow" onclick="VW.itemLib.openForRoom('...')">
  📚 Add from Library
</button>
```

The same `openForRoom` is accessible from the graph toolbar "📚 Item Library" button, then selecting a room. The room inspector's version adds clutter.

## Proposed Change

Remove the "Add from Library" button from the Area Actions section in `inspector.js:_showRoom()`.

If the room inspector feels empty after removal, consider replacing with a text hint like "Use 📚 Item Library in the toolbar to add items." instead.

## Audit

**Status**: Ready to test
**How to test**:
- Open the inspector for any room. Under "Area Actions", verify the "📚 Add from Library" button is **not** present.
- Verify the 📚 Item Library toolbar button still works for adding items to areas.

## Files Affected

- `static/js/inspector.js` — remove button HTML and its action section if empty