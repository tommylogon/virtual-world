---
type: task
status: todo
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
