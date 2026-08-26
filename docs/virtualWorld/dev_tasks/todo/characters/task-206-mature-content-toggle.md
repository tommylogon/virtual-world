---
group: Pleasure System
---

# Mature Content Toggle

**Filed**: 2026-08-11
**Priority**: High
**Status**: Todo

---

## Problem

The pleasure/arousal system must be fully gated behind a global opt-in flag so the base game stays a standard survival RPG. Without a toggle, the new vitals, intimacy verbs, and adult traits leak into every scenario.

## Design

- **No config.toml in this repo.** Settings follow the `ghost_mode` pattern (verified): a world attribute (`app.world.mature_content`, default `False`) + `/api/settings/mature_content` GET/POST routes + frontend toggle persisted in IndexedDB via `config.js`. Mirror the existing `ghost_mode` wiring: `routes/settings.py:13-35`, `static/js/config.js:43-98`, `static/js/api.js:299-310`.
- Check the flag everywhere the erotic system touches:
  - `tick_turn()` (`engine/tick_manager.py:83`): skip arousal/stimulation/pleasure decay + threshold checks
  - `routes/action.py`: disable intimacy verbs entirely
  - `player.py` condition application: never apply `aroused`, `nipple_hard`, `wetness`, etc.
  - NPC perception: ignore sexual states
  - Trait list/UI: adult traits hidden or greyed out

## Files

- `virtual_world_engine.py` — world attribute `mature_content`
- `routes/settings.py` — GET/POST `/api/settings/mature_content`
- `static/js/config.js` + `static/js/api.js` + settings UI — toggle
- Every pleasure-system touchpoint above

## Testing

- [ ] With flag OFF: no arousal vitals appear, intimacy verbs rejected, no adult traits in list
- [ ] With flag ON: system fully active
- [ ] Toggling is respected across tick, actions, and NPC reactions

## Related

- `dev_tasks/# Nipple & Erogenous Zone System - Desig.md` — §Additions #6
