---
group: Environment
---
# Scenario Clock Start Time

**Filed**: 2026-08-19
**Priority**: High
**Status**: In Review — implemented 2026-08-19 (backend endpoint + settings UI field)

---

## Idea

Allow changing the scenario's clock start time.

## Implemented

- `routes/settings.py` — `GET/POST /api/settings/clock_start`, validates HH:MM, writes `world.clock_start_hour/minute` (engine already computes the clock from these).
- `templates/index.html` — "Clock Start (HH:MM)" `<input type="time">` in the Game Clock settings group.
- `static/js/ui/settings-view.js` — `populateForm()` prefills the field from the backend when settings open.
- `static/js/ui/saveload-view.js` + `static/js/main.js` — `updateClockStart(value)` posts the new time and refreshes state.

**Verified**: full suite 980 passed; JS `node --check` clean; `routes.settings` imports.

## Notes

- Clock settings are already serialized per scenario (see `docs/virtualWorld/Environment/Time & Weather.md`); this is wiring the start time through load/save so a scenario can begin at, e.g., dawn or midnight.
- Trivial scope — mostly reading an existing setting at startup and exposing it in the editor/scenario file.
- Related to `task-301` (default turn duration): both are "scenario clock" knobs.

## Related

- `developer ideas.md` line 7
- `docs/virtualWorld/Environment/Time & Weather.md`, scenario files (`world_template.json` clock settings)
