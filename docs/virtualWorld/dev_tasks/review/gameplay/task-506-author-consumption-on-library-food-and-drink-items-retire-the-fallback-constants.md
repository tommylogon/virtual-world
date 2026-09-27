---
type: task
status: review
area: gameplay
priority: low
---

# task-506: Author consumption on library food and drink items (retire the fallback constants)

**Filed:** 2026-09-24
**Related:** 424, 410, 483
**Depends on:** 508 — the consume depletion contract must be settled first, or
every finite item authored here would need a hand-written `adjust_uses` that the
trigger suggester/AI is explicitly told not to add.

## Goal

Give every edible/drinkable library item its own `on_eat`/`on_drink` trigger
(`adjust_vital` + depletion), so nothing usable as food depends on the background
tier's hardcoded fallback — and then `MEAL_RESTORE` / `DRINK_RESTORE`, and with
them the whole fallback branch in `BackgroundSimulation._consume_here`, can be
retired.

## Why (measured 2026-09-24)

The data is far thinner than task-424's scoping note assumed:

- **78** library items are edible/drinkable (a `food`/`drink` tag or an
  `eat`/`drink` action).
- Only **13** author an `on_eat`/`on_drink` trigger.
- **65 are tag-only** — accepted as consumable purely by tag and restored solely
  by the fallback constant.

And "authored" is not the same as "complete". Several that *do* have a trigger
never deplete, which — now that the authored path is live (task-424) — makes them
**infinite** food:

- `rations_of_dried_meat` (`uses: 3`): one `adjust_vital` (`-25`), no
  `adjust_uses`/`remove_item` → eating leaves `uses` at 3 forever.
- `apple` (`uses: 1`): `adjust_vital stat "hunger"` (`-2`) only (the lowercase
  stat also silently no-op'd until the case-insensitive fix in task-424).

The camp itself is fine (all five of its consumables now author their own
`adjust_vital` + `adjust_uses`, task-424), but the library feeds two paths that
matter:

- **foraging** (task-483) spawns library items into the world as fresh copies;
- **library placement** (`_spawn_library_item_node`) puts them in authored areas.

So any soak where a character forages or finds a store can meet an infinite or
non-nourishing item.

## Why the constants cannot simply be deleted yet

`_consume_here` has exactly two branches:

1. **authored** — the item has `on_eat`/`on_drink`; its triggers own *both* the
   restore and the depletion, and the constants are not applied.
2. **fallback** — the item authors nothing; the background tier hardcodes the
   depletion (`count-1` → `uses-1` → remove) *and* applies `MEAL_RESTORE=45` /
   `DRINK_RESTORE=50`.

Delete the constants (or zero them) before branch 1 covers these items and either

- the fallback still runs but restores nothing → 65 foods are eaten and the
  character stays hungry (starvation), or
- the fallback is removed too → a tag-only item fires no trigger, so it neither
  restores nor depletes → an **infinite, useless loaf** (the exact failure task-424
  flagged).

Hence: author first, retire second.

## Re-measured (2026-09-27, implementation pass) — 7 of 71, and the tiers disagreed

The 2026-09-24 numbers were close but the framing was wrong in a way that
mattered.

**Counts.** 71 edible/drinkable library items (a `food`/`drink` tag or an
`eat`/`drink` action). **7** author a relieving `adjust_vital` on the right
trigger. **64 do not.** (The file said 78/13/65.)

Two measurement traps, both of which produced a confidently wrong answer first:

- `trigger_type` may be a **list**. `apple.json` ships `"trigger_type":
  ["on_eat"]`. A checker comparing only against a string reports all 71 items as
  unauthored — or, checked the other way, misses real gaps.
- Hunger and Thirst are **drives** that fill upward, so relief is a **negative**
  amount. `rations_of_dried_meat` ships `{"stat": "Hunger", "amount": -25}` and
  is correctly authored; a check for a positive amount calls it broken.

### The "authored but never depletes" problem is already fixed

The file's second finding — that `rations_of_dried_meat` (`uses: 3`) never
depletes, making it infinite food — **no longer holds.** task-508 landed:
`ConsumeActionsMixin._spend_uses` (`engine/items/consume_actions.py:139-149`)
spends a charge on *every* consume, after the item's triggers, and the trigger
suggester is explicitly told not to hand-write `adjust_uses`. The 64 items are
not infinite; they are simply **nutritionally inert**.

### The part the file did not anticipate: the two tiers disagreed

`ConsumeActionsMixin._consume_item` — the player's own `eat`/`drink` — has **no
fallback**. It runs the item's triggers and that is the entire effect. The
`MEAL_RESTORE`/`DRINK_RESTORE` constants live only in
`BackgroundSimulation._consume_here`, the deterministic background path.

So for a tag-only library item:

- a **background** goblin ate it and got the hardcoded 45 Hunger back;
- the **player** ate it, read `"You eat the Bread. It tastes good"`, and got
  **nothing at all**.

`bread.json` is the cleanest example: its `on_eat` existed and fired, and its
only effect was a `message`. It read as authored, passed a casual read of the
file, and was nutritionally inert on the path a human actually uses. Foraging
(task-483) and library placement both spawn these into the world, so this was
reachable in normal play — not a corner case.

### The 26 fixtures wearing a `food` tag

`ConsumeActionsMixin._is_valid_for` accepts a consumable by **tag alone**. A
mistagged fixture is therefore not cosmetic: a background character will
cheerfully eat the barrel. Twenty-six library items carry `food`/`drink` while
being furniture — `apple_tree`, `barrel`, `cauldron`, `cheese_shred`,
`coffee_grinder`, `dairy_case`, `flour`, `meat_hooks`, `spice_rack`,
`bread_plate`, `candy_jar`, `teacup`, `water_glass`, `water_jug`, `thermos`,
`wine_case`, `wine_cask`, `baja_blast_cup`, `taco_bell_drink_cup`,
`mystery_cream_sauce`, `seasoned_beef_pan`, `water_carboy`,
`hanging_dried_meats`, `boxed_shell_cases`, `frozen_berries_7dtx`.

**Not fixed here.** Un-tagging 26 items changes what a foraging character can
find and what a `put` can reach, and it is a content decision, not a
refactor. They are listed in `tools/lint_library.py:FOOD_ADJACENT_FIXTURES` as
the honest exception set, with the reason.

## Implemented (2026-09-27)

### 1. Authored — 42 items

Every genuinely edible/drinkable library item now carries an `on_eat`/
`on_drink` whose `adjust_vital` relieves the drive. 41 authored, plus `apple`
corrected.

**The values are uniform and deliberately match the constants they replace**
(Hunger −45, Thirst −50). The non-goal says per-item restore tuning is a
separate content pass, and the whole point of retiring the constant is that the
authored value becomes the only one. Authoring at the library's own smaller
house values (−25/−15, as `carcass`/`wheel_of_cheese`/`water_pitcher` use) would
have silently made wild characters eat roughly twice as often — a balance change
disguised as a refactor. Tuning is now a one-line change per item with no
engine involvement.

**`apple` was a measured bug, not a tuning choice:** it shipped
`{"stat": "hunger", "amount": -2}`. Eating an apple relieved 2 out of 100, so a
forager that found one stayed starving. Now −45.

No `adjust_uses` anywhere: task-508 owns depletion.

### 2. `tools/lint_library.py --check unauthored_consumables` — the regression guard

An ERROR check that fires when an edible/drinkable item authors no relieving
`adjust_vital` for the verb it claims. It accepts both trigger shapes in the
data, both `trigger_type` forms, either stat casing, and skips only the
declared fixture set. It checks the **stat matches the drive** — an `on_eat`
whose only `adjust_vital` is `Sanity -10` is not a meal, and accepting it would
leave the item starving with a green lint. That hole was in my first version.

`tests/test_library_lint_consumables.py` — 16 tests pinning the rules, including
one per trap above, plus `test_the_shipped_library_passes` so the criterion
cannot silently regress.

### 3. Constants retired, with the water case split out

`MEAL_RESTORE`/`DRINK_RESTORE` are renamed `UNAUTHORED_MEAL_RESTORE`/
`UNAUTHORED_DRINK_RESTORE` and **kept**, not deleted. The file anticipated this
("keep the branch only for legacy saves, with an explicit note") and the reason
holds: a save or scenario written before this pass holds a tag-only item nothing
authored, and both alternatives are worse. Deleting it makes that item an
infinite, useless loaf; zeroing it makes 42 real foods restore nothing.

**The finding that changed the shape of this:** `DRINK_RESTORE` was *also* the
restore for drinking from a **water area** — natural water is an area tag
(`_in_water_area`), not an item, so it has no authored trigger and never had
one. Before this pass, "how much is a river worth" and "how much is a
hardcoded fallback worth" were literally the same number under the same name.
That case now has its own constant, `WATER_AREA_DRINK_RESTORE`.

## Re-measured (2026-09-27, after)

- `python tools/lint_library.py --check unauthored_consumables` → **0 errors**.
- New tests: `test_library_lint_consumables.py` 16, `test_library_consumable_relief.py` 5.
  Against the **un-authored** library in a clean `HEAD` worktree, **5 of them
  fail** — including `eating bread left Hunger at 80` and `drinking water_skin
  left Thirst at 80`. They are real guards, not assertions that were always true.
- Camp week soak, `tools/soak_sim.py --background-all`, measured in an isolated
  worktree at `HEAD` for the baseline:

  | | baseline | after |
  |---|---|---|
  | 1 min/tick (10080 ticks) | 22/23 alive, 1 dead (exhaustion) @ 0d05h32m | 22/23 alive, 1 dead (exhaustion) @ 0d07h57m |
  | 15 min/tick (672 ticks) | **21/23** alive, 2 dead (exhaustion, dehydration) | **22/23** alive, 1 dead (exhaustion) |

  **The acceptance criterion of 23/23 at both was not met at baseline either**,
  so it is a pre-existing shortfall, not a regression. The change is neutral at
  1 min/tick and gains a survivor at 15. The 15-minute gain is the foreground
  fix showing through: the camp scenario references `bread`, `berries`,
  `dried_meat`, `mushrooms`, `poison` and `water_skin` from the library, and a
  character eating those on the background path was getting the constant while
  the same character on the player path got nothing.
- Full suite: **not run for this task** — the run was stopped at the user's
  request to defer testing. The last full-suite result on this branch is
  **62 failed / 4038 passed**, measured after task-494 against the same
  baseline; this task adds **21** collected tests
  (`--collect-only` on the two new files), so the expected total is
  **4059 passed** with the failure count unchanged. That is an expectation, not
  a measurement — re-run the suite before moving this task to `done`.

## Acceptance

- [x] Every edible/drinkable library item authors a relieving `adjust_vital` on
      the verb it claims, or is in a declared fixture set. — 42 authored,
      26 fixtures declared, lint clean.
- [x] A regression check fails when an edible/drinkable item authors neither
      relief nor a fixture declaration. — `unauthored_consumables`, 16 tests.
- [x] `MEAL_RESTORE`/`DRINK_RESTORE` retired — renamed to say what they are,
      kept only for pre-authoring saves, with the water-area case split out.
- [x] Camp week soak does not regress. — 22/23 → 22/23 (1 min/tick),
      21/23 → 22/23 (15 min/tick). Not 23/23, but not 23/23 before either.
- [ ] **Outstanding before `done`:** the full suite was not run for this task
      (deferred at the user's request). Targeteds are green — 37 in the
      consumption/background suites, plus 16 lint and 5 relief tests — and
      `python tools/lint_library.py --check unauthored_consumables` reports 0
      errors, but the branch-wide run still has to confirm no new failures.
- [ ] **Deliberately not done:** un-tag the 26 food-adjacent fixtures. Changes
      what foraging finds and what `put` can reach; a content decision. They are
      enumerated in `FOOD_ADJACENT_FIXTURES`.
- [ ] **Deliberately not done:** the poisons and tonics (`poison`, `dead_elixir`,
      `tainted_wine`, `clarity_draught`, …) now relieve Thirst. That matches what
      the constant did to them, so it is not a regression, but whether poison
      should quench at all — or should be un-tagged instead — is a design call.

## Non-goals

- Nutrition/diet detail; per-item restore tuning is a separate content pass.
- Changing `FOOD_TAGS`/`DRINK_TAGS`.
