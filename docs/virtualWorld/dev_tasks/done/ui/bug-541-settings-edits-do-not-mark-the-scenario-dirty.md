---
type: bug
status: done
area: ui
priority: medium
---

# bug-541: Settings edits do not mark the scenario dirty

**Filed:** 2026-10-10
**Related:** task-234, task-228, task-753

## What

The top-bar scenario chip is dirty when world._edit_seq != world._commit_seq (routes/saveload.py scenario_status). The after_request autosave hook in app.py bumped _edit_seq only for paths containing /api/graph/, /api/players/, /api/build/ or /api/world/ — so POST /api/settings/date (also clock_start, time_per_tick, forecast, forecast-override, narration, ghost_mode, mature_content) mutated scenario-persisted state (time_ticks, clock_start_hour, forecast_schedule, calendar_config, narration_mode, ghost_mode, mature_content) but never marked the world dirty. Since /api/scenario/commit just sets _commit_seq = _edit_seq, a settings edit was invisible to Commit and the user was never prompted. Fix: include the scenario-persisted settings in the dirty bump, excluding the app-global settings (engine_config, equip_slots, auto_generate_descriptions) which do not live in the scenario; a settings edit pushes no undo entry so a time-skip does not flood the undo history with 'world edit'. Verified live on a running app: clean dirty=False, POST /api/settings/engine_config stays False (excluded), POST /api/settings/date flips to True.

## Why

TODO

## How

TODO

## Steps to verify

1. GET /api/scenario/status; POST /api/settings/engine_config {values:{}}; POST /api/settings/date {}; re-GET status.
   - expected: engine_config excluded (dirty stays false); date is a scenario edit (dirty true).
   - observed (2026-10-10, live): dirty false -> engine_config 200 -> dirty false -> date 200 -> dirty true.

## Acceptance

- [x] POST /api/settings/date flips the dirty chip true (measured false -> true).
- [x] POST /api/settings/engine_config stays clean (measured false -> false).

## Files

- TODO
