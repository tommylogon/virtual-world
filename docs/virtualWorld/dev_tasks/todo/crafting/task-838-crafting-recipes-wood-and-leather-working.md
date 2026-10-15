---
type: task
status: todo
area: crafting
priority: medium
related: [task-831, task-2, task-703]
---

# task-838: Crafting recipes — wood and leather working

<!-- deps:start -->
**Related:** [[task-831-crafting-recipe-schema-v2-ingredients-duration-tiered-outcomes]], [[task-2-crafting_and_recipes]], [[task-703-recipe-as-activity-recipes-become-plan-templates-with-duration-success-and-fail-outcomes]]
<!-- deps:end -->

## What

13 recipes: greenwood to bowl, hide to strap — the village craftsman's chain.

| # | Recipe | Ingredients | Equipment | Cond | Min | Skill/DC | Success | Fail | Crit-fail |
|---|---|---|---|---|---|---|---|---|---|
| 1 | carve spoon | green_wood ×1 | carving_knife | — | 20 | Woodcraft 8 | wooden_spoon | wooden_spoon (rough, kept) | split blank (firewood) |
| 2 | carve bowl | seasoned_log ×1 | adze, carving_knife | — | 60 | Woodcraft 11 | wooden_bowl | wooden_bowl (leaky) | split log (firewood) |
| 3 | shape staff | straight_branch ×1 | knife | — | 30 | Woodcraft 9 | quarterstaff | staff (crooked, half damage) | snapped stick |
| 4 | fletch arrows | straight_stick ×3, feather ×3, flint_chip ×3 | knife | — | 30 | Woodcraft 10 | arrow ×6 | arrow ×3 | broken shafts (lost) |
| 5 | make shortbow | yew_stave ×1, rope (uses 1), wax ×1 | tiller | — | 180 | Woodcraft 13 | shortbow | shortbow (weak, half range) | snapped stave (firewood) |
| 6 | shield blank | oak_plank ×2, rope (uses 1) | workbench | — | 90 | Woodcraft 11 | shield_blank | shield_blank (heavy, slow) | split planks (firewood) |
| 7 | cure hide | raw_hide ×1, salt (uses 2), wood_ash ×1 | hide_rack | — | 1440 (1 day) | Leatherwork 11 | cured_hide | stiff_hide (craftable, worse) | rotted_hide (lost) |
| 8 | tan leather | cured_hide ×1, oak_bark ×2, boiled_water ×1 | tanning_pit | — | 4320 (3 days) | Leatherwork 13 | leather_hide | leather_hide (thin, half armor) | ruined hide (leather_scraps) |
| 9 | cut straps | leather_hide (uses 1) | knife | — | 10 | Leatherwork 8 | leather_strap ×4 | leather_strap ×2 | nicked hide (uses lost) |
| 10 | stitch pouch | leather_hide (uses 1), waxed_thread ×1 | awl, needle | — | 30 | Leatherwork 10 | leather_pouch | pouch (small, half capacity) | ruined hide (leather_scraps) |
| 11 | patch boots | leather_scraps ×2, waxed_thread ×1 | awl | — | 20 | Leatherwork 9 | boots (repaired) | boots (patched, half durability) | ruined boots (scraps) |
| 12 | weave basket | withy ×6 | knife | — | 45 | Woodcraft 10 | basket (container) | basket (small) | broken withies |
| 13 | ash bucket | oak_plank ×3, iron_hoop ×1 | workbench, hammer | — | 60 | Woodcraft 12 | wooden_bucket | bucket (leaky) | split planks |

New items: green_wood, carving_knife (check), wooden_spoon (check), split_blank, seasoned_log, adze (check), wooden_bowl (check), leaky_bowl, straight_branch, quarterstaff, crooked_staff, snapped_stick, straight_stick, feather (check), flint_chip, arrow (check), yew_stave, wax, tiller (station), shortbow (check), weak_bow, oak_plank, workbench (station), shield_blank, heavy_shield, raw_hide, cured_hide, stiff_hide, rotted_hide, hide_rack (station), oak_bark, tanning_pit (station), leather_hide, thin_leather, leather_strap (check), nicked_hide, leather_pouch, small_pouch, boots_repair handling, withy_basket, small_basket, iron_hoop, wooden_bucket, leaky_bucket.

## Why

Wood and leather are the material base for tools, armor, and containers — every other chain consumes what this card makes (pouches hold rations, buckets carry water, straps bind packs).

## How

Per task-831. Hide→leather is a 2-deep chain (cure then tan); wood outputs feed fire recipes as salvage (split log → firewood) so crit-fails stay in-world instead of vanishing.

## Steps to verify

1. Gate over this card's files.
   - expected: clean; hide chain unbroken; salvage outputs are real fuel ids.
   - observed: TODO
2. Cure → tan → straps → pouch end to end.
   - expected: chain completes; fail degrades one step without breaking the next.
   - observed: TODO

## Acceptance

- [ ] All 13 recipes validate clean.
- [ ] Salvage outputs reference real fuel/material ids.
- [ ] New outputs exist as library files.

## Files

- `data/library/items/*.json` — new outputs above

## Browser UI and intended live verification

Intended UI home: game view → Make bowl / cure hide → inventory + event stream.

Current availability: card only.

Live steps when available:
1. Carve a spoon from greenwood.
   - expected: spoon per tier; crit-fail gives a split blank usable as kindling.
