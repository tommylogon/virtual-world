---
id: 332
title: Migrate Legacy Item Effect Props to Triggers, Then Remove Support
status: todo
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
plus 62 in root `world_template.json`):

| File | Items | Notes |
|---|---|---|
| `data/scenarios/mansion2.json` | **172** | Primary migration target: mostly `inv_*` character inventory items |
| `data/scenarios/pines.json` | 97 | |
| `world_template.json` / `data/scenarios/world_template.json` | 62 | Root template and scenario copy |
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
| `data/library/items/*.json` | 3 | photograph, portrait_e2e1ec7b, table_35eb71c1 |
| `data/scenarios/mansion.json` | 1 | |
| `data/library/characters/kaelen_voss.json` | 1 | |

Breakdown by content:
- **436 items: keys present but `effect_stat: null` / `None`** - pure save pollution, safe to strip.
- **63 functional vital items** - `Hunger` 13 (+14 lower-case), `Energy` 8 (+17 lower-case),
  `Thirst` 9 (+2 lower-case). All target self/player and fire via `action: "use"`.
  Lower-case values are currently dead (the engine read block in `use_actions.py` matches
  `player.vitals` keys exactly). Migrating them normalizes casing and restores intended behavior.
- **16 light items** - `effect_stat: "light"`, `effect_target: "room"` (e.g. `item_hand_lamp`,
  phone flashlights): legacy room-light change.
- **1 connection item** - `data/scenarios/heist.json` sets a used-on way's `current_state` from `effect_stat`.

## How

### 1. One-off migration script: `tools/migrate_legacy_item_effects.py`

Runs over `data/scenarios/*.json`, root `world_template.json`, and `data/library/**/*.json`.
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

- [ ] `rg "effect_stat|effect_amount|effect_target"` over `data/scenarios/`, `data/library/`, `engine/`, `static/js/` returns zero production hits.
- [ ] `mansion2.json` inventory items still restore vitals when used (spot-check 5).
- [ ] `hand_lamp`-style lights still work natively.
- [ ] Old saves containing legacy props load cleanly post-removal (scrub path).
- [ ] Targeted tests pass (not full suite); script idempotent and dry-run by default.

## Why

The legacy consumable shortcut `effect_stat` / `effect_amount` / `effect_target` is a second, parallel way to express what triggers already express. An item effect is a trigger (`on_use`/`on_eat`/`on_drink` with `adjust_vital`), and the legacy props are a pre-trigger spelling of the same fact. Keeping both means two readers, two writers, and a data migration that has to be right twice.

Task-886 established that triggers belong in `node.properties["triggers"]`, retiring `logic_trigger` nodes and `triggers` edges. Migrating legacy item effects directly into inline triggers aligns all items with current simulation invariants.

## Steps to verify

1. Data migration
   - expected: `python tools/migrate_legacy_item_effects.py --apply` migrates all 535 objects across data files (strips nulls, converts functional vitals and lights); script is idempotent.
   - observed: Not run live; script not yet created.

2. Engine removal
   - expected: legacy read blocks removed from `engine/items/use_actions.py`; serialization stops writing keys and scrubs on load.
   - observed: Not run live; legacy reads/writes still present.

3. Spot checks
   - expected: mansion2 inventory items still restore vitals when used (5 items); hand_lamp-style lights work natively; old save with legacy props loads cleanly.
   - observed: Not run live; not verified.

4. Cleanup
   - expected: `rg "effect_stat|effect_amount|effect_target"` over `data/scenarios/`, `data/library/`, `engine/`, `static/js/` returns zero production hits.
   - observed: 535 objects in `data/` still carry legacy keys.

## Files

- `tools/migrate_legacy_item_effects.py` - new migration script (idempotent, dry-run default, --apply)
- `engine/items/use_actions.py` - remove legacy effect_stat/effect_amount/effect_target read block
- `engine/serialization_legacy.py`, `engine/serialization_template.py`, `engine/serialization.py` - stop writing legacy keys; scrub-on-load for old saves
- `data/scenarios/*.json`, `world_template.json`, `data/library/**/*.json` - migrated by script
- Targeted tests to verify post-removal behavior

## Browser UI and intended live verification

Intended UI home: load a mansion scenario -> select consumables and lights in Inventory/Inspector -> use/eat/drink them through normal item actions -> inspect event stream and resulting vitals/light.

Current availability: legacy `effect_stat`/`effect_amount`/`effect_target` props are still present in 535 items across `data/`. Trigger-based replacements and engine support removal are not yet implemented.

Live steps when available:
1. Load `mansion2.json`; choose five inventory items that previously used the legacy stat-effect props. Use each through its normal action and inspect the affected character vitals.
   - expected: all five restore/apply intended vital effects via `on_use` triggers; no legacy prop is needed at runtime.
2. Turn a `hand_lamp` on and off, then inspect its light level and event output.
   - expected: the light still works through native light behavior after the legacy item-effect path is removed.
3. Load an old save that still contains legacy props and inspect items.
   - expected: the scrub path loads cleanly, preserves intended effects, and produces no error.
4. Inspect item details and `/api/state` after actions.
   - expected: the trigger record is the single operational effect source and obsolete props are absent.

## Refactor discipline (applies to this task)

1. **Dedup & reuse pass (mandatory).** Scan touched concerns for duplicate logic; consolidate onto one owner.
2. **Agent-experience & cleanliness (mandatory).** Keep modules under ~600 lines where seams allow; add one-line module docstrings.
3. **No behaviour change unless the card says so.** Extraction and consolidation only.
4. **One file/concern at a time**, verified with a targeted test selection (never full suite by default, never -q).

## Reconnaissance (2026-10-31)
- Measured: `engine/items/use_actions.py` reads legacy keys (lines 187-205, 419-426). `data/` has 535 items carrying `effect_stat`. Task-886 has retired trigger nodes in favor of `node.properties["triggers"]`, so migration script must emit inline trigger properties, not `logic_trigger` nodes.
- Verdict: STILL_VALID, updated to reflect task-886 architecture. Status remains todo.
