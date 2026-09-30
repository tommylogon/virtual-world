---
type: bug
status: done
area: bugs
priority: high
---

# bug-54: Weather is invisible to the engine: WEATHER_LIGHT_MULT has no readers and compiled areas carry no outdoor/exterior tag

**Filed:** 2026-09-27
**Related:** task-559, task-553, task-227, task-230, task-496

## Goal

A forecast never darkens the world, and a painted WorldPainter world gets no
weather at all.

Found while implementing task-559, which added the *narration* of weather. The
narration now works; these are the two mechanical gaps underneath it. Same
symptom, two independent causes.

## Cause 1 — `WEATHER_LIGHT_MULT` is dead data — **FIXED 2026-09-27**

`engine/weather_forecast.py` defined the weather → light multiplier
(`clear` 1.0 … `stormy` 0.3). A search for every reference to the name across
`engine/`, `routes/` and `virtual_world_engine.py` returned **the definition and
nothing else**. Nothing applied it.

So weather did not change the light level in any world, hand-authored or
painted. `LightingSystem._own_light` read `env["weather"]` at `:172` but only
to decide whether the *moon* was obscured — not to scale the ambient light.

A midday thunderstorm and a midday clear sky were equally bright.

**Shipped:** `weather_light_mult()` in `engine/weather_forecast.py` is the
reader (returns `1.0` for unset/unknown, so a world with no forecast is
completely unaffected), and `LightingSystem._own_light` now scales the
**time-of-day curve** by it — not an authored `environment.light`, because a
hand-set value is a light source and a torch does not care that it is raining.
Seven tests in `tests/test_lighting.py::TestWeatherDimsTheSky`, including the
two "must not" cases (no forecast, authored light) and the no-double-dip
against the storm-nulled moon bonus.

## Cause 2 — a compiled painted area is neither `outdoor` nor `exterior` — **FIXED 2026-09-30**

The card's warning that another session owned `world_compile.py` and
`biomes.json` had resolved by the time this was picked up: the taxonomy grew
51 → 105 biomes and three of them (`porch`, `courtyard`, `balcony`) now declare
`outdoor`. That fixed *half* the problem and is exactly why the rest was still
broken — and why the remaining half was not the card's picture any more.

**The real shape of the bug was one fact with four readers.** "Is this area
under the open sky?" was asked four ways, and the spellings disagreed:

| Reader | Before | Now |
|---|---|---|
| `lighting.LightingSystem.is_outdoor_area` | `"outdoor" in tags` | `is_open_sky(...)` |
| `area_description._is_open_sky` | either spelling | delegates to `engine/area_tags.py` |
| `environment_propagation` (×2, heat reservoirs) | `"exterior" in tags` | `is_open_sky(...)` |
| `tick_manager` (wind Energy drain) | `"exterior" in tags` | `is_open_sky(...)` |
| `virtual_world_engine._apply_forecast_env` | `"exterior" in tags` | `is_open_sky(...)` |

A painted area was tagged `outdoor` by its biome, and the forecast — the thing
this bug is named for — was looking for the literal `exterior`. So it was skipped,
every turn, silently.

### Decisions taken, deliberately

**Which spelling?** Both are *read*; only one is *written*. Neither can be
retired cheaply on disk: `data/worldpainter/biomes.json` authors write
`outdoor`, and a few hundred hand-authored library areas carry `exterior` by
hand. So `engine/area_tags.py::is_open_sky` is the one predicate, it accepts
either, and `compile_grid` writes exactly one — asserted by a test, because
emitting both is the cheap fix that re-creates the trap.

**Where does the compiler get the fact?** From the scope's **mode**, not the
biome. The biome record cannot supply it: of 105 biomes only 3 claim open sky
and an outdoor `beach` is not one of them, so delegating would have left the
most obvious outdoor biome in the game still locked to a static light value.
`compile_grid` already computed `outdoor = record.mode == "world"` and threw it
away.

### What changed

- **`engine/area_tags.py`** (new) — `OPEN_SKY_TAGS`, `is_open_sky()`. One home
  for the fact, with the history in the docstring.
- **`engine/world_compile.py`** — `compile_grid` writes `outdoor` onto every
  area of a `world`-mode scope.
- **`engine/lighting.py`**, **`engine/environment_propagation.py`**,
  **`engine/tick_manager.py`**, **`virtual_world_engine.py`** — all four read
  through the predicate.
- **`tests/test_open_sky.py`** (new, 35 tests) — the predicate, every reader
  agreeing on either spelling, a real `town`/`interior` compile staying
  untagged, a real `world` compile being tagged, exactly one spelling written,
  and the forecast reaching a painted area while staying out of interiors.
  One test is a deliberate grep guard: a new `"outdoor" in tags` in a known
  reader fails the suite, which is how this bug comes back.

### Live browser verification

Compiled a painted world through the app's own
`POST /api/world/scopes/verify_wild/grid/generate` (3×3 `sparse_forest`,
`world` mode), then ran one `POST /api/turn/apply`:

- Header went 36 → **45 areas**, and the nine new areas carry
  `["forest", "woods", "outdoor"]` — written by the compiler, once.
- After one turn, **all 9** had `weather: "snowy"`, `humidity: "humid"`,
  `temperature: 19.6`. Before this change a compiled painted world received
  none of it, ever.

### Known limits

`light: 72` on those areas is the authored value, not the curve: the diurnal
curve is skipped for an area that authored an explicit `environment.light`,
which is deliberate (a hand-set value is a light source, and a torch does not
care that it is raining). A painted cell that wants the curve should author no
`light`.

Two spellings of "under the open sky" are in use, and **the compiler emits
neither**:

| Tag | Readers |
|---|---|
| `outdoor` | `lighting.py:138` (`is_outdoor_area` → the diurnal light curve), `area_description.py:219` (moon) |
| `exterior` | `virtual_world_engine.py:1288` (forecast `apply_scope`), `environment_propagation.py:133,139` (heat reservoirs), `tick_manager.py:129` |

`engine/world_compile.py` builds an area's tags from the biome record
(`biomes_mod.area_tags`) plus `feature` for a child scope — and **no biome
record in `data/worldpainter/biomes.json` declares `outdoor` or `exterior`**.
Re-verified after the taxonomy grew from 16 to 51 biomes: still neither tag.

```
biome tags: beach building cell_kind:passable cliff civic commercial deep_water
dense farmland field forest hill hills industrial lake medical military mountain
mountains ocean pine ravine river rocky rural settlement shore spring storage
stream structure threshold trade transport water woods …
```

**⚠ Note on coordinates.** `engine/world_compile.py` and
`data/worldpainter/biomes.json` are being edited concurrently (the taxonomy
grew 16 → 51 biomes during this investigation). The line numbers below were
valid when measured and will drift; the *facts* — no biome declares the tags,
the compiler derives its tags from the biome record — re-verify with:

```powershell
python -c "import json;d=json.load(open('data/worldpainter/biomes.json'));\
t=set();[t.update(r.get('tags',[])) for r in d['biomes'].values()];\
	print('outdoor' in t, 'exterior' in t)"
```

Because another session owns those two files right now, cause 2 should be
picked up **after** that work lands, or by whoever owns it — not in parallel.

Consequences for any WorldPainter world, every turn:

- **The forecast is never applied.** `apply_scope` defaults to `exterior`
  (`runtime_config.py:59`) and `virtual_world_engine.py:1288` skips every node
  without that tag — so `_apply_forecast_env` writes nothing, and no area ever
  gets a `weather`/`wind`/`humidity` value.
- **No diurnal light.** `is_outdoor_area` is False, so the area's light is the
  static `env.light` (default 80) at every hour.
- **No moon** (that half is now moot — it was dead code anyway, see task-559).
- **Heat reservoirs are wrong.** An exterior area is meant to be an infinite
  heat sink; a painted area is instead a finite body that exchanges heat with
  its neighbours like a room.

Hand-authored scenarios are unaffected: `world_template.json` (28 hits),
`The Valerious Case.json` (28) and `kraktooth_goblin_camp.json` (11) all carry
the tags by hand. Only compiled worlds are affected, which is why this has
survived.

`world_compile.py` already computes the answer and throws it away (inside
`compile_grid`):

```python
outdoor = str(record.get("mode") or "world") == "world"
```

## What to change

1. **Tag the areas.** In `compile_grid`, add the open-sky tag(s) to every area
   built from a `world`-mode scope, using the `outdoor` local that is already
   computed at `:670`. This alone restores the forecast, the diurnal light and
   the heat-reservoir behaviour for painted worlds.
2. **Decide the spelling.** `outdoor` and `exterior` are two words for one
   fact — the exact trap `surface` vs `floor` and `base_temperature` vs
   `temperature` exist to avoid. Emitting both is the cheap fix and keeps every
   reader working; unifying is the right fix and touches `lighting.py`,
   `environment_propagation.py`, `tick_manager.py`, the forecast and the
   scenario files. **Pick deliberately, and say which in a code comment.**
3. **Apply the multiplier.** Make `_own_light` scale the outdoor light by
   `WEATHER_LIGHT_MULT`, or delete the table. Leaving defined-but-unread data
   in a module is what made this invisible in the first place.

## Acceptance

- A painted world with a `stormy` forecast is darker than the same world with
  `clear`.
- A painted outdoor area's light follows the diurnal curve, so it is dim at
  03:00 and bright at noon.
- A painted outdoor area receives `weather`/`wind`/`humidity` from the
  forecast.
- A painted outdoor area is a heat reservoir: opening a door to it does not
  slowly cool the room the way opening a door to another room does.
- A `town`- or `interior`-mode scope still compiles **without** the tag.
- An existing saved world recompiles without losing areas.
- No name in `engine/weather_forecast.py` is defined without a reader.
