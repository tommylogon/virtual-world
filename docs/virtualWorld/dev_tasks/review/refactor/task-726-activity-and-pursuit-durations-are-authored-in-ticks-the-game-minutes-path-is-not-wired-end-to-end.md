---
type: task
status: review
area: refactor
priority: medium
---

# task-726: Activity and pursuit durations are authored in ticks; the game-minutes path is not wired end to end

**Filed:** 2026-10-06
**Related:** task-702, task-716, task-569

## Goal

Durations should be authored in game minutes, not ticks. Activities already track both units deliberately (engine/activities.py:469 - duration_ticks predates the author-in-game-minutes rule, duration_minutes counts game time), but the plan step and start_activity effect only read duration_ticks, and background_plans._satisfied compares a duration_minutes value against elapsed_ticks. Fix the unit comparison, wire duration_minutes through start_activity, and convert the authored templates (data/library/pursuit_templates/fish-and-bring-home.json, data/library/items/angling_rod.json) to minutes.

## Measured evidence (2026-10-06)

`engine/activities.py:469-479` states the intent directly: *"Two units, deliberately.
`duration_ticks` counts turns and predates the author-in-game-minutes rule;
`duration_minutes` counts game time."* Both `elapsed_ticks` and `elapsed_minutes` are
tracked (`engine/activities.py:242-245`). The minutes path is incomplete:

- **Unit-comparison bug.** `background_plans.py:196-199` (`_satisfied`, `kind ==
  "activity"`) reads `duration = step.get("duration_ticks") or step.get("duration_minutes")`
  then compares it against `activity.get("elapsed_ticks", 0)`. A `duration_minutes` value
  is therefore compared against ticks. The correct dual-unit logic already exists in
  `_check_activity_completion` (`background_plans.py:140-144`) and
  `engine/activities.py:476-479`; the inline step path does not use it.
- **`start_activity` only takes ticks.** `background_plans.py:276-288` resolves
  `duration = duration_ticks or duration_minutes` and passes it as the `duration_ticks`
  argument to `ActivitySystem.start_activity`, whose signature is `duration_ticks:
  Optional[int] = None` (`engine/activities.py:117`, `:673`). A minutes value is silently
  used as a tick count.
- **The `start_activity` effect only takes ticks.** `engine/effect_handlers/activities.py:8,20`
  reads `params.get("duration_ticks")` only.
- **Authored data uses ticks.** `data/library/pursuit_templates/fish-and-bring-home.json`
  (`"duration_ticks": 120`), `data/library/items/angling_rod.json`
  (`start_activity` -> `"duration_ticks": 120`), and `data/library/activities/fishing.json`
  (`tick.interval_ticks: 5`) all author in ticks.

Note: `engine/effect_handlers/activities.py` exists, so the `start_activity` effect is
implemented; task-716's "missing `start_activity` effect" line is stale and should be
re-checked when 716 is next updated.

## Acceptance

- `duration_minutes` is compared against `elapsed_minutes` everywhere a duration is
  resolved (fix `background_plans.py:196-199`).
- `start_activity` (engine + effect handler) accepts and honours `duration_minutes`; a
  minutes value is never used as a tick count.
- The authored templates and the fishing activity definition are converted to minutes, or
  the tick fields are removed so only one unit is authored.
- A regression test proves a minutes duration elapses in game minutes, not ticks.

## Implemented (2026-10-06)

- **Unit bug fixed** in `background_plans.py::_satisfied` — `duration_minutes` is
  now compared against `elapsed_minutes`, `duration_ticks` against
  `elapsed_ticks` (previously the minutes value was compared against ticks).
- **`start_activity` accepts minutes** (`engine/activities.py`): new
  `duration_minutes` parameter, stored on the activity with an initialised
  `elapsed_minutes` (the tick loop already accumulates it at `:245`). Also
  `background_plans` passes the two units separately instead of collapsing them.
- **`start_activity` effect** (`engine/effect_handlers/activities.py`) reads and
  forwards `duration_minutes`; module gained its `@module`/`@contributes`/`@docs`
  headers (it was one of three flagged as missing the contract).
- **Authored data converted to minutes**: `data/library/pursuit_templates/fish-and-bring-home.json`
  and `data/library/items/angling_rod.json` now use `duration_minutes: 120`
  (the numeric value was kept from the previous `duration_ticks: 120`; confirm
  this is the intended game time — a tick is `time_per_tick_minutes`).
  `fishing.json`'s `tick.interval_ticks` is a sampling cadence, not a duration,
  and is left alone.
- **Regression test** `tests/test_activity_duration.py` (4 tests): a minutes
  duration elapses on `elapsed_minutes` and is *not* satisfied by a large tick
  count; `start_activity` stores `duration_minutes`.

Caveat: not yet verified live — the running server needs a restart to load the
change, and the 120-minute value needs a human confirm.

## Non-goals

- The activity-step executor itself (task-702).
- The pursuit slice flow (task-716).
