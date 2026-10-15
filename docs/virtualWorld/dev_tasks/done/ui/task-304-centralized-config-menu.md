---
area: ui
status: done
type: task
priority: medium
---

# Centralized Config Menu for Engine Constants

**Filed**: 2026-08-19
**Priority**: Low
**Status**: In Review — implemented 2026-08-20, pending browser E2E

---

## Idea

Centralized config menu for all constants — sound propagation values, heat propagation, light spill, and any other values that currently require a code change to test and adjust.

## Implementation (2026-08-20)

### Backend
- **`engine/runtime_config.py`** (new) — single source of truth for the tunables.
  - `DEFAULTS` dict holds the current values (sound speech/war barriers/noise levels,
    heat `base_rate`/`max_delta`, light spill).
  - Loads optional overrides from `data/engine_config.json` at import; missing/empty
    file → stock values. Unknown/malformed keys are logged and skipped; values are
    coerced to the default's type so a bad hand-edit can't crash the engine.
  - `config.get(key, default)` is called by the engine modules at runtime — a saved
    value applies with no restart.
  - `RuntimeConfig.save(values)` merges + persists; `reset()` restores defaults.
- **Engine modules now read config live** (defaults unchanged unless overridden):
  - `engine/sound.py` — `SPEECH_LEVELS`/`WAY_BARRIERS`/`NOISE_LEVELS` reads go through
    config-backed helpers `_speech_levels()`, `_way_barriers()`, `_noise_levels()`;
    see-through barrier `sound.way_see_through`.
  - `engine/environment_propagation.py` — `BASE_RATE`→`_heat_base_rate()`,
    `MAX_DELTA`→`_heat_max_delta()`.
  - `engine/lighting.py` — spill `0.5` → `_spill_factor()` (adds module const `SPILL_FACTOR`).
  - Backward-compat module-level constants (`sound.SPEECH_LEVELS`, etc.) are kept as
    snapshot exports for importers/tests.
- **Routes** in `routes/settings.py`:
  - `GET /api/settings/engine_config` → `{values, schema, sections}` (schema drives a
    schema-less frontend; a new `DEFAULTS` key shows up in the UI automatically once it
    gets a `SCHEMA` entry).
  - `POST /api/settings/engine_config` → merge + persist; `POST
    /api/settings/engine_config/reset` → restore defaults.

### Frontend
- **`static/js/ui/engine-config-view.js`** (new) — lit-html-rendered editor (`window.EngineConfigView`).
  Renders one labeled number input per key grouped by section (Sound / Heat / Light),
  with 💾 **Apply** (POSTs the form) and **↩️ Reset to defaults** buttons. Loads on
  tab click via `EngineConfigView.load()`; re-renders with server-coerced values after
  each save.
- **`templates/index.html`** — new settings tab button + pane
  (`tab-engine-config`), script tag loaded after `settings-view.js`.

### Tests
- **`tests/test_engine_config.py`** (new, 5 tests): GET shape/schema, save persists +
  engine reads live, sound/light live override, reset, unknown/bad keys ignored.
  Uses a tmp-file-backed singleton (fixture swaps `runtime_config.config._config_file`).
- Full suite: **1021 passed** (3 pre-existing failures in test_trigger_system.py
  unchanged), 1 skipped.

## Usage

Settings → ⚙️ **Engine Config** → edit values → 💾 Apply. File persisted in
`data/engine_config.json`.

> User-facing documentation: `docs/virtualWorld/UI & Settings/Engine Config.md` (full key table,
> "add a new tunable" recipe). Cross-referenced from `Settings & Configuration.md`,
> `Environment/Light System.md`, `Environment/Temperature System.md`, and
> `Environment/Time & Weather.md`.

## Notes

- This is the "user-facing version" of tuning constants by editing code.
- Keep the MVP tight: one JSON config file + a route to read/write it + a simple editor panel.
- Related: `task-301` (turn duration default is the exact kind of constant this exposes).

## Files

- `engine/runtime_config.py` (new)
- `engine/sound.py`, `engine/environment_propagation.py`, `engine/lighting.py`
- `routes/settings.py`
- `static/js/ui/engine-config-view.js` (new)
- `templates/index.html`
- `tests/test_engine_config.py` (new)
- `data/engine_config.json` (generated on first save)

## Related

- `developer ideas.md` line 11
- `config` module / constants in engine modules (sound, lighting, environment_propagation)

## What

TODO

## Why

TODO

## How

TODO

## Steps to verify

1. Open Settings → ⚙️ Engine Config and read `sound.way_see_through`.
   - expected: the row is grouped under Sound and starts from the server's
     current value (default 0.75 when no override is saved).
2. Change that value to 0.65 and click 💾 Apply; reopen Engine Config and then
   call `GET /api/settings/engine_config`.
   - expected: the input and endpoint both report 0.65, and the save toast
     confirms the value was applied without restarting.
3. Click ↩️ Reset to defaults and reload the settings tab.
   - expected: `sound.way_see_through` returns to 0.75 and other tunables
     return to their declared defaults.
   - observed: this card records tests for live engine reads and reset; no
     browser run of the settings tab is recorded.

## Browser UI and intended live verification

Intended UI home: Settings modal → ⚙️ Engine Config → Sound / Heat / Light.

Current availability: The schema-driven editor, Apply, and Reset to defaults
are implemented. The Settings tab is loaded on click from the modal; the task
records backend tests but marks browser E2E pending.

Live steps when available:
1. Open Settings → Engine Config and locate `sound.way_see_through` under Sound.
   - expected: its current server value is shown in the numeric field.
2. Change it from 0.75 to 0.65 and click Apply; inspect the toast and reopen
   the tab.
   - expected: the value reads 0.65 after the reload and the engine uses the
     changed setting without a server restart.
3. Click Reset to defaults.
   - expected: the field returns to 0.75 and other values return to their
     schema defaults.

This section defines intended access and live acceptance. It is not a claim
that planned UI exists or works today.

## Acceptance

- [ ] TODO
