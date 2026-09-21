---
type: task
status: todo
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

- A **7-day** background-only soak of the goblin camp ends with all 23 alive, or
  every death is attributable to an authored cause and documented — not supply
  collapse.
- Food counts stabilize instead of monotonically falling to zero.
- A plant never exceeds 10 produce and never grows past its cap; growth resets
  cleanly at 100.
- Deterministic under a fixed seed; spawned food is trace-visible.
- Plant items remain intact (not removed) as their counters move.

## Non-goals

- A market economy, trade pricing, or detailed nutrition.
- Repurposing `uses` for anything but remaining charges.

## Verification

- Extend `tools/soak_sim.py` reporting with food/drink counts over time.
- A 7-day soak run with the supply curve recorded in the progress doc.
- Unit test: growth ticks to 100, spawns, resets, and respects the 10-item cap.
