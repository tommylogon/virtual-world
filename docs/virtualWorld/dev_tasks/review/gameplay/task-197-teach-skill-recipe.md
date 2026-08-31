---
group: Gameplay & Combat
---

# Teach Skill / Recipe Action

**Filed**: 2026-08-10
**Priority**: Medium
**Status**: Todo

---

## Problem

There is no way to teach a skill or a recipe as a stateful action. Recipes are multi-step stateful actions (see task-2 crafting), and teaching someone a recipe — narrating the steps so they learn it — is itself a stateful action. This is ideas #15 and #20 (omelet recipe) from developer ideas.

## Design

- Recipes = stateful actions orchestrating many sub-actions (see task-2 crafting); a recipe is a template of ordered steps.
- Teaching = a stateful action of narrating a recipe to someone; on completion the target character learns the recipe/skill.
- Tag-based optional matching ("any vegetable") keeps recipes generic across different items.
- Success is skill-gated: the teacher must know the recipe, and the learner must be capable of learning it (trait/level check).
- Learner gets a learned-skill entry so they can later perform the recipe themselves.

## Files

- `engine/crafting.py` (future) — recipe templates and stateful execution.
- `engine/item_actions.py` — teach action handler orchestrating the narrative sub-steps.
- `static/js/agent/prompt-builder.js` — instruct the model to emit teach actions targeting a recipe/skill.
