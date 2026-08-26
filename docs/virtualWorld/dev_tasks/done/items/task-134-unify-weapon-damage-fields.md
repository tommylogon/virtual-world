---
group: Equipment & Inventory
---
# Unify Weapon Damage Fields

**Filed**: 2026-07-30 (updated 2026-07-30)  
**Priority**: Lowest  
**Status**: Review  

---

## Summary

Combine the two separate `damage` (flat) and `damage_dice` fields on weapon items into a single `damage` field that accepts dice notation like `"2d6+3"` or a flat number `"8"`.

---

## Problem

Weapons currently have two fields:
- `damage`: flat number (e.g. `8`)
- `damage_dice`: dice string (e.g. `"1d6"`)

This is confusing and inconsistent. The system uses `damage_dice` if available, otherwise falls back to `damage`. Having a single field simplifies the item schema and the parsing logic.

## Requirements

- Replace `damage` + `damage_dice` with a single `damage` field
- Accept formats: `"2d6+3"`, `"1d8"`, `"5"` (bare number = flat damage)
- Parse in `engine/equipment_bonuses.py` (already has `parse_dice()`)
- Update all weapon items in `data/library/items/` to use the new format
- Update any references in the codebase
- Migration: existing items with `damage_dice` should be read and migrated

## What was changed

- `engine/equipment_bonuses.py` — `parse_dice()` renamed to `parse_damage()`, handles both dice strings and flat numbers. `aggregate_bonuses()` reads unified `damage` field.
- `engine/combat.py` — removed duplicate `_parse_dice()` method, uses `parse_damage()` from equipment_bonuses. Removed `import re`.
- `data/library/items/iron_shortsword.json` — combined `damage: 8, damage_dice: "1d6"` → `damage: "1d6"`
- `data/library/items/heavy_club.json` — combined `damage: 10, damage_dice: "1d8"` → `damage: "1d8"`
- `data/library/items/lumber_axe.json` — combined `damage: 0, damage_dice: "1d6"` → `damage: "1d6"`
- `data/scenarios/combat_pit.json` — all weapon entries updated
- `static/js/item-library.js` — replaced separate Flat Damage + Damage Dice inputs with a single "Damage" field. Save/load/sync/diff all use unified field.
- `static/js/inspector/item-view.js` — replaced separate Flat Damage + Damage Dice inputs with single Damage field.
