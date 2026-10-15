---
type: task
status: todo
area: crafting
priority: high
related: [task-831, task-2, task-703]
---

# task-837: Crafting recipes — survival gear and camp craft

<!-- deps:start -->
**Related:** [[task-831-crafting-recipe-schema-v2-ingredients-duration-tiered-outcomes]], [[task-2-crafting_and_recipes]], [[task-703-recipe-as-activity-recipes-become-plan-templates-with-duration-success-and-fail-outcomes]]
<!-- deps:end -->

## What

13 recipes: the gear that keeps you alive outside — shelter, cordage, traps, first aid. High Survival weight, mostly fireless.

| # | Recipe | Ingredients | Equipment | Cond | Min | Skill/DC | Success | Fail | Crit-fail |
|---|---|---|---|---|---|---|---|---|---|
| 1 | cordage from fibre | flax_fibre ×3 | — | — | 30 | Survival 9 | rope (uses 4) | frayed_cord (uses 2) | tangled_waste (lost) |
| 2 | weave fish trap | withy ×4, rope (uses 1) | knife | — | 60 | Survival 12 | fish_trap | fish_trap (leaky, half catch) | broken_withies (lost) |
| 3 | set snare | rope (uses 1), stick ×1 | knife | — | 15 | Survival 11 | snare (set) | snare (slack, won't catch) | snapped cord (lost) |
| 4 | lean-to shelter | branch ×4, rope (uses 2) | hatchet | — | 120 | Survival 12 | lean_to (shelter) | drafty_shelter (half cover) | collapsed pile (materials kept) |
| 5 | bedroll | wool_fleece ×2, cloth_bolt ×1 | needle | — | 60 | Survival 10 | bedroll | lumpy_bedroll (half rest) | wasted stitching (fleece kept, cloth lost) |
| 6 | tear bandages | linen_cloth ×1 | knife | — | 5 | Medicine 6 | bandages (uses 4) | bandages (uses 2, ragged) | shredded rags (lost) |
| 7 | herbal poultice | herb_bunch ×1, honey ×1, cloth_scrap ×1 | — | — | 15 | Medicine 11 | poultice | weak_mash (half heal) | spoiled_mash (useless) |
| 8 | splint | stick ×2, cloth_scrap ×1, rope (uses 1) | knife | — | 10 | Medicine 10 | splint | splint (loose, half effect) | snapped stick (lost) |
| 9 | brew antiseptic wash | boiled_water ×1, willow_bark ×1, honey ×1 | cup | — | 10 | Medicine 12 | antiseptic_wash | weak_wash (half) | spoiled_mash |
| 10 | make pack frame | branch ×2, rope (uses 2), leather_strap ×1 | knife | — | 45 | Survival 10 | pack_frame (carry bonus) | pack_frame (creaky, no bonus) | broken frame (materials kept) |
| 11 | sew waterskin | leather_hide ×1, waxed_thread ×1 | awl, needle | — | 60 | Leatherwork 11 | waterskin | leaky_skin (half capacity) | ruined hide (leather_scraps) |
| 12 | pitch torch (trail) | stick ×1, pine_resin ×1, cloth_scrap ×1 | — | — | 10 | Survival 8 | pitch_torch | pitch_torch (smoky, half light) | sticky mess (lost) |
| 13 | signal fire stack | firewood (uses 4), green_bough ×2 | — (at high ground) | — | 20 | Survival 9 | signal_pyre (ready) | signal_pyre (damp, slow light) | scattered stack (kept) |

New items: flax_fibre (check), frayed_cord, tangled_waste, withy (check), fish_trap (check), leaky_trap, snare, slack_snare, lean_to, drafty_shelter, wool_fleece (check), bedroll, lumpy_bedroll, linen_cloth (check), bandages (check), weak_mash, spoiled_mash, splint, loose_splint, antiseptic_wash, weak_wash, pack_frame, creaky_frame, leather_hide, waxed_thread, awl (check), leaky_skin, pine_resin, pitch_torch, signal_pyre, green_bough.

## Why

Survival gear is the other half of "survival" alongside food/water/fire. Traps and shelters also feed background-sim pursuits (a set snare catches rabbits off-screen per task-410-style timers).

## How

Per task-831. Shelter/trap outputs are placed items (not carried) — outputs support a `place_in_area: true` flag the executor honors.

## Steps to verify

1. Gate over this card's files.
   - expected: clean.
   - observed: TODO
2. Weave trap → set snare → poultice in a scratch world.
   - expected: trap/snare place in area; poultice heals per tier.
   - observed: TODO

## Acceptance

- [ ] All 13 recipes validate clean.
- [ ] Placed vs carried outputs flagged correctly.
- [ ] New outputs exist as library files.

## Files

- `data/library/items/*.json` — new outputs above

## Browser UI and intended live verification

Intended UI home: game view → Make snare / poultice → area view + inventory + event stream.

Current availability: card only.

Live steps when available:
1. Craft a poultice and apply it.
   - expected: healing per tier; crit-fail gives a useless spoiled mash.
