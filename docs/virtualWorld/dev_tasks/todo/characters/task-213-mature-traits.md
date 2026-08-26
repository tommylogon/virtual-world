---
group: Pleasure System
---

# Mature Traits & Body Reactions (folded from design v3.1)

**Filed**: 2026-08-11
**Priority**: Low
**Status**: Todo

---

## Problem

The design calls for personality traits that modulate the pleasure system (`wired_differently`, `attention_seeker`, `exhibitionist`, `quick_recovery`, `sensory_memory`, `single_track`, `sex_addict`) plus a set of non-erotic "body reactions" (goosebumps, shivers, cough, sneeze, hiccup, itch).

## Design

### Traits

- Add to `TRAIT_DEFINITIONS` (`engine/traits.py:90`), respecting the **existing schema** — `name`, `description`, `category`, `params`, `effects` (VITAL_MULTIPLIER etc.), `conflicts`. New pleasure traits need a parallel `body_part_multipliers` key (consumed by task-212) since the stock `effects` dict doesn't know about body parts:
  - `wired_differently` — nipple ×3.0, genital ×0.1
  - `attention_seeker` — arousal on being looked at
  - `exhibitionist` — arousal on public nudity, behavior_prompt
  - `quick_recovery` — halves overstimulated duration
  - `sensory_memory` — lingering sensitivity after release
  - `single_track` — release gated to one path
  - `sex_addict` — Entertainment decay ×2 when Arousal < 15
- All hidden from trait pickers unless `mature_content` on (task-206).

### Body Reactions (non-erotic)

- **NOTE: task-166 already covers involuntary actions** (hiccups, burps, yelps, stutters, `static/js/agent-engine.js` speech post-processing). Goosebumps/shivers/cough/sneeze/itch overlap heavily — extend task-166 rather than duplicating. Only add what task-166 misses (itch, goosebumps as condition-driven).
- These are always active, independent of `mature_content`.

## Files

- `engine/traits.py` — new trait definitions
- `engine/pleasure_actions.py` — trait multiplier consumption
- `static/js/agent-engine.js` / `prompt-builder.js` — body reaction injection (via task-166)
- `static/js/character creation` — trait hiding behind mature flag

## Testing

- [ ] Each trait's effect applies (e.g. wired_differently nipple actions ×3)
- [ ] `sex_addict` Entertainment decay doubles at low arousal
- [ ] Body reactions from task-166 work without mature toggle
- [ ] Adult traits invisible when mature_content off

## Related

- `dev_tasks/# Nipple & Erogenous Zone System - Desig.md` — §7, §Additions #2/#4
- `task-166 involuntary actions`, `task-212 verb multipliers`
