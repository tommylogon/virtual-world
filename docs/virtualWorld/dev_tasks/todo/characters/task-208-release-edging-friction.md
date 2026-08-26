---
group: Pleasure System
---

# Release Event, Edging & Clothing Friction

**Filed**: 2026-08-11
**Priority**: High
**Status**: Todo

---

## Problem

The arousal meter needs a payoff path (release), a frustration path (edging), and a passive source (clothing friction). None exist yet.

## Design

- Release event in `tick_turn()`: when `Stimulation >= 65` AND `Arousal >= 40` → trigger cascade (Energy -20, Entertainment +30, Hygiene -10, Sanity +15, Stimulation reset to 5, Arousal -30, apply `satisfied` 20t + `overstimulated` 5t).
- Edging in `tick_turn()`: when `50 <= Stimulation < 65`, add `sensitized` (level 1, 10t) stacks + Arousal +1.
- Clothing friction: per tick sum `friction` over equipped items → small Arousal trickle (0-3/tick).

## Files

- `engine/tick_manager.py` — `tick_turn()` hooks: `_check_release_threshold`, `_trigger_release_event`, `_apply_edging_effect`, `_apply_clothing_friction`

## Testing

- [ ] Release fires only above threshold, applies correct vital deltas + conditions
- [ ] Edging adds `sensitized` stacks without releasing
- [ ] Friction trickle present with equipped clothing, absent when naked

## Related

- `dev_tasks/# Nipple & Erogenous Zone System - Desig.md` — §4 Release/Edging, §6 friction, Phase 1
