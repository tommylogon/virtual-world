---
type: task
status: todo
area: crafting
priority: medium
related: [task-831, task-840, task-841]
---

# task-842: Crafting UI — library recipes tab, turn modal, activity banner

<!-- deps:start -->
**Related:** [[task-831-crafting-recipe-schema-v2-ingredients-duration-tiered-outcomes]], [[task-840-crafting-runtime-who-crafts-activities-backsim-abort]], [[task-841-known-recipes-live-in-the-mind-panel]]
<!-- deps:end -->

## What

Three surfaces, three jobs. Nothing crafts from the editor, nothing
authors from the turn modal.

**1. Library Recipes tab (browse + author).** Add `'recipes'` to
`REGISTRY_TYPES` (`routes/library_ops.py:27`) — the generic
`/api/library/<type>` CRUD then serves `data/library/recipes/*.json`
with no new backend code. Tab polish in one module (`recipe-library.ts`,
mirroring `item-library/`): outcome ladder (crit → success → fail →
crit-fail with fail items named), inventory checkmarks per ingredient,
`variant_of` grouping, ➕ New scaffolding the task-831 shape,
`recipe_check.py` on save naming the exact bad field. Browse and author
only — no Cook button here.

**2. Turn modal / command line (execute).** `Make X` is a character
action like any verb: requirement check first (fail-closed missing list),
then Activity start. Craftable-now recipes appear in contextual guidance.
Completion toast carries the tier flavor ("Fluffy and golden!" /
"Burned beyond eating."); outputs land in inventory; fail items get
their own icon. This is the ONLY execution surface alongside the agent
verb and backsim.

**3. Activity banner (watch + abort).** While cooking: banner shows
recipe name, station, ticks remaining (existing `activity_description`),
plus Stop (= `stop_activity()`). Interruption for any reason shows
"the pot waits" and consumes nothing. Completion shows the tier result.

Minigame: not built. The banner reserves a stage area the future
staged-roll minigame (task-840 seam) will fill.

## Why

Each surface does one job so the invariants hold: authorship never
executes, knowledge never acts, actions stay in the turn system.

## How

1. One-line registry addition; verify the 4 existing recipe files list.
2. `recipe-library.ts` tab polish (ladder, checkmarks, variants, New).
3. Turn modal `Make X` path + completion toast (wires existing route).
4. Activity banner ticks-remaining + Stop (existing data + command).

## Steps to verify

1. Open Library → Recipes.
   - expected: 4 files listed; entry shows ladder + checks; no Cook.
   - observed: TODO
2. `Make boiled_water` at a lit fire, Stop mid-way, re-make to finish.
   - expected: abort consumes nothing; completion toasts the tier.
   - observed: TODO

## Acceptance

- [ ] Recipes tab browses/authors; zero execution paths.
- [ ] Turn modal executes; activity banner watches/aborts.
- [ ] Mind panel (task-841) links to library entries read-only.

## Files

- `routes/library_ops.py` — add `'recipes'` to REGISTRY_TYPES
- `static/js/recipe-library.ts` — new tab module
- Turn modal + banner wiring

## Browser UI and intended live verification

Intended UI home: Library → Recipes tab; turn modal → Make X; activity
banner during the cook.

Current availability: card only; registry line not yet added.

Live steps when available:
1. Browse fried_egg in the Recipes tab, then Make it in the turn modal.
   - expected: tab shows ladder with burned_egg named; modal crafts
     with tiered toast; banner aborts cleanly mid-cook.
