---
type: task
status: review
area: characters
priority: medium
related: ['"\'task-210\'"', "'task-253'", "'task-534'", 'task-253', 'task-534']
---

# task-486: Auto-regenerate description on body-state change

**Filed:** 2026-09-23
**Related:** task-210

<!-- deps:start -->
**Related:** [[task-210-description-enrichment]], [[task-253-body-part-targeted-injuries]], [[task-534-missing-body-reaction-sneeze]]
<!-- deps:end -->

## What

Regenerate the stored player.description when conditions/body_state change, not only on equip/unequip: add an _update_state_description() hook (guarded by world.auto_generate_descriptions) and optionally _get_state_hash() caching skipped when mature_content is off. Tracked from task-210.

## Acceptance

- `player.description` refreshes when a visible condition/body-state change is applied or removed (e.g. `nipple_hard`, `blushing`, `wetness`), not only on equip/unequip.
- Guarded by `world.auto_generate_descriptions` (off → no regeneration) and respects the `world.mature_content` gate on the body-state block (`engine/equipment.py:_body_state_description_lines`).
- Optional per design: `_get_state_hash()` (equipment + conditions + body_state) prevents redundant regeneration when nothing changed.
- `engine/pleasure_actions.py`-style matures stay off in non-mature worlds.
- Test coverage added; `python -m pytest tests/test_<name>.py -q` green.

## How

- `engine/equipment.py`:
  - `VISIBLE_BODY_STATE_PHRASES` module constant — the visible-condition map shared by the prompt block and the fingerprint.
  - `_get_state_hash(player)` — equipment (slot, id, `current_state`) + `mature_content` flag + present visible conditions + body-state sensitivity.
  - `_update_state_description(player)` — hash-guarded, `auto_generate_descriptions`-guarded reconcile hook; returns whether it rebuilt.
  - `_update_equipment_description()` re-seeds `player._description_state_hash` after writing prose.
- `engine/tick_manager.py` — `tick_turn()` reconciles every living character once per turn, catching conditions changed by direct `player.conditions` dict writes (not just `add_condition`/`remove_condition`).
- `engine/conditions.py` — `ConditionsSystem.apply_condition`/`remove_condition` refresh immediately via `_refresh_description` (best-effort; the per-turn hook is the safety net).

## Steps to verify

- [x] `tests/test_description_enrichment.py` (11 tests): regeneration on apply/remove, no-op when unchanged, non-visible conditions ignored, `auto_generate_descriptions` gate, `mature_content` gate, item `current_state` sensitivity, conditions-system immediate refresh, and the tick safety net after a direct dict write.
- [x] `python -m pytest tests/test_description_enrichment.py -q` → 11 passed.
- [x] Full suite unchanged from baseline (63 pre-existing failures, no new ones).

## Why

TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Character Inspector → Bio → Appearance description and
Conditions; run the scenario with `auto_generate_descriptions` and
`mature_content` set in its test configuration.

Current availability: Condition editing and the appearance-description field
exist. The engine regenerates on condition changes when enabled; this card's
recorded verification is unit-level, not a browser run.

Live steps when available:
1. In a scratch world with `auto_generate_descriptions` and
   `mature_content` enabled, select a character, record the current appearance
   description, add the `blushing` condition in the Conditions editor, then
   read the description again.
   - expected: the text includes the authored visible phrase that the
     character's cheeks are flushed.
2. Remove `blushing` or let its duration expire, then inspect the description
   after the condition change and after the next tick.
   - expected: the flushed phrase is removed and the tick does not regenerate
     the same unchanged description again.
3. Disable `auto_generate_descriptions`, apply `blushing` in a fresh test
   world, and compare the description; then turn `mature_content` off and
   repeat with the mature body-state block.
   - expected: the auto-generation-off world does not rewrite the description;
     the mature-state phrase is absent when the mature-content gate is off.

This section defines intended access and live acceptance. It is not a claim
that planned UI exists or works today.
