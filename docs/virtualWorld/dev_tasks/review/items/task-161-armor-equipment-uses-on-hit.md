---
id: 161
title: Armor and Equipment Uses Reduced on Hit
status: review
priority: medium
created: 2026-08-02
tags: [items, equipment, combat, durability]
type: task
area: items
related: [task-155]
---

# Armor and Equipment Uses Reduced on Hit

<!-- deps:start -->
**Related:** [[task-155-item-uses-affect-weight]]
<!-- deps:end -->

## What

Reduce armor/equipment uses when the wearer takes a hit, giving items durability without introducing new systems or values.

## Why

Combat already reduces *weapon* uses on a hit (engine/combat.py:115-117), but armor and other worn equipment never take wear. A vest that absorbed a dozen hits is as good as new, so durability has no downside.

## How

- In `player_attack` (engine/combat.py:47), when the target takes a hit, decrement `uses` on their equipped armor/defense items
- Respect `uses > 0` (skip infinite-use items, `uses = -1`)
- When armor reaches 0 uses, it breaks: log a message, remove from equipped slots, fire `on_break` trigger if present
- Optionally scale the absorbed defense by remaining uses (weaker as it degrades) — keep it optional to avoid over-engineering
- Reuse the existing `uses` field so no new schema is needed

## Files to Modify

1. `engine/combat.py` — decrement equipped armor uses on hit, break at 0
2. `engine/equipment.py` — helper to find equipped defense items and remove broken ones

## Steps to verify

- [ ] Armor uses decrease when the wearer is hit
- [ ] Armor breaks at 0 uses and is removed from equipment
- [ ] Infinite-use armor is unaffected
- [ ] Weapon durability behavior unchanged

## Related

- [[todo/items/task-155-item-uses-affect-weight|task-155: Item uses affect weight]]

## Acceptance

- [ ] TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: equip armor in Character Inventory/Paperdoll → take a controlled hit in combat → inspect the armor's remaining uses/durability and the combat log.

Current availability: the card proposes consuming equipment uses when its wearer takes a hit. No durability-on-hit behavior is claimed as implemented.

Live steps when available:
1. Equip one armor item with a known `uses` count, record the count, then have the wearer receive a hit with a known damage result.
   - expected: the armor's uses decrease by the documented amount and the combat log identifies the armor interaction; the wearer takes damage after the existing defense rules.
2. Repeat with an attack that misses.
   - expected: a missed attack does not consume a use if the design ties wear to an actual hit.
3. Continue until the item reaches zero uses and inspect Inventory/Paperdoll.
   - expected: the item follows the generic `uses` depletion behavior and no separate durability counter is introduced.
4. Save/reload and inspect the armor and wearer.
   - expected: remaining uses and equipment state persist without duplicating the item.

This section is not a claim that armor wear on hit is implemented today.
