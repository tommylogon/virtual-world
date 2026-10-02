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

## Blocked in the inspector-ui lane (2026-10-02)

Not attempted. The surface this task needs does not live in this lane's files
(`static/js/inspector/**`, `static/js/help/**`, `templates/index.html`): the
"scope card" is `static/js/graph/scope-tree.js` and the alternative home
(the per-scope `⚙ Generate`) is `static/js/worldpainter/editor.js`.

`static/js/graph/scope-tree.js` is being changed by the **in-progress
task-592**, which *deliberately* replaced the scope-row Generate with a
**🖌 Paint** jump ("generating lives in the painter, per scope-tree.js's own
rule — no Generate button on a scope row"). Re-adding a Generate there now
would directly collide with that live work and reverse its documented decision.
Implementing instead in the WorldPainter means editing another cluster's owned
file.

When this task is picked up it needs: (1) a preview endpoint on
`routes/world_grid_ops.py` that builds the patch from `engine/library_nodes.py`
without writing, returning areas/items/ways/seed/recipe version plus the
report's missing tag candidates; (2) the Generate button + preview modal on the
chosen surface; (3) the no-op-on-made-scope guard. Recommend resolving the
scope-tree vs painter ownership question with task-592 first.

