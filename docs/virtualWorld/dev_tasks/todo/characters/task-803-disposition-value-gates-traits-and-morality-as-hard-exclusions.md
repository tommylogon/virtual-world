---
type: task
status: todo
area: characters
priority: medium
wiki: "[[Character Pursuits]]"
related: [task-704]
blocked_by: [task-800]
---

# task-803: Disposition value gates: traits and morality as hard exclusions

**Filed:** 2026-10-12
**Related:** task-704

<!-- deps:start -->
**Blocked by:** [[task-800-disposition-score-registry-declare-the-decision-score-vocabulary]]
**Related:** [[task-704-mosiac-selector-needs-memory-and-personality-choose-and-bind-plans]]
<!-- deps:end -->

## What

Hard gates that REMOVE options (honest excludes theft, nonviolent excludes attack, loyal excludes betraying an ally), as distinct from weights that merely lower a score.

## Why

A weight says 'rather not'; a gate says 'cannot'. Personality must never make an impossible action possible, and morality is an exclusion, not a preference.

## How

Gate table keyed by trait/moral flag -> excluded verb classes. Applied after the capability gates (budget, prereqs, location). Never a score delta.

## Steps to verify

1. In the app, open the action menu for a character carrying `honest`, beside a stealable item.
   - expected: the steal verb is ABSENT from the menu, not present as a low-score option.
   - observed: TODO
2. A character with no value traits, same room.
   - expected: the verb is present, so the gate is trait-driven and not global.
   - observed: TODO

## Acceptance

- [ ] A gate removes the option; it is never only a score penalty.
- [ ] Gates never enable an action the capability gate denied.

## Files

- `engine/disposition.py`
