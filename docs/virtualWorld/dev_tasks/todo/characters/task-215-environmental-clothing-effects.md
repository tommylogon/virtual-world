---
group: Pleasure System
---

# Environmental & Clothing Effects (Wet/Transparency/Friction)

**Filed**: 2026-08-11
**Priority**: Low
**Status**: Todo

---

## Problem

Clothing needs `comfort`/`friction`/`coverage`/`opacity` properties so the LLM can reason about layer visibility, and wet clothing should become more transparent + change friction. Environment needs weather/humidity to drive wetness.

## Design

- **Item props** (graph nodes, verified item property pattern): add `comfort`, `friction`, `coverage`, `opacity` to `item.properties`. Defaults `opacity: 0.8`, `coverage: 0.8` when absent.
- **Clothing friction → arousal trickle:** per-tick sum of equipped `friction` in `tick_turn()` (`engine/tick_manager.py:83`), small Arousal gain (0-3/tick). Already designed in task-208 — keep the friction read here, hook the trickle there.
- **Environment:** extend `area_node.properties.environment` (verified, used by `engine/area_description.py` + `lighting.py`) with `weather`/`wind_speed`; humidity tracked under task-232 (task-195 was cancelled — humidity lives there).
- **Wet clothing:** rain/swimming → clothing wet → `opacity` up (more transparent), `friction` changes, trigger `_update_equipment_description()` (`engine/equipment.py:524`). Gated by `mature_content` for the arousal-coupling parts; wetness/transparency itself is generic.
- **Layer visibility** is the real fix — enrichment lands in task-210.

## Files

- `engine/item_actions.py` / `engine/equipment.py` — item prop defaults + wetness state
- `engine/tick_manager.py` — wetness/environment checks
- `engine/area_description.py` — environment-driven wet clothing
- `data/library/items/*.json` — optional prop additions to seed clothing

## Testing

- [ ] Clothing without props defaults to opacity/coverage 0.8
- [ ] Rain → clothing wet → opacity increases, description regenerates
- [ ] Friction sum feeds arousal trickle only when mature content on

## Related

- `dev_tasks/# Nipple & Erogenous Zone System - Desig.md` — §6, Phase 7
- `task-232 humidity`, `task-210 description enrichment`, `task-208 release/edging/friction`
