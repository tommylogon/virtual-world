---
id: 165
title: Chance to Stun on Attack
status: done
priority: low
created: 2026-08-02
tags: [combat, conditions, gameplay]
---

# Chance to Stun on Attack

## Summary

Add a chance to stun the target when an attack hits — e.g. a heavy hit from a slasher can leave the target needing to rest for a turn.

## Problem

Combat resolves damage but has no crowd control (engine/combat.py). A hit either deals damage or misses; there's no way for a hit to stagger the target. Conditions exist (engine/conditions.py, player.py:7-33) but nothing in combat applies `stunned`/`paralysed` to a hit target.

## Implementation

- Add a stun chance on hit, driven by weapon properties: `stun_chance` (e.g. 0-100) on the weapon, plus maybe a `stun_duration` in turns
- On a successful hit, roll for stun; if it succeeds, apply the `stunned` condition to the target for the duration
- `stunned` already exists in the condition hierarchy (player.py CONDITION_HIERARCHY) — make sure it blocks acting (BLOCKING_CONDITIONS may need `stunned` added; currently it has `paralysed` but not `stunned`)
- A stunned character: can't act for N turns, then recovers (state_timer handles countdown)
- Log it clearly: `[COMBAT] Hit landed a stunning blow! X is stunned.`

## Files to Modify

1. `engine/combat.py` — stun roll on hit ✅
2. `player.py` — `stunned` added to BLOCKING_CONDITIONS, CONDITION_HIERARCHY, CONDITION_DEFAULT_TIMERS (2 ticks) ✅
3. `routes/items_registry.py` — `stun_chance`/`stun_duration` copied in build + refresh; `static/js/item-library.js` — Stun Chance/Duration fields in the weapon editor ✅

## Testing

- [x] Weapon with stun_chance can stun a target
- [x] Stunned target can't act for the duration
- [x] Stun wears off via state_timer
- [x] No stun when the weapon has no stun_chance

**Implemented 2026-08-02** — `CombatSystem.player_attack` rolls `stun_chance` (0-100) on a weapon hit; success applies `stunned` + `state_timer = max(timer, stun_duration)` and logs `[COMBAT] X's hit with Y stuns Z!`. `stunned` blocks acting via `BLOCKING_CONDITIONS` and expires via the standard timed-condition path. Tests in `tests/test_combat.py::TestStunOnAttack` (4 tests).

**Status: DONE** — moved to `done/gameplay/`.

## Related

- [[todo/gameplay/task-159-saves-and-reactions|task-159: Saves and reactions]]
- [[todo/gameplay/task-131-stateful-actions-over-time|task-131: Stateful actions (conditions)]]
