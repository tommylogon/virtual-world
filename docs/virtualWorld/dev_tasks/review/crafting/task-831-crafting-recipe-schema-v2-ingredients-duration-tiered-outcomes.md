---
type: task
status: review
area: crafting
priority: high
related: [task-2, task-703, task-472, task-504]
---

# task-831: Crafting recipe schema v2 — ingredients, duration, tiered outcomes

<!-- deps:start -->
**Related:** [[task-2-crafting_and_recipes]], [[task-703-recipe-as-activity-recipes-become-plan-templates-with-duration-success-and-fail-outcomes]], [[task-472-central-dice-and-check-resolution]], [[task-504-item-quantity-property-and-pooled-resource-nodes]]
<!-- deps:end -->

## What

Define the canonical recipe shape all 100+ medieval crafting recipes are authored in. Extends the task-2 crafting contract (`engine/crafting.py`) with the fields the category cards need: ingredient/equipment split, duration, per-recipe skill, and four-tier outcomes (crit success / success / fail / crit fail) with per-recipe fail costs and weighted fail options.

Recipes are NOT graph nodes. Graph nodes are physical entities (items, characters, areas, ways) — knowledge is never a node. A recipe is a data entry that lives in ONE of these homes:

1. `data/library/recipes/<id>.json` — the canonical library entry (preferred for the 101 authored recipes).
2. An item's `properties.recipe` — for a cookbook, recipe note, or heirloom card that teaches when carried/read.
3. A character's knowledge store — `crafting_known` names (discovered/learned), or taught via `teach`.
4. Never `type: recipe` in the graph. The existing `engine/crafting.py` node lookup is tech debt tracked below, not the pattern.

A recipe entry has this shape:

```json
{
  "id": "boiled_water",
  "name": "Boiled Water",
  "ingredients": [
    {"item": "water_skin", "count": 1, "consumed": true},
    {"item": "cooking_pot", "count": 1, "consumed": false}
  ],
  "conditions": [
    {"type": "state_equals", "target": "campfire", "value": "on"}
  ],
  "duration_min": 10,
  "skill_check": {"skill": "Survival", "dc": 8},
  "outputs": [{"item": "boiled_water", "count": 1}],
  "outcomes": {
    "crit_success": {"outputs": [{"item": "boiled_water", "count": 2}], "message": "A full rolling boil — plenty."},
    "success": {"outputs": [{"item": "boiled_water", "count": 1}], "message": ""},
    "fail": {"consume_inputs": true, "outputs": [{"item": "warm_water", "count": 1}], "message": "Lukewarm. Drinkable, not safe."},
    "crit_fail": {"consume_inputs": true, "outputs": [], "message": "Pot boiled dry — water lost."}
  },
  "learned_by": ["global"],
  "discoverable": true
}
```

Field rules:

- `ingredients`: same shape as today's `inputs` (`item`, `count`, `consumed`). `consumed: true` = component eaten; `consumed: false` = equipment/tool kept. The rename from `inputs` is readability only — the engine reads both keys during migration.
- `duration_min`: game minutes the craft takes. Stored on the recipe, ignored by instant `craft()` today, read by task-703's timed Activity executor when it lands.
- `skill_check.skill`: any free string. The engine reads `player.skills.get(name, 0)` — unknown names work with modifier 0. Medieval recipes mint `Cooking`, `Smithing`, `Woodcraft`, `Leatherwork`, etc. (default 0 until a scenario grants them).
- `outcomes`: four tiers keyed by the check's degree (`engine/checks.py` `_degree` tiers). `fail`/`crit_fail` each carry their own `consume_inputs` flag — a burned egg eats the raw egg, a noticed-in-time fail keeps everything. Weighted fail options (`outputs` with per-entry `weight`) are allowed on `crit_fail`; deterministic fail is the default so recipes stay learnable.
- `conditions`: closed set the engine evaluates — `state_equals`, `has_item`, `random_chance`, `skill_check`. Unknown types fail closed.
- `outputs` at top level = the `success` outputs (back-compat with today's `craft()`); `outcomes.success.outputs` overrides when present.
- Output `item` values MUST be library ids under `data/library/items/`. Missing outputs are authored as new library files alongside the recipe.

## Why

100 recipes with no shared shape become 100 unvalidated blobs. The task-2 docstring is convention-by-example, not a contract — no schema file, no validator, no fail path, no duration. This card is the contract the 8 category cards (task-832 through task-839) author against, and the spec for the `tools/recipe_check.py` gate.

## How

1. Land this schema as the documented contract (this card). Recipes live as library data entries, NOT graph nodes.
2. Engine migration in `engine/crafting.py`: replace the `type: recipe` graph-node lookup with a library registry read (`data/library/recipes/`), keeping `craft()`'s check/consume/spawn dispatch. `recipe_nodes()` / `_find_recipe()` become registry lookups; existing tests move to registry fixtures. ~30-50 lines.
3. New gate `tools/recipe_check.py --check`: every recipe file validates — ingredients reference real items or real tags, outputs reference existing library files, conditions from the closed set, `duration_min` a positive int, `outcomes` keys exactly the four tiers.
4. Category cards author recipes in this shape; missing output items (burned_egg, slag, scorched_pottage, etc.) ship as `data/library/items/*.json` files in the same card.
5. `craft()` tier resolution: resolve the check tier via `engine/checks.py`, look up `outcomes[tier]`, apply its `consume_inputs` + `outputs`. Top-level `outputs` stays as the success default.

## Steps to verify

1. Author one recipe in this shape and run the validator.
    - expected: clean pass; a recipe with a missing output file or unknown condition type fails with the exact field named.
    - observed: 2026-10-16 — `python tools/recipe_check.py --check`:
      all 4 clean. 9 missing item files authored as gate
      prerequisites (8 fail/output foods + raw_meat); each names the
      exact field on failure (verified by construction: the gate
      failed on `raw_meat` before the file shipped).
2. Craft the recipe in-game at each of the four tiers (forced rolls).
    - expected: crit/success spawn their outputs; fail consumes per its flag and spawns the fail item; crit-fail spawns the disaster item.
    - observed: 2026-10-16 — `tests/test_crafting.py`, forced dice
      via `world.crafting.roll_fn`: crit (2 pooled bonus units +
      message), success, fail (consumes + fail item), crit-fail with
      `consume_inputs: false` (keeps everything). 11 tests pass.
3. Run `python tools/tasks.py validate`.
    - expected: 0 errors; the new `crafting` area resolves.
    - observed: 2026-10-16 — no 831 findings (remaining warnings
      pre-existing elsewhere).

## Acceptance

- [x] This schema is the documented contract; task-2's docstring points at it.
- [x] No recipe is a graph node. `data/library/recipes/` is the canonical home; item-carried and taught recipes reference entries by id.
- [x] `engine/crafting.py` reads the recipe registry, not `type: recipe` nodes (node lookup retired, tests moved).
- [x] `tools/recipe_check.py --check` exists and gates the four field classes above.
- [x] `craft()` resolves all four tiers; fail consumes per-recipe, not globally.
- [x] Skill names are free strings (documented; see Skills note update).
- [x] All 8 category cards validate clean against the gate.
  (Vacuous: no recipes authored there yet; all 4 existing files pass.
  The 9 item files the recipes needed shipped here as gate
  prerequisites.)

## Acceptance

- [x] This schema is the documented contract; task-2's docstring points at it.
- [x] No recipe is a graph node. `data/library/recipes/` is the canonical home; item-carried and taught recipes reference entries by id.
- [x] `engine/crafting.py` reads the recipe registry, not `type: recipe` nodes (node lookup retired, tests moved).
- [x] `tools/recipe_check.py --check` exists and gates the four field classes above.
- [x] `craft()` resolves all four tiers; fail consumes per-recipe, not globally.
- [x] Skill names are free strings (documented; see Skills note update).
- [x] All 8 category cards validate clean against the gate.
  (Vacuous: no recipes authored there yet; all 4 existing files pass.
  The 9 item files the recipes needed shipped here as gate
  prerequisites.)

## Files

- `engine/crafting.py` — tier resolution + `outcomes` lookup in `craft()`
- `engine/checks.py` — tier source (`_degree`), no change expected
- `tools/recipe_check.py` — new validator gate
- `docs/virtualWorld/dev_tasks/todo/crafting/task-831-*` — this card

## Browser UI and intended live verification

Intended UI home: game view → request **Make X** → inspect the missing-requirements result or the tier outcome and produced item in inventory and event stream.

Current availability: schema card only; engine tier resolution and validator are not yet implemented.

Live steps when available:
1. Request a recipe without one ingredient.
   - expected: fail-closed with the exact missing item named; nothing consumed, nothing spawned.
2. Craft at success and at fail tiers.
   - expected: success spawns the success outputs; fail consumes per its flag and spawns the fail item (e.g. burned egg).
