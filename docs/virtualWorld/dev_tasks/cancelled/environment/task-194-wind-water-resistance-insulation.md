---
area: environment
type: task
status: cancelled
priority: medium
---

# Wind & Water Resistance on Clothing (Insulation)

**Filed**: 2026-08-10
**Priority**: Medium
**Status**: Todo

---

## Why

Insulation should react to wet and wind. Right now a garment contributes a flat insulation value regardless of weather, so a drenched coat protects exactly as well as a dry one.

## How

- Insulation is now a singular modifier: `effective_temp = ambient_temp + total_insulation` (equipment_bonuses.py:97,116).
- Wet on a slot can dynamically shift that garment's insulation contribution (wet coat insulates less).
- Wind in an area pushes `effective_temp` harder, with insulation resisting the wind chill.
- Keep the single-modifier model; wind/wet just modify the value before it aggregates.

## Files

- `engine/equipment_bonuses.py` — fold wind/wet modifiers into total insulation
- `engine/equipment.py` — track wet state per equipped slot
- `engine/environment_propagation.py` — wind as an area-level factor that adjusts effective_temp

## What

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Acceptance

- [ ] TODO
