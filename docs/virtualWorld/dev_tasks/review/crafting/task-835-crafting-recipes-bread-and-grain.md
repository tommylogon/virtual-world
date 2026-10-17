---
type: task
status: review
area: crafting
priority: medium
related: ['task-2', 'task-703', 'task-831', 'task-840']
---

# task-835: Crafting recipes — bread and grain

<!-- deps:start -->
**Related:** [[task-2-crafting_and_recipes]], [[task-703-recipe-as-activity-recipes-become-plan-templates-with-duration-success-and-fail-outcomes]], [[task-831-crafting-recipe-schema-v2-ingredients-duration-tiered-outcomes]], [[task-840-crafting-runtime-who-crafts-activities-backsim-abort]]
<!-- deps:end -->

## What

12 recipes: thresh → grind → dough → loaf, the full medieval grain chain plus oatcakes, flatbread, and honeyed extras.

| # | Recipe | Ingredients | Equipment | Cond | Min | Skill/DC | Success | Fail | Crit-fail |
|---|---|---|---|---|---|---|---|---|---|
| 1 | thresh barley | barley_sheaf ×1 | flail / threshing_floor | — | 20 | Survival 8 | barley (uses 4) + straw ×1 | barley (uses 2) | scattered grain (uses 1) |
| 2 | grind meal | barley (uses 2) | grindstone / quern | — | 30 | Survival 9 | barley_meal (uses 3) | coarse_meal (uses 2) | spilled meal (uses 1) |
| 3 | grind flour fine | wheat (uses 2) | millstone | — | 30 | Crafting 10 | flour (uses 3) | coarse_meal (uses 2) | spilled meal |
| 4 | mix dough | flour (uses 2), boiled_water ×1, salt ×1 | wooden_bowl | — | 15 | Cooking 8 | dough (uses 2) | sticky_dough (uses 1) | soupy mess (lost) |
| 5 | leaven dough | dough (uses 2), barm ×1 | wooden_bowl (covered) | — | 120 | Cooking 10 | risen_dough (uses 2) | dough (flat, uses 1) | soured dough (useless) |
| 6 | flatbread | dough (uses 1) | hearth_stone, fire (on) | fire on | 5 | Cooking 8 | flatbread ×2 | flatbread ×1 | burned_flatbread |
| 7 | barley loaf | risen_dough (uses 2) | clay_oven / hearth, fire (on) | fire on | 40 | Cooking 11 | barley_loaf | barley_loaf (small, half) | burned_loaf |
| 8 | wheat bread | risen_dough (uses 2, wheat) | clay_oven, fire (on) | fire on | 40 | Cooking 12 | bread ×1 | bread (small) | burned_loaf |
| 9 | oatcake | oats (uses 2), animal_fat ×1, salt ×1 | hearth_stone, fire (on) | fire on | 10 | Cooking 9 | oatcake ×3 | oatcake ×1 | burned_oatcake |
| 10 | honeyed bread | bread ×1, honey ×1 | — | — | 5 | Cooking 7 | honeyed_bread | honeyed_bread (half) | soggy mess (lost) |
| 11 | breadcrumbs | stale_bread ×1 | — | — | 5 | Cooking 6 | bread_crumbs (uses 3) | bread_crumbs (uses 1) | — |
| 12 | bake apple tart | dough (uses 1), apple ×2, honey ×1 | clay_oven, fire (on) | fire on | 30 | Cooking 13 | apple_tart | apple_tart (soggy, half) | burned_tart |

New items: barley_sheaf, wheat, wheat_sheaf, straw, coarse_meal, spilled meal→(use existing flour spill?), dough, sticky_dough, soupy_mess, barm, risen_dough, soured_dough, flatbread, burned_flatbread, barley_loaf (check existing), oatcake, burned_oatcake, stale_bread, apple_tart (check), burned_tart, burned_loaf, clay_oven (station), quern (station), flail (tool).

## Why

Bread is the medieval calorie base. The chain gives farmers, millers, and bakers distinct pursuits instead of one "make bread" button.

## How

Per task-831; sheaf→grain→meal→dough→loaf is a 4-deep chain — each step's outputs are the next step's inputs, validated in order.

## Steps to verify

1. Gate over this card's files.
    - expected: clean; chain links resolve (no step consumes what no prior step makes).
    - observed: 2026-10-16 — `recipe_check.py --check`: all 55 clean
      (12 new + 43 prior). 14 missing item files authored alongside
      (flail/honeyed_bread/barm/flour etc. already existed — reused,
      `hearth` mapped to existing `hearth_stone`, no duplicates).
2. Run thresh → grind → dough → loaf end to end.
    - expected: full chain completes; one forced fail mid-chain degrades but doesn't break the chain.
    - observed: 2026-10-16 —
      `test_grain_chain_sheaf_to_loaf_end_to_end`: sheaf → barley →
      meal → dough → risen → loaf completes through the engine.
      Caught a REAL break on the way: the table's mix-dough takes
      flour, but grind-meal makes coarse_meal — the specified chain
      could never complete. Mix dough now takes coarse_meal (the
      verify step wins over the table). Consequence, recorded: wheat
      flour currently has no consumer — needs a future
      wheat-dough variant, not invented here.

## Acceptance

- [x] All 12 recipes validate clean; grain chain is unbroken.
- [x] New outputs exist as library files.

## Files

- `data/library/items/*.json` — new outputs above

## Browser UI and intended live verification

Intended UI home: game view → Make dough / bake loaf → inventory + event stream.

Current availability: card only.

Live steps when available:
1. Bake a barley loaf from risen dough at a lit oven.
   - expected: loaf per tier; crit-fail gives burned loaf, dough consumed.
