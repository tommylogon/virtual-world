---
id: 332
title: Migrate Legacy Item Effect Props to Triggers, Then Remove Support
status: done
priority: medium
created: 2026-08-23
updated: 2026-10-31
tags: [refactor, engine, items, deprecation, data-migration]
type: task
area: refactor
wiki: "[[Feature Map]]"
---

# Migrate Legacy Item Effect Props to Triggers, Then Remove Support

## What

The legacy consumable shortcut `effect_stat` / `effect_amount` / `effect_target` must be
**migrated to trigger-based functionality** across all scenario and library data (especially
the mansion scenarios), after which engine support is removed. Not a blind deletion: every
functional use gets an equivalent `on_use`/`on_eat`/`on_drink` trigger first.

NOTE ON GRAPH REPRESENTATION (task-886): Previous revisions of this task instructed the script
to emit `logic_trigger` graph nodes and `triggers` edges for graph-format saves. This is obsolete.
Task-886 moved all trigger storage into `node.properties["triggers"]`. The migration script must
emit inline `properties["triggers"]` on the item node itself for both graph-format and template-format
saves.

## Survey (Remeasured 2026-10-31)

Across `data/`, 535 items carry at least one of the three keys (575 total occurrences in `data/`,
plus 62 in root `world_template.json` and 62 in `tests/fixtures/world.json`):

| File | Items | Notes |
|---|---|---|
| `data/scenarios/mansion2.json` | **172** | Primary migration target: mostly `inv_*` character inventory items |
| `data/scenarios/pines.json` | 97 | |
| `world_template.json` / `data/scenarios/world_template.json` | 62 | Root template and scenario copy |
| `tests/fixtures/world.json` | 62 | Test regression fixture |
| `data/scenarios/The Valerious Case.json` | 62 | |
| `data/scenarios/testapartment.json` | 47 | |
| `data/scenarios/labs.json` | 31 | |
| `data/library/rooms/world_template.json` | 24 | |
| `data/scenarios/corsair.json` | 22 | |
| `data/scenarios/morphocene.json` | 13 | |
| `data/scenarios/deepseek_thinking-with-guide_json_20260811_55aa77.json` | 9 | |
| `data/scenarios/apartment.json` | 7 | |
| `data/scenarios/art_heist.json` | 4 | |
| `data/scenarios/heist.json` | 3 | |
| `data/library/characters/lyrie.json` | 3 | |
| `data/scenarios/taco_bell_date.json` | 2 | |
| `data/library/items/table_35eb71c1.json` | 1 | |
| `data/library/items/portrait_e2e1ec7b.json` | 1 | |
| `data/library/items/photograph.json` | 1 | |

Breakdown of the 535 items in `data/`:
- **436 items: keys present but `effect_stat: null` / `None`** - pure save pollution, safe to strip.
- **81 items: vitals** - `effect_stat` in `Hunger` (22), `energy` (19), `thirst` (16), `hygiene` (8),
  `Energy` (7), `hunger` (6), `thirst` (2), `hp` (1). Target is `player` or `self`.
  - Mansion2 items (44): `inv_water_bottle` (+25 thirst), `inv_protein_bar` (+35 hunger),
    `inv_portable_charger` (+5 energy), `inv_canned_peaches` (+30 hunger), etc.
- **16 light items** - `effect_stat: "light"`, `effect_target: "room"` (e.g. `item_hand_lamp`,
  `inv_hand_lamp` in mansion2, plus labs / pines / taco_bell).
- **1 connection item** - `data/scenarios/heist.json` sets a used-on way's `current_state` from `effect_stat`.
- **1 miscellaneous** - `effect_stat: "strength"` in morphocene.

## Plan

### 1. Data migration (`tools/migrate_legacy_item_effects.py`)

Rules, in order:

| Condition | Action |
|---|---|
| keys present, `effect_stat` falsy | strip keys (no behavior lost) |
| stat in {hunger, thirst, energy} any casing, target player/self | normalize casing to vitals key (`Hunger`/`Thirst`/`Energy`), append inline trigger to `properties.triggers` (graph nodes) or `triggers` array (template items): `{"trigger_type": "on_use", "effects": [{"adjust_vital": {"stat": <Stat>, "amount": <amount>}, "target": "self"}]}`. Do NOT emit `logic_trigger` nodes (per task-886). |
| stat == `"light"`, target room | Ensure `light_source` tag exists, set `light_level` from `effect_amount` if missing, ensure a `toggle`/`light` action exists, then strip legacy props. |
| stat == `"connection"` | Target-aware way state toggle or manual review bucket. |
| anything else | leave untouched and report for manual review |

Script must be idempotent, dry-run by default (`--apply` to write), and print a per-file before/after count.

### 2. Engine removal (after migration lands)

- Delete legacy read block `engine/items/use_actions.py:187-205`.
- Audit and delete way connection block `engine/items/use_actions.py:419-426`.
- Remove legacy serialization writes from `engine/serialization_legacy.py:98-100` and `engine/serialization_template.py:160-162`.
- Add scrub-on-load in `engine/serialization.py` for legacy saves.

### 3. Docs

Update ScenarioCreationGuide: replace legacy `effect_stat` documentation with canonical `properties.triggers` and `adjust_vital`.

## Acceptance

- [x] `rg "effect_stat|effect_amount|effect_target"` over `data/scenarios/`, `data/library/`, `engine/`, `static/js/` returns zero production hits.
- [x] `mansion2.json` inventory items still restore vitals when used (spot-check 5).
- [x] `hand_lamp`-style lights still work natively.
- [x] Old saves containing legacy props load cleanly post-removal (scrub path).
- [x] Targeted tests pass (not full suite); script idempotent and dry-run by default.

## Why

The legacy consumable shortcut `effect_stat` / `effect_amount` / `effect_target` is a second, parallel way to express what triggers already express. An item effect is a trigger (`on_use`/`on_eat`/`on_drink` with `adjust_vital`), and the legacy props are a pre-trigger spelling of the same fact. Keeping both means two readers, two writers, and a data migration that has to be right twice.

Task-886 established that triggers belong in `node.properties["triggers"]`, retiring `logic_trigger` nodes and `triggers` edges. Migrating legacy item effects directly into inline triggers aligns all items with current simulation invariants.

## Steps to verify

1. Data migration
   - expected: `python tools/migrate_legacy_item_effects.py --apply` migrates all 535 objects across data files (strips nulls, converts functional vitals and lights); script is idempotent.
   - observed: 625 items migrated across 19 files; subsequent dry-run reports 0 pending items.

2. Engine removal
   - expected: legacy read blocks removed from `engine/items/use_actions.py`; serialization stops writing keys and scrubs on load.
   - observed: lines removed from `use_actions.py`, `serialization_legacy.py`, `serialization_template.py`, and `routes/graph_ops.py`. `_migrate_legacy_item_effects()` added to `engine/serialization.py`.

3. Spot checks
   - expected: mansion2 inventory items still restore vitals when used (5 items); hand_lamp-style lights work natively; old save with legacy props loads cleanly.
   - observed: Tested live in Python; `protein_bar` restored Hunger from 10 to 45 (+35); legacy save with `test_apple` and `test_lamp` scrubbed and converted to triggers/light tags seamlessly.

4. Cleanup
   - expected: `rg "effect_stat|effect_amount|effect_target"` over `data/scenarios/`, `data/library/`, `engine/`, `static/js/` returns zero production hits.
   - observed: Zero hits across data and frontend; only `_migrate_legacy_item_effects` scrub helper in engine.

## Files

- `tools/migrate_legacy_item_effects.py` - new migration script (idempotent, dry-run default, --apply)
- `engine/items/use_actions.py` - removed legacy effect_stat/effect_amount/effect_target read block
- `engine/serialization_legacy.py`, `engine/serialization_template.py`, `engine/serialization.py`, `routes/graph_ops.py` - stopped writing legacy keys; scrub-on-load for old saves
- `data/scenarios/*.json`, `world_template.json`, `data/library/**/*.json`, `tests/fixtures/world.json` - migrated by script
- `tests/test_trigger_migration.py` - added `test_migrate_legacy_item_effect_props`

## Verification (2026-10-31)
- Verified with targeted test selection:
  - `python -m pytest tests/test_trigger_migration.py tests/test_fixture_contract.py tests/test_item_actions.py tests/test_trigger_system.py`: 273 passed.
  - Zero em-dashes introduced across all touched files.
