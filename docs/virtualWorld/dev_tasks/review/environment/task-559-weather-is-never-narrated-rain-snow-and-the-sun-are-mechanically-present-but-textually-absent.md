---
type: task
status: review
area: environment
priority: medium
---

# task-559: Weather is never narrated: rain, snow and the sun are mechanically present but textually absent

**Filed:** 2026-09-27
**Related:** task-556, task-553, task-227

## Goal

Add weather prose to the area description so a character standing outside in a
storm is told about it, and give the sun a presence beyond an implied light
level.

Text-only: no new state, no new engine module. Companion to task-556, which
adds the *state* that snow needs; this adds the *words* for what already exists.

## Measured (2026-09-27) — `env["weather"]` has exactly two readers

Every functional read of the weather key in the backend:

| Where | What it does |
|---|---|
| `engine/lighting.py:172` | applies the weather light multiplier |
| `routes/action_handlers.py:477` | sets the DC of the `guess time` skill check |

That is all. `env["weather"]` is written by the forecast
(`virtual_world_engine.py:1292`) and is **never narrated**.

`engine/area_description.py:299-337` builds its environment summary from
`temperature`, `air`, `smell` and `noise` — and `weather` is not among them. So
a character standing in a thunderstorm gets a temperature sentence, an air
sentence, maybe a smell and a noise sentence, and **not one word about the
rain**. The only hint that it is storming is that the light is dimmer.

**The near-miss that hides this.** `area_description.py:326-334` maps raw
descriptor values to real sentences, and one of them is:

```python
noise_prose = {"windy": "The wind howls outside.", ...}
```

But that reads the **`noise`** key, while the forecast writes **`wind`**
(`virtual_world_engine.py:1293`). Two keys for one phenomenon, so an *authored*
`noise: "windy"` narrates wind and a *forecast* gale does not. Worth fixing in
the same pass.

**The sun does not exist as an object.** There is no sunrise, no sunset, no sun
position, no "the sun beats down" anywhere. Daylight is a light curve
(`lighting.py:19-36`) plus an hour comparison. The only mention of the sun in
prose is one line in the `guess time` output: "The sun's position is clear to
you" (`action_handlers.py:498`).

## What already works, and should not be touched

- **Time** is fully implemented and is the best-designed part of this area:
  `routes/action_handlers.py:470-536` runs a Survival check whose DC scales
  with the weather (clear 10 → stormy 20) and reports precision by tier —
  exact `HH:MM` naming the sun or the stars, then hour-bucket, then "somewhere
  around", then "probably the middle of the day".
- **The moon** is narrated at night in the room description
  (`area_description.py:215-232`): full moon, blood moon, or plain moonlight,
  and it carries a real `light_bonus` (0-25) plus `OBSCURING_WEATHER` hiding
  it. `guess time` also names the phase.

Reuse those conventions rather than inventing a second phrasing style.

## What to change

1. A `weather_prose` map in the same place as `noise_prose`, keyed off
   `env["weather"]`, gated on the area being exterior (a storm is not
   something you hear through a stone wall — the same reason the moon text is
   outdoor-night-only).
2. Draw the keys from `WEATHER_STATES` (`weather_forecast.py:26`) so a forecast
   can never write a state that has no sentence. Today `guess time` already
   carries a **second, divergent** list including `"sunny"` and `"overcast"`,
   which are not in `WEATHER_STATES` — collapse the two.
3. Unify wind: either narrate `env["wind"]` directly, or have the forecast
   write `noise` too. Pick one and document it.
4. A time-of-day line for exteriors — dawn, midday, dusk, night — so the sun has
   a presence. Reuse the hour boundaries already used at
   `area_description.py:221` and `action_handlers.py:497` (05:00-19:00 is day)
   rather than inventing a third set.

## Acceptance

- Standing outside in `rainy` says it is raining; in `stormy` says something
  worse. Indoors it does not.
- Every value in `WEATHER_STATES` produces a sentence.
- The two weather lists (`WEATHER_STATES` and the DC map) are one list.
- Forecast wind is narrated, not just authored `noise: "windy"`.
- An exterior area at dawn/dusk says so, and the day boundary agrees with the
  existing 05:00-19:00 rule.
- The `guess time` behaviour and the moon description are unchanged.

## Implemented (2026-09-27)

Narration landed, and it turned up a **live bug that had been hiding in plain
sight**: the moon has never been narrated anywhere, in any world, ever.

`get_area_description` read a local `node` on the first line of the moon block.
Python resolves `node` as a local — because it is assigned *later* in the same
method, in the item and people loops — so the line raised `UnboundLocalError`,
and the bare `except Exception: pass` underneath swallowed it. Proven by AST
(the only assignments to `node` are at lines 289/349/355) and by a repro that
produced no moon text at 22:00 with a full moon. The except is now narrowed to
the provider errors it was written for, so the next real failure is not
invisible.

**Shipped**

- `engine/area_description.py` — `WEATHER_PROSE` (one sentence per weather
  state), `WIND_PROSE` (one per wind magnitude), `TIME_OF_DAY_BANDS` +
  `time_of_day_prose()`, `_is_open_sky()` (accepts `outdoor` *or* `exterior`),
  and `weather_description()`. The moon block's node lookup is fixed and the
  bare except is gone.
- `engine/weather_forecast.py` — `WEATHER_ALIASES` + `normalize_weather()`,
  and `WEATHER_TIME_DC` / `WEATHER_TIME_DC_DEFAULT` moved in from the action
  handler so the DC table and the vocabulary cannot drift apart again.
- `routes/action_handlers.py:470-486` — uses the shared table and the
  normaliser; the private list (which knew `sunny`/`overcast`) is deleted.
- `engine/lighting.py:172` — the moon-obscured check normalises, so a world
  spelling it `overcast` behaves like `cloudy`.
- `tests/test_weather_narration.py` — 26 tests, including three that pin the
  vocabularies together (every weather state has prose, every wind state has a
  sentence, every weather state has a DC), the moon regression, the outdoor
  gate, and the no-duplicate-wind cases.
- `docs/virtualWorld/Environment/Time & Weather.md` — a new "What the Weather
  Looks Like" section, the alias rule, the tag table, and a correction to the
  Weather Modifier table.
- `docs/design/weather-world-integration.md` — §1 and §2 corrected.

**Full suite: 59 failed / 4071 passed** — the failure count matches the
recorded baseline exactly, and all 59 are the documented pre-existing ones
(`test_mcp_*` FastMCP wrapper mismatch, plus `test_world_grid_routes.py`,
`test_character_identity.py`, `test_scenario_name.py`, `test_templates.py` —
none of which this change touches).

## Filed while implementing this

**bug-54** — two causes behind the same symptom, and the reason a painted world
still sees no weather even with narration in place:

1. `WEATHER_LIGHT_MULT` has **no readers at all**. A storm never darkens the
   world. (I had told the user this was wired into `lighting.py:172`; it is
   not. That line only decides whether the moon is obscured.)
2. The compiler builds area tags from the biome record, and **no biome in
   `data/worldpainter/biomes.json` declares `outdoor` or `exterior`** — so for a
   WorldPainter world the forecast is skipped entirely, the diurnal light curve
   never applies, and exterior areas are not heat reservoirs.
   `world_compile.py:670` computes `outdoor` from the scope mode and discards
   it.

Hand-authored scenarios carry the tags by hand, which is why this survived:
`world_template.json` has 28 hits, `The Valerious Case.json` 28,
`kraktooth_goblin_camp.json` 11.
