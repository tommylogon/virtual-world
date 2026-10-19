---
type: task
status: todo
area: items
priority: high
related: [task-2, task-18, task-197, task-504, task-472, task-699, task-701, task-702, task-807]
blocked_by: [task-701, task-702]
wiki: "[[Items and Inventory/Item System & Properties Overview]]"
---

# task-703: World recipes resolve transformations performed by Activities

**Clarified:** 2026-10-05

<!-- deps:start -->
**Blocked by:** [[task-701-plan-template-library-generic-plan-schedule-templates-as-versioned-library-entries]], [[task-702-plan-executor-runtime-the-engine-runs-typed-plans-for-any-character-with-invalidation-and-needs-override]]
**Related:** [[task-2-crafting_and_recipes]], [[task-18-fireplace_lighting_recipe]], [[task-197-teach-skill-recipe]], [[task-504-item-quantity-property-and-pooled-resource-nodes]], [[task-472-central-dice-and-check-resolution]], [[task-699-mosiac-design-doc-schedules-plan-templates-and-recipe-activities-as-one-decision-layer]], [[task-701-plan-template-library-generic-plan-schedule-templates-as-versioned-library-entries]], [[task-702-plan-executor-runtime-the-engine-runs-typed-plans-for-any-character-with-invalidation-and-needs-override]], [[task-807-gimp-the-goal-model-and-its-serialization]]
<!-- deps:end -->

## What

Keep three meanings distinct. A **Pursuit** can bring a character to a place and give them a reason to cook. The **cooking Activity** is the visible process happening over time at a cooking area. The **world recipe** defines how the food transformation resolves: required ingredients, equipment, area conditions, duration, skill/quality tiers, and resulting items.

Evolve task-2's crafting from instant graph-node transmutation to a world-recipe entry while preserving the existing `craft_item` path, condition leaves, and `give_item` outputs. A breakfast schedule may prompt a meal-preparation pursuit; it does not own the cooking rules.

## Acceptance

- [ ] A world recipe is stored separately from pursuit templates. The graph-node recipe shape is retired (never nodes — see task-831 and the AGENTS.md invariant); task-2's engine execution (`craft_item`, condition leaves, `give_item` outputs) remains the normal dispatch underneath, reading the recipe registry.
- [ ] “Make X” checks recipe requirements before starting and answers with an explicit missing list, such as “you are missing: egg.” Keep today's fail-closed behavior.
- [ ] On success, the character starts the crafting/cooking Activity at the required area or station for the recipe's game-minute duration (the egg: 10 minutes). The Activity is visible and interruptible according to its authored rules; it binds the actual station and any required spatial relationship.
- [ ] Completion rechecks required conditions and resolves the world recipe once. Interruption cannot create an output or quality result unless the normal action path says the transformation completed.
- [ ] Skill checks use task-472's central dice and can produce authored quality tiers such as cooked or burned (optionally perfect).
- [ ] Author the cooked-egg recipe end to end in the fixture world. A meal-preparation pursuit can call that recipe, and a clock schedule can prompt the pursuit at breakfast time.
- [ ] Demonstrate the Activity, recipe outcome, and pursuit progress in the browser and event stream; another character can perceive the cook at the station.
- [ ] Resolve task-2's review status with a pointer to this task; retire the old node shape rather than maintaining a second source of truth (recipes are entries per task-831, never graph nodes).

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

Intended UI home: game view → request **Make X** → inspect the missing-requirements result or the character's cooking Activity at the required station → inspect the produced item and event stream.

Current availability: the card separates a Pursuit (reason/place), cooking Activity (visible timed process), and world recipe (requirements and transformation). Recipe templates and timed Activity execution are not claimed as implemented by this card.

Live steps when available:
1. In a scratch world, use the authored egg recipe without one required ingredient and submit `Make X`.
   - expected: the action fails closed and lists the exact missing ingredient (for example, “you are missing: egg”); it does not consume ingredients or create output.
2. Supply all ingredients and required equipment, place the character at the authored cooking station, and request the same recipe.
   - expected: the character starts the recipe's timed cooking Activity at that station; the Activity is visible and can be interrupted according to its authored rule.
3. Advance the world through the recipe duration and inspect the event stream, inventory, and activity status.
   - expected: the normal `craft_item`/condition/`give_item` dispatch produces the authored result once at completion; no instant graph-node transmutation bypasses the Activity.
4. Repeat with a failed condition or interrupted Activity.
   - expected: the recipe's fail outcome applies, required ingredients are not silently duplicated, and the Pursuit does not own the recipe's resolution rules.

This section is not a claim that planned UI exists or works today.
