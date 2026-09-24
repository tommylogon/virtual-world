---
type: task
status: todo
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

## Acceptance

- Every edible/drinkable library item either authors an `on_eat`/`on_drink` with
  both a relieving `adjust_vital` **and** depletion (`adjust_uses` /
  `remove_item` / persistent `set_state`), or is deliberately marked
  non-consumable (e.g. a fixture like `sink`, `fountain`, `meat_hooks` that is
  edible-looking by tag but should not be eaten).
- A regression test (or a `tools/lint_library.py` check) fails when an
  edible/drinkable item has neither, and when an authored item has no depletion.
- After that pass, remove `MEAL_RESTORE`/`DRINK_RESTORE` and the fallback branch
  (or keep the branch only for legacy saves, with an explicit note).
- Week soak on the camp stays 23/23 at 1 and 15 min/tick.

## Non-goals

- Nutrition/diet detail; per-item restore tuning is a separate content pass.
- Changing `FOOD_TAGS`/`DRINK_TAGS`.
