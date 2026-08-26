---
group: Environment & Climate
---
# Tag-based light and heat sources

## Summary

Turned `light_source` from a decorative tag into a mechanic gate, and added `heat_source` as its thermal counterpart. Items no longer contribute light just because they're `current_state == "lit"` — they need the `light_source` tag. Heat works the same way: slap `heat_source` on any lit item and it pushes room temperature toward its target.

`light_level` property uses string enum values instead of numbers: `pitch_black` (10), `dim` (30), `normal` (55), `bright` (80), `blinding` (95). Inspector shows a dropdown.

## Changes

### `data/library/tags/heat_source.json` — new tag

Category `state`, applies to items. When present on a lit item, the heat system reads `target_temperature` (default 30°C) and `heating_rate` (default 0.5°C/tick) and pushes area temp toward target each tick.

### `engine/lighting.py:45-55` — `light_source` tag is now required

`get_item_light_contribution()` skips items without the `light_source` tag. `light_level` accepts string enums (dim/normal/bright/etc.) or legacy numbers. Default: `"dim"` (30). Also accepts `"on"` as active state for fireplace compat.

### `engine/environment_propagation.py:112-151` — `apply_heat_sources()`

New function, called from tick_manager each tick after vitals but before temperature propagation. Scans all areas for items with `heat_source` tag + active state, pushes room temp toward each item's `target_temperature` at its `heating_rate`.

### `engine/tick_manager.py:336-338` — hook

Calls `apply_heat_sources()` then `propagate_temperature()` each tick. Order: generate heat → spread through open doors.

### `static/js/inspector/item-view.js` — inspector fields

| Tag | Fields shown |
|-----|-------------|
| `light_source` | Light Level (dropdown: pitch_black/dim/normal/bright/blinding, default dim) |
| `heat_source` | Target Temperature (°C, default 30), Heating Rate (°C/tick, default 0.5) |

Fields toggle live as tags change.

### `data/library/items/` — updated

| Item | Tag changes | Properties |
|------|-------------|-----------|
| `fireplace.json` | `+heat_source` | `light_level: "bright"`, `target_temperature: 22`, `heating_rate: 1.0` |
| `flashlight.json` | — | `light_level: 50` → `"normal"` |
| `hand_lamp.json` | `+heat_source` | `light_level: 50` → `"normal"`, `target_temperature: 25`, `heating_rate: 0.3` |
| `lantern.json` | `+heat_source` | `light_level: 40` → `"dim"`, `target_temperature: 25`, `heating_rate: 0.3` |
| `oil_lamp.json` | `+heat_source` | `+light_level: "dim"`, `target_temperature: 25`, `heating_rate: 0.3` |
| `unlit_torch.json` | `+heat_source` | `target_temperature: 28`, `heating_rate: 0.3` |
| `everflame_ember.json` | `+heat_source` | `target_temperature: 30`, `heating_rate: 0.5` |
| `stone_table_with_heating_rune.json` | `+heat_source` | `target_temperature: 30`, `heating_rate: 1.0` |

## Caveats

- The world template still has fireplace on_tick triggers doing `adjust_environment temperature +1` — redundant now but harmless (room settles ~1°C above target). Remove when convenient.
- Items carried/equipped by characters in an area contribute to light but NOT to heat (yet). Heat only scans items directly in the area via `EDGE_LOCATION`.

## Files touched

```
virtual_world/
├── data/library/
│   ├── tags/heat_source.json              ← NEW
│   └── items/{fireplace,flashlight,hand_lamp,lantern,oil_lamp,unlit_torch,everflame_ember,stone_table_with_heating_rune}.json  ← updated
├── engine/
│   ├── lighting.py                        ← tag gate + string enum light_level
│   ├── environment_propagation.py         ← apply_heat_sources(), no temp clamp
│   └── tick_manager.py                    ← hook
└── static/js/inspector/
    ├── item-view.js                       ← light_level dropdown + heat_source fields
    └── trigger-helpers.js                 ← fix "Effect: ?" for empty effects
```
