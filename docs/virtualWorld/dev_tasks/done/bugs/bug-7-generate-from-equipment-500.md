# Bug 7: "Generate from Equipment" bio button → 500 Internal Server Error

**Filed**: 2026-07-23
**Priority**: High
**Status**: Fixed

## Summary

Clicking "Generate from Equipment" in the character inspector's bio tab causes a POST to `/api/players/Kaelen%20Voss/generate-description` that returns a 500 error.

## Root Cause

Method name mismatch between `virtual_world_engine.py` and `engine/equipment.py`.

`virtual_world_engine.py:422` calls `self.equipment.update_equipment_description(p)` (no underscore), but `engine/equipment.py:341` defines the method as `_update_equipment_description(self, player)` (with underscore prefix). `EquipmentSystem` has no attribute named `update_equipment_description`, so an `AttributeError` is raised.

The route handler in `routes/players.py:355` catches this and returns a 500.

## Fix

Either:
- Add a public alias `update_equipment_description` in EquipmentSystem that delegates to `_update_equipment_description`, or
- Change `virtual_world_engine.py:422` to call `self.equipment._update_equipment_description(p)` directly

## Files

- `virtual_world_engine.py:422` — calls wrong method name
- `engine/equipment.py:341` — method defined with different name
- `routes/players.py:345-356` — route that returns 500 on exception
