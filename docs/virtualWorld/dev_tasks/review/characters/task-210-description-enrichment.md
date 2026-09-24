---
group: Pleasure System
status: review
---

# Description Enrichment (Body State + Item Details)

**Filed**: 2026-08-11
**Priority**: Medium
**Status**: In review — all acceptance items met (auto-regen completed under task-486)

---

## Problem

`_update_equipment_description()` (`engine/equipment.py:524`) feeds only item names to the LLM, so it can't reason about body state or visibility through clothing layers (a hard nipple under a sheer blouse, flushed cheeks, etc.).

## Design

- Enrich `_update_equipment_description()` prompt with:
  - `_get_body_state_description(player)` — text derived from conditions (`nipple_hard`, `aroused`, `blushing`, `wetness`) + `body_state` numeric values (e.g. cheeks flush > 0.5)
    - **Shipped** as `_body_state_description_lines()` (`engine/equipment.py:706`): mature-gated map (`VISIBLE_BODY_STATE_PHRASES`) of visible conditions → phrases, injected as a `VISIBLE PHYSICAL STATE` prompt block.
  - `_get_enriched_equipment_text(player)` — item names + description + `opacity`/`coverage` props (nodes from `graph.get_node_by_name()`)
    - **Shipped** as `_equipment_detail_lines()` (`engine/equipment.py:782`): per-item `coverage`/`current_state` plus the item's description; `opacity`/`friction` were retired (task-215 re-scope).
- Trigger regeneration on state changes via `_update_state_description()` (guarded by `world.auto_generate_descriptions` — existing flag, see `routes/settings.py:109`).
  - **Wired (task-486):** `_update_state_description()` (`:682`) hashes equipment + visible conditions + `mature_content`, and rebuilds `player.description` when that fingerprint changes. Called every turn from `tick_manager.tick_turn()` for each living character, and immediately from `ConditionsSystem.apply_condition`/`remove_condition`. Equip/unequip paths still call `_maybe_update_equipment_description()` directly.
- Optional caching: `_get_state_hash()` (equipment + conditions + body_state) → cache dict on player, skipped when `mature_content` is off.
  - **Implemented** as `EquipmentSystem._get_state_hash()` (`:649`); the fingerprint is stored on `player._description_state_hash` and short-circuits regeneration when nothing appearance-relevant changed. (`body_state` now only carries sensitivity — erogenous state is conditions since task-207 — so the visible-condition set is what drives it.)
- **Frontend prompt note**: agent appearance flows through `static/js/agent/prompt-builder.js` — body state should also surface there so LLM agents see the same info as description generation.
  - **Shipped** in `static/js/agent/prompt-builder/character-state.js:478-492`, mature-gated, emitting first-person body-state lines (e.g. `nipple_hard`, `wetness`).

## Files

- `engine/equipment.py` — `VISIBLE_BODY_STATE_PHRASES` (`:26`), `_get_state_hash()` (`:649`), `_update_state_description()` (`:682`), `_body_state_description_lines()` (`:706`), `_equipment_detail_lines()` (`:782`), prompt injection in `_update_equipment_description()` (`:816`)
- `engine/tick_manager.py` — per-turn reconciliation in `tick_turn()`
- `engine/conditions.py` — immediate refresh on `apply_condition`/`remove_condition`
- `static/js/agent/prompt-builder/character-state.js` — mature-gated body-state lines (`:478-492`)
- `tests/test_description_enrichment.py` — 11 tests (task-486)

## Testing

- [x] Description includes "hard nipples"/"flushed" when conditions present — visible-condition map in `_body_state_description_lines()`
- [x] Sheer/opaque layer distinction shows in output — `opacity`/`coverage` in `_equipment_detail_lines()`
- [x] Description regenerates on body-state change, not just equip/unequip — `EquipmentSystem._update_state_description()` + `_get_state_hash()`, called from `tick_turn()` and the conditions system (task-486)
- [x] Gated off when `mature_content = false` — `_body_state_description_lines()` returns `[]` unless `world.mature_content`

## Related

- `task-486` — auto-regenerate description on body-state change (implemented; the former unmet acceptance item above)
- `dev_tasks/# Nipple & Erogenous Zone System - Desig.md` — §9, Phase 3
- `task-179 event stream redesign` (if description updates need to surface visually)
