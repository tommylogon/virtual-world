---
group: Triggers
---

# Keycard / Clearance System: unified has_tag (target) + unlock_way target

**Filed**: 2026-08-09  
**Priority**: High  
**Status**: In Review — implemented 2026-08-09, full suite 757 passed (only the 11 pre-existing give-item failures), UI smoke 25/25, trigger E2E pass.

---

## Summary

Enables the "keycard unlocks a door" and "high-clearance card opens many doors" patterns:

- **`on_use_on` target resolution now spans all node types.** New `TriggerSystem._find_target_node()` (`engine/trigger_system.py`) resolves the used-on target by name across ways, items, areas and characters — with **exit-direction matching** for doors (so "use card on the vault door" resolves to the door node). Used by the `target_tag` trigger filter, the effect-target resolution, and the `has_tag` condition.
- **Unified `has_tag` condition** — no separate `target_has_tag`. The existing `target` field (`self` / **`target` (on_use_on)** / character name) now actually works: with `target: "target"` it checks the used-on node's tags. `value` is **any-of**: a single tag or a list. The editor value field is now a **TagMultiselect**. (`target_has_tag` remains as a hidden engine alias for already-saved data.)
- **`unlock_way` now supports the dynamic target** — `way_id: "target"` (or blank) unlocks the door the card was used on (`handle_unlock_way` gains `target_item_node`). The editor way picker has a **🎯 target (used-on)** option.
- **Latent bug fixed:** `Effects.execute()` only passes `target_item_node` to handlers that declare the parameter (`inspect.signature`) — previously any `on_use_on` with a resolvable target crashed `message`/`set_state`/etc. handlers.

## Keycard authoring (single door, with flavor)

Keycard item (`use` action) → Triggers → Add:
1. Trigger type: `on_use_on`
2. Condition: `has_tag` → **Target**: `target`, **Tags (any of)**: `clearance-4`
3. Effect 1: `message` → success "Access granted." / fail "Access denied — insufficient clearance."
4. Effect 2: `unlock_way` → Way ID: **target (used-on)**

High-clearance card = the same trigger repeated once per level (clearance-4, -3, -2, -1); doors carry the matching `clearance-N` tag. Alternative for single doors: the legacy `unlocks` edge (item → way) still works with zero trigger authoring.

## Tests

- `test_unlock_way_target_fallback` / `test_unlock_way_target_fallback_ignores_non_way` (TestEffects)
- `test_has_tag_target_uses_used_on_node` (tree evaluator: target node + array any-of + single value + missing target fails safe)
- `test_keycard_on_use_on_clearance_unlocks_way` (door tagged clearance-4 → unlocks, "Access granted")
- `test_keycard_clearance_mismatch_fails_with_message` (door tagged clearance-2 → stays locked, "Access denied")

## Files Changed

- `engine/trigger_system.py` — `_find_target_node`, unified `has_tag` (target/array), `target_has_tag` alias, target resolution before conditions (`context["target_node"]`), `target_tag` filter uses it
- `engine/effects.py` — `handle_unlock_way` target fallback; `execute()` kwarg guard
- `static/js/shared/trigger-editor.js` — way picker "target (used-on)", `has_tag` value = TagMultiselect (data-subcond toggling), collection as array
- `static/js/inspector.js`, `static/js/item-library.js` — no new condition types (unified into has_tag)
- `tests/test_trigger_system.py` — 5 new tests
- `docs/virtualWorld/Rules Engine/Triggers & Effects.md` — condition + effect docs
