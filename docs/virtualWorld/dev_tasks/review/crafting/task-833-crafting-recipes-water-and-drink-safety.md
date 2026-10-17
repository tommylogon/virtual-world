---
type: task
status: review
area: crafting
priority: high
related: ['task-2', 'task-703', 'task-831', 'task-840']
---

# task-833: Crafting recipes — water and drink safety

<!-- deps:start -->
**Related:** [[task-2-crafting_and_recipes]], [[task-703-recipe-as-activity-recipes-become-plan-templates-with-duration-success-and-fail-outcomes]], [[task-831-crafting-recipe-schema-v2-ingredients-duration-tiered-outcomes]], [[task-840-crafting-runtime-who-crafts-activities-backsim-abort]]
<!-- deps:end -->

## What

12 recipes covering the full chain from muddy water to safe drink: fetching, filtering, boiling, storing, plus the medieval small-drink staples (tisane, broth, small beer, cider). Task-831 schema throughout.

| # | Recipe | Ingredients | Equipment | Cond | Min | Skill/DC | Success | Fail | Crit-fail |
|---|---|---|---|---|---|---|---|---|---|
| 1 | fill waterskin | — (at well/stream) | waterskin | in_area well/stream | 5 | Survival 6 | waterskin (full, unsafe) | half fill | spilled, skin kept |
| 2 | settle muddy water | muddy_water ×1 | wooden_pail | — | 30 | Survival 7 | settled_water ×1 | still cloudy (unsafe) | knocked-over pail, water lost |
| 3 | filter through cloth | settled_water ×1, cloth_scrap ×1 | wooden_pail | — | 10 | Survival 8 | filtered_water ×1 | filtered_water ×1 (still unsafe flag) | torn cloth + lost water |
| 4 | boil water safe | filtered_water ×1 | cooking_pot, fire (on) | fire on | 10 | Survival 8 | boiled_water ×1 | warm_water (unsafe, drinkable) | pot boiled dry — water lost, pot kept |
| 5 | herbal tisane | boiled_water ×1, herb_bunch ×1 | cup | — | 5 | Medicine 8 | herbal_tisane ×1 | weak_tea (half restore) | bitter_sludge (useless) |
| 6 | willow-bark tea | boiled_water ×1, willow_bark ×1 | cup | — | 10 | Medicine 10 | willow_tea (pain relief) | weak_tea | bitter_sludge |
| 7 | meat broth | boiled_water ×1, bones ×1, salt ×1 | cooking_pot, fire (on) | fire on | 30 | Cooking 9 | broth ×2 | thin_broth ×1 | scorched_broth (useless) |
| 8 | brew small beer | barley (uses 3), water (uses 2), honey ×1 | brew_barrel | — | 4320 (3 days) | Cooking 12 | small_beer (uses 6) | weak_beer (uses 3) | vinegar_barrel (useless, barrel kept) |
| 9 | press apple cider | apple ×4 | cider_press | — | 30 | Cooking 9 | apple_cider (uses 4) | cloudy_cider (uses 2) | pomace (pig feed only) |
| 10 | honey mead (small) | honey ×2, boiled_water ×2 | brew_barrel | — | 10080 (7 days) | Cooking 14 | mead (uses 4) | weak_mead (uses 2) | vinegar_barrel |
| 11 | salt the water barrel | salt ×2 | water_barrel (full) | — | 5 | Survival 8 | barrel keeps 2× longer (param) | no effect, salt lost | — |
| 12 | clean waterskin (mold) | waterskin (empty), wood_ash ×1, boiled_water ×1 | — | — | 15 | Survival 9 | waterskin (clean) | still musty (kept) | ruined skin (leather_scraps) |

New library items: muddy_water, settled_water, filtered_water, boiled_water, warm_water, willow_bark, willow_tea, weak_tea, bitter_sludge, broth, thin_broth, scorched_broth, small_beer, weak_beer, mead, weak_mead, vinegar_barrel, cloudy_cider, pomace, brew_barrel (station), cider_press (station), water_barrel (container).

Food-safety rule: only `boiled_water` and its derivatives clear the unsafe flag; warm/filtered/settled water restores thirst but risks sickness (condition hook for a future disease pass — flag only, no new system here).

## Why

Survival starts with water. The sim has waterskins and wells but no path from stream to safe sip — this chain makes thirst a solvable problem instead of set dressing.

## How

Per task-831; water containers use `uses` as fill level (pile semantics — one skin, N drinks). Unsafe flag is a tag (`unsafe_water`) consumed recipes strip.

## Steps to verify

1. Gate over this card's files.
    - expected: clean pass.
    - observed: 2026-10-16 — `recipe_check.py --check`: all 29 clean
      (12 new + 17 prior). 23 missing item files authored alongside.
2. Fetch → settle → filter → boil → tisane end to end.
    - expected: each step's outputs feed the next; unsafe tag survives until boil.
    - observed: 2026-10-16 — `test_water_chain_fill_to_tisane_end_to_end`
      crafts the real chain through the engine; `unsafe_water` tag
      asserted present on filtered_water, gone by construction on
      boiled_water (fresh item without the tag).

## Acceptance

- [x] All 12 recipes validate clean.
- [x] Unsafe-water tag lifecycle documented and respected by all 12.
  (Muddy/settled/filtered/warm carry `unsafe_water`; boiled and
  derivatives do not. Sickness-on-drink is a flagged future hook —
  no new system, per the card.)
- [x] New outputs exist as library files.

## Engine deviations (deliberate, recorded)

- "At well/stream" is not a condition type (closed set has no
  location gate): #1 has no condition. Location gating is future
  grammar, not this card.
- #11 salt-the-barrel resolves to a parameter change, not an item:
  message-only + 703 note (craft never writes node state).
- #12 clean-skin success is message-only (same skin, now clean);
  crit-fail spawns the existing `leather_scraps`.
- Broth items carry both `on_eat` and `on_drink` triggers — the
  consumables lint demands relief for every consumable tag.

## Files

- `data/library/items/*.json` — new outputs above

## Browser UI and intended live verification

Intended UI home: game view → Make boiled water / brew small beer → inventory + event stream.

Current availability: card only.

Live steps when available:
1. Boil filtered water at a lit fire.
   - expected: boiled_water spawns; fail gives warm water (unsafe); crit-fail loses the water.
