---
type: task
status: inprogress
area: docs
priority: high
related: [task-409, task-426, task-2, task-694]
---

# task-699: GOSP design doc: schedules, plan templates and recipe activities as one GOAP layer

**Filed:** 2026-10-04
**Related:** task-409,task-426,task-2,task-694

## Goal

Write docs/virtualWorld/design/GOSP-schedules.md - the spine document for the schedule/recipe/planning vision. First line: 'This is GOAP; the action vocabulary is schedules; the blackboard is memory and perception; the goals are needs weighted by personality.' Must capture: the six primitives (go, perform, observe, take, restore, wait); plan templates as library entries generic like items; actor sovereignty (a schedule resolves nothing but its owner's intent - no other-character reactions, no world events as fail conditions); plans as disposable (invalidation means re-compose, not on_fail chains); durations in game minutes with sub-tick completion rule; the ladder (freeform LLM plan -> archetypes task-426 -> templates -> schedules); the Vekka 'use hanging meat' event-stream exhibit as the grounding motivation; and the fisherman as the acceptance test.

## Acceptance
- [ ] The doc opens with the GOAP declaration and names the referent (F.E.A.R. /
      Jeff Orkin's GOAP) so the next contributor or AI does not rebuild a
      template library and call it the vision.
- [ ] Defines the six primitives with their precondition/effect shapes, and
      shows the taxonomy collapsing (work/sleep/travel/mingle/craft/forage/
      patrol/raid/stalk are bindings, not separate systems).
- [ ] States the constitutional rules: actor sovereignty; plans disposable -
      invalidation means re-compose; needs outrank any plan; every step and
      timer re-verifies preconditions on fire; durations in game minutes.
- [ ] Contains the 2026-10-04 event-stream exhibit (Vekka, "use hanging meat")
      as the grounding motivation, with the same plan re-typed as facts.
- [ ] Carries the 15 composition examples (kraktooth + mansion) as worked
      cases, including the butcher as cached-plan horror and whiskers as the
      depth-one degenerate case.
- [ ] States the ladder explicitly (freeform LLM plan -> archetypes -> templates
      -> schedules) and what each rung adds; names the fisherman as the
      acceptance test.
- [ ] Linked from the relevant Feature Map row once one exists.
