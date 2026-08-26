# Engine Config

The **Engine Config** tab (Settings → ⚙️ Engine Config) is the user-facing editor for the engine's
numeric tuning constants — the values that previously required editing Python source and
restarting to experiment with. It is task-304.

This is **not** the browser-side settings (API keys, model, graph layout) which live in the
`ConfigManager`/IndexedDB — see [[Settings & Configuration]]. Engine Config persists server-side
in `data/engine_config.json` and applies live: a saved value takes effect on the next engine call
with no restart.

## Motivation

Constants like sound penetration, heat propagation rate, and light spill are authored as hardcoded
literals in the engine. Tuning them for a scenario ("this fireplace warms the room too slowly", "a
scream should be heard three rooms away") meant finding the literal, editing Python, and restarting
the server. Engine Config centralizes those knobs in one JSON file surface in the UI.

## How it works

```
Settings → Engine Config tab
        │  GET/POST /api/settings/engine_config   (routes/settings.py)
        ▼
engine/runtime_config.py  ── reads/writes ──>  data/engine_config.json
        │  config.get(key, default)  (live, at call time)
        ▼
engine/sound.py · engine/environment_propagation.py · engine/lighting.py
```

### Storage: `engine/runtime_config.py`

- `DEFAULTS` dict — the current values, keyed by dotted name (`sound.way_open`,
  `heat.base_rate`, `light.spill_factor`). This is the source of truth for the current
  value.
- `data/engine_config.json` — optional overrides on top of `DEFAULTS`. A missing/empty file
  means "stock values"; the file is written on first save/reset.
- `config` singleton (`engine.runtime_config.config`) is loaded once at import.
- `config.get(key, default)` — reads the merged value, used by engine modules at call time.
- `RuntimeConfig.save(values)` — merges + persists + returns the merged values.
- `RuntimeConfig.reset()` — restores `DEFAULTS` and persists.
- Unknown keys in the JSON file are ignored with a warning (pruning an old key never crashes).
  Values are coerced to the `DEFAULTS` type (`int`/`bool`/`float`), so a bad hand-edit can't
  crash the engine.

### API (`routes/settings.py`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/settings/engine_config` | Returns `{values, schema, sections}` — live values + a schema (`{key: {section, label, type}}` + section descriptions) that drives the UI. Adding a `DEFAULTS`+`SCHEMA` key shows up in the menu automatically. |
| POST | `/api/settings/engine_config` | Body `{"values": {key: value, ...}}` — saves overrides and returns the merged values. |
| POST | `/api/settings/engine_config/reset` | Restores built-in defaults and persists. |

### UI: `static/js/ui/engine-config-view.js`

- **Rendering**: lit-html-driven, schema-driven. Loads via `EngineConfigView.load()` on tab
  click, renders into `#tab-engine-config`.
- Each key renders as a labeled number input (grouped by section: Sound / Heat / Light).
- 💾 **Apply** — reads all inputs, POSTs as `{values}`, re-renders with the server-coerced
  response so the fields reflect what actually persisted.
- ↩️ **Reset to defaults** — POSTs the reset endpoint, re-renders.
- Adding a new tunable requires **only** a `DEFAULTS` key + `SCHEMA` entry — no HTML/JS wiring.

## The tunables

All values come from `DEFAULTS` in `engine/runtime_config.py`. The table shows the current
defaults (the stock behavior).

### Sound (`engine/sound.py`)

Speech penetration values (how many "rooms" of sound a voice carries through open doors):

| Key | Default | Meaning |
|-----|---------|---------|
| `sound.speech_whisper` | 0 | Whisper base penetration |
| `sound.speech_normal` | 1 | Normal speech |
| `sound.speech_shout` | 2 | Shout |
| `sound.speech_scream` | 3 | Scream |

Way/door sound barrier costs (accumulated along a path; sound stops when barriers ≥ penetration):

| Key | Default | Meaning |
|-----|---------|---------|
| `sound.way_open` | 0.5 | Open doorway |
| `sound.way_closed` | 1 | Closed door |
| `sound.way_locked` | 2 | Locked door |
| `sound.way_blocked` | 2 | Blocked door |
| `sound.way_hidden` | 2 | Hidden door |
| `sound.way_see_through` | 0.75 | Window/grate (see-through) |

Ambient noise reduction (subtracted from penetration in the origin area):

| Key | Default |
|-----|---------|
| `sound.noise_silent` | 0 |
| `sound.noise_quiet` | 0 |
| `sound.noise_normal` | 1 |
| `sound.noise_loud` | 2 |
| `sound.noise_chaotic` | 2 |

> The speech/door/noise constants live in `engine/sound.py` as module-level dicts for backward
> compat (`SPEECH_LEVELS`, `WAY_BARRIERS`, `NOISE_LEVELS`), but the actual reads in
> `get_way_barrier()`, `get_area_noise_level()`, and `get_areas_hearing_speech()` are routed through
> config-backed helpers (`_speech_levels()`, `_way_barriers()`, `_noise_levels()`), so a live save
> is reflected immediately. See [[Environment/Time & Weather]] / the sound propagation docs for the
> BFS propagation itself.

### Heat (`engine/environment_propagation.py`)

| Key | Default | Meaning |
|-----|---------|---------|
| `heat.base_rate` | 0.05 | Base heat exchange rate per tick between connected areas (per tick) |
| `heat.max_delta` | 2.0 | Max °C change per single tick per connection (prevents single-tick spikes) |

The module keeps the `BASE_RATE`/`MAX_DELTA` module constants for backward compat; the propagation
functions read the live config.

### Light (`engine/lighting.py`)

| Key | Default | Meaning |
|-----|---------|---------|
| `light.spill_factor` | 0.5 | Fraction of a lit neighbor area's light that spills through an open door (`spill = max(0, int(other_light * factor))`) |

`LightingSystem.get_ambient_light()` reads the live value at call time.

## Adding a new tunable

1. Add a default to `engine/runtime_config.py` `DEFAULTS` (e.g. `"sound.new_knob": 0.5`).
2. Add a `SCHEMA` entry with `section`, `label`, and `type` (`"number"` for ints, `"float"` for
   floats).
3. In the engine module that uses it, read it via `config.get("<key>", <module default>)` — the
   helper already contains the default, so a fresh install stays at the stock value.

Done. The value will appear in Settings → Engine Config on next load.

## Related

- [[dev_tasks/review/ui/task-304-centralized-config-menu|task-304: Centralized config menu]]
- [[Settings & Configuration]]
- [[Environment/Light System]] — light spill + light levels
- [[Environment/Temperature System]] — heat propagation
- [[Environment/Time & Weather]] — tick cycle that drives propagation
- `data/engine_config.json` — the persisted overrides