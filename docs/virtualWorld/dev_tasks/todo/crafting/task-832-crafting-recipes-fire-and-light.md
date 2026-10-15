---
type: task
status: todo
area: crafting
priority: medium
related: [task-831, task-2, task-703]
---

# task-832: Crafting recipes — fire and light

<!-- deps:start -->
**Related:** [[task-831-crafting-recipe-schema-v2-ingredients-duration-tiered-outcomes]], [[task-2-crafting_and_recipes]], [[task-703-recipe-as-activity-recipes-become-plan-templates-with-duration-success-and-fail-outcomes]]
<!-- deps:end -->

## What

13 recipes covering fire-making, fuel processing, and medieval light sources. All authored in the task-831 schema shape (`ingredients`, `duration_min`, `skill_check`, four-tier `outcomes`).

Base materials: branch, log, firewood, kindling, flint, tinderbox (tool), tallow, beeswax, wick, oil, torch, candle, lantern.

| # | Recipe | Ingredients (consumed) | Equipment (kept) | Cond | Min | Skill/DC | Success | Fail | Crit-fail |
|---|---|---|---|---|---|---|---|---|---|
| 1 | split kindling | branch ×1 | hatchet | — | 5 | Survival 8 | kindling ×3 | kindling ×1 + wood_scraps | wasted branch (nothing) |
| 2 | chop firewood | log ×1 | axe | — | 15 | Survival 9 | firewood (uses 6) | firewood (uses 3) | jammed axe, log kept, time lost |
| 3 | bundle tinder | bark_stripping ×2, cloth_scrap ×1 | — | — | 5 | Survival 7 | tinder_bundle ×2 | tinder_bundle ×1 | damp wad (useless) |
| 4 | light campfire | kindling ×1, firewood (uses 2) | tinderbox | — | 10 | Survival 8 | campfire on | consume kindling, fire unlit | consume kindling + singed fingers (minor burn cond) |
| 5 | bank coals overnight | wood_ash ×1 | campfire (lit) | — | 5 | Survival 10 | banked_coals | coals out, relight needed | — |
| 6 | burn charcoal | firewood (uses 6) | charcoal_pit / covered fire | — | 240 | Survival 12 | charcoal (uses 6) | charcoal (uses 3) + wood_ash | fire pit burned out, all lost |
| 7 | render tallow | animal_fat ×2 | cooking_pot, fire (on) | fire on | 30 | Cooking 9 | tallow (uses 4) | tallow (uses 2, scorched) | burned_grease (useless) |
| 8 | dip tallow candle | tallow (uses 2), wick ×1 | fire (low) | fire on | 20 | Survival 8 | candle ×2 | lumpy_candle ×1 (half light) | spilled tallow (lost), wick kept |
| 9 | pour beeswax candle | beeswax ×1, wick ×1 | fire (low) | fire on | 20 | Survival 10 | beeswax_candle ×2 | beeswax_candle ×1 | wax fire — all lost |
| 10 | refill lantern oil | animal_fat ×1 | lantern, fire (low) | fire on | 10 | Survival 8 | lantern_oil (uses 4) | lantern_oil (uses 2) | spilled oil (lost) |
| 11 | make torch | stick ×1, cloth_scrap ×1, tallow (uses 1) | — | — | 10 | Survival 8 | torch ×1 | soggy_torch (won't light) | — |
| 12 | light torch | torch ×1 | campfire (lit) / tinderbox | fire or tool | 2 | Survival 6 | torch (lit) | torch unlit, time lost | torch dropped in mud (kept, unlit) |
| 13 | fire-hardened stake | green_stick ×1 | campfire (lit) | fire on | 15 | Survival 9 | sharpened_stake ×1 | stake ×1 (soft, half damage) | burned_stick (useless) |

New library items to author with this card: tinder_bundle, wood_scraps, banked_coals, burned_grease, lumpy_candle, beeswax, beeswax_candle, lantern_oil, soggy_torch, green_stick, sharpened_stake, burned_stick, charcoal_pit (station).

## Why

Fire is the gate for every cooking, forge, and night-travel mechanic. Without fuel-processing recipes the sim's fireplaces are decoration fed by hand-placed kindling.

## How

Author each recipe entry (`data/library/recipes/*.json`) per task-831 � recipes are data, never graph nodes; author missing `data/library/items/*.json` outputs with `on_eat`/`on_use` triggers where edible/usable; validate with `tools/recipe_check.py --check`.

## Steps to verify

1. Run the recipe gate over this card's files.
   - expected: clean pass, all outputs resolve to library files.
   - observed: TODO
2. Craft split-kindling → light campfire → dip candle end to end in a scratch world.
   - expected: each tier behaves per its outcome row; fail consumes per its flag.
   - observed: TODO

## Acceptance

- [ ] All 13 recipes validate clean.
- [ ] All new output items exist in `data/library/items/` with descriptions.
- [ ] Fire-gated cooking/forge recipes can reference the lit-campfire state set here.

## Files

- `data/library/items/*.json` — new outputs listed above
- `data/library/recipes/*.json` � new entries per task-831 schema (data, never nodes)

## Browser UI and intended live verification

Intended UI home: game view → Make split kindling / light campfire → inspect inventory, fire state, event stream.

Current availability: card only; recipes not yet authored.

Live steps when available:
1. Craft kindling from a branch, then light the campfire.
   - expected: kindling spawns per tier; lighting consumes kindling and sets fire on, or fails per its row.
