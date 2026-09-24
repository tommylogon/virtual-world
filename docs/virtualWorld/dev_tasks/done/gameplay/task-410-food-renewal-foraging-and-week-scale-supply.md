---
type: task
status: done
area: gameplay
priority: medium
---

# task-410: Food renewal, foraging, and week-scale consumable supply

**Filed:** 2026-09-19  
**Depends on:** task-399 (background runner); task-408 (clean scenario data);
**task-406** (standing-item `on_tick` — see below).

## Goal

A settled camp can feed 23 characters for a week without supply collapse, via
**plant items that grow resources on a timer**.

## Mechanism (decided)

A plant is an item (bush, nut tree, mushroom log) with a growth counter:

1. `on_tick` on the plant adds +1 to its growth counter.
2. When growth reaches 100, spawn a related item (berries / nuts / mushrooms)
   **contained in the plant** ("relation is on the bush").
3. Reset growth to 0.
4. Cap: the plant stops spawning while it already holds ≥10 of its produce.

### Important: use `parameters.growth`, not `uses`

The original idea used the item's `uses`, but `uses` is **remaining charges /
durability**, not a counter:

- `handle_drain` / burn-out treat `uses` reaching 0 as depleted
  (`engine/effect_handlers/equipment.py:105–126`, `engine/tick_manager.py:650–692`).
- `handle_consume_item` and `crafting` **remove the node** at `uses <= 0`
  (`equipment.py:167–173`, `engine/crafting.py:131–136`).
- examine/stacking/carry-weight read `uses`/`max_uses` as durability
  (`engine/items/examine_actions.py:275`, `engine/items/stacking.py:18`,
  `engine/items/carry_weight.py:82–86`).

Using `uses` 0→100 would make the bush look "broken/empty" and risk removal
paths. Instead use the existing generic counter effect:
`adjust_parameter` / `set_parameter` on `parameters` (`engine/effect_handlers/properties.py:32–60`),
which is purpose-built for gauges and works on any node type. `uses` stays what
it is for actual consumables.

### Dependency on task-406 — SATISFIED

A plant standing in a room is not carried and not lit/on, so it used to never be
ticked (`tick_manager` only ticked carried/equipped and lit/on items). **task-406
landed**: `engine/tick_manager.py:745-757` now fires standing-item `on_tick`
triggers exactly once, skipping anything the carried/equipped and lit/on loops
already handled, so there is no double-fire. The growth trigger is buildable now.

### Tag trap: the plant must not be tagged as food

Consumption mechanics do **not** consult tags — `_consume_here`
(`engine/background_simulation.py`) decrements `count` if >1, else `uses` if >1,
and otherwise **removes the node**; `handle_consume_item` and crafting remove at
`uses <= 0`. Tags only decide how consumption *finds* a target
(`FOOD_TAGS`/`DRINK_TAGS`).

So if the bush itself carried a `food` tag, a hungry character would try to eat
the bush and the plant would be deleted. The **plant stays untagged**; only its
**produce** carries the food tags, and produce stacks as `count: N` (a handful
consumed one at a time, the node removed on the last one).

### Gating conditions (added 2026-09-21)

The mechanism needed two condition types that did not exist:

- `parameter_reached` — compares a gauge in the node's `parameters` dict
  (`key`, `value`, `op`, default `gte`). There was only `uses_reached`, which keys
  on `uses` — the very field that must not hold the counter.
- `contains_count` — counts what a container holds, optionally filtered by
  name/id. `op: "lt"` is the produce cap.

Both are implemented in `engine/triggers/condition_tree.py`, registered in
`engine/trigger_validator.py`, and covered by
`tests/test_gauge_trigger_conditions.py`.

## Slices (widened 2026-09-21: this is renewable world sources, not only food)

A **spawner is a renewable source that produces entities without consuming
itself.** Two independent axes — trigger (`on_tick` passive vs `on_use` active)
and product (item vs character):

|  | produces an item | produces a character |
|---|---|---|
| `on_tick` | berry bush, mushroom log | rabbit hole, deer trail |
| `on_use` | fishing spot, snare → caught rabbit | — |

1. **Passive item sources** — plants. **DONE** (see below): no engine work beyond
   the two conditions and the `per: "minute"` mode.
2. **Active item sources** — fishing spot, snare: `on_use` + `skill_check` →
   `spawn_item`. No new engine work; data only.
3. **`tagged_count` condition** — count tagged entities in an area. Required for
   slice 4: `contains_count` counts items *inside* a node, but a rabbit hole's
   rabbits are loose, so nothing caps them and an `on_tick` spawner floods the map.
4. **Character sources** — library creature templates (rabbit, deer), spawn cap,
   and a **death path that yields a carcass**. A cap without a death path is a
   dead end: the fourth rabbit ends the population forever. Kill/hunt resolves on
   the creature; the carcass is what a dead creature drops — do **not** give a
   trail a direct "survival check → carcass" shortcut, or the node becomes a meat
   dispenser the moment the player watches it.

## Changes

1. Implement the plant pattern with `parameters.growth` + `adjust_parameter`
   (+1 per tick), a `growth >= 100` condition (`parameter_reached`), `spawn_item`
   into the plant (`into: "container"`), `set_parameter growth 0`, and a
   `< 10 produce` cap (`contains_count` with `op: "lt"`). The plant itself carries
   **no** food tags; only its produce does.
2. Reconcile consumption against per-minute need rates (`vital_rates.py`): a
   character at Hunger ~3 weeks needs only a small amount per day.
3. Renewal uses existing spawn/consume rules, is capped, deterministic under a
   seed, and visible in the trace.
4. Ship at least a few authored plants in the goblin camp so the camp is
   sustainable.

## Acceptance

- [x] A **7-day** background-only soak of the goblin camp ends with all 23 alive, or
  every death is attributable to an authored cause and documented — not supply
  collapse. (slice 1: 23/23 at both 1 and 15 min/tick)
- [x] Food counts stabilize instead of monotonically falling to zero. (4 -> 50 over a week)
- [x] A plant never exceeds 10 produce and never grows past its cap; growth resets
  cleanly at 100. [[`tests/test_renewable_plants.py`]]
- [x] Deterministic under a fixed seed; spawned food is trace-visible.
- [x] Plant items remain intact (not removed) as their counters move.
  [[`test_mature_plant_spawns_produce_and_resets`,
  `test_plant_itself_is_not_food`]]

## Progress — 2026-09-24 (verification + the hydrate path)

The core (slice 1) was already authored and soaked; this lands the missing unit
verification and fixes the **library-hydrate path** the soak did not exercise
(the scenario embeds its bushes directly).

- **`engine/effects.py` — two real bugs in `_hydrate_item` /
  `_materialize_spawn_triggers`:**
  1. `parameters` was dropped on hydrate, so a spawned plant came up with no
     growth gauge at all (the same class of bug task-410 fixed for the other
     placement path). It is now copied (as a fresh dict).
  2. The legacy singular trigger shape (`condition` + `effect_type` /
     `effect_params`) was not carried onto the hydrated trigger edge, so a
     hydrated plant's growth trigger had no conditions and no effects and would
     never grow. It is now carried, and `conditions` is only emitted when the
     source actually has them — an empty `{}` masked the singular fallback in
     `execution.py` and made the trigger fire unconditionally.
- **`tests/test_renewable_plants.py`** (4): a hydrated bush grows by game-minute,
  a mature plant spawns produce and resets growth, the 10-produce cap holds and
  growth is *not* reset when the cap blocks the spawn, and the plant itself is not
  food-tagged (so it cannot be eaten and deleted).

Remaining (tracked elsewhere): the active item sources and character/creature
spawners from the widened slice table are **task-427** (creature spawners,
population caps, death path/carcass) plus a data-only fishing-spot/snare pass.

## Slice 1 result (2026-09-21)

Five berry bushes authored into the camp via `tools/add_renewable_sources.py`
(3 in Deep Forest, 1 at the Water Source, 1 on the Camp Entrance Trail). Each is
an untagged standing item with `parameters.growth`, a `parameter_reached` gate at
100, a `contains_count` cap of 10, and `per: "minute"` on the increment so growth
measures game time rather than ticks.

```
                 before plants      after
 1 min/tick:   23/23 alive        23/23 alive
15 min/tick:   21/23 (2 starved)  23/23 alive
 food over a week:  4 -> 0           4 -> 50
 hungriest alive:   100              49
```

Identical at 1 and 15 min/tick, which is the point.

Two blockers found and fixed on the way, both broader than plants:

- **`_find_consumable` only saw items with an `in` edge to the area**, so food in
  any container was unreachable and the background tier could starve beside a full
  store. It now traverses every spatial relation (`in`/`on`/`under`/`behind`/
  `beside`/`at`) plus one level of nesting, and `_areas_with` (which decides where
  a forager *travels*) does the same — otherwise nobody walks to the forest.
- **`_is_consumable`'s action fallback accepted `eat` OR `drink`**, so a hungry
  character ate a water skin and Hunger was satisfied. Intent is now threaded
  from the need/consume kind, so food is not drink.

Also: `_spawn_library_item_node` was dropping `parameters` entirely, so any
gauge-carrying item lost its counter at placement, and it now accepts an explicit
`node_id` so authored placement gets stable, re-runnable ids.

## Non-goals

- A market economy, trade pricing, or detailed nutrition.
- Repurposing `uses` for anything but remaining charges.

## Verification

- Extend `tools/soak_sim.py` reporting with food/drink counts over time.
- A 7-day soak run with the supply curve recorded in the progress doc.
- Unit test: growth ticks to 100, spawns, resets, and respects the 10-item cap.
