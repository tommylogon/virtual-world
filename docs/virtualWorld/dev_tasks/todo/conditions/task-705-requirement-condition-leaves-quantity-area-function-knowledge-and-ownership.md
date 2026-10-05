---
type: task
status: todo
area: conditions
priority: medium
related: [task-566, task-504, task-472, task-699, task-701, task-702]
---

# task-705: Requirement condition leaves: quantity, area-function, knowledge and ownership

**Filed:** 2026-10-04
**Related:** task-566,task-504,task-472

## Goal

Extend the shared condition-leaf vocabulary so pursuit templates and world recipes can express requirements in the house grammar: `has_quantity` (item + count, from pooled resources task-504), `area_has_function` (a heat source, a river, a bed - ties task-566's place-by-function), `knows_about` (a memory query as a requirement - the merchant's gemstone belief), and `owns` (ownership as a property). Unknown leaves fail closed, as everywhere. These leaves are consumed by the short-term plan grounding validator, pursuit-template requirements, and selector alike - one vocabulary, no parallel condition system. Activity start requirements use the same leaves; the Activity itself remains runtime state, not a template.

## Acceptance
- [ ] has_quantity: item + count against pooled/stacked resources
      (task-504 shapes), consumed correctly by requirement checks.
- [ ] area_has_function: resolves areas by function (heat source, river, bed)
      through task-566's function index - a requirement names a function, not
      a node id.
- [ ] knows_about: a memory query as a requirement (the merchant's gemstone
      belief); falsifiable - when perception contradicts it, the requirement
      stops resolving and the belief-correction memory path fires.
- [ ] owns: ownership-as-property check for beds, tools, claimed spots.
- [ ] Unknown leaves fail closed everywhere (validator, template load,
      selector), matching the existing trigger-leaf contract.
- [ ] Each leaf has a unit test proving the mechanism AND a micro-scenario
      proving it is reachable from a real plan requirement.
