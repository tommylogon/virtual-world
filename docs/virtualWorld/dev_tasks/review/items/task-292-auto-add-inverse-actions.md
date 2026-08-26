---
group: Items
wiki: "[[UI & Settings/Inspector]]"
---

# Auto-Add Inverse Actions (take↔drop, equip↔unequip)

**Filed**: 2026-08-18  
**Priority**: Low  
**Status**: In Review — implemented 2026-08-18, unit + integration tests pass (971 total). Toggling an allowed action **on** now also enables its inverse (`take`→`drop`, `equip`→`unequip`, and back), deduplicated, across every item write path (inspector/build endpoints, library placement/import/refresh, scenario deserialization, `spawn_item` effects) plus read-time normalization so existing items surface the inverse immediately. Frontend action-grid toggle mirrors the pair in the UI and creates the inverse's base `on_*` trigger hook.

---

## Problem

Item `actions` are a gate/allowlist, but inverse verbs are not automatic: an item you can `take` doesn't advertise `drop` in its available actions, and one you can `equip` doesn't advertise `unequip`. Defining one and remembering the other by hand is error-prone.

## Goal

When a designer enables an allowed action on an item, also enable its inverse automatically (`take`↔`drop`, `equip`↔`unequip`), so the pair stays in sync everywhere item actions are defined or rendered.

## Behavior

- If `take` is present → also `drop`; if `drop` → also `take`. Same for `equip`↔`unequip`. Bidirectional, no duplicates, unknown actions preserved.
- Applies at every write path (inspector `update_node`/`build_item`, library place/import/refresh-from-library, scenario deserialization incl. container contents, `spawn_item` effect) and at read time in `_get_available_actions` so existing, never-re-saved items show the inverse immediately.
- The world item inspector's action checkbox grid toggles the inverse together and creates a base `on_<inverse>` trigger when the action is enabled.

## Implementation

- `engine/item_actions.py` — new `INVERSE_ACTIONS` map + `normalize_item_actions()` helper (string or list → deduped list with inverses).
- `routes/graph.py` — normalize `actions` in `update_node` and `build_item_legacy`.
- `routes/library_routes.py` — normalize in library placement, character/area item import, and `_refresh_item` (both selective and blind refresh).
- `engine/serialization.py` — normalize in scenario item deserialization and container contents.
- `engine/effects.py` — normalize `actions` in the `spawn_item` effect.
- `engine/trigger_system.py` — normalize in `_get_available_actions` (read-time safety net).
- `static/js/inspector/item-view.js` — `INVERSE_ACTIONS` client-side; `_toggleAction` adds/removes the inverse and ensures the inverse's base trigger.

## Verification

- [x] `python -m pytest tests/test_action_inverses.py -q` (9 tests: helper unit cases + `update_node`/`build_item` integration)
- [x] Full suite: `python -m pytest tests/ -q -k "not mcp and not emote"` → 971 passed, 1 skipped
- [x] `node --check static/js/inspector/item-view.js` clean
- [ ] In-browser: enable `equip` on an item → `unequip` auto-checks + `on_unequip` trigger created; enable `take` → `drop` appears in the item's available actions
