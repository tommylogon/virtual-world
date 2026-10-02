# Soak Lab

The Soak Lab (`/soak`) runs automated long-horizon simulations with live tuning and telemetry (Feature Map row 58: "Automated long runs, live tuning, telemetry").

## Architecture

**Frontend** (`static/js/soak/`):
- **soak-app.js** — bootstrap, binds UI, loads meta/runs, restores shared-URL config
- **soak-state.js** — single-source store: config, run list, incremental polling (450 ms), cursors for samples/events, run selection, telemetry cache (`SERIES_CACHE`)
- **soak-ui.js** — full dashboard rendering: form, presets, saved configs, run list, progress, Overview/Vitals/Survival/Growth/Space-Time/Characters/Compare tabs, toasts
- **soak-api.js** — thin fetch wrappers (`meta`, `listRuns`, `startRun`, `stopRun`, `getRun`, `report`, `characters`, `characterSeries`, `samples`, `telemetry`)
- **soak-charts.js** — dependency-free SVG helpers: `renderLineChart`, `renderDonut`, `renderBarChart`, `renderVerticalBars`, `histogram`, `niceTicks`, `scaleFor`
- **soak-spacetime.js** — pure geometry + renderers for the space-time swimlane view (task-544)
- **soak-presets.js** — preset configs (Kraktooth, stress, long) and localStorage saved configs
- **soak-format.js** — formatters (`fmtInt`, `fmtNum`, `pct`, `fmtDuration`, `fmtClock`, `titleCase`, `vitalColor`, `esc`, `queryToConfig`)

**Backend** (`engine/`):
- **soak_runner.py** — `SoakRun` / `SoakConfig` / registry. Single active run (global RNG). `execute()` sync or `start()` on daemon thread. Records samples, events, deaths, per-character vitals series, growth metrics. **Telemetry** (task-543) via `engine/soak_telemetry.TelemetryRecorder`.
- **soak_telemetry.py** — run-owned measurement store, separate from `lived_log`. See the module docstring for the boundary table.

## Launching a soak run

1. Select a scenario (`data/scenarios/*.json` + `world_template.json`) — form shows cast size and `minutes_per_tick` from the file.
2. Configure: ticks, `minutes_per_tick` (optional override), seed, `sample_every` (0 = auto ~2000 samples), label, flags (`engine_decay`, `background_all`, `mature`, `neutral_environment`, `debug_hp`, `track_characters`, `telemetry`), `decay_overrides`, `starting_vitals`, `traits`, `track_vitals`.
3. Apply a preset (Kraktooth, Stress, Long) or load a saved config.
4. Click **Start soak** → `SoakState.start()` → `SoakApi.startRun` → `soak_runner.start_run` → daemon thread running `SoakRun.execute`.

## Live tuning & progress

Polling (450 ms) fetches incremental samples/events via cursors (`next_since`, `next_event_since`). Progress bar shows tick fraction, game span, ticks/sec (instant + average), alive/dead, ETA, projected wall time for 1 day / 1 week / 1 month. Stop button calls `SoakApi.stopRun` → `SoakRun.cancel`.

## Charts & tables

- **Overview** — vitals line chart (avg), deaths-by-cause donut, deaths-by-area bar chart, delta table (first→last living sample), alerts (mass casualty, throughput warning).
- **Vitals** — selectable metrics, modes (avg/min/max), % of starting toggle, min–max band.
- **Survival** — alive % line + death tick histogram + deaths table (searchable, with vitals at death).
- **Growth** — log-toggle line chart for game_log, turn_events, memories, lived_log, graph_nodes; throughput line; first/latest/delta table.
- **Characters** — filterable table (alive/dead/all), per-character vitals series drill-down.

## Space-Time view (task-544 — in progress)

Answers: **did those two ever share a room?** A line chart cannot show this; a heatmap aggregates characters away.

**Swimlanes** (`soak-spacetime.js`): x = time, y = area lanes ordered spatially (from `area_placements` / graph layout) with alphabetical fallback. One band per presence interval per character. Overlapping bands in the same lane = collision (two characters in one room). Deaths marked on the band at the tick with cause. **Condition ribbons** (thin strips beneath bands) show condition state over time (excludes ambient `awake`/`busy`). Single-character isolation collapses to visited areas only.

**Companion panels** (same telemetry payload):
- **Why breakdown** — ranked `why` distribution grouped by prefix (`needs`, `goal`, `plan`, `social`, `threat`, `order`, `env`, `schedule`, `agenda`, `search`, `forage`, `traversal`, `timeskip`, `fidelity`, `cause`, `react`, `sense`, `sim`). Stacked over time so a rule starting to dominate is visible.
- **Action composition** — `kind` donut/stacked area (what they spent time on; coarser than `why`).
- **Occupancy heatmap** — time × area density, zoomed-out companion.
- **Collisions table** — per area, shared ticks, who (click a pair to isolate one character).

**Density guard** — warns when >900 visible intervals (individual stays indistinguishable).

**Integrity alerts** — gaps/overlaps in presence intervals, rejected `why` tags, truncated action stream.

## Telemetry vs. lived log (task-543 — in review)

| | `lived_log` | telemetry |
|---|---|---|
| scope | per **character** | per **run** |
| stored | **in the save**, on the player | **out of the save**, on the run |
| grain | salience-filtered, runs collapsed | complete, every move |
| test | "would a person remember this" | "measure exactly this" |
| lifetime | ~200 entries, rolled up | the whole run, then archived |
| consumer | LLLM summarisation on promote/demote | dashboard, export, benchmark |

**Presence intervals** — one record per area change (`character`, `area`, `from_tick`, `to_tick`). Cost bounded by moves, not ticks. Seeded at tick 0 so a non-moving character still has a band. Closed on area change, death, or run end.

**Events** — action/condition/death records with `why`. Vocabulary: closed prefix set (`WHY_PREFIXES`), **excludes `llm:`** (soaks make no LLM calls by construction). Rejected tags counted in `rejected_why` / `rejected_events`; unattributed (empty `why`) counted separately so shares add up.

**Persistence** — hot window in memory (20k events) + append-only JSONL on disk (`data/soak_telemetry/<run_id>.jsonl`). Full run exportable as JSONL independent of RAM.

## Separation from `lived_log`

The telemetry recorder is installed via `recording(recorder)` context manager (`engine/lived_log.record` fans out to `active_recorder()`). Three boundary guarantees (asserted by tests):
1. **One way** — telemetry never writes to `lived_log`; live-log readers never serve the dashboard.
2. **Off by default** — `active_recorder()` is `None` outside a soak; normal game pays one identity check.
3. **Refuses wrong vocabulary** — `is_valid_why` rejects unknown prefixes; `EXCLUDED_PREFIXES = ("llm:",)`.

## Status

- **task-543** (telemetry capture): **review** — acceptance criteria met (intervals on area change, `why` vocabulary, save exclusion, flat memory, JSONL export).
- **task-544** (space-time view): **inprogress** — swimlanes, collisions, deaths, condition ribbons, why breakdown, heatmap built; remaining: 30-day render without freezing, spatial lane ordering stability, empty state for no-telemetry runs, pure-JS geometry unit tests.

## Key code references

| File | Role |
|------|------|
| `static/js/soak/soak-app.js` | bootstrap, init |
| `static/js/soak/soak-state.js` | `SoakState` — store, polling, cursors, telemetry cache, run selection |
| `static/js/soak/soak-ui.js` | `SoakUI` — all rendering: form, progress, charts, space-time, tables |
| `static/js/soak/soak-api.js` | `SoakApi` — fetch wrappers for meta, runs, telemetry, report |
| `static/js/soak/soak-charts.js` | SVG chart primitives (line, donut, bar, vertical bars, histogram) |
| `static/js/soak/soak-spacetime.js` | `SoakSpacetime` — pure geometry (laneOrder, clipToWindow, packRows, findCollisions, buildLayout, whyOverTime) + renderers (renderSwimlanes, renderHeatmap, filterCharacter, collisionsFor) |
| `static/js/soak/soak-presets.js` | presets + localStorage saved configs |
| `static/js/soak/soak-format.js` | formatters, query-string config |
| `engine/soak_runner.py` | `SoakRun` / `SoakConfig` / registry, `execute`, `snapshot`, `report`, telemetry integration |
| `engine/soak_telemetry.py` | `TelemetryRecorder` — intervals, events, why_breakdown, condition_spans, JSONL, vocabulary |