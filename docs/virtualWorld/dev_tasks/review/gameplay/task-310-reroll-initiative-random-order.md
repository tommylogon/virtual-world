---
group: Gameplay
---
# Reroll Initiative on Random Order

**Filed**: 2026-08-19
**Priority**: Low
**Status**: In Review — implemented 2026-08-19 (turn-queue reshuffle)

---

## Idea

When using random order in turn-based mode, reroll the initiative list at the end of the turn.

## Implemented

- `static/js/agent/turn-queue.js` — new `reshuffleRandom()` (Fisher–Yates on `agent.turnQueue`, resets index, updates `controllingPlayer` to the new first actor); called from `endTurn()` when `turnBased && turnOrder === 'random'`.
- Exported from the `TurnQueue` module.

**Verified**: `node --check` clean; full suite 980 passed.

## Notes

- Small turn-system tweak: with `random` order, reshuffle at turn end instead of keeping a fixed list.
- Real payoff for chaos in combat/tense scenes — no one can predict who acts next.

## Related

- `developer ideas.md` line 17
- Turn/initiative system (`static/js/` turn UI / agent turn scheduling)
