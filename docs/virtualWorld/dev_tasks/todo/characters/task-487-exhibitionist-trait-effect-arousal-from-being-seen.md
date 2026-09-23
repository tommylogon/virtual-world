---
type: task
status: todo
area: characters
priority: low
---

# task-487: Exhibitionist trait effect: arousal from being seen

**Filed:** 2026-09-23
**Related:** task-213

## Goal

Wire the exhibitionist trait effect, which is currently defined but inert (effects: {exhibitionist: true}, no consumer): grant arousal/pleasure when the character is publicly exposed or being looked at, and add a behavior_prompt. Tracked from task-213.

## Acceptance

- `exhibitionist` gains a live consumer (`TraitSystem.has_effect(p, "exhibitionist")`), granting arousal/pleasure when the character is publicly exposed or being looked at.
- A `behavior_prompt` is added so the agent references the trait.
- Only active when `world.mature_content` is on; the trait stays hidden from pickers when off (`routes/library_ops.py:195-205`).
- Test asserting the effect fires (and does not fire for non-carriers).
