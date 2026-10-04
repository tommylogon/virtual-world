---
type: task
status: todo
area: characters
priority: medium
related: [task-426, task-409, task-685]
blocked_by: [task-701, task-702, task-705]
---

# task-704: GOSP selector: needs, memory and personality choose and bind plans

**Filed:** 2026-10-04
**Related:** task-426,task-409,task-685

## Goal

The goal-selection layer: on need-signals and plan completion (never per tick), score candidate plan templates from current vitals, memories and perception, then bind parameters (whose bed, which area, until what). Personality enters as goal weights and precondition sloppiness (a low-caution merchant drops the 'bring weapon' requirement) so bad plans emerge from the same catalog as good ones. LLM agents get the same catalog offered in their decide phase instead of a separate mechanism. Memory-triggered goals: a recalled belief (gemstones in the hills) can raise a goal - and falsified beliefs correct it through the normal memory loop. Integrate task-426's archetypes as the first bound templates.

## Acceptance
- [ ] Selection fires on need-signals and plan completion, never per tick -
      measured against the background runner's budget like task-409's data
      decision (A/B before shipping any catalog-wide behavior).
- [ ] Personality enters as goal weights and requirement sloppiness: the same
      catalog yields different plans for different characters, and a low-
      caution character demonstrably drops a safety requirement (the Belne
      case) without any authored "bad plan" template.
- [ ] Memory-triggered goals: a recalled belief raises a goal; when the belief
      is falsified by perception, the goal dies and the correcting memory is
      written through the normal loop (task-685 integration).
- [ ] LLM agents receive the same candidate catalog in their decide phase -
      one catalog, two selectors; the typed plan they emit (task-700) can be a
      template binding or a fresh composition.
- [ ] Actor sovereignty holds at the selector too: a chosen plan binds only
      the actor's own parameters and never pre-decides another character's
      response.
- [ ] task-426's archetypes are either absorbed as the first bound templates
      or explicitly retired with a pointer - no second archetype system
      survives alongside this one.
