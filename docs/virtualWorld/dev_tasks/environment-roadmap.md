# Environment Roadmap — grouped plan (2026-08-31)

Refactor of the environment todo queue into **four groups**. Design sources:
`docs/virtualWorld/Environment/Time & Weather.md` (canonical specs for forecast/moon/wind/humidity/
area-status/trigger integration), `docs/virtualWorld/Scenario Workflows & UI Audit.md` (#12/#13).

Groups:
- **📍 AREAS** — presence (360), area conditions (233, *reframed*), bulk selection (378), env presets (379), sounds-heard-here (173)
- **🕐 TIME & DATES** — calendar (228), default turn (301 — **done**)
- **🌦 WEATHER & SKY** — forecast (227), moon (229), trigger/GM integration (234), wind (231), humidity (232), + the **Sun/Moon/Weather top-bar widget**
- **📍 Authoring glue** items ride under AREAS (bulk + presets).

---

## Group 1 — 📍 AREAS: presence & place

### 1.1 Presence window (task-360) — REDESIGNED: **per-area presence ledger**

Decision (Tommy, 2026-08-31): keep the registry **per area**, not per character.
`world.area_presence: {area_id: {char_name: entry_tick}}` — who is here and since when.

- On movement entry → write `area_presence[new_area][char] = time_ticks`; remove char from the old area's map.
- **Window = entry_tick → their next turn.** Witnessed events are the current turn's
  `turn_events` in that area with `evt.tick >= entry_tick`, excluding the character's own rows
  (existing area+actor filter stays as the base).
- **Random initiative is fine**: if your turn was last in round N and first in round N+1, the
  window between them is genuinely tiny — you learn (almost) nothing, and **that is correct**.
  No sub-tick/initiative resolution needed in v1.
- **Leaving for a new room**: the new room's presence map decides the window from the moment
  you enter it — fresh start, fresh knowledge.
- **Back-and-forth is memory's job**: re-entering resets the window; the character's existing
  memory system keeps what they knew. **Never auto-replay old events.**
- **The `_areaEventLog` frontend accumulator stays a designer log** (inspector "room events")
  but is **dropped from the perception path** — agent prompts never fall back to it.

Engine/JS touched: `virtual_world_engine.py` (+`area_presence`, serialization),
`engine/movement.py` (entry hook), `static/js/agent/prompt-builder/room-context.js`
(witnessed filter — remove the fallback), `static/js/event-stream.js` (keep log, stop feeding
prompts), tests.

```
WITNESSED (v1 window — what you can actually know since you walked in):
 [Tick 4] Butcher moved to Kitchen
 [Tick 4] a voice said: "hey, where did you go?"      ← addressed-to-you mark kept
(hidden: everything before your entry_tick — no stale rows, ever)
```

### 1.2 Area conditions (task-233 — reframed from "statuses")

Tommy: "it's honestly sounding a lot more like area conditions" — agreed. Model it on the
**player-conditions machinery** (catalog + multi-instance + periodic/ends_on/known), scoped to
areas:

- `area.conditions: {condition_id: [instances]}` (+ catalog in `engine/area_conditions.py`,
  catalog-driven like `player_conditions.py`): `on_fire`, `flooded`, `poison_gas`, `blessed`,
  `darkness_magic`, `burning`, `affected_by_weather`…
- Instance fields: `duration`, `periodic` (env deltas: temp/light/air), `affects` (HP drain,
  apply_condition to characters inside), `propagation` (spread through open ways), `ends_on`.
- Trigger integration: `apply_area_condition` / `clear_area_condition` effects,
  `area_has_condition` condition. Serialization survives saves.
- **Phased series** (registry → catalog → tick hook → triggers → description) — deliberately
  NOT one PR; sequenced after the weather group (forecast can impose area conditions).

### 1.3 Bulk selection (task-378 / audit #12) — ✅ greenlit

Shift-click (and rubber-band) multi-select on the graph + an **action bar**:
`[🏷 Tag] [🗂 Env preset] [⚠ State] [🗑 Delete] [↔ Move]` — undo-safe, no new storage.

```
   Graph canvas                  Action bar (appears on selection ≥ 2)
 ┌──────────────┐               ┌───────────────────────────────────┐
 │ ▣RoomA  ▣RoomB│  (shift-c)    │ Selected: 2 areas  [🏷 Tag] [🌦 Env Preset] [⚠ State] [🗑] │
 │  ▣RoomC       │               └───────────────────────────────────┘
 └──────────────┘
```

### 1.4 Env presets & zone apply (task-379 / audit #13)

Named env bundles ("Arctic Blizzard") + **apply to selection**, reusing `set_environment`
semantics + the per-area Save-to-Library env path. After 1.3.

### 1.5 Sounds heerd here (task-173)

Read-only block in the area inspector fed by the existing engine sound helpers +
`GET /api/areas/<id>/sounds` (no propagation logic re-implemented in JS).

```
Area inspector → Environment
  Light 80 · Temp 21° · Air fresh · Smell —
  🔇 Sounds heard here:
    📣 Jukebox (loud, repeating)  ·  🔔 Phone ring (faint, from: Order Counter)
```

---

## Group 2 — 🕐 TIME & DATES

### 2.1 Calendar (task-228) — S

`game_day / game_month / game_year` derived from `time_ticks`; calendar config
(`minutes_per_day`, `days_per_month`, `months_per_year`) stored in world state and exposed via
`/api/state` (per `Time & Weather.md`). Game Clock group shows the date: `Day 3 of 27 · Aug 2084`.

### 2.2 Default turn duration (task-301) — ✅ DONE (default 5 → 1 minute)

---

## Group 3 — 🌦 WEATHER & SKY (the big session)

### 3.1 Forecast engine (task-227) — L, gated OFF by default

`engine/forecast.py` per `Time & Weather.md`: modes `authored | deterministic | random |
hybrid`, entries (`offset`, `weather`, `wind`, `temperature_mod`, `light_mod`, `air`,
`message`), granularities hourly/weekly/yearly, applied as the **environmental baseline** each
`tick_turn()`; `forecast_override` (GM/trigger) supersedes with `duration_ticks` auto-revert.
**Default mode: `authored` with ZERO entries = no behavioral change** — existing per-area envs
and tests stay stable until a scenario authors a schedule.

### 3.2 Moon phases (task-229) — M, on top of 2.1

Deterministic 30-day cycle from `game_day` → `get_moon_phase()` exposed in `/api/state` +
`moon_phase` condition. Night-light bonus applied only in `lighting.py`'s outdoor night path,
exactly per the `Time & Weather.md` table; existing `test_realism_perception` pinned with an
explicit date so the bonus is deterministic in tests.

### 3.3 Sky widget (new UI)

Top-bar widget + editor "World Sky" panel. ASCII mockup:

```
 TOP BAR
 ┌──────────────────────────────────────────────────────────────────┐
 │  🕐 08:37  · Day 3 of 27 (Aug 2084) · 🌙 waning · ⛅ clear · ☔ 14:00 │
 │  └──── click → World Sky panel ────┘  └moon──┘   └weather┘ └forecast┘
 └──────────────────────────────────────────────────────────────────┘

 WORLD SKY PANEL (Settings → Game Clock, expanded)
 ┌─────────────────────────────────────────────────────────────┐
 │  SUN/MOON DIAL                · · · · · 12                   │
 │        ☀  ·      (arc: 08:37 = morning; moon ❀ at night)    │
 │  Clock: [08:37] [+15m][+1h][+1 day]   Date: [Aug 3, 2084]    │
 │  Moon: ● new  ◐ quarter  ◑ gibbous  ● full  ◐ waning         │
 │  Weather: [⛅ clear ▾]   Forecast: ☔ next change 14:00 (3t)   │
 │  Override: [☔ rain ▾] [5 turns] [Set] [Clear]                │
 └─────────────────────────────────────────────────────────────┘
```

### 3.4 Trigger integration (task-234 slice)

Effects: `set_time` / `set_date` / `set_weather` (+ keep `forecast_override` as an effect).
Trigger types: `on_turn_start`, `on_turn_end`, `on_dawn`, `on_dusk`, `on_day`, `on_night`,
`on_full_moon`, `on_blood_moon` (one-shot per transition via last-fired cache). Conditions:
`date_equals`, `moon_phase_equals`, `weather` (exists, read-only today).
(GM panel = the World Sky panel above; no separate GM UI.)

### 3.5 Wind (task-231) + humidity (task-232) — M each

Env keys `wind` / `humidity` with the `Time & Weather.md` effect tables; **defaulted kwargs**
on `effective_temperature` (never break its 6 callers); air/humidity propagation; Engine Config
keys so values are tunable live.

---

## What gets touched (per group)

| Group | Engine | Routes | JS |
|---|---|---|---|
| AREAS (360) | movement.py entry hook, world.area_presence, serialization, log schema | /api/state | room-context witnessed filter, event-stream (log stays, prompts stop using it) |
| AREAS (273/378/379/173) | area_conditions.py (+catalog), set_environment reuse | library env path | graph bulk-select + action bar, inspector blocks, preset manager |
| TIME (228) | tick_manager date getters, serialization | /api/state | Game Clock group date row, sky widget |
| WEATHER (227/229/234/231/232) | forecast.py, lighting moon bonus (outdoor night only), environment propagation, trigger types/effects/conditions | settings forecast API | trigger editor/graph entries, sky widget, Engine Config keys |

## Sequencing & risks

1. **Now:** 1.1 presence window (small, self-contained) + 1.3 bulk selection (unblocks 1.4) + 1.5 sounds block. Low risk each.
2. **Next session:** Group 3 (weather & sky) as one coherent build — forecast first (gated no-op), then clock/date, moon bonus (day-pinned tests), then trigger/GM integration, wind/humidity last. **Risk watch:** the tick hook must be a no-op for unauthored worlds; moon bonus only in the outdoor-night branch; `effective_temperature` kwargs defaulted.
3. **After:** 1.2 area conditions (phased; the biggest new subsystem), 1.4 env presets/zone apply.
4. **Parked forever-ish:** 301 global re-pace done as default-only; 233 stays in AREAS group (phased).

**Task-doc refactor map:** task-360 → rewritten to the per-area presence design above; 227/228/229/
231/232/234/173 → stay as specs, referenced from this roadmap; 233 → retitled "Area Conditions";
378/379 → grouped under AREAS.
