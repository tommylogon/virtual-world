---
type: task
status: review
area: environment
priority: medium
related: [task-763, task-227, task-557, task-745, task-746, task-747]
---

# task-772: Weather types are a closed enum; make them per-scenario data (enables extreme + setting-specific weather)

**Filed:** 2026-10-10
**Related:** task-763, task-227, task-557, task-745, task-746, task-747

<!-- deps:start -->
**Related:** [[task-763-weather-generator-seeded-terrain-aware-dated-weather-field-with-date-and-area-overrides]], [[task-227-environment-forecast-schedule]], [[task-557-worldpainter-climate-layer-paint-a-coarse-climate-compile-it-to-base-temperature]], [[task-745-worldpainter-hazards-a-current-strength-paint-layer-plus-a-hazards-json-category-table]], [[task-746-a-single-roll-hazard-effect-one-check-branch-forced-move-and-a-sweep-guard-against-cascades]], [[task-747-worldpainter-compiler-emits-terrain-hazards-river-cliff-thorn-fall-from-the-painted-layers]]
<!-- deps:end -->

## What

WEATHER_STATES is a hardcoded list (clear/cloudy/windy/rainy/stormy/foggy/snowy) spread across 19 sites: engine/weather_forecast.py (WEATHER_ALIASES, WEATHER_TIME_DC, WEATHER_LIGHT_MULT), engine/area_description.py prose, engine/effect_handlers/environment.py (adjust_weather validates against it), routes/action_handlers.py (guess-time skill DC) and static/js/sky-scape.ts (WEATHER_CHIP icons). A scenario therefore cannot express setting-specific weather: no acid rain for cyberpunk, no ion storm or lethal sunrise for sci-fi (Riddick's Crematoria), no sandstorm, flash freeze or blood rain. Open the vocabulary into a data-driven weather-type registry - one record per type, per scenario, following the data/library/<type> pattern - carrying id, name, icon, kind (normal|extreme), light multiplier, wind/humidity/temperature tendency, guess-time DC and prose, plus an optional effect payload for extremes with teeth (acid rain damages, flash freeze freezes water, a tornado forces movement; reuse the effect/trigger machinery or hazards.json, task-745/746). Then normalize_weather, the DC table, the light multiplier, the prose and the UI icon all become registry lookups instead of parallel maps, so they cannot drift (the same one-copy rule bug-54 was). The Markov generator (task-763) then references registry ids and can author rare, gated extremes. Constraint: the registry must work for any setting, never tuned to one world.

## Why

Two problems, one cause. First, the seven weather words are hardcoded in Python, so a world can only ever use those seven: a cyberpunk setting cannot have acid rain and a sci-fi setting cannot have an ion storm, because there is no way to name them without a code change. Second, the same seven words and their data - the guess-time DC, the light multiplier, the prose sentence, the UI icon - are written out again in several separate places, so editing one leaves the rest stale; bug-54 was a light table nothing read, and the guess-time DC had already grown a second copy in the action handler. Putting the vocabulary in the library (data/library/weather) fixes both: a world adds or edits a weather type as data, and every reader looks it up in one place so the copies cannot disagree. It is also a precondition for the generator (task-763), because setting-specific extremes have to exist as named types before anything can roll for them.

## How

Mechanism: make weather types a library registry exactly like biomes, so add/edit/remove and tags come from the existing editable surface instead of new code. Add one entry to VOCABULARY_TYPES (routes/library_ops.py:421): 'weather': {'backing': 'dir', 'dir': 'weather'}. Records live at data/library/weather/<id>.json with name, description, tags and an optional triggers/effects payload - the same shape item records already carry (see data/library/items/ace_bandage.json, which holds a trigger with an adjust_vital effect). Because 'weather' becomes a vocabulary type, the browse + create/update + delete + rename endpoints (handle_library_create_or_update, handle_library_delete, handle_library_rename) serve it for free - no new CRUD, and tags filter like every other library type. Each record carries id, name, icon, kind (normal|extreme), light_mult, wind/humidity/temperature tendency, guess-time DC and prose, plus the effect payload for extremes with teeth (acid rain damages, flash freeze freezes water, a tornado forces a move). The teeth can reference a hazard id: 'hazards' is already a VOCABULARY_TYPES entry backed by data/worldpainter/hazards.json (task-745), so an extreme weather type can point at a hazard rather than inventing an effect vocabulary. Then engine/weather_forecast.py (normalize_weather, WEATHER_TIME_DC, WEATHER_LIGHT_MULT), engine/area_description.py prose and static/js/sky-scape.ts WEATHER_CHIP all read the registry (or the served vocabulary API) instead of their own hardcoded copies, which is the one-copy rule bug-54 established.

## Steps to verify

1. The registry is the single source.
   - expected: `WEATHER_STATES` / `WEATHER_TIME_DC` / `WEATHER_LIGHT_MULT` / `WEATHER_PROSE` derive from `data/library/weather/*.json`; with the directory absent they fall back to the original seven.
   - observed: `tests/test_weather_types.py` 7 passed (registry loads in canonical order; stormy reads DC 20 / light 0.3; pointed at a tmp dir holding `acid_rain.json` the new id appears and its light_mult 0.4 is read; absent dir falls back to the seven).
2. No drift and no regression in existing readers.
   - expected: the weather / narration / description suites are unchanged.
   - observed: 133 passed across `test_weather_types`, `test_weather_narration`, `test_area_description`, `test_open_sky`, `test_timeskip`.
3. The gate catches a broken record.
   - expected: missing fields, an id/filename mismatch, or an unreachable type are reported.
   - observed: `python tools/weather_library_check.py --report` reports 7 records, 0 errors, 1 warning (`snowy: unreachable - no transition enters it`); exit 0.
4. The front-end reads the registry (pending).
   - expected: `sky-scape.ts` `WEATHER_CHIP` renders from the served vocabulary, built-in map as fallback.
   - observed: TODO - still hardcoded.

## Acceptance

- [x] `weather` is a library registry: `data/library/weather/<id>.json`, registered in `VOCABULARY_TYPES` (`routes/library_ops.py`) — so add/edit/remove and tags come from the existing library surface
- [x] Save is validated: `_vocabulary_problems` routes `weather` to `engine.weather_types.record_problems` (found live — it had no branch and fell through to the *floor-plan* validator). Verified on a running app: `POST /api/vocabulary/weather/acid_rain` 200 and it appears in the list, a record missing `icon` 400, `DELETE` 200 and the list is back to seven
- [x] `engine/weather_types.py` loads the records and derives `WEATHER_STATES` / `WEATHER_TIME_DC` / `WEATHER_LIGHT_MULT` / `WEATHER_PROSE`, falling back to the original seven when the directory is absent
- [x] `engine/weather_forecast.py` re-exports the registry names (existing imports unchanged); `engine/area_description.py` prose now reads the registry
- [x] `tools/weather_library_check.py` validates records and flags an unreachable type (it already flags `snowy`); wired into `npm run precommit` (+ `npm run weather:check`)
- [x] Tests: `tests/test_weather_types.py` (registry loads, fallback, a new record is picked up); weather/open-sky/area-description/timeskip suites green
- [x] `static/js/sky-scape.ts` fetches `/api/vocabulary/weather` and renders icons from the registry, with the built-in `WEATHER_CHIP` map as the pre-fetch and spelling fallback; the route now ships `aliases` so an authored value resolves to its canonical icon. Live: the widget shows `☁️ overcast` (was `☀️`), request 200; front-end gate green

## Files

- `data/library/weather/<id>.json` (new) - 7 records: clear, cloudy, windy, rainy, stormy, foggy, snowy
- `engine/weather_types.py` (new) - registry loader + derived tables + `normalize_weather` / `weather_light_mult`
- `engine/weather_forecast.py` (modified) - re-exports the registry names; moved the literals out
- `engine/area_description.py` (modified) - `WEATHER_PROSE` now imported from the registry
- `routes/library_ops.py` (modified) - `weather` added to `VOCABULARY_TYPES`
- `tools/weather_library_check.py` (new) - the guard; wired into `package.json` (`weather:check`, `precommit`)
- `tests/test_weather_types.py` (new), `tests/test_weather_narration.py` (modified) - alias + registry tests
- `AGENTS.md` (modified) - gate-table row for `data/library/weather/`
- `static/js/sky-scape.ts` (pending) - `WEATHER_CHIP` still hardcoded
