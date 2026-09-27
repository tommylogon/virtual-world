---
group: Pleasure System
status: done
type: task
area: characters
priority: low
---

# Mature Traits & Body Reactions (folded from design v3.1)

**Filed**: 2026-08-11
**Closed**: 2026-09-27
**Priority**: Low
**Status**: Done — 7 trait definitions shipped, 5 with live consumers. The two
inert traits and the three undelivered body reactions were split out to task-487,
task-488 and task-534.

---

## Problem

The design calls for personality traits that modulate the pleasure system (`wired_differently`, `attention_seeker`, `exhibitionist`, `quick_recovery`, `sensory_memory`, `single_track`, `sex_addict`) plus a set of non-erotic "body reactions" (goosebumps, shivers, cough, sneeze, hiccup, itch).

## What shipped

Seven mature trait definitions at `engine/traits.py`, each `"mature": True`.
Five have live consumers:

| Trait | Consumer | Test |
|-------|----------|------|
| `wired_differently` | `engine/pleasure_actions.py` (`body_part_multipliers`) | `tests/test_pleasure_system.py` |
| `quick_recovery` | `engine/tick_manager.py` | `tests/test_pleasure_system.py` |
| `sensory_memory` | `engine/tick_manager.py` | **none** |
| `sex_addict` | `engine/tick_manager.py` | **none** |
| `attention_seeker` | `engine/background_social.py` | **none** |

`body_part_multipliers` rides inside the standard `effects` dict rather than
inventing a parallel schema key, and is consumed by the pleasure pipeline
(task-212).

Mature gating works: `routes/library_ops.py` (`_filter_mature_entries`)
drops `mature: true` entries from the registries unless `mature_content` is on.
The definitions stay functional either way, so a save authored with the toggle on
keeps working when it is off.

### Inert definitions

`exhibitionist` (`engine/traits.py`) and `single_track` 
define their effect flags but **nothing reads them** — there is no
`has_effect(..., "exhibitionist")` or `"single_track"` consumer anywhere in the
tree. They are currently decorative: a character can be assigned either and
nothing happens. Both were split out rather than left as silent no-ops here:

- **task-487** — exhibitionist trait effect (arousal from being seen)
- **task-488** — single_track trait effect (gate release to one path)

## Body reactions — the deferral did not fully land

This task originally deferred all body reactions to task-166, on the reasoning that
they overlap heavily. task-166 shipped (2026-09-22) and covered most of them as
condition-driven speech interruptions in `static/js/agent/involuntary.js`:

| Reaction | Status | Where |
|----------|--------|-------|
| hiccup | shipped | `involuntary.js` (`GENERIC_SPEECH` baseline) |
| shiver | shipped | `involuntary.js` (`hypothermia` → shiver, 0.40) |
| cough | shipped | `involuntary.js` (`sick` 0.35, `poisoned` 0.40) |
| stutter / ramble / yelp | shipped (166's own scope) | `involuntary.js-52, 32` |
| **goosebumps** | **already shipped** | condition at `engine/player_conditions.py`; emote pool in `involuntary.js` |
| **itch** | **already shipped** | condition in `player_conditions.py` + `data/library/conditions/itch.json`; emote pool; unit test in `test_involuntary.js` |
| **sneeze** | **missing** | no condition, no trigger — genuinely absent |

> **Correction, 2026-09-27.** An earlier revision of this table said `goosebumps`
> and `itch` were also missing, on the strength of a regex search that missed
> `engine/player_conditions.py` entirely (and matched "pitch"/"switch" inside
> `pitch_black` and `switch` statements). Re-measured: both were already complete.
> Only `sneeze` ever was missing, and task-534 shrank to match.

So the deferral was correct in principle, but the receiving task took only one of
the items 213 flagged as "what task-166 misses" — the other two were never
missing at all (see the correction above). The one real gap, `sneeze`, is now
**task-534**.

## Testing

- [x] `wired_differently` multiplies the authored body parts — `tests/test_pleasure_system.py`
- [x] `quick_recovery` halves the overstimulation bout — `tests/test_pleasure_system.py`
- [ ] `sex_addict` doubles Entertainment decay at low arousal — **implemented at
 `engine/tick_manager.py` but untested.** Code presence was previously
 recorded here as if it were verification; it is not.
- [ ] `sensory_memory` lingering sensitivity — implemented, untested
- [ ] `attention_seeker` arousal when observed — implemented, untested
- [x] Adult traits hidden when `mature_content` off — `routes/library_ops.py`
- [ ] Body reactions work without the mature toggle — true for everything task-166
 shipped (they are condition-driven and independent of `mature_content`); the
 three missing ones are task-534.

The three untested traits are the honest gap in this task. They are cheap to cover
and worth adding alongside task-534 rather than reopening 213.

## Related

- task-487 — exhibitionist trait effect (inert here)
- task-488 — single_track trait effect (inert here)
- task-534 — goosebumps / sneeze / itch, the body reactions 213 deferred and
 task-166 did not deliver
- `dev_tasks/# Nipple & Erogenous Zone System - Desig.md` — §7, §Additions #2/#4
- task-166 (done) — involuntary actions; covered hiccups, burps, yelps, stutters,
 shiver, cough, ramble
- task-212 — verb multipliers (`body_part_multipliers` consumer)
