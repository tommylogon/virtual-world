---
type: task
status: done
area: world
priority: normal
wiki: "[[Scenarios]]"
related: ["task-744", "task-519"]
---

# task-913: Millwood scenario world prop density and anchor room itemization

**Filed:** 2026-10-30
**Related:** task-744, task-519

## What

Populate key anchor locations across the 56 areas of `data/scenarios/Millwood.json` with thematic, interactable items and containers:

1. **Academic Locations:**
   - `Chemistry Lab`: bunsen burner, test tube rack, glass beaker, safety goggles, hydrochloric acid bottle.
   - `Detention Room 104`: detention slip stack, box of whiteboard markers, wall clock, hall pass.
   - `B-Wing Lockers`: combination padlock, student textbook, stray flyer.
   - `School Entrance & Courtyard`: trophy display case, bike lock, flyers on corkboard.

2. **Commercial & Town Locations:**
   - `7-Eleven`: energy drink can, sour candy packet, sunglasses rack, disposable lighter, receipts.
   - `Aroma Cafe`: espresso machine, ceramic coffee mug, barista tip jar, bag of roast coffee beans.
   - `Skate Park`: spare skateboard wheels, skate tool, wax block, sticker pack.

3. **Residential Locations:**
   - `Jake's Bedroom`: gaming headset, portable soldering iron, loose skateboard deck, laundry basket.
   - `Sammy's Living Room`: television remote control, volleyball bag, framed family photograph.
   - `Ashford Manor Foyer`: antique brass room key, ornamental marble umbrella stand.

4. **Canonical Graph Wiring:**
   - All authored items placed with canonical `in` edges to areas or containers (`on` surfaces).
   - Valid action sets, descriptions, weights, and tags defined on every item node.

## Why

Millwood currently contains only 7 world items across 55 areas outside the cafeteria and player inventories. An interactive simulation requires physical objects for characters to inspect, pick up, use, share, or steal during autonomous movement.

## How

- Author new item nodes with standard properties in `data/scenarios/Millwood.json`.
- Connect each item with canonical `in` or `on` edges.
- Validate graph integrity via `tests/test_scenarios.py` and `tests/test_spatial_edges.py`.
