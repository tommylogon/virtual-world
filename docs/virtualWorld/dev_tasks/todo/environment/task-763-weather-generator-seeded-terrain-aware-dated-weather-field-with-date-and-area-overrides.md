---
type: task
status: todo
area: environment
priority: medium
---

# task-763: Weather generator: seeded, terrain-aware, dated weather field with date and area overrides

**Filed:** 2026-10-10
**Related:** task-227, task-231, task-234, task-555, task-556, task-557, task-758, task-762

## What

A heuristic weather field a world can generate over a dated horizon (e.g. a month) and that the forecast view (task-762) reads. Seeded from the world so the horizon is reproducible. Per scope/area, terrain modifies the heuristic: reuse the existing thermal baseline (base_temperature, season, temp_curve_for_hour) plus the climate paint layer (task-557) and the biome/area tags the compiler already writes (world_compile.py), instead of a second climate model: elevation/mountain colder and snowier, coast wetter and foggier, forest humid, desert dry. Overrides are ordered patches with one precedence chain: area override > date override > generated heuristic > authored schedule > default. Extend engine/weather_forecast.py and world.forecast_schedule; the authored schedule becomes one input mode, not the whole system. New state only where the model genuinely lacks it: precipitation amount (there is no mm/accumulation field today) and wind direction (task-555, todo). This field is what task-762 renders and what task-556's effects consume; without task-555/556 the field is decorative.

## Why

This generator was already designed, in pieces, before this card. docs/design/weather-world-integration.md sets the layering rule (world -> clock+season -> forecast+override -> interior physics -> presentation), the base_temperature vs temperature split, and an ordered plan (task-553 base_temperature+curve, task-554 season, task-555 wind direction, task-556 weather reaches the world, task-557 climate paint layer). It also measures why a spatial field cannot exist today: outdoor temperature is one global 21 C applied to every exterior area, and forecast.apply_scope is a two-way exterior/all switch, not a field. The terrain vocabulary the heuristic needs is designed in docs/design/world-environment-taxonomy.md: 170 categories carrying Climate and Elevation fields and a temperature x moisture matrix, though only 16 biomes ship as data. The user's own notebook (docs/design/notebook-notes.md) already frames weather / temp / climate as map overlays plus a heightmap with a colour key to features and biomes. Correction: weather-world-integration.md Section 8 had listed 'a procedural weather simulation' and 'per-area seasons' as Non-goals, reading the forecast as authored / state-machine only. That was a misreading of the intended design, not a decision; the doc was corrected 2026-10-10 to record the heuristic generator as the target. Seeded heuristic generation of a dated, terrain-aware, per-area weather field is the actual intent; the authored modes are inputs to it, not the ceiling. Treat Section 7 (open questions: lapse rate, snow accumulate-or-boolean, humidity source) as the unresolved decisions this card inherits.

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Acceptance

- [ ] TODO

## Files

- TODO
