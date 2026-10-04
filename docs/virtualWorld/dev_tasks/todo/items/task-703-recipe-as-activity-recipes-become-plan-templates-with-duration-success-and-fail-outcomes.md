---
type: task
status: todo
area: items
priority: medium
related: [task-2, task-18, task-197, task-504, task-472]
blocked_by: [task-701, task-702]
---

# task-703: Recipe-as-activity: recipes become plan templates with duration, success and fail outcomes

**Filed:** 2026-10-04
**Related:** task-2,task-18,task-197,task-504,task-472

## Goal

Evolve task-2's crafting from instant graph-node transmutation to the plan-template model: a recipe is a library plan template (requirements incl. equipment and area state, duration in game minutes, skill check with quality tiers such as cooked/burned, success and fail outcome items). 'make X' checks requirements up front and replies with a missing-list; on success the character enters the crafting activity for the duration. The craft_item engine path, condition leaves and give_item outputs survive under the new format; graph-node recipe definitions are migrated to library entries. Author the first recipe (cooked egg) end to end in the fixture world as the reference implementation.

## Acceptance
- [ ] A recipe is a library plan template; the graph-node recipe format is
      migrated (migration path documented; task-2's engine execution -
      craft_item, condition leaves, give_item outputs - survives underneath).
- [ ] "make X" checks requirements up front and answers with an explicit
      missing-list ("you are missing: egg") when they fail - the fail-closed
      behavior of today, unchanged.
- [ ] On success the character enters the crafting activity for the recipe's
      duration in game minutes (the egg: 10), visibly occupied at the required
      area state (heat source lit), interruptible; interruption re-verifies
      preconditions and routes to the fail outcome or re-composition.
- [ ] Skill check produces quality tiers (cooked / burned; optionally perfect)
      through task-472's central dice.
- [ ] The egg is authored end to end in the fixture world and demonstrable in
      the browser: human verb path AND a simple NPC cooking on a schedule.
- [ ] task-2's review status is resolved with a pointer to this task - the
      old node format is retired, not left as a second source of truth.
