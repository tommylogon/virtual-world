# Sky Widget — Reconciled Design (A)

Reference note reconciling the **qwen/GLM sky-stage mockups** (`docs/design/sky-clock-mockup-v1.html`, `sky-clock-mockup-v2-real-moon.html`) with the **roadmap 3.3** spec (`docs/virtualWorld/dev_tasks/environment-roadmap.md`) and the **implementation** in `static/js/sky-scape.js` + `engine/weather_forecast.py`.

## Source materials

| File | Source | What |
|------|--------|------|
| `sky-clock-mockup-v1.html` | Qwen assistant | Full animated sky stage + slider (demo, no engine wiring) |
| `sky-clock-mockup-v2-real-moon.html` | GLM assistant | v1 + realistic moon physics (rise/set, elongation glare, phase terminator) |
| `environment-roadmap.md` §3.3 | Tommy | **Compact top-bar widget** + **World Sky editor panel** (stage + forecast/override/date controls) |
| `Time & Weather.md` (canonical spec) | Team | Forecast engine, moon 30-day cycle, wind/humidity tables, trigger integration |
| `sky-scape.js` (this session) | Implementation | Port of the stages into an engine-driven module; top-bar + modal |

## What was adopted

### From the mockups (display layer)

- **Sky stage gradient** (`skyAt()`): the v1 gradient keyframes ported directly (hour→color pair).
- **Sun arc**: position/animation logic from v1, with dimming via weather.
- **Moon arc**: v2's `age = day/30` + `moonrise = sunrise + age × 24h` + `moonset = rise + dayLen` — correct real-lunar behavior. Used in the stage and the readout.
- **Season palettes**: v1's `SEASON_STYLE` map (spring/summer/autumn/winter hill colors, sunrise/sunset times).
- **Weather layers**: clouds, rain streaks, snow flakes, fog overlay, dimming — all ported from the mockup's `WEATHER_LAYER` table.
- **Reduced-motion** respect: low-OP computing; kept the `transition: opacity .4s` on the stage.
- **Moon phase chips**: `MOON_CHIP` emoji map from v2.

### From the roadmap (product layer)

- **Top-bar widget**: `renderTopBar(el, state)` replaces the bare `#ui-time` clock with a compact line: `🕐 08:37 · Day 3 of 27 (Aug 2084) · 🌙 waning · ☀️ clear · ☔ next change in 2h`.
- **World Sky panel**: modal with the stage as the centerpiece, time skips (`+15m`/`+1h`/`+1 day`), weather override dropdown + duration + Set/Clear buttons, moon phase readout, forecast-next-change indicator, GM override indicator.
- **Engine drive**: EVERYTHING is read from `/api/state`: `game_time`, `game_day/month/year`, `moon_phase`, `forecast_schedule`, `forecast_override`. The mockup's independent chips are replaced by read-only derived displays (season from month, weather from effective forecast, moon from `get_moon_phase()`).
- **Forecast next-change** helper: `nextForecastChange(state)` computes the next entry offset from the current time, returning human-readable delta + weather.

### What was left out (v1 scope cuts)

| Mockup feature | Reason |
|----------------|--------|
| **Flow** (animated hour-per-0.5s rAF) | Demo affordance; real panel uses clickable time skips that call engine APIs |
| **Lightning flashes** | Stormy weather layer only — lightning is a visual treat but adds no authoring value in v1 |
| **Tree silhouettes** | Seasonal tree styling in the hills — low ROI; ground+hill is enough |
| **Realistic moon terminator** | v2's shadow disc per phase was nice but the emoji + readout is sufficient |
| **Drag-to-set-time slider** | v1's time slider; replaced by discrete skip buttons (+15m/+1h/+1 day) |
| **Per-area override** | `forecast_override` is global in v1; per-area is a future extension |

## Implementation architecture

```
┌───────────────┐     ┌──────────────────────┐
│  Engine tick  │ ──→ │  engine/weather_forecast.py  │
│  tick_turn()  │     │  ForecastSchedule     │
│               │     │  get_moon_phase()     │
└──────┬────────┘     └──────────┬───────────┘
       │                        │
       ▼                        ▼
┌──────────────────────────────────────┐
│  /api/state (action_handlers.py)     │
│  game_day · moon_phase · forecast    │
│  schedule · override                  │
└───────────────┬──────────────────────┘
                │
                ▼
┌──────────────────────────────────────┐
│  static/js/sky-scape.js              │
│  renderTopBar() → #ui-time           │
│  World Sky modal → stage + controls  │
│  effectiveWeather() / nextChange()    │
└──────────────────────────────────────┘
```

## Files changed / created (this session)

### Engine
- `engine/weather_forecast.py` — NEW: ForecastSchedule, get_moon_phase, wind/humidity tables
- `virtual_world_engine.py` — calendar_config, forecast_* fields, game_day/month/year properties, `_forecast_tick()`, `_fire_time_triggers()`, `set_game_time()`, `set_game_date()`, `current_moon_phase()` (blood_moon aware)
- `engine/tick_manager.py` — forecast_tick hook, wind extinguish, wind energy drain, on_turn_start/end hooks, humidity social
- `engine/lighting.py` — moon_provider + moon night-light bonus (weather-gated)
- `engine/equipment_bonuses.py` — effective_temperature wind/humidity kwargs, aggregate wind_resistance/water_resistance
- `engine/environment_propagation.py` — wind multiplier on heat propagation
- `engine/effects.py` — import WEATHER_HANDLERS
- `engine/effect_handlers/environment.py` — weather/wind/humidity/transparent keys + adjust cycling
- `engine/effect_handlers/weather.py` — NEW: set_time, set_date, set_weather, forecast_override, adjust_forecast
- `engine/runtime_config.py` — forecast.apply_scope key
- `engine/serialization.py` — save/load calendar_config, forecast_schedule, forecast_override

### Routes
- `routes/action_handlers.py` — /api/state exposes game_day/month/year, moon_phase, forecast_schedule, forecast_override
- `routes/settings.py` — GET/POST /api/settings/forecast, POST /api/settings/forecast-override

### Frontend
- `static/js/sky-scape.js` — NEW: engine-driven sky widget (top-bar + modal stage + controls)
- `templates/index.html` — script include for sky-scape.js

### Tests
- `tests/test_graph_batch.py` — 6 batch tests (from earlier session)
- `tests/test_engine_config.py` — baseline includes forecast.apply_scope