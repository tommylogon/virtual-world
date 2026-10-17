---
area: characters
status: done
type: task
priority: medium
related: ["'task-207'", "'task-208'", "'task-210'", "'task-211'", "'task-212'", "'task-213'", "'task-215'", 'task-207', 'task-208', 'task-210', 'task-211', 'task-212', 'task-213', 'task-215']
---

# Arousal State Conditions & Threshold Triggers

**Filed**: 2026-08-11
**Priority**: High
**Status**: Done — shipped in v1.4.0

---

<!-- deps:start -->
**Related:** [[task-207-body-state-and-vitals]], [[task-208-release-edging-friction]], [[task-210-description-enrichment]], [[task-211-intimacy-verbs-actions]], [[task-212-verb-multipliers]], [[task-213-mature-traits]], [[task-215-environmental-clothing-effects]]
<!-- deps:end -->

## Why

The arousal vitals need to manifest as visible/influential character states. These are modeled as conditions with periodic effects, symptoms, and combat mods — no new architecture.

## How

- Add condition definitions to `player.py` `CONDITION_DEFINITIONS` (verified location, `player.py:30`):
  - `warming_up` (periodic Stimulation +1), `aroused` (Stim +2, attack/defense -2, auto_fail perception/concentration), `highly_aroused` (Stim +3, Energy -2, attack/defense -3, auto_fail + willpower), `frantic` (Stim +4, Energy -3, Sanity -2, attack/defense -5, auto_fail + self_control)
  - `overstimulated` (Pleasure -3, Energy -1, excludes satisfied/numb)
  - `nipple_hard` (periodic Arousal +1, known), `blushing` (visual only), `wetness` (periodic Arousal +2, not known unless exposed)
  - `sensitized` (edging stack), `satisfied`
- **`stack` field required** — the catalog's `stack` (accumulate/refresh/noop) governs re-application; `sensitized` should `accumulate` (stacks), arousal states likely `refresh`. `excludes` → use the existing `CONDITION_EXCLUSIONS` map (`player.py`).
- Threshold checks in `tick_turn()` (`engine/tick_manager.py:83`): apply/remove arousal-state conditions based on Arousal value (0-15 baseline, 15-30 warming, 30-50 aroused, 50-90 highly, 90+ frantic).
- Condition → vital feedback loops via `periodic` (already supported by `conditions.process_tick()`, called from `tick_turn()` line 108).
- **Combat mods verified**: combat does `attack + attack_mod − target_defense_mod`, so aroused/highly_aroused/frantic `attack_mod`/`defense_mod` penalties will work if the catalog fields match the existing schema.

## Files

- `engine/player.py` — condition definitions (`CONDITION_DEFINITIONS` at `player.py:30`)
- `engine/tick_manager.py` — threshold checks (`tick_turn()` at line 83)

## Steps to verify

- [ ] Arousal crosses 15/30/50/90 → correct condition applied
- [ ] Drops below threshold → condition removed
- [ ] `periodic` effects feed back into vitals each tick
- [ ] Combat mods apply (attack/defense penalties, auto-fail checks)

## Related

- `dev_tasks/# Nipple & Erogenous Zone System - Desig.md` — §2, §4, Phase 2

## What

TODO

## Acceptance

- [ ] TODO
