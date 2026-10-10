---
type: task
status: todo
area: environment
priority: medium
blocked_by: [task-763]
---

# task-762: Forecast page: author and view the weather schedule

**Filed:** 2026-10-10
**Related:** task-227, task-229, task-231, task-234, task-555, task-556, task-758

## What

One surface to author and view forecast_schedule (task-227), extending the existing World Sky modal (static/js/sky-scape.ts) rather than building a second weather engine. The modal today shows the current sky, the next change and an override quick-set; it cannot edit the schedule entries. Add a timeline of the schedule entries laid out over the period granularity (hourly 1440 / weekly 10080 / yearly 525600 minutes, entries repeat), each editable in place (offset, weather, wind, temperature_mod, light_mod, air, message), plus mode (authored|deterministic|random|hybrid), seed and transition_table controls, over the existing GET/POST /api/settings/forecast. Columns must be honest: temperature is the derived effective outdoor value (base_temperature + diurnal/seasonal curve + climate + humidity/wind-chill), not an authored per-entry temperature; there is no precipitation model, so do not render mm; wind is magnitude only until task-555 gives direction. Random/deterministic modes are not enumerable ahead, so show the transition table rather than a fake dated forecast.

## Why

TODO

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
