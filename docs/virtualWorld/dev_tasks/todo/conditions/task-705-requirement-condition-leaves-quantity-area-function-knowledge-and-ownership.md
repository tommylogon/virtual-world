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

<!-- deps:start -->
**Related:** [[task-566-let-the-simulation-seek-a-place-by-function-a-bed-a-forge-a-bath]], [[task-504-item-quantity-property-and-pooled-resource-nodes]], [[task-472-central-dice-and-check-resolution]], [[task-699-mosiac-design-doc-schedules-plan-templates-and-recipe-activities-as-one-decision-layer]], [[task-701-plan-template-library-generic-plan-schedule-templates-as-versioned-library-entries]], [[task-702-plan-executor-runtime-the-engine-runs-typed-plans-for-any-character-with-invalidation-and-needs-override]]
<!-- deps:end -->

## What

Extend the shared condition-leaf vocabulary so pursuit templates and world recipes can express requirements in the house grammar: `has_quantity` (item + count, from pooled resources task-504), `area_has_function` (a heat source, a river, a bed - ties task-566's place-by-function), `knows_about` (a memory query as a requirement - the merchant's gemstone belief), and `owns` (ownership as a property). Unknown leaves fail closed, as everywhere. These leaves are consumed by the short-term plan grounding validator, pursuit-template requirements, and selector alike - one vocabulary, no parallel condition system. Activity start requirements use the same leaves; the Activity itself remains runtime state, not a template.

**Every leaf declares its subject (2026-10-13).** A leaf is meaningless until it says what it is about. `tag:meaningful_challenge` cannot be evaluated - a tag on *what*? The holder, a named entity, the world? This is the single most load-bearing ambiguity in the goal layer: 8 of the 15 goals in `docs/design/Zikka_GIMP_MOSIAC_Proposal_v2.json` block on a bare `tag:` ref. So each leaf below names its subject explicitly:

| leaf | subject | reads |
|---|---|---|
| `has_quantity` | holder | pooled/stacked item count |
| `area_has_function` | a named area, or any area with the function | task-566's function index |
| `knows_about` | holder | a memory query |
| `owns` | holder | ownership-as-property |
| `tag` | **must be stated**: `tag:holder:<t>` / `tag:entity:<id>:<t>` / `tag:world:<t>` | node/player tags |
| `present` | a named character | **co-location**, not node existence |
| `known` | holder | `Player.known` |
| `flag` | holder or world | a stored fact a trigger or action sets |

`world_resolvers.character` is *node existence*, which is permanently true and therefore useless as a gate. Co-location is `present:`, and it is a different predicate - do not overload `character:` for it.

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
- [ ] Every leaf declares its subject, and `tag` / `present` / `known` / `flag`
      exist as stated in the table above.
- [ ] Unknown leaves fail closed everywhere (validator, template load,
      selector), matching the existing trigger-leaf contract.
- [ ] Each leaf has a unit test proving the mechanism AND a micro-scenario
      proving it is reachable from a real plan requirement.

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO
