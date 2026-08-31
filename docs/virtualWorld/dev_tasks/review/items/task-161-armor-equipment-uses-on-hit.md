---
id: 161
title: Armor and Equipment Uses Reduced on Hit
status: todo
priority: medium
created: 2026-08-02
tags: [items, equipment, combat, durability]
---

# Armor and Equipment Uses Reduced on Hit

## Summary

Reduce armor/equipment uses when the wearer takes a hit, giving items durability without introducing new systems or values.

## Problem

Combat already reduces *weapon* uses on a hit (engine/combat.py:115-117), but armor and other worn equipment never take wear. A vest that absorbed a dozen hits is as good as new, so durability has no downside.

## Implementation

- In `player_attack` (engine/combat.py:47), when the target takes a hit, decrement `uses` on their equipped armor/defense items
- Respect `uses > 0` (skip infinite-use items, `uses = -1`)
- When armor reaches 0 uses, it breaks: log a message, remove from equipped slots, fire `on_break` trigger if present
- Optionally scale the absorbed defense by remaining uses (weaker as it degrades) — keep it optional to avoid over-engineering
- Reuse the existing `uses` field so no new schema is needed

## Files to Modify

1. `engine/combat.py` — decrement equipped armor uses on hit, break at 0
2. `engine/equipment.py` — helper to find equipped defense items and remove broken ones

## Testing

- [ ] Armor uses decrease when the wearer is hit
- [ ] Armor breaks at 0 uses and is removed from equipment
- [ ] Infinite-use armor is unaffected
- [ ] Weapon durability behavior unchanged

## Related

- [[todo/items/task-155-item-uses-affect-weight|task-155: Item uses affect weight]]
