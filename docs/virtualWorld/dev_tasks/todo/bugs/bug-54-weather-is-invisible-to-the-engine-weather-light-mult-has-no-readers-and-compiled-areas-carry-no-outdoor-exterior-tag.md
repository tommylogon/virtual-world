---
type: bug
status: todo
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

## Cause 2 — a compiled painted area is neither `outdoor` nor `exterior` — **OPEN**

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
