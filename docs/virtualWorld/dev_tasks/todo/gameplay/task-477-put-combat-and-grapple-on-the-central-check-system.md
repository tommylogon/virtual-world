---
type: task
status: todo
area: gameplay
priority: medium
---

# task-477: Put combat and grapple on the central check system

**Filed:** 2026-09-23
**Related:** task-472, task-475

## What

Migrate attack rolls and grapple onto engine/checks.resolve and checks.opposed so combat inherits ability modifiers, condition-driven advantage/disadvantage and the degree/critical ladder, replacing the bespoke rolling in engine/combat.py and engine/grapple.py; expose the d20 breakdown in the combat log.

## Acceptance

- TODO

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

## Browser UI and intended live verification

Intended UI home: game view → choose **Attack** or **Grapple** against a valid target → inspect the resulting combat event/log detail and character conditions.

Current availability: the card proposes moving combat and grapple from bespoke rolls to `checks.resolve`/`checks.opposed`, including ability modifiers, advantage/disadvantage, degree/critical results, and a visible d20 breakdown. This unified check presentation is not claimed as implemented.

Live steps when available:
1. In a scratch combat, attack a target with a known ability modifier and record the event log.
   - expected: the log shows the d20, modifier, final result, degree, and any critical branch used by the central check resolver.
2. Add a condition that grants advantage, then repeat the attack with the same seed and character state.
   - expected: the condition contributes through the central check path and the log identifies the advantage result; the bespoke combat roller is not also applied.
3. Grapple the same target with known opposed modifiers, then repeat with a disadvantage condition.
   - expected: attacker and defender rolls/modifiers and opposed degree are visible; disadvantage affects the appropriate side once.
4. Compare attack/grapple outcomes with the same central check configuration outside combat.
   - expected: identical inputs resolve through the same degree/critical ladder and produce the same result class.

This section is not a claim that planned UI exists or works today.
