---
area: items
wiki: "[[Items & Inventory/Items Overview]]"
type: task
status: review
priority: medium
related: [task-197, task-831, task-155]
---

# Crafting and Recipe System

**Filed**: 2026-07-15
**Priority**: Medium
**Status**: Draft / Not Started

---

<!-- deps:start -->
**Related:** [[task-197-teach-skill-recipe]], [[task-831-crafting-recipe-schema-v2-ingredients-duration-tiered-outcomes]], [[task-155-item-uses-affect-weight]]
<!-- deps:end -->

## What

Add a crafting/recipe system where items can be combined to create new items. Example: if character has recipe for "fried eggs" and uses egg on pan while oven is on → spawn fried_egg. If requirements not met → descriptive error message.

## How

### Recipe Format

> RETRACTED 2026-10-15: recipes are NEVER graph nodes. Graph nodes are
> physical entities; knowledge lives ON things (item properties, character
> knowledge, library data files). The `type: recipe` shape below is preserved
> as history only - the canonical shape is task-831 (recipe entries in
> `data/library/recipes/`, never nodes). `engine/crafting.py` still reads
> nodes at the time of writing; that lookup is tech debt, not the pattern.

Recipes stored ~~as a new node type or~~ as item properties:

```json
{
  "id": "recipe_fried_eggs",
  "type": "recipe",
  "name": "Fried Eggs",
  "properties": {
    "inputs": [
      { "item": "egg", "count": 1, "consumed": true },
      { "item": "pan", "state_required": "present" }
    ],
    "conditions": [
      { "type": "state_equals", "target": "oven", "value": "on" },
      { "type": "in_area", "room": "Kitchen" }
    ],
    "outputs": [
      { "item": "fried_egg", "count": 1 }
    ],
    "skill_check": { "skill": "Cooking", "dc": 10 }
  }
}
```

### Execution Flow

When a player uses "craft fried_eggs" or "make fried_eggs":
1. Check player knows the recipe (has recipe item, or recipe is global)
2. Check all input items exist in inventory or room
3. Check all conditions are met (oven is on, in kitchen)
4. Roll skill check (if applicable)
5. Consume input items (or mark them as used)
6. Spawn output items in inventory or room
7. Return success message
8. If any check fails, return specific error message

### Discovery

Recipes can be:
- **Learned**: character has a recipe item (e.g., "cookbook" containing recipes)
- **Innate**: character knows it by default (e.g., based on skills/traits)
- **Discovered**: first successful attempt teaches the recipe

### UI

- Recipe book / crafting menu accessible from inspector
- List of known recipes with requirements shown
- "Craft" button if requirements met, grayed out with reason if not
- Recipe browser in library (new recipe type)

### Trigger-based alternative

An alternative approach uses triggers instead of a recipe system:
- Item "egg" has `on_use_on` trigger: target "pan", condition oven=on → spawn fried_egg
- This works for simple cases but doesn't scale:
  - No way to check multiple inputs
  - No recipe discovery
  - No skill checks
  - No multiple outputs

Recommendation: Recipe system for complex crafting, triggers for simple single-item effects.

## Files

- `virtual_world_engine.py` - add recipe processing, craft/make command
- `app.py` - add craft/make command handler
- `static/js/item-library.js` - recipe editor
- `static/js/inspector.js` - recipe display

**Deferred**: Post-merge feature branch. This branch is refactoring/testing only.

## Refactoring Impact (July 2026)

Engine is modular. Create engine/crafting.py - constructor receives graph, player_manager, item_actions, game_state. Wire in virtual_world_engine.py. Recipe data in data/recipes.json. API routes in new routes/crafting.py.

---

## Supersession pointer (amended 2026-10-05)

The recipe-entry format (task-831) described here is the authoring basis for
the `todo/crafting/` card family (task-831 through task-839, 101 recipes).
The recipe owns transformation requirements, process duration, skill/quality
outcomes, and produced items. Pursuit templates from task-701 may refer to a
recipe when they lead an actor to cook; the cooking Activity is the visible
process, and the recipe owns the transformation rules. See task-699 for the
pursuit/activity/schedule distinction. The engine execution layer built for
this task (`craft_item`, condition leaves, `give_item` outputs) is expected
to survive the data migration; the graph-node format should not remain a
second source of truth alongside the world-recipe entry.


## Acceptance

- [x] Crafting recipes match required ingredient items in character inventory.
- [x] Successful crafting consumes ingredients and materializes output item.

## Files

- `engine/crafting.py`
- `tests/test_crafting.py`
