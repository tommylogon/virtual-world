---
group: Pleasure System
---

# Description Enrichment (Body State + Item Details)

**Filed**: 2026-08-11
**Priority**: Medium
**Status**: Todo

---

## Problem

`_update_equipment_description()` (`engine/equipment.py:524`) feeds only item names to the LLM, so it can't reason about body state or visibility through clothing layers (a hard nipple under a sheer blouse, flushed cheeks, etc.).

## Design

- Enrich `_update_equipment_description()` prompt with:
  - `_get_body_state_description(player)` — text derived from conditions (`nipple_hard`, `aroused`, `blushing`, `wetness`) + `body_state` numeric values (e.g. cheeks flush > 0.5)
  - `_get_enriched_equipment_text(player)` — item names + description + `opacity`/`coverage` props (nodes from `graph.get_node_by_name()`)
- Trigger regeneration on state changes via `_update_state_description()` (guarded by `world.auto_generate_descriptions` — existing flag, see `routes/settings.py:109`).
- Optional caching: `_get_state_hash()` (equipment + conditions + body_state) → cache dict on player, skipped when `mature_content` is off.
- **Frontend prompt note**: agent appearance flows through `static/js/agent/prompt-builder.js` — body state should also surface there so LLM agents see the same info as description generation.

## Files

- `engine/equipment.py` — `_update_equipment_description()` enrichment (line 524)
- `static/js/agent/prompt-builder.js` — body state in agent observation prompt

## Testing

- [ ] Description includes "hard nipples"/"flushed" when conditions present
- [ ] Sheer/opaque layer distinction shows in output
- [ ] Description regenerates on body-state change, not just equip/unequip
- [ ] Gated off when `mature_content = false`

## Related

- `dev_tasks/# Nipple & Erogenous Zone System - Desig.md` — §9, Phase 3
- `task-179 event stream redesign` (if description updates need to surface visually)
