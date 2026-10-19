# Bug 5: Rat NPC shows 11/10 HP with "low HP" warning

**Filed**: 2026-07-23
**Priority**: Medium
**Status**: fixed

## Summary

A rat NPC displayed 11 out of 10 HP (exceeding max) and showed a low-HP warning. Two issues: HP exceeded max and the warning threshold was incorrect.

## Root Cause

1. **HP overheal in template data**: `world_template.json` initialized the rat with `"HP": 11` and `"Max_HP": 10`.
2. **No clamping on load**: `engine/serialization.py` did not clamp HP to `Max_HP` when loading player data from saves or templates.
3. **Hardcoded warning threshold**: `static/js/ui-controller.js` used a fixed `<= 20` HP threshold for the critical warning, which didn't scale with different `Max_HP` values.

## Fix Applied

- **`world_template.json:7565`**: Clamped rat HP from 11 to 10 to match `Max_HP`.
- **`engine/serialization.py:134-140`**: Added HP clamping on player data load. Ensures `HP` never exceeds `Max_HP`, defaults `Max_HP` to 100 if missing, and clamps `Energy` to 0-100.
- **`static/js/ui-controller.js:109`**: Changed HP critical warning from hardcoded `<= 20` to `20% of Max_HP`, so it scales correctly for characters with different max HP values.

## Verification

- Relevant pytest suites pass: `test_engine_init.py`, `test_trigger_system.py`, `test_combat.py`, `test_conditions.py`, `test_traits.py`.

## Second fix (alternate root cause, also landed)

A companion note ("bug_5 ... 1.md") documented a second root cause: `handle_adjust_vital` had no `Max_HP` clamp for **other-target** healing. That fix also shipped — `engine/effects.py:446-450` clamps other-target HP to `min(max_hp, ...)` with `max_hp = vitals.get("Max_HP", 100)`. Both files described the same bug; this file is the consolidated record. Audited 2026-08-03.
