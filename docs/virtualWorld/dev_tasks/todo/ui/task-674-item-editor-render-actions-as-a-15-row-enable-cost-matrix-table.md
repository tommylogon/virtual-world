---
type: task
status: todo
area: ui
priority: medium
wiki: "[[UI Reference/Rendering & UI Modules]]"
---

# task-674: Item editor: render actions as a 15-row enable/cost matrix table

**Filed:** 2026-10-02
**Related:** task-13, task-57, task-626

## What

Phase 2 of docs/design/full-entity-editors.md. The item data is a 15x5 matrix presented as two stacked chip piles in a 379px column. Render it as a real table inside the full-surface editor: one row per ALL_ACTIONS entry (examine take use open close eat drink read light activate equip unequip throw break drop) with columns enabled, Energy, Hunger, Thirst, HP, and skill/DC. Requirements: (a) use a real table element with th scope=col and th scope=row so it is navigable and announced as tabular data - not a grid of divs; (b) keep the existing ACTION_ICONS and ACTION_COLORS as the row label, and never let colour be the only channel - the text label must survive; (c) make the INVERSE_ACTIONS coupling (take/drop, equip/unequip) visible, since today it is invisible until you toggle one; (d) keep triggers in a disclosure at the bottom - they are a different task, not part of the matrix; (e) fix the markup/CSS mismatch while here - the container is class 'checkbox-grid actions-grid' but only .actions-grid is styled and it is display:flex with flex-wrap, not a grid, while .checkbox-grid has no rule at all. Save-on-change semantics stay as they are. Verify in a live browser at 1600x1000 and again below 1200px.

## Known data gap to close while here

ALL_ACTIONS has 15 entries ending in 'drop' (item-view.js:38-40), but ACTION_COLORS (:50-56) and ACTION_ICONS (:57-63) each have only 14 - both are missing 'drop'. This is visible in the live UI, not theoretical: the drop chip renders as a bare bullet because the icon lookup misses and actionColor() falls back to '#8b949e' (item-view.js:71). Add 'drop' to both tables. It is the INVERSE_ACTIONS partner of 'take', so give it a visually paired but distinguishable icon and colour rather than reusing take's, since the coupling is exactly what requirement (c) is making visible. Confirm no other name in ALL_ACTIONS is missing from either table before closing - grep the whole property set, not one member of it. Consider whether these hand-maintained tables want a guard the way tools/way_property_index.py guards way properties.

## Acceptance

- TODO

## Browser UI and intended live verification

Intended UI home: 📚 Library Browser or the full-surface Item Editor → Actions section. The action settings belong in a semantic table with one row for each `ALL_ACTIONS` entry.

Current availability: The current item action settings are described as two stacked chip piles in a 379px column; the 15×5 matrix and responsive table are planned.

Live steps when available:
1. At 1600×1000, open an item with action settings and inspect the Actions section using visual layout and keyboard table navigation.
   - expected: one table has 15 action rows—examine, take, use, open, close, eat, drink, read, light, activate, equip, unequip, throw, break, drop—and columns for enabled, Energy, Hunger, Thirst, HP, and skill/DC; row/column headers are announced as headers.
2. Toggle Take and inspect Drop, then toggle Equip and inspect Unequip.
   - expected: the inverse-action coupling is visible in the table, and the existing save-on-change behavior persists each toggle/cost.
3. Expand the triggers disclosure below the matrix.
   - expected: triggers remain a separate disclosure and do not become action rows.
4. Resize below 1200px and repeat keyboard navigation through the table.
   - expected: labels remain textual (colour is not the only cue), all costs and enable states remain reachable, and the table does not overflow the editor viewport.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO
