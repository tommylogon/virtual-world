---
type: task
status: todo
area: gameplay
priority: medium
---

# task-424: Background consumption uses the authored path (bread vs glass)

**Filed:** 2026-09-21  
**Depends on:** task-410 (renewable sources — the same `_find_consumable` path).  
**Relates:** `engine/items/consume_actions.py`, `engine/background_simulation.py`.

## Scoping notes (2026-09-21, measured)

Two things this task did not know, both of which change its shape. It is **three
pieces, not one**, and the first piece on its own is invisible.

**1. Almost nothing authors its own consumption.** Of ~40 edible/drinkable library
items, only six have an `on_eat`/`on_drink` trigger (`rations_of_dried_meat`,
`water_pitcher`, `wheel_of_cheese`, and three Taco Bell items). The rest are
tag-only, and `_consume_item` accepts them on the tag alone — so with the authored
path they would fire no effect and never deplete: an infinite loaf. The hardcoded
depletion is currently the *only* thing making camp food finite.

**2. The camp places five consumables**, not a sprawling inventory:
`item_berries`, `item_bread`, `item_dried_meat`, `item_mushrooms` (food) and
`item_water_skin` (drink) — and none of them has a trigger today. So the data pass
is small and tractable, and it is what makes the change *visible*; the code half
alone would leave the camp on the fallback and change nothing observable.

**3. "A glass empties and persists" needs a mechanism that does not exist yet.**
`uses` reaching 0 is handled generically in the *use* path
(`items/use_actions.py`, which detaches the item from its area) and for **lit**
items (`tick_manager` fires `on_depleted` under `if is_lit`) — but **not** in the
consume path. `_consume_item` relies on the item calling `adjust_uses`. So a
drinkable container cannot currently author "at 0 charges, become empty and stay
in the world" through consumption: that generic depletion hook is part of this
task, and the acceptance item about the empty glass depends on it.

Suggested order: the code delegation (a) → the generic `uses == 0 → on_depleted /
set_state` hook (c) → the data pass on the five camp consumables (b). Only then
retire `MEAL_RESTORE`/`DRINK_RESTORE`, and the soak should be unchanged because
until (b) lands every camp item is still on the fallback.

## Problem

Consumption has two mechanisms that disagree:

- **Player path** (`engine/items/consume_actions.py:consume_item`) is **data-driven**.
  It fires the item's `on_eat`/`on_drink` triggers, applies the action cost, records
  a turn event, and then **stops** — depletion is the item's own business via
  `adjust_uses`, `set_state`, or `rename`. So bread can be destroyed, a glass can
  *empty and persist*, and a container can be refillable, because the item authors it.
- **Background path** (`background_simulation._consume_here`) is **hardcoded**:
  `count - 1` → `uses - 1` → **remove the node**. It ignores authored triggers
  entirely.

So the background tier cannot empty a container, destroys anything with
`uses == -1` that it consumes, and forced the wash-spot fixture (task-410) to avoid
the `water` tag purely to escape deletion.

## Goal

One consumption path. The background tier calls the authored one, with the active
player swapped in for the decision (the same trick `_travel_toward` already uses
for movement), so a glass empties, a skin keeps its charges, and bread is eaten.

## Changes

1. `_consume_here` delegates to the item-consume path instead of hardcoding
   depletion. Keep the current behaviour only as a degenerate fallback for items
   with **no** authored consumption triggers, and log when it is taken.
2. **Data pass:** consumables must author their own effect, because the vital
   restore currently comes from the background hardcode
   (`MEAL_RESTORE = 45`, `DRINK_RESTORE = 50`). Each food/drink item gains an
   `on_eat`/`on_drink` trigger with `adjust_vital` (Hunger/Thirst), plus
   `adjust_uses` and an empty/finished state where it should persist.
3. Add the missing pattern: a **drinkable container** authors
   `uses_reached 0 → set_state empty` (+ optional `rename`), so it survives being
   drunk from. `uses` is charges/durability, never a gauge (task-410).
4. Only then retire `MEAL_RESTORE`/`DRINK_RESTORE` from the background tier.

## Acceptance

- Drinking from a glass leaves an empty glass in the world; eating bread removes it.
- An item with `uses: -1` is never destroyed by being consumed.
- A refillable container can be refilled and drunk again.
- Authored `on_eat`/`on_drink` triggers fire for background characters exactly as
  they do for the player, and the trace shows the same reason tags.
- Camp food supply behaviour is unchanged from task-410 (still 23/23 over a week).

## Non-goals

- New consumption verbs or nutrition detail.
- Changing what counts as food/drink (`FOOD_TAGS`/`DRINK_TAGS`).
- Refill mechanics beyond making them possible in data.

## Verification

- Unit: `_consume_here` on a container item that authors an empty state leaves the
  node; on an item with no triggers it falls back and says so.
- Unit: background eat fires the item's `adjust_vital` (Hunger drops by the
  authored amount, not by a constant).
- Soak: a week at 1 and 15 min/tick, survival and food counts unchanged vs
  task-410's result.
