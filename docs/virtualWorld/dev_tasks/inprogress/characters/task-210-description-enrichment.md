---
group: Pleasure System
status: inprogress
---

# Description Enrichment (Body State + Item Details)

**Filed**: 2026-08-11
**Priority**: Medium
**Status**: In progress — shipped except auto-regen on body-state change; remaining work: task-486

---

## Problem

`_update_equipment_description()` (`engine/equipment.py:524`) feeds only item names to the LLM, so it can't reason about body state or visibility through clothing layers (a hard nipple under a sheer blouse, flushed cheeks, etc.).

## Design

- Enrich `_update_equipment_description()` prompt with:
  - `_get_body_state_description(player)` — text derived from conditions (`nipple_hard`, `aroused`, `blushing`, `wetness`) + `body_state` numeric values (e.g. cheeks flush > 0.5)
    - **Shipped** as `_body_state_description_lines()` (`engine/equipment.py:617`): mature-gated map of visible conditions → phrases, injected as a `VISIBLE PHYSICAL STATE` prompt block (`:690-701`).
  - `_get_enriched_equipment_text(player)` — item names + description + `opacity`/`coverage` props (nodes from `graph.get_node_by_name()`)
    - **Shipped** as `_equipment_detail_lines()` (`engine/equipment.py:645`): per-item `opacity`/`coverage`/`current_state`/`friction`.
- Trigger regeneration on state changes via `_update_state_description()` (guarded by `world.auto_generate_descriptions` — existing flag, see `routes/settings.py:109`).
  - **Gap:** `_maybe_update_equipment_description()` (`:611`, guarded by `auto_generate_descriptions`) is only called from equip/unequip paths (`:213,297,299,318,320,347`) and a manual route (`routes/player_ops.py:723`). Nothing regenerates the stored `player.description` when conditions/body-state change; `_update_state_description()` was never added.
- Optional caching: `_get_state_hash()` (equipment + conditions + body_state) → cache dict on player, skipped when `mature_content` is off.
  - **Not implemented** (design marked optional) — no `_get_state_hash` in the codebase.
- **Frontend prompt note**: agent appearance flows through `static/js/agent/prompt-builder.js` — body state should also surface there so LLM agents see the same info as description generation.
  - **Shipped** in `static/js/agent/prompt-builder/character-state.js:478-492`, mature-gated, emitting first-person body-state lines (e.g. `nipple_hard`, `wetness`).

## Files

- `engine/equipment.py` — `_body_state_description_lines()` (`:617`), `_equipment_detail_lines()` (`:645`), prompt injection in `_update_equipment_description()` (`:671`)
- `static/js/agent/prompt-builder/character-state.js` — mature-gated body-state lines (`:478-492`)

## Testing

- [x] Description includes "hard nipples"/"flushed" when conditions present — visible-condition map in `_body_state_description_lines()`
- [x] Sheer/opaque layer distinction shows in output — `opacity`/`coverage` in `_equipment_detail_lines()`
- [ ] Description regenerates on body-state change, not just equip/unequip — **not wired** (see Gap above); tracked as task-486
- [x] Gated off when `mature_content = false` — `_body_state_description_lines()` returns `[]` unless `world.mature_content`

## Related

- `task-486` — auto-regenerate description on body-state change (the unmet acceptance item above)
- `dev_tasks/# Nipple & Erogenous Zone System - Desig.md` — §9, Phase 3
- `task-179 event stream redesign` (if description updates need to surface visually)
