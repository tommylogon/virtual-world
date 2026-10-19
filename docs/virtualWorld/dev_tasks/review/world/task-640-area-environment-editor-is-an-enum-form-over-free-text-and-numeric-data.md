---
type: task
status: review
area: world
priority: medium
related: ['task-497', 'task-557', 'task-758', 'task-569']
---

# task-640: Area environment editor is an enum form over free-text and numeric data

**Filed:** 2026-09-30
**Related:** 

<!-- deps:start -->
**Related:** [[task-497-worldpainter-biome-feature-taxonomy-and-distribution-layers]], [[task-557-worldpainter-climate-layer-paint-a-coarse-climate-compile-it-to-base-temperature]], [[task-758-biome-records-add-climate-and-neighbour-fields-for-the-palette]], [[task-569-biome-resource-distribution-consumer]]
<!-- deps:end -->

## What

The editor offers dropdown choices over data that is free-text and numeric. Area weather reads 'clear' while the world header reports 'overcast' -- precedence between area and world source is unresolved.

## Acceptance

- [x] Area Inspector provides enum dropdowns and range pickers for environment fields.
- [x] Saved environment settings persist valid numeric and tag values to graph node.

## Resolved 2026-10-02 (wt/graph-render)

Measured the mismatch in `kraktooth_goblin_camp` area `environment`:

| field | data shape | editor (before) | editor (after) |
|---|---|---|---|
| `light` | number (`80`) **and** enum (`"normal"`) | `<select>` enum only - a numeric 80 matched no option, so the panel silently showed the first preset ("pitch black") | text input + preset datalist; stores a number when one is typed, else the word |
| `noise` | free text (`"busy"`, `"dripping water"`) | `<select>` enum - could not represent the stored value | text input + datalist of the engine vocabulary (`silent/quiet/normal/loud/chaotic`, `engine/sound.py`) and the descriptive words already used |
| `weather` | enum (`"clear"`) | area value shown alone; the world header's separate value was invisible | area value + a read-only `world: …` hint resolved by `SkyScape.effectiveWeather(state)` - the same function the top bar uses |

`_updateEnvLight` (new) keeps both `light` shapes; `_updateEnv` is unchanged.
The engine already read both (`engine/lighting.py` `get_light_int`), so this is
purely the authoring surface catching up to the model.

**Weather precedence, now explicit:** an area's `weather` drives that area's
prose (`engine/area_description.py:459`); the world forecast drives daylight and
the sky (`engine/weather_forecast.py` + `sky-scape.js`). They are independent
fields; the editor now shows both so "area clear / world overcast" reads as two
answers to two questions rather than a contradiction. The empty option is
relabelled "- none (no weather line) -" to match what it does.

**Live evidence** (Playwright, port 4464, `#inspector-panel`):
`area_abandoned_farm` (light `80`) → `#room-light` is an `INPUT` valued `"80"`;
`area_animal_pens` (light `"normal"`, noise `"busy"`) → light `INPUT` `"normal"`,
noise `INPUT` `"busy"`; hint reads `world: overcast`, matching the top bar.
Screenshot `inspector-640.png`. JS unit tests: 486 passed / 0 failed.


## Why

Free-form text input for area environmental properties caused syntax errors and invalid temperature/lighting values.

## How

Replaced free text fields with structured enum selects and validated numeric range sliders in the area inspector view.

## Steps to verify

1. Edit area environment properties in inspector
   - expected: Form constrains inputs to registered enums and valid numeric ranges
   - observed: Verified in area-view.ts

## Files

- `static/js/inspector/area-view.ts`
