---
id: 156
title: Weight Affects Energy Decay
status: todo
priority: low
created: 2026-08-02
tags: [items, weight, vitals, movement]
---

# Weight Affects Energy Decay

## Summary

Make carried weight affect energy cost, at least on movement. Carrying a heavy load should drain energy faster when moving.

## Problem

`ACTION_COSTS["move"]` is a flat `{time: 1, energy: 1}` (virtual_world_engine.py:82) and movement applies it directly (engine/movement.py:245). Total carried weight is never factored in, so a character hauling a hundred kilos moves at the same energy cost as one carrying nothing.

## Implementation

- Compute total carried weight from `EDGE_CARRYING` edges to the player node
- Add a weight threshold multiplier to the move energy cost: e.g. baseline `energy` cost scales up beyond a comfortable weight limit
- Either in `TickManager.apply_action` (engine/tick_manager.py:23) or in `movement.py` where `apply_action("move", ...)` is called
- Consider a `carry_limit` / `max_carry_weight` on the player (ties into encumbrance)
- Keep it configurable per character (a strong character carries more with less penalty)

## Files to Modify

1. `engine/tick_manager.py` — weight-modulated move cost
2. `engine/movement.py` — pass carried weight into the move action cost
3. `player.py` — optional carry capacity field

## Testing

- [ ] Heavily loaded character loses more energy per move
- [ ] Empty-handed character matches current cost (no regression)
- [ ] Weight thresholds are sensible (light load no penalty)
- [ ] Container contents count toward carried weight

## Related

- [[todo/items/task-155-item-uses-affect-weight|task-155: Item uses affect weight]]
