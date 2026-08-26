---
group: UI & Settings
---

# Searchable Picker (SearchSelect) for Trigger Editor Target Fields

**Filed**: 2026-08-09  
**Priority**: Medium  
**Status**: In Review — implemented 2026-08-09, verified with `tools/test_trigger_search_select.cjs` (Playwright) + `tools/test_ui.cjs` (25/25), no console errors.

---

## Summary

The trigger editor's searchable target fields were bare text inputs with native `<datalist>` autocomplete (inconsistent browser behavior, must know node ids by heart). Replaced with a TagMultiselect-style searchable picker across all target fields.

## Implementation

New shared component `static/js/shared/search-select.js` — `SearchSelect`, single-value combobox with the tag-searchbox interaction: click/focus → dropdown of all options, type → live filter on label *or* value, click/Enter/arrow-keys to pick, Escape to cancel, clear (×) when set. Keeps a hidden input with a configurable class/id so all existing save collectors (`row.querySelector('.eff-x')?.value`, `getElementById`) work unchanged. `allowFreeText` per field: off for node/way pickers (no garbage ids), on for items/traits/names/states.

`shared/trigger-editor.js`:
- Generic `_searchSelectOptions(kind)` builds options per kind: `ways`, `items` (graph + library), `nodes` (+`self`), `areas`, `states`, `conditions`, `vitals`, `skills`, `chars` (self/target + players), `traits`, `tags`, `targets` (parses the on_use_on datalist).
- Generic `_initEffectSearchSelects()` scans `.eff-select[data-kind]` divs (data-value = initial, data-input-class/id = hidden input wiring, data-free = allow free text), called from `show()` (initial + effect rows), `_addEffectRow()`, `_addLeafTo()`, `_addGroupTo()` (dynamic condition rows).
- Converted fields: unlock_way Way ID, set_state Node ID + New State, set_hidden/adjust_uses Node ID, spawn_item/give_item/remove_item Item IDs, give_item Target, set_environment Target, apply/remove_trait Trait ID + Target, apply_condition Condition, adjust_vital Stat, on_use_on Target, and condition fields (has_item value, has_trait/has_tag value, vital, is_equipped item, state_equals node+state, skill_check skill, save_throw skill, condition target).
- Also fixed: the on_use_on Target field (and target-state field) stayed hidden when opening an existing trigger until the trigger-type select was touched — `show()` now dispatches a change event once so initial visibility matches the selected type.

`templates/index.html`: script tag for `search-select.js` added before `trigger-editor.js`.

## Verification

`tools/test_trigger_search_select.cjs` (Playwright): unlock_way way picker opens with all 10 world ways and saves `way_id`; set_state node+state pickers save `node_id`/`state`; dynamically-added `state_equals` condition's node+state pickers save `target`/`value`; on_use_on target picker saves the chosen target. `tools/test_ui.cjs` 25/25. `node --check` clean.

## Files Changed

- `static/js/shared/search-select.js` — new component
- `static/js/shared/trigger-editor.js` — generic SearchSelect wiring + target-field visibility fix
- `templates/index.html` — script include
- `tools/test_trigger_search_select.cjs` — new Playwright test
