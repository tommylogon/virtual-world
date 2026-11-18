---
type: feature
feature_id: 77
status: wired
section: in-game
tags: [status/wired, surface/in-game, system/items]
---
# Crafting

**What you can do:** Make, combine, split and teach: recipes, tools and results

## How it works

Recipes are JSON data entries in `data/library/recipes/<id>.json` loaded by `load_registry` (`engine/crafting.py`), not graph nodes. Each entry can define `id`, `name`, `ingredients` (or `inputs` with `item`, `count`, `consumed`), `conditions`, `duration_min`, `skill_check` (`skill`, `dc`), `outputs`, `outcomes` (`crit_success`, `success`, `fail`, `crit_fail`), `learned_by`, and `discoverable`.

- **Craft and make (`craft <recipe>`, alias `make`)**: Dispatched in `routes/action_handlers.py` and defined as `VerbSpec("craft", aliases=("make",), scope="crafting", target_schema="target", cost_key="major")` in `engine/action_verbs.py`.
  - Untimed recipes (`duration_min <= 0`) resolve immediately via `world.craft_item` -> `CraftingSystem.craft`.
  - Timed recipes (`duration_min > 0`) start a `"cooking"` activity via `CraftingSystem.start_cooking`, adding an `"at"` edge to a matching station node when present. When the activity finishes (`finish_craft` in `engine/activities.py`), `CraftingSystem.complete_cooking` re-verifies inputs and conditions before resolving. Interrupting the activity ends it without consuming inputs.
- **Requirement checks and conditions**: `CraftingSystem.check_craft` fails closed before rolling or consuming: it looks up the recipe (`_find_recipe`), checks `_recipe_learned`, verifies ingredients (`_verify_inputs`), and evaluates `conditions` (`_condition_passes`).
  - `_input_nodes` matches carried or equipped items first (`EDGE_CARRYING`, `EDGE_EQUIPPED`), then reachable area items via `engine.item_reach.find_reachable`.
  - `_condition_passes` supports `state_equals` (checking current area spatial items first, then graph nodes), `has_item`, `random_chance`, and `skill_check`, failing closed on unknown condition types.
- **Skill checks, outcomes, and outputs**: `CraftingSystem.resolve_craft_tier` (`_resolve_tier`) runs `engine.checks.resolve` once for `skill_check` (recipes without a `skill` default to `"success"`), mapping degrees via `TIER_MAP` (`strong_success` -> `success`, `auto_fail` -> `fail`) into `crit_success`, `success`, `fail`, or `crit_fail`. `CraftingSystem._finish` consumes `consumed: true` inputs via `_consume_input` (gated by `consume_inputs` on `fail`/`crit_fail`, default `True`), decrements `uses` (reconciling weight with `reconcile_item_weight`) or removes exhausted nodes, resolves weighted tier outputs (`_resolve_outputs`), spawns items via `effects.handle_give_item`, and records a `"craft"` turn event.
- **Recipe knowledge, discovery, and API**: `_recipe_learned` and `_recipe_source` grant access via `learned_by` rules (`"global"`, `"skill:<name>"` when skill >= 1 or in `crafting_known`, `"item:<name>"` when carrying/equipping a matching item/cookbook) or `player.crafting_known` (declared in `engine/character_record.py` and persisted in `engine/serialization.py`). Recipes with `"discoverable": true` append their recipe label to `player.crafting_known` in `_finish`. `CraftingSystem.known_recipes` projects known recipes for `GET /api/players/<name>/recipes` (`routes/players.py` -> `handle_character_recipes` in `routes/player_ops.py`).
- **Combine and split (`combine <source> with <target>`, `split <item> [into N]`)**: Defined as `item`-scoped major verbs in `engine/action_verbs.py` and routed through `routes/action_handlers.py` -> `world.combine_items` / `world.split_item` -> `StackingMixin` (`engine/items/stacking.py`). `combine_items` merges two carried/equipped `stackable_twins` items (summing `uses` clamped at `max_uses`, reconciling weight, checking carry capacity, and removing the source node). `split_item` splits a carried item with `uses >= 2` into equal parts (default 2), updating the original node and creating a new `EDGE_CARRYING` node for the remainder.
- **Teach (`teach <recipe | skill:NAME> to <character>`)**: Defined as a `social`-scoped major verb in `engine/action_verbs.py` and routed through `routes/action_handlers.py` -> `world.teach_item` -> `CraftingSystem.teach`. Teacher and student must be distinct characters in the same `current_area`. Teaching `skill:<name>` requires teacher skill >= 1 and increments `student.skills[skill_name]` by 1; teaching a recipe requires `_recipe_learned` for the teacher and appends the recipe name to `student.crafting_known`.
- **Trigger behaviors**: `engine/triggers/behaviors.py` handles `craft`, `cook`, `combine`, and `teach` behavior actions via `game_state.crafting.craft`, `game_state.craft_item`, `game_state.combine_items`, and `game_state.teach_item`.

## Where it lives

- `engine/crafting.py` - `CraftingSystem`, `load_registry`, `_default_recipe_dir`, `TIER_MAP`, `OUTCOME_TIERS`
- `engine/items/stacking.py` - `StackingMixin` (`combine_items`, `split_item`), `stackable_twins`, `is_stackable`
- `engine/action_verbs.py` - `VerbSpec` entries for `craft` (`make`), `combine`, `split`, `teach`
- `routes/action_handlers.py` - command parsing and dispatch for `combine`, `split`, `craft`/`make`, `teach`
- `virtual_world_engine.py` - `combine_items`, `split_item`, `craft_item`, `teach_item` delegation methods
- `engine/activities.py` - `finish_craft` activity completion calling `complete_cooking`
- `routes/players.py` and `routes/player_ops.py` - `GET /api/players/<name>/recipes` (`handle_character_recipes`)
- `engine/triggers/behaviors.py` - `craft`, `cook`, `combine`, `teach` behavior action handlers
- `engine/character_record.py` and `engine/serialization.py` - `crafting_known` field definition and save/load persistence
- `data/library/recipes/` - JSON recipe entries (validated by `tools/recipe_check.py`)

## Connected

- Feature Map: [[Feature Map|row 77]] (In a game)
- Sibling features: [[look-around]], [[examine]], [[move]], [[open-close]], [[take-drop-give]], [[use-use-on]]
- All features: [[Features Overview]]

> [!note] Status - `wired`
> Recorded from [[Feature Map|the Feature Map]] on 2026-10-24. This page is an entry point; the
> deep documentation is linked under **How it works**.
