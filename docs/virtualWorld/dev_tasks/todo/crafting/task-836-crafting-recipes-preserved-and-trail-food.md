---
type: task
status: todo
area: crafting
priority: medium
related: [task-831, task-2, task-703]
---

# task-836: Crafting recipes — preserved and trail food

<!-- deps:start -->
**Related:** [[task-831-crafting-recipe-schema-v2-ingredients-duration-tiered-outcomes]], [[task-2-crafting_and_recipes]], [[task-703-recipe-as-activity-recipes-become-plan-templates-with-duration-success-and-fail-outcomes]]
<!-- deps:end -->

## What

12 recipes: smoke, dry, salt, pickle, cheese — food that keeps. The difference between a camp that eats today and one that eats all winter.

| # | Recipe | Ingredients | Equipment | Cond | Min | Skill/DC | Success | Fail | Crit-fail |
|---|---|---|---|---|---|---|---|---|---|
| 1 | smoke meat | raw_meat ×2, firewood (uses 2) | smokehouse / low fire | fire on | 180 | Survival 13 | smoked_meat (uses 4) | half_smoked (eat now, won't keep) | charred_meat |
| 2 | smoke fish | raw_fish ×2, firewood (uses 1) | smokehouse / low fire | fire on | 120 | Survival 12 | smoked_fish (uses 4) | half_smoked_fish | charred_fish |
| 3 | dry apple rings | apple ×3 | drying_rack, sun/air | — | 480 | Survival 9 | dried_apple (uses 4) | dried_apple (uses 2, leathery) | moldy_apple (useless) |
| 4 | dry mushrooms | mushroom ×4 | drying_rack | — | 480 | Survival 9 | dried_mushroom (uses 4) | dried_mushroom (uses 2) | moldy_mushroom |
| 5 | salt pork | raw_meat ×2, salt (uses 3) | salt_barrel | — | 1440 (1 day) | Survival 11 | salt_pork (uses 4) | salt_pork (uses 2, very salty) | spoiled_meat (useless) |
| 6 | salt fish | raw_fish ×2, salt (uses 2) | salt_barrel | — | 1440 | Survival 10 | salt_fish (uses 4) | salt_fish (uses 2) | spoiled_fish |
| 7 | hard cheese | milk (uses 4), rennet ×1, salt ×1 | cheese_press | — | 2880 (2 days) | Cooking 13 | hard_cheese | soft_cheese (eat now) | spoiled_curd |
| 8 | pickle veg | carrot ×2, onion ×1, vinegar ×1, salt ×1 | pickle_crock | — | 2880 | Cooking 11 | pickles (uses 4) | pickles (uses 2, soft) | mush_crock (useless) |
| 9 | fruit leather | wild_berries (uses 3), honey ×1 | drying_rack, low fire | fire on | 240 | Cooking 10 | fruit_leather (uses 3) | fruit_leather (uses 1, sticky) | burned_paste |
| 10 | jerky | raw_meat ×1, salt ×1 | drying_rack, low fire | fire on | 360 | Survival 12 | jerky (uses 3) | jerky (uses 1, tough) | charred_meat |
| 11 | parched grain | barley (uses 3) | frying_pan, fire (on) | fire on | 15 | Cooking 9 | parched_grain (uses 3, trail-ready) | parched_grain (uses 1) | burned_grain |
| 12 | pack trail rations | jerky (uses 1), hard_cheese (uses 1), oatcake ×1, dried_apple (uses 1) | cloth_scrap ×1 | — | 10 | Survival 8 | trail_rations (uses 4) | trail_rations (uses 2) | — |

New items: smoked_meat, half_smoked, smoked_fish, half_smoked_fish, charred_fish, dried_apple, moldy_apple, dried_mushroom, moldy_mushroom, salt_pork, spoiled_meat, salt_fish, spoiled_fish, milk, rennet, hard_cheese, soft_cheese, spoiled_curd, vinegar, pickle_crock, pickles, mush_crock, wild_berries (check), fruit_leather (check), jerky, parched_grain, burned_grain, trail_rations, drying_rack (station), smokehouse (station), salt_barrel (container).

Spoilage rule: `half_smoked` / `soft_cheese` carry a `perishable` tag with short shelf (future decay pass reads it); fully preserved outputs don't. Fail states that rot (`spoiled_*`, `moldy_*`) are inedible and compost-only.

## Why

Preservation turns surplus into security — and gives autumn pursuits (harvest, slaughter, forage) a reason to exist beyond immediate hunger.

## How

Per task-831. Long durations (days) are `duration_min` values the future Activity executor will honor; instant `craft()` resolves them immediately until then (documented, not hidden).

## Steps to verify

1. Gate over this card's files.
   - expected: clean.
   - observed: TODO
2. Smoke meat → pack rations end to end.
   - expected: preserved outputs feed the ration recipe; perishable flags correct.
   - observed: TODO

## Acceptance

- [ ] All 12 recipes validate clean.
- [ ] Perishable vs shelf-stable tags applied per the rule above.
- [ ] New outputs exist as library files.

## Files

- `data/library/items/*.json` — new outputs above

## Browser UI and intended live verification

Intended UI home: game view → Make smoked meat / pack rations → inventory + event stream.

Current availability: card only.

Live steps when available:
1. Smoke raw meat at a low fire.
   - expected: smoked meat per tier; crit-fail chars it.
