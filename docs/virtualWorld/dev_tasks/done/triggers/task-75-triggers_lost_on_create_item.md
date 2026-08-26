# Triggers Lost on New Item Creation

**Filed**: 2026-07-18
**Priority**: High
**Status**: Fixed in `2aa346c`

## Summary

When creating a new item via the "Create New Item" modal (graph toolbar → 📦 Item → fill form + triggers → create), triggers are sent to the backend in the request data but are silently discarded. They never become graph edges, so they never appear in the inspector panel.

## Root Cause

`/api/build/item` (`build_item_legacy` in `app.py:1261`) never reads the `triggers` field from the request body. The code handles location edges (room/container/character placement) but completely ignores the trigger data.

The `build_item_from_library` endpoint already correctly creates `logic_trigger` nodes + `triggers` edges, but `build_item_legacy` was never updated with similar logic.

## Fix

Added trigger processing to `build_item_legacy` (before the final `return jsonify(...)`):

1. Reads `data.get('triggers', [])`
2. For each trigger, creates a `logic_trigger` node
3. Creates a `triggers` edge from the item to the trigger node
4. Handles both old format (`effect_type`/`effect_params`) and new format (`effects`/`conditions` arrays)

## Files Changed

- `app.py`: Added ~30 lines of trigger edge creation in `build_item_legacy`
