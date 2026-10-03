---
type: task
status: todo
area: environment
priority: medium
---

# task-556: Weather reaches the world: snow accumulation, movement, forage

**Filed:** 2026-09-27
**Related:** task-232, task-553

## Goal

Give snowy weather a consequence: accumulate snow on an area and let it change surface presentation, movement cost and forage, instead of being a label that only dims the light.

Depends on task-553 (snow needs a real per-area temperature to be worth
simulating).
Design: `docs/design/weather-world-integration.md` §2.5, §5.

## Measured (2026-09-27) — `snowy` is a string with three readers

Every occurrence of snow in the backend:

| Where | What it does |
|---|---|
| `engine/weather_forecast.py:26` | `snowy` is in `WEATHER_STATES` |
| `engine/weather_forecast.py:49` | `WEATHER_LIGHT_MULT` gives snowy `0.6` — it dims the light |
| `routes/action_handlers.py:483` | a perception skill DC of `18` for `snowy` — the same value as `foggy` |

That is the whole of it. Snow **does not accumulate**, does not touch
`properties.surface`, does not gate movement, does not change forage, and does not shift temperature. A blizzard and a fog bank are the same event with a different word. The world's own surface vocabulary has no winter in it.

The same is true of the other weather states in a weaker form: `rainy` and `stormy` reach the world only through humidity, which is itself only ever *asserted* by a forecast entry — there is no water cycle producing it.

## What to change

1. A per-area accumulated value (`snow_depth`, or a boolean if accumulation
   proves too heavy — see the open question below) written when the weather is `snowy`, and decayed when it is not. Exterior areas only, consistent with
   `_apply_forecast_env`'s `apply_scope`.
2. Read it where the world actually cares:
   - **surface** — presentation and the `properties.surface` material
   - **movement** — a cost or a rule, not just a longer DC
   - **forage** — `engine/foraging.py` already keys off area tags, so this is
     likely a tag effect rather than new code
3. Keep the accumulation on the *area*, not the weather state, so it survives a
   forecast change the way a real world does (snow does not vanish the moment
   the sky clears).

## Open question

Accumulate and decay, or a boolean? Accumulation is the better model and gives
descriptions something to say ("snow to the knee"), but it needs a per-tick
decay rule, a save/load story, and a place in the compiled world. A boolean is
a fifth of the work. **Decide before coding** — this is the difference between
a small and a large task.

## Acceptance

- Snowy weather over an exterior area changes what that area is like, not just
  how bright it is.
- Clearing weather decays snow rather than clearing it instantly.
- Movement and forage actually respond.
- A saved world reloads with its snow intact.
- `dry`/`clear` worlds are bit-for-bit unchanged.
