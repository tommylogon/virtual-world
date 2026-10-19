---
area: library
type: task
status: review
priority: medium
related: ['task-296', 'task-291', 'task-357']
---

# Select Library Item as Template When Syncing

**Filed**: 2026-08-19
**Priority**: Medium
**Status**: In Review - implemented 2026-08-19

---

<!-- deps:start -->
**Related:** [[task-296-library-instance-mismatch-warning]], [[task-291-unified-library-api-and-data-driven-catalogs]], [[task-357-structure-save-load-connected-areas]]
<!-- deps:end -->

## Idea

When syncing from library or saving to library, allow selecting which item from the library to use as the template for a specific instance.

## Implemented

- Item inspector now has a **Library Template** `<select>` (item-view.js footer) listing every entry from `data/library/items/`, pre-selected to the node's current `library_id`.
- `POST /api/library/refresh-to-world` accepts an optional `template_id`; `_refresh_item` refreshes from that entry **and rebinds `node.properties['library_id']`** to it - a node can adopt a different library entry as its template (task-355).
- `ApiClient.refreshFromLibrary(nodeId, sections, templateId)` passes the override through.
- `saveWorldItem` (item-library.js) targets the **selected template** instead of the name-slug when one is chosen, and rebinds the node's `library_id` after saving (update → template id; duplicate → the new entry id).

## Verified

- 2 new backend tests: `test_refresh_item_override_template_rebinds_library_id`, `test_refresh_item_template_override_keeps_current_when_missing` - full suite **988 passed**.
- Browser check: Lumber Axe (`item_lumber_axe`) dropdown pre-selected `lumer_axe`; refreshing with `template_id=lumber_axe` pulled weight 7 / damage 1d6 / equip_slots `["hands"]` and rebind `library_id → lumber_axe`. This resolves the parked **refresh-nulls-items** bug (bug_14 sibling): the node was bound to the sparse `lumer_axe` entry while `lumber_axe` held the rich values.

## Notes

- Currently sync is one-library-entry-per-node-id via `refresh-to-world` (`POST /api/library/refresh-to-world`), keyed on `library_id`.
- This lets a node adopt a different library entry as its template, supporting duplicate/variant items that differ per node.
- Natural sibling of `task-356` (mismatch warnings) - consider doing both in one "library sync" work session.

## Related

- `developer ideas.md` line 2
- `data/library/items/*.json`, `routes/library_routes.py`


## Acceptance

- [x] Sync action permits selecting an alternate library template when template ID differs.
- [x] DiffModal shows property diff against newly selected template.

## Files

- `static/js/inspector/diff-modal.js`
- `routes/library_ops.py`
