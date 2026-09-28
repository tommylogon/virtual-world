---
type: task
status: todo
area: ui
priority: medium
---

# task-580: Unmade-scope Generate affordance and generation preview

**Filed:** 2026-09-28
**Related:** task-397, task-398

## Goal

Expose task-398's deterministic generation through the UI: a Generate action on an unmade scope card that carries a recipe, and a preview of the patch the recipe would apply (areas, items, and any missing tag candidates from the report) before anything is written.

## Why this is needed

task-397 step 5 (the `Generate` affordance on an unmade scope card) and the
preview half of task-398 are the last two items both tasks left open, because
both depended on a generator existing. `apartment.v1` landed in task-398, so
this is now unblocked. The backend is done: `engine/generation_recipes.py` holds
the recipe and `engine/library_nodes.py` the public materialisation service, and
`tests/test_apartment_recipe.py` covers determinism, no-duplicate re-runs,
save/reload and manual-edit survival. Only the surface is missing.

## Requirements

- A `Generate` action appears on a scope card **only** when the scope is unmade
  and carries a `recipe`. A made scope must not offer it.
- The preview is a *preview*: it renders the patch (areas, items, ways, the seed
  and recipe version) and the report's missing tag candidates, and writes
  nothing until the user confirms.
- A second press on an already-made scope is a no-op with an explanation, not an
  error and not a second node set.
- Generation goes through `engine/library_nodes.py`, never a UI-side mutation of
  the graph, so a hand edit in the editor still wins afterwards.

## Acceptance

- An unmade `apartment_3b` in Pines shows `Generate`; generating it from the UI
  produces the same three areas `tests/test_apartment_recipe.py` produces, and
  Hallway 3 can walk into all of them.
- The preview lists the recipe's areas and items and the report's missing tag
  candidates before confirmation.
- Confirming twice creates no duplicate nodes, ways or items.
- A made scope offers no `Generate`.
- A manual edit to a generated item, then a reload, survives; a second
  generation attempt does not erase it.

## Non-goals

- Chunk eviction or scope unloading (task-401).
- Authoring new recipes; `apartment.v1` is the one this hangs off.
