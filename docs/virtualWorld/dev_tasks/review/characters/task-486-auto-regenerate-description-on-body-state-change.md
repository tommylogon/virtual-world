---
type: task
status: review
area: characters
priority: medium
---

# task-486: Auto-regenerate description on body-state change

**Filed:** 2026-09-23
**Related:** task-210

## Goal

Regenerate the stored player.description when conditions/body_state change, not only on equip/unequip: add an _update_state_description() hook (guarded by world.auto_generate_descriptions) and optionally _get_state_hash() caching skipped when mature_content is off. Tracked from task-210.

## Acceptance

- `player.description` refreshes when a visible condition/body-state change is applied or removed (e.g. `nipple_hard`, `blushing`, `wetness`), not only on equip/unequip.
- Guarded by `world.auto_generate_descriptions` (off → no regeneration) and respects the `world.mature_content` gate on the body-state block (`engine/equipment.py:_body_state_description_lines`).
- Optional per design: `_get_state_hash()` (equipment + conditions + body_state) prevents redundant regeneration when nothing changed.
- `engine/pleasure_actions.py`-style matures stay off in non-mature worlds.
- Test coverage added; `python -m pytest tests/test_<name>.py -q` green.

## Implementation

- `engine/equipment.py`:
  - `VISIBLE_BODY_STATE_PHRASES` module constant — the visible-condition map shared by the prompt block and the fingerprint.
  - `_get_state_hash(player)` — equipment (slot, id, `current_state`) + `mature_content` flag + present visible conditions + body-state sensitivity.
  - `_update_state_description(player)` — hash-guarded, `auto_generate_descriptions`-guarded reconcile hook; returns whether it rebuilt.
  - `_update_equipment_description()` re-seeds `player._description_state_hash` after writing prose.
- `engine/tick_manager.py` — `tick_turn()` reconciles every living character once per turn, catching conditions changed by direct `player.conditions` dict writes (not just `add_condition`/`remove_condition`).
- `engine/conditions.py` — `ConditionsSystem.apply_condition`/`remove_condition` refresh immediately via `_refresh_description` (best-effort; the per-turn hook is the safety net).

## Testing

- [x] `tests/test_description_enrichment.py` (11 tests): regeneration on apply/remove, no-op when unchanged, non-visible conditions ignored, `auto_generate_descriptions` gate, `mature_content` gate, item `current_state` sensitivity, conditions-system immediate refresh, and the tick safety net after a direct dict write.
- [x] `python -m pytest tests/test_description_enrichment.py -q` → 11 passed.
- [x] Full suite unchanged from baseline (63 pre-existing failures, no new ones).
