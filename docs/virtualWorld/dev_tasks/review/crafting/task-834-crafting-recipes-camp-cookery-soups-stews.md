---
type: task
status: review
area: crafting
priority: high
related: [task-831, task-2, task-703]
---

# task-834: Crafting recipes — camp cookery, soups and stews

<!-- deps:start -->
**Related:** [[task-831-crafting-recipe-schema-v2-ingredients-duration-tiered-outcomes]], [[task-2-crafting_and_recipes]], [[task-703-recipe-as-activity-recipes-become-plan-templates-with-duration-success-and-fail-outcomes]]
<!-- deps:end -->

## What

14 recipes: the heart of the request — pot food over fire. Porridge to pottage to meat stew to fish soup, plus eggs every way and the fail states that make cooking honest (gruel, scorched pots, burned eggs).

| # | Recipe | Ingredients | Equipment | Cond | Min | Skill/DC | Success | Fail | Crit-fail |
|---|---|---|---|---|---|---|---|---|---|
| 1 | fried egg | raw_egg ×1, butter ×1 | frying_pan, fire (on) | fire on | 10 | Cooking 10 | fried_egg | rubbery_egg (half) | burned_egg |
| 2 | boiled egg | raw_egg ×1, boiled_water ×1 | cooking_pot, fire (on) | fire on | 8 | Cooking 8 | boiled_egg | cracked_egg (half) | rubber_ball_egg (useless) |
| 3 | scrambled egg + herbs | raw_egg ×2, herb_bunch ×1, butter ×1 | frying_pan, fire (on) | fire on | 10 | Cooking 11 | herbed_eggs | plain_scramble (no herb bonus) | burned_egg |
| 4 | oat porridge | oats (uses 2), boiled_water ×1, honey ×1 | cooking_pot, fire (on) | fire on | 15 | Cooking 8 | porridge ×2 | thin_gruel ×1 | scorched_pot (pot kept, food lost) |
| 5 | barley pottage | barley (uses 2), boiled_water ×1, onion ×1 | cooking_pot, fire (on) | fire on | 40 | Cooking 12 | pottage ×2 | thin_gruel ×2 | scorched_pot |
| 6 | vegetable soup | carrot ×1, onion ×1, potato ×1, salt ×1 | cooking_pot, fire (on) | fire on | 35 | Cooking 10 | vegetable_soup ×2 | thin_broth ×2 | scorched_pot |
| 7 | meat stew | raw_meat ×2, carrot ×1, onion ×1, salt ×1 | cooking_pot, fire (on) | fire on | 60 | Cooking 13 | meat_stew ×2 | greasy_stew ×1 (half) | burned_stew (useless) |
| 8 | fish soup | raw_fish ×2, wild_garlic ×1, salt ×1 | cooking_pot, fire (on) | fire on | 30 | Cooking 11 | fish_soup ×2 | fishy_broth ×1 | burned_stew |
| 9 | mushroom stew | mushroom ×3, butter ×1, salt ×1 | cooking_pot, fire (on) | fire on | 25 | Cooking 11 | mushroom_stew ×2 | mushroom_broth ×1 | burned_stew |
| 10 | roast meat on spit | raw_meat ×1, salt ×1 | spit, fire (on) | fire on | 45 | Cooking 10 | roast_meat | dry_roast (half) | charred_meat (barely food) |
| 11 | roast root veg | carrot ×2, potato ×1, animal_fat ×1 | fire (coals) | fire on | 30 | Cooking 9 | roast_veg ×2 | roast_veg ×1 | charred_veg |
| 12 | cheese toast | bread ×1, cheese ×1 | hearth_stone, fire (on) | fire on | 5 | Cooking 7 | cheese_toast | warm_bread_cheese (half) | burned_toast |
| 13 | trail stew (big pot) | raw_meat ×1, barley (uses 2), carrot ×1, onion ×1, salt ×1 | iron_cauldron, fire (on) | fire on | 90 | Cooking 14 | trail_stew ×4 | trail_stew ×2 | scorched_cauldron (food lost, pot kept) |
| 14 | bone broth (long) | bones ×2, boiled_water ×2, wild_garlic ×1 | iron_cauldron, fire (low) | fire on | 240 | Cooking 12 | bone_broth ×3 | thin_broth ×2 | scorched_cauldron |

New library items: raw_egg, fried_egg, rubbery_egg, burned_egg, boiled_egg, cracked_egg, rubber_ball_egg, herbed_eggs, plain_scramble, oats, porridge, thin_gruel, scorched_pot, onion, carrot, potato, mushroom, raw_meat, raw_fish, bones, wild_garlic, salt, butter, vegetable_soup, meat_stew, greasy_stew, burned_stew, fish_soup, fishy_broth, mushroom_stew, mushroom_broth, roast_meat, dry_roast, charred_meat, roast_veg, charred_veg, cheese, cheese_toast, warm_bread_cheese, burned_toast, trail_stew, bone_broth, scorched_cauldron, frying_pan, spit, iron_cauldron.

Check before authoring: some may already exist (pottage, vegetable_soup exist — reuse, don't duplicate).

## Why

This is the card the request was really about — "cooking water to be safe or soup." Pot + fire + time + skill, with failure you can taste.

## How

Per task-831. Stew outputs use `uses` for servings (one pot, N bowls). Verify each output id against the library first; reuse existing files where present.

## Steps to verify

1. Gate over this card's files.
    - expected: clean; no duplicate ids with existing library.
    - observed: 2026-10-16 — `recipe_check.py --check`: all 43 clean
      (14 new + 29 prior). No id collisions (new ids verified
      against the library dir before authoring; `pottage`,
      `vegetable_soup` reused, not duplicated). 26 missing item
      files authored alongside.
2. Cook pottage → fail path → scorched pot recovery.
    - expected: fail spawns gruel, crit-fail kills the food but keeps the pot.
    - observed: 2026-10-16 —
      `test_camp_pottage_fail_path_and_pot_recovery`: forced fail →
      `thin_gruel`, forced crit → `scorched_pot` carried. Caught a
      real matching gap on the way: "barley pottage camp" found
      nothing (spaces vs underscores vs parens) — `_find_recipe`
      now normalizes punctuation, covered by the same test.

## Acceptance

- [x] All 14 recipes validate clean with no id collisions.
- [x] Servings modeled as `uses` on pot outputs.
- [x] Fail/crit-fail items exist as library files.

## Files

- `data/library/items/*.json` — new outputs above (minus pre-existing)

## Browser UI and intended live verification

Intended UI home: game view → Make pottage / fry egg at a lit fire → inventory + event stream.

Current availability: card only.

Live steps when available:
1. Fry an egg at a lit fire.
   - expected: success/fail/crit-fail per the row; egg consumed on fail and crit-fail.
