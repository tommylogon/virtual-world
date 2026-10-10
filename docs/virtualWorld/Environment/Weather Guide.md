---
type: doc
tags: [system/environment]
---

# Weather Guide

A player / GM guide to the weather system: where it lives, how to read it, how to
author it, and what it actually does in play. For the engine internals, see
[[Weather System]]; for the clock, calendar and lighting it rides on, see
[[Time & Weather]].

## Where it lives

The whole weather surface is one modal: the **World Sky** panel.

- The top bar carries the **Sky Clock** — `🕐 08:58 · May 13, 2016 · 🌓 quarter ·
  ☁️ overcast · 🌧️ in 3h 2m: rain`. It is the current sky in one line: time, date,
  moon phase, weather, and the next forecast change.
- **Click the Sky Clock** to open **World Sky**.

Nothing about the weather is edited anywhere else. The panel is view + author in
one place, over the same schedule the engine runs.

## The World Sky panel

From top to bottom:

| Part | What it shows |
|------|---------------|
| **Hero** | The live sky scene, drawn from the current weather, time of day and moon. It is a preview surface, not a control. |
| **Live strip** | The *actual* environment of the area the controlled character is standing in: Wind, Humidity, Air, Temp, Light, Precip, Snow. Empty chips are simply not set on that area. |
| **Transport** | `▶ Play day` animates the schedule across the period; `Dawn` / `Noon` / `Dusk` / `Midnight` jump to an hour; `⏱ Now` returns to the live clock. Transport previews the sky — it does not move game time. |
| **Tabs** | **Forecast** (author/view the schedule) and **Regions** (a dated per-area outlook). The hero and transport stay visible across both. |
| **Footer** | Clock, Moon and Forecast readouts: `Day N`, the moon phase and its night-light bonus, and the entry count. |

## The Forecast tab

### Time & date

Set the exact time, nudge it with `−1h / −15m / +15m / +1h / +1d`, or set the
day / month / year. These drive the real game clock, so the sky, the forecast and
every time-of-day effect move with them.

### Override

A one-shot GM override that **supersedes the schedule** for a set number of turns:
pick a `weather`, `wind` magnitude, wind `dir`ection, and `humidity`, set a
duration, and **Set override**. The `● active` dot shows while one is running; it
auto-reverts when the duration runs out, or you can **Clear** it. An override that
names a weather wins over the generated field and applies to the whole world.

Use it for a scripted storm, a sudden cold snap, or a scene that needs a
particular sky right now.

### Forecast schedule

The schedule is the world's baseline weather. The card authors it:

| Control | Meaning |
|---------|---------|
| **mode** | How the weather is decided — see the table below. |
| **period** | How long one pass of the entries lasts: `hourly` = 1 day, `weekly` = 7 days, `yearly` = 365 days. Entries repeat each period. |
| **seed** | Makes `deterministic`, `random` and `generated` reproducible. The same seed and day always roll the same weather. |
| **every N ticks** | How often the state machine rolls to a new state. |
| **+ entry** | Add a row. |
| **Save** | Writes the schedule. Nothing is applied until you save. |

Each entry row is one scheduled moment:

| Field | Meaning |
|-------|---------|
| **Offset** | Minutes into the period the entry starts (0…1440 for hourly). |
| **Weather** | The sky state (`clear`, `cloudy`, `rainy`, `stormy`, `snowy`, `foggy`, `windy`, plus any extremes the library adds). |
| **Wind** | Magnitude: `none` → `hurricane`. |
| **From** | Wind **direction** — where the wind blows *from* (a "north wind" comes out of the north). |
| **Humidity** | `dry` / `humid` / `wet` / `flooding`. |
| **Temp Δ** | Degrees added to the area's own baseline temperature. A *delta*, not a temperature. |
| **Light Δ** | Added to outdoor ambient light. |
| **Air** | Optional air override (`fresh`, `stale`, `toxic`, …). |
| **Message** | A line narrated in the log when this entry becomes active. |

Below the rows sits a **timeline**: each entry is a block on the period axis, and
you can **drag a block** to reschedule it or **hover** to scrub the hero sky to
that moment. **Presets** (Clear / Showery / Storm front / Snow day / Foggy dawn)
fill in a whole day in one click. A collapsed **Transition table** holds the JSON
weights the state-machine modes roll against.

### Modes

| Mode | What decides the weather |
|------|--------------------------|
| **authored** | Exactly the entries you wrote, at their offsets. Most control. |
| **deterministic** | A weighted transition table rolled with a fixed seed: reproducible, but it changes state. |
| **random** | The same table, rolled without a seed. |
| **hybrid** | The authored entries set the base temperature/light; the state machine layers the weather on top. |
| **generated** | The **seeded, terrain-aware field**: every open-sky area rolls its own weather, biased by season, biome tags and painted climate, with neighbours coupled so a front spreads across the map. This is the mode the **Regions** tab is built for. |

For `authored` and `hybrid`, the entries are the source of truth. For
`deterministic`, `random` and `generated`, the mode rolls; the kinds of weather it
can reach are the **Transition table** (plus the season/biome extremes).

### A 60-second recipe

1. Open **World Sky**, go to the **Forecast** tab.
2. Set **mode** to `generated` and give it a **seed** (e.g. `7`).
3. Open the **Regions** tab to see what that seed produces for the next 7 days.
4. Adjust the seed until the week reads the way you want; **Save**.

## The Regions tab

A **dated outlook**: one row per open-sky area, one column per day, **today
first**. Each cell is the weather that area would get that day, with its
tuning-derived daytime temperature; hover a cell for the details. A **filter**
box narrows the rows by name, and the **days** box sets how many days ahead to
show (1–30).

The badge tells you the truth of what you are looking at:

- **`live field`** — the world's mode is `generated`, so this *is* the weather the
  simulation will produce.
- **`preview - mode: <mode>`** — the world is on another mode, so the live sim
  follows its authored schedule instead and the grid is a preview of what
  `generated` *would* give.

Opening the tab is a **read**: it never advances the clock or the world.

## What weather actually does

Weather is not a cosmetic word. It reaches temperature, light, travel, foraging
and the area's prose.

### Temperature

Each area has an authored **base temperature** (its climate). The engine adds a
diurnal curve and a season bias on top, plus any forecast delta, to write the
area's simulated temperature. What the character *feels* is
`effective_temperature`, which folds in **wind chill** and **humidity** on top of
that. A mountain base in winter is genuinely colder than a valley base; the sky
only modulates it.

### Light

Weather scales the time-of-day light curve: `clear` 100%, `cloudy` 70%, `rainy`
50%, `windy` 80%, `foggy` 40%, `stormy` 30%. A torch is unaffected — the
multiplier applies to daylight, not to a light you carry. Storms and fog also
blunt the moon's night bonus.

### Snow

Under the open sky, snowing weather **settles a depth** on the area (in cm). The
depth — not the word "snowy" — is what everything reads:

| Depth | Travel | Foraging |
|-------|--------|----------|
| < 2 cm | no effect | no effect |
| ≥ 2 cm | +1 move Energy | +2 search DC |
| ≥ 15 cm | +3 move Energy | +4 search DC |
| ≥ 35 cm | +6 move Energy | +6 search DC |

Snow builds while it snows (faster with heavier precipitation), caps out, and
**thaws slowly** otherwise — so the ground stays snowed *after* the sky clears,
and travel and foraging stay slow until it melts. Outdoor descriptions narrate
the depth, so the ground keeps "looking" snowed-over for as long as it is.

### Wind, humidity and air

- **Wind** accelerates heat exchange between connected areas, adds **wind chill**,
  can extinguish open flames, drains extra move Energy outdoors, and dries wet
  items faster.
- **Humidity** tilts effective temperature (warmer in the heat, colder in the
  cold), slows drying, and makes you easier to notice when wet.
- **Air** can drain Energy (`stale`), cost you socially (`humid`), or hurt
  (`toxic`).

### What you read and what you can guess

An outdoor area narrates its weather, its wind and the time of day; an indoor
room narrates none of it. The **guess time** action is harder in bad weather —
the sky's DC runs from `clear` (easy) to `stormy` (hard).

### Seasons and the moon

- **Season** comes from the engine, not the widget: an authored
  `world_state.season` wins, otherwise the calendar decides (Dec–Feb winter,
  Mar–May spring, Jun–Aug summer, Sep–Nov autumn). The season is a **temperature
  bias**, not a temperature — a tropical base in winter is still warm. A season
  change is narrated once (`[Season] Winter arrives.`).
- **Moon** follows a deterministic 30-day cycle. A full moon brightens outdoor
  nights (+25 light); a new moon leaves them dark. `stormy` and `foggy` sky
  hides the bonus.

## Where the content lives

Weather types are **library data**, not code. Each state is a record in
`data/library/weather/*.json` (`clear`, `cloudy`, `rainy`, `stormy`, `snowy`,
`foggy`, `windy`, and the extremes `blizzard`, `cold_snap`, `heatwave`,
`thunderstorm`). A record carries its icon, light multiplier, guess-time DC and
prose. Adding a new weather type — a sandstorm, acid rain — is adding a record,
not editing the engine; the generator and the dropdowns pick it up.

The **schedule** itself is stored per scenario in `world_state.forecast_schedule`
and edited through the panel or `POST /api/settings/forecast`.

<!-- connected:start -->
## Connected

*Generated by `python tools/doc_connected.py --apply` — relations the repo already asserts (Feature Map rows, task `wiki:` frontmatter, module `@docs` headers, same-folder notes), not invented.*

**Neighbouring notes** — [[Light System]], [[Temperature System]], [[Time & Weather]], [[Weather System]]

<!-- connected:end -->
