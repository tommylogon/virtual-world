---
group: Pleasure System
status: inprogress
---

# Mature Traits & Body Reactions (folded from design v3.1)

**Filed**: 2026-08-11
**Priority**: Low
**Status**: In progress — 7 traits shipped, `exhibitionist`/`single_track` effects inert; remaining work: task-487, task-488

---

## Problem

The design calls for personality traits that modulate the pleasure system (`wired_differently`, `attention_seeker`, `exhibitionist`, `quick_recovery`, `sensory_memory`, `single_track`, `sex_addict`) plus a set of non-erotic "body reactions" (goosebumps, shivers, cough, sneeze, hiccup, itch).

## Design

### Traits

- Add to `TRAIT_DEFINITIONS` (`engine/traits.py:90`), respecting the **existing schema** — `name`, `description`, `category`, `params`, `effects` (VITAL_MULTIPLIER etc.), `conflicts`. New pleasure traits need a parallel `body_part_multipliers` key (consumed by task-212) since the stock `effects` dict doesn't know about body parts:
  - `wired_differently` — nipple ×3.0, genital ×0.1 — **shipped**; `body_part_multipliers` consumed by `engine/pleasure_actions.py:97-108`
  - `attention_seeker` — arousal on being looked at — **shipped**; consumed in `engine/background_social.py:227,271,304`
  - `exhibitionist` — arousal on public nudity, behavior_prompt — **inert**: effect flag defined but no consumer (`has_effect(...,"exhibitionist")` appears nowhere)
  - `quick_recovery` — halves overstimulated duration — **shipped**; `engine/tick_manager.py:1066-1068`
  - `sensory_memory` — lingering sensitivity after release — **shipped**; `engine/tick_manager.py:1071-1072`
  - `single_track` — release gated to one path — **inert**: effect flag defined but no consumer
  - `sex_addict` — Entertainment decay ×2 when Arousal < 15 — **shipped**; `engine/tick_manager.py:322-325`
- All hidden from trait pickers unless `mature_content` on (task-206). **Shipped** via the registry filter in `routes/library_ops.py:195-205` (drops `mature: true` entries when the toggle is off).

### Body Reactions (non-erotic)

- **NOTE: task-166 already covers involuntary actions** (hiccups, burps, yelps, stutters, `static/js/agent-engine.js` speech post-processing). Goosebumps/shivers/cough/sneeze/itch overlap heavily — extend task-166 rather than duplicating. Only add what task-166 misses (itch, goosebumps as condition-driven).
- These are always active, independent of `mature_content`.

## Files

- `engine/traits.py` — 7 mature trait definitions (`:210-276`), each `"mature": True`
- `engine/pleasure_actions.py` — `body_part_multipliers` consumption (`:97-108`)
- `engine/tick_manager.py` — `quick_recovery`/`sensory_memory`/`sex_addict` effects
- `engine/background_social.py` — `attention_seeker`
- `routes/library_ops.py` — mature gating for the traits/conditions registries (`:195-205`)

## Testing

- [ ] Each trait's effect applies (e.g. wired_differently nipple actions ×3) — 5 of 7 wired; `exhibitionist` (task-487) and `single_track` (task-488) have no consumer
- [x] `sex_addict` Entertainment decay doubles at low arousal — `engine/tick_manager.py:322-325`
- [ ] Body reactions from task-166 work without mature toggle — deferred to task-166 (design note); itch/goosebumps not verified here
- [x] Adult traits invisible when mature_content off — registry filter `routes/library_ops.py:195-205`

## Related

- `task-487` — exhibitionist trait effect (inert here)
- `task-488` — single_track trait effect (inert here)
- `dev_tasks/# Nipple & Erogenous Zone System - Desig.md` — §7, §Additions #2/#4
- `task-166 involuntary actions` (in review — covers body reactions), `task-212 verb multipliers`
