---
id: 163
title: Wind as an Environmental Enum
status: todo
priority: low
created: 2026-08-02
tags: [environment, temperature, weather, propagation]
---

# Wind as an Environmental Enum

## Summary

Add `wind` as an environment enum (from no wind to hurricane), affecting temperature and heat propagation, and potentially energy and other stats/conditions.

## Problem

Environment props are `temperature`, `light`, `air`, `smell`, `noise` (area.py:10, engine/effects.py:300). There's no wind. Heat propagation (engine/environment_propagation.py:24) and heat sources don't know about airflow, so outdoor breeze or indoor draft can't affect temperature spread.

## Implementation

### Wind enum

- Add `wind` to area environment with a level enum: `none` / `breeze` / `wind` / `gale` / `storm` / `hurricane` (or 0-5 scale)
- Add to area.py defaults, environment_propagation, serialization, area description output

### Effects

- Wind accelerates heat propagation between connected areas (especially exterior areas): stronger wind → faster temperature equalization
- Wind affects effective temperature (wind chill in cold areas, cooling in hot areas) — extend `equipment_bonuses.effective_temperature` or add a wind modifier
- High wind drains more Energy per move for exterior areas (ties into vitals)
- Strong wind may extinguish or reduce light/heat sources, and can be a `sound_source`/noise factor

### Editor

- Add wind to the area editor and `set_environment` / `adjust_environment` effect keys

## Files to Modify

1. `area.py` — wind default
2. `engine/environment_propagation.py` — wind affects propagation rate
3. `engine/equipment_bonuses.py` — wind chill on effective temperature
4. `engine/effects.py` — wind in set/adjust environment
5. `routes/graph.py` + area editor JS — wind field

## Testing

- [ ] Wind level persists in area env and serialization
- [ ] Heat propagates faster in windy exterior areas
- [ ] Wind chill lowers feels-like temperature
- [ ] Hurricane-level wind has meaningful gameplay impact

## Related

- [[review/environment/task-5-heat_propagation|task-5: Heat propagation]]
- [[todo/environment/task-85-time-weather-dates|task-85: Time, weather, dates]]
