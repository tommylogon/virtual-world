---
type: task
status: todo
area: gameplay
priority: high
---

# task-603: Combat adds raw ability scores to the d20 instead of ability_mod

**Filed:** 2026-09-30
**Related:** 

## Goal

combat.py:212 rolls d20 + raw STR and combat.py:213 rolls d20 + raw DEX, so STR 9 lands as +9 and DEX 11 as +11. engine/checks.py:74 already defines ability_mod() and combat never calls it. STR9 vs DEX11 gives the attacker 42.8%.

## Acceptance

- TODO
