---
group: Pleasure System
status: inprogress
---

# Environmental & Clothing Effects (Wet/Transparency/Friction)

**Filed**: 2026-08-11
**Priority**: Low
**Status**: In progress — environment + friction trickle shipped; prop defaults and wet transparency missing (task-489)

---

## Problem

Clothing needs `comfort`/`friction`/`coverage`/`opacity` properties so the LLM can reason about layer visibility, and wet clothing should become more transparent + change friction. Environment needs weather/humidity to drive wetness.

## Design

- **Item props** (graph nodes, verified item property pattern): add `comfort`, `friction`, `coverage`, `opacity` to `item.properties`. Defaults `opacity: 0.8`, `coverage: 0.8` when absent.
  - **Gap:** no defaults are applied and no `data/library/items/*.json` defines them; `_equipment_detail_lines()` only reads the props when present (`engine/equipment.py:645`). → task-489.
- **Clothing friction → arousal trickle:** per-tick sum of equipped `friction` in `tick_turn()` (`engine/tick_manager.py:83`), small Arousal gain (0-3/tick). Already designed in task-208 — keep the friction read here, hook the trickle there.
  - **Shipped** in `engine/tick_manager.py:1028-1045`, mature-gated (`:1020-1023`).
- **Environment:** extend `area_node.properties.environment` (verified, used by `engine/area_description.py` + `lighting.py`) with `weather`/`wind_speed`; humidity tracked under task-232 (task-195 was cancelled — humidity lives there).
  - **Shipped:** `weather`/`wind`/`humidity` flow through `engine/weather_forecast.py`, `engine/environment_propagation.py`, `engine/effect_handlers/weather.py`.
- **Wet clothing:** rain/swimming → clothing wet → `opacity` up (more transparent), `friction` changes, trigger `_update_equipment_description()` (`engine/equipment.py:524`). Gated by `mature_content` for the arousal-coupling parts; wetness/transparency itself is generic.
  - **Partial:** a `wet` condition exists and dampens insulation (`engine/equipment_bonuses.py:107-115`), but nothing couples wetness to `opacity`/`friction` or retriggers the description. → task-489.
- **Layer visibility** is the real fix — enrichment lands in task-210.
  - **Shipped** for reading props (task-210); the props themselves are still missing (above).

## Files

- `engine/equipment.py` — reads `opacity`/`coverage`/`friction` in `_equipment_detail_lines()` (`:645`)
- `engine/tick_manager.py` — friction trickle (`:1028-1045`)
- `engine/equipment_bonuses.py` — wet-clothing insulation loss (`:107-115`)
- `engine/weather_forecast.py` — weather/wind/humidity environment
- **missing:** prop defaults + wet→opacity/friction coupling (no `engine/item_actions.py` exists)

## Testing

- [ ] Clothing without props defaults to opacity/coverage 0.8 — **not implemented** (task-489)
- [ ] Rain → clothing wet → opacity increases, description regenerates — **not implemented**; wetness only affects insulation (`engine/equipment_bonuses.py:107`) (task-489)
- [x] Friction sum feeds arousal trickle only when mature content on — `engine/tick_manager.py:1020-1045`

## Related

- `task-489` — prop defaults + wet transparency/friction (the unmet items above)
- `dev_tasks/# Nipple & Erogenous Zone System - Desig.md` — §6, Phase 7
- `task-232 humidity`, `task-210 description enrichment`, `task-208 release/edging/friction`
