---
type: task
status: review
area: ui
priority: low
wiki: "[[UI Reference/Rendering & UI Modules]]"
---

# task-655: Equipment readout renders weapon damage as '1dd+8' (doubled d)

**Filed:** 2026-09-30
**Related:** task-654, task-607

## What

The character inspector's Equipment section and slot modal rendered weapon damage as `1dd+8 piercing` when `props.damage_dice` was authored as a string (such as `'1d8'`). The paperdoll code assumed `damage_dice` was an array `[count, sides, flat]` and indexed `dice[0]`, `dice[1]`, `dice[2]` directly onto string characters `'1'`, `'d'`, `'8'`, producing `'1dd+8'`.

## Why

Weapon damage expressions can come from `properties.damage` or `properties.damage_dice` as strings (`"1d8"`, `"1d6+2"`, `"8"`), arrays (`[1, 8, 0]`), or integers. Indexing into a string as if it were a 3-element tuple corrupts the dice formula display and fabricates nonexistent modifiers.

## How

1. Added `parseDamage(value: unknown): [number, number, number]` in `static/js/inspector/paperdoll-view.ts` mirroring `engine/equipment_bonuses.py:parse_damage`, parsing string dice notation (`"1d8"`, `"2d6+3"`, `"d8"`, `"1d4-1"`), numeric strings, numbers, or tuple arrays into clean `[count, sides, bonus]` numbers.
2. Centralized `formatDamage(dmg, dice, type)` to format parsed dice tuples and optional damage type cleanly without duplicating `'d'` or injecting phantom bonuses.
3. Updated `P.computeEquipmentTotals` and `P.showSlotModal` to parse weapon damage before comparison and formatting.
4. Added unit test coverage in `tools/unit/test_paperdoll_facing.js` verifying dice string parsing, flat damage parsing, array formats, and clean output formatting.

## Steps to verify

1. Run unit test suite:
   - expected: unit test suite passes with 878 passed (3 new tests for damage parsing and formatting) and 1 pre-existing failure.
   - observed: 878 passed, 1 failed.
2. Run TypeScript build and check:
   - expected: `npm run build:ts` and `npx tsc -p tsconfig.check.json --noEmit` exit with code 0.
   - observed: 0 errors.

## Acceptance

- [x] Unified damage parsing handles string dice (`"1d8"`), arrays (`[1, 8, 0]`), flat values (`"8"`, `8`), and null/undefined.
- [x] Equipment section and slot modal format damage without doubled `'d'` or phantom `+8`.
- [x] Best weapon comparison correctly evaluates dice count, sides, and flat bonus.
- [x] Zero em-dash characters introduced.
- [x] Unit tests and TypeScript checks pass cleanly.

## Files

- static/js/inspector/paperdoll-view.ts
- static/js/inspector/paperdoll-view.js
- tools/unit/test_paperdoll_facing.js

## Browser UI and intended live verification

Intended UI home: Select the character carrying Rusty Hatchet or a spear -> Inspector -> Inventory/Equipment section -> equipped weapon detail.

Current availability: Shipped in `InspectorPaperdoll` (`paperdoll-view.ts`).

Live steps:
1. Open the inspector for a character equipped with Rusty Hatchet or Spear.
   - expected: Equipment stat chip displays `1d6 slashing` or `1d8 piercing`, with no doubled `d` and no phantom modifiers.
2. Click the slot to open the slot detail modal.
   - expected: Per-layer damage and slot totals display cleanly formatted dice expressions.
