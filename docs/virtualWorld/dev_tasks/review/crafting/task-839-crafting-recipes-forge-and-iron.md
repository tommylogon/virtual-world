---
type: task
status: review
area: crafting
priority: medium
related: [task-831, task-2, task-703]
---

# task-839: Crafting recipes — forge and iron

<!-- deps:start -->
**Related:** [[task-831-crafting-recipe-schema-v2-ingredients-duration-tiered-outcomes]], [[task-2-crafting_and_recipes]], [[task-703-recipe-as-activity-recipes-become-plan-templates-with-duration-success-and-fail-outcomes]]
<!-- deps:end -->

## What

12 recipes: ore to horseshoe — the blacksmith's chain, highest DCs, hottest fails. Slag is honest.

| # | Recipe | Ingredients | Equipment | Cond | Min | Skill/DC | Success | Fail | Crit-fail |
|---|---|---|---|---|---|---|---|---|---|
| 1 | smelt ingot | iron_ore ×2, charcoal (uses 3) | forge (lit), bellows | forge on | 90 | Smithing 12 | iron_ingot | half_smelt (re-smeltable lump, ore kept as lump) | slag (ore lost) |
| 2 | forge nails | iron_ingot (uses 1), charcoal (uses 1) | forge (lit), anvil, hammer | forge on | 30 | Smithing 10 | nails ×8 | nails ×4 (bent) | slag sliver (lost) |
| 3 | forge knife blank | iron_ingot (uses 1), charcoal (uses 2) | forge (lit), anvil, hammer | forge on | 60 | Smithing 12 | knife_blank | knife_blank (flawed, worse) | slag |
| 4 | grind knife edge | knife_blank ×1 | grindstone | — | 20 | Smithing 10 | iron_knife | dull_knife (half damage) | ruined blank (scrap_iron) |
| 5 | forge horseshoes | iron_ingot (uses 1), charcoal (uses 2) | forge (lit), anvil, hammer | forge on | 45 | Smithing 11 | horseshoes (set of 4) | horseshoes (2 fit, half effect) | slag |
| 6 | forge axe head | iron_ingot (uses 2), charcoal (uses 3) | forge (lit), anvil, hammer | forge on | 90 | Smithing 14 | axe_head | axe_head (soft, half damage) | slag + cracked anvil? (no — slag only, anvil kept) |
| 7 | forge sword blade | iron_ingot (uses 3), charcoal (uses 4) | forge (lit), anvil, hammer | forge on | 240 | Smithing 16 | sword_blade | sword_blade (flawed) | slag (all ingots lost) |
| 8 | mend pot | cracked_pot ×1, scrap_iron (uses 1), charcoal (uses 1) | forge (low), hammer | forge on | 30 | Smithing 10 | cooking_pot (repaired) | pot (patched, half uses) | ruined pot (scrap_iron) |
| 9 | make chain links | iron_ingot (uses 1), charcoal (uses 1) | forge (lit), anvil, hammer | forge on | 40 | Smithing 11 | chain (uses 6) | chain (uses 3) | slag |
| 10 | shoe horse | horseshoes ×1, nails ×4 | hammer, forge (low for fit) | — | 30 | Smithing 9 | horse (shod, speed bonus) | horse (shod loose, half bonus) | thrown shoe (kept, retry) |
| 11 | forge fire poker | scrap_iron (uses 2), charcoal (uses 1) | forge (lit), anvil, hammer | forge on | 25 | Smithing 9 | fire_poker | fire_poker (bent) | slag sliver |
| 12 | temper tool | dull_tool ×1, charcoal (uses 1) | forge (lit), quench_barrel | forge on | 20 | Smithing 12 | tool (restored) | tool (brittle, half uses) | cracked tool (scrap_iron) |

New items: iron_ore (check), charcoal (check), forge (station, check), bellows (check), anvil (check), hammer (check), iron_ingot (check), half_smelt, slag, nails, bent_nails, slag_sliver, knife_blank, flawed_blank, iron_knife (check), dull_knife, horseshoes, loose_shoes, axe_head, soft_axe_head, sword_blade, flawed_blade, cracked_pot, cooking_pot (check), patched_pot, chain, fire_poker, bent_poker, quench_barrel (station), dull_tool, brittle_tool, cracked_tool, scrap_iron (check).

Forge rule: every forge recipe requires `forge on` state; charcoal is fuel (`uses` decrement); the hammer/anvil/forge are never consumed. Sword DC16 is the hardest in the set — intended as the aspirational craft.

## Why

Iron turns a camp into a village. The chain (ore→ingot→blank→blade) gives miners, charcoal-burners, and smiths interlocking pursuits.

## How

Per task-831. Smelt fail keeps the ore as a re-smeltable lump (fail ≠ ruin); only crit-fail makes slag. Sword crit-fail loses all three ingots — documented, intended.

## Steps to verify

1. Gate over this card's files.
    - expected: clean; forge-on conditions present on all hot recipes.
    - observed: 2026-10-16 — `recipe_check.py --check`: all 105 clean
      (12 new + 93 prior). Every hot recipe carries `forge on`
      (10 of 12; grind-edge and shoe-horse need no fire by design).
      25 item files authored (no horse item — horses are characters;
      #10 resolves shoes/nails + message).
2. Smelt → nails → knife end to end with one forced fail.
    - expected: lump re-smelts; chain survives a single fail.
    - observed: 2026-10-16 —
      `test_forge_smelt_nails_knife_end_to_end`: smelt → nails →
      blank → edge completes; forced fail yields `half_smelt`.
      Honest gap recorded: the lump is flavor until the grammar
      grows OR-inputs (same known gap as wheat flour) — it exists
      as an item, nothing re-consumes it yet.

## Acceptance

- [x] All 12 recipes validate clean.
- [x] Forge-on gating present on every hot recipe.
- [x] New outputs exist as library files.

## Files

- `data/library/items/*.json` — new outputs above

## Browser UI and intended live verification

Intended UI home: game view → Smelt ingot / forge knife at a lit forge → inventory + event stream.

Current availability: card only.

Live steps when available:
1. Smelt an ingot at a lit forge.
   - expected: ingot per tier; fail keeps a re-smeltable lump; crit-fail gives slag.
