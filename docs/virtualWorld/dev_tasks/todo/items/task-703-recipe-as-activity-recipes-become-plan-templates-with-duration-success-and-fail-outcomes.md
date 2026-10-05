---
type: task
status: todo
area: items
priority: medium
related: [task-2, task-18, task-197, task-504, task-472, task-699, task-701, task-702]
blocked_by: [task-701, task-702]
---

# task-703: World recipes resolve transformations performed by Activities

**Clarified:** 2026-10-05

## Goal

Keep three meanings distinct. A **Pursuit** can bring a character to a place and give them a reason to cook. The **cooking Activity** is the visible process happening over time at a cooking area. The **world recipe** defines how the food transformation resolves: required ingredients, equipment, area conditions, duration, skill/quality tiers, and resulting items.

Evolve task-2's crafting from instant graph-node transmutation to a world-recipe entry while preserving the existing `craft_item` path, condition leaves, and `give_item` outputs. A breakfast schedule may prompt a meal-preparation pursuit; it does not own the cooking rules.

## Acceptance

- [ ] A world recipe is stored separately from pursuit templates. The graph-node recipe format is migrated with a documented path; task-2's engine execution (`craft_item`, condition leaves, `give_item` outputs) remains the normal dispatch underneath.
- [ ] “Make X” checks recipe requirements before starting and answers with an explicit missing list, such as “you are missing: egg.” Keep today's fail-closed behavior.
- [ ] On success, the character starts the crafting/cooking Activity at the required area or station for the recipe's game-minute duration (the egg: 10 minutes). The Activity is visible and interruptible according to its authored rules; it binds the actual station and any required spatial relationship.
- [ ] Completion rechecks required conditions and resolves the world recipe once. Interruption cannot create an output or quality result unless the normal action path says the transformation completed.
- [ ] Skill checks use task-472's central dice and can produce authored quality tiers such as cooked or burned (optionally perfect).
- [ ] Author the cooked-egg recipe end to end in the fixture world. A meal-preparation pursuit can call that recipe, and a clock schedule can prompt the pursuit at breakfast time.
- [ ] Demonstrate the Activity, recipe outcome, and pursuit progress in the browser and event stream; another character can perceive the cook at the station.
- [ ] Resolve task-2's review status with a pointer to this task; retire the old node format rather than maintaining a second source of truth.
