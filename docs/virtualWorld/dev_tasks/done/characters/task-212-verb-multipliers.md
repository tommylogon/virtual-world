---
area: characters
status: done
type: task
priority: medium
related: ['task-207', 'task-208', 'task-209', 'task-210', 'task-211', 'task-213', 'task-215']
---

# Verb Base Multipliers & Action→BodyPart→Trait Pipeline

**Filed**: 2026-08-11
**Priority**: Medium
**Status**: Done - shipped in v1.4.0

---

<!-- deps:start -->
**Related:** [[task-207-body-state-and-vitals]], [[task-208-release-edging-friction]], [[task-209-physiological-state-conditions]], [[task-210-description-enrichment]], [[task-211-intimacy-verbs-actions]], [[task-213-mature-traits]], [[task-215-environmental-clothing-effects]]
<!-- deps:end -->

## Why

Each intimacy verb needs base mechanical properties (pressure, pleasure multiplier, pain potential, stim type) so the system can compute stimulation before intensity/body-part/trait modifiers. Without defaults, "gentle kiss" vs "firm pinch" can't be calculated.

## How

- New file `engine/pleasure_actions.py` with `VERB_BASE` table (from design §Additions #1): `caress/pinch/kiss/lick/suck/bite/blow/tickle` with `pressure`, `pleasure_mult`, `pain_potential`, `stim_type` (sustained/rhythmic/spike).
- Multiplier pipeline: `VERB_BASE → × intensity modifier (light/normal/firm) → × body_part sensitivity (from `body_state`) → × trait multiplier (per-body-part) → applies to Stimulation/Pleasure, adjusted by mood/context/relationship`.
- `pain_potential` flips to negative pleasure if it exceeds comfort (overstimulation).
- **Trait multiplier source:** read from `TRAIT_DEFINITIONS` (`engine/traits.py:90`) - see task-213. Design's `"multipliers": {"body_part:nipple": 3.0}` shape needs mapping onto the existing trait `effects` schema, or a parallel `body_part_multipliers` key on the trait dict.

## Files

- `engine/pleasure_actions.py` - NEW: `VERB_BASE`, `apply_stimulation()`, multiplier pipeline
- `engine/traits.py` - body-part multiplier lookup (see task-213)

## Steps to verify

- [ ] Same verb + different intensity scales stimulation correctly
- [ ] Body-part sensitivity (nipple 0.9 vs 0.7) affects gain
- [ ] Trait multiplier (e.g. `wired_differently` nipple ×3.0) applies
- [ ] Pain potential can make pleasure go negative (overstimulation)

## Related

- `dev_tasks/# Nipple & Erogenous Zone System - Desig.md` - §Additions #1, Phase 4
- `task-211 intimacy verbs` (action dispatch), `task-213 traits`

## What

TODO

## Acceptance

- [ ] TODO
