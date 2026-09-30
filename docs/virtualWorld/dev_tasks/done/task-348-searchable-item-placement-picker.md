# task-348-searchable-item-placement-picker

## Summary

Replace the legacy item placement/move UI in both the create-item modal and the item inspector’s **Move To** section with a search-based picker for characters/areas/items, plus a spatial-relationship selector.

## Acceptance Criteria

- [ ] `routes/search.py` exists and exposes `/api/search/placement-targets?q=...`, returning matching areas, items, and characters from the live world graph.
- [ ] `static/js/ui/create-modal.js` no longer renders the old `item-target-area` / `item-target-container` / `item-target-character` selects. Instead it renders:
  - target-type radios: Item / Character / Area
  - a single search box that calls `/api/search/placement-targets` filtered by the selected type
  - a relation dropdown (`in`, `on`, `under`, `behind`, `beside`, `at`) shown for item targets
- [ ] `static/js/inspector/item-view.js` **Move To** section mirrors the same search-picker + relation selector UX.
- [ ] `static/js/main.js` AI-generation prompt context reads `item-target-type`, `item-target-id`, and `item-target-relation` from the new fields.
- [ ] `static/js/api.js` `moveItemToRoom` forwards `targetType`, `targetId`, and `relation`.
- [ ] `routes/graph_ops.py` `handle_build_item_legacy` and `handle_move_item_node` accept the unified `target_type` + `target_id` + `relation` payload, while still accepting legacy `area` / `container` / `character` fields.
- [ ] No dead references remain to `item-target-area`, `item-target-container`, `item-target-character`, `move-item-area-select`, `move-item-container-select`, or `move-item-character-select` in the frontend codebase.
