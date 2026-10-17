---
id: 332
title: Migrate Legacy Item Effect Props to Triggers, Then Remove Support
status: todo
priority: medium
created: 2026-08-23
updated: 2026-08-23
tags: [refactor, engine, items, deprecation, data-migration]
type: task
area: refactor
---

# Migrate Legacy Item Effect Props to Triggers, Then Remove Support

## What

The legacy consumable shortcut `effect_stat` / `effect_amount` / `effect_target` must be
**migrated to trigger-based functionality** across all scenario/library data (especially
the mansion scenarios), after which engine support is removed. Not a blind nuke — every
functional use gets an equivalent `on_use`/`on_eat`/`on_drink` trigger first.

## Survey (2026-08-23)

461 items across 15 files carry at least one of the three keys:

| File | Items | Notes |
|---|---|---|
| `scenarios/mansion2.json` | **172** | the real migration target — mostly `inv_*` character inventory items |
| `scenarios/pines.json` | 97 | |
| `scenarios/world_template.json` | 62 | incl. `item_hand_lamp` light variant |
| `scenarios/testapartment.json` | 47 | |
| `scenarios/labs.json` | 31 | |
| others (morphocene, corsair, deepseek dump, apartment, art_heist, heist) | 38 | |
| `scenarios/mansion.json` | 1 | effectively clean |
| `library/items/*.json` | 3 | photograph, portrait_e2e1ec7b, table_35eb71c1 |

Breakdown by content:
- **315 items: keys present but `effect_stat: None`** — pure save pollution, safe to strip.
- **~132 functional vital items** — `hunger`/`Hunger` (27), `thirst` (11), `energy` (25),
  mixed casing; `target: "player"`; e.g. `inv_Elena Vance_protein_bar` (Hunger 35),
  `inv_Miki_portable_charger` (Energy 5). All fire via `action: "use"`.
- **14 light items** — `effect_stat: "light"`, `effect_target: "room"` (e.g.
  `item_hand_lamp` amount 60, `pines` miki phone amount 35): legacy room-light change.

## How

### 1. One-off migration script: `tools/migrate_legacy_item_effects.py`

Runs over `data/scenarios/*.json`, root `world_template.json`, and
`data/library/items/*.json`. Rules, in order:

| Condition | Action |
|---|---|
| keys present, `effect_stat` falsy | strip keys (no behavior lost) |
| stat ∈ {hunger, thirst, energy} any casing, target player/self | normalize casing to vitals key (`Hunger`/`Thirst`/`Energy`), append inline `properties.triggers` entry `{trigger_type:"on_use", effects:[{adjust_vital {stat, -amount? sign-preserving}, target self}]}` — for graph-format scenario nodes, emit `logic_trigger` node + `triggers` edge instead (guide §20.6) |
| stat == `"light"`, target room | DEAD DATA today — nothing reads it for items (`item_actions.py:1552–1570` only matches vitals keys). Native system = `light_source` tag + `light_level` + `current_state` lit/unlit (`lighting.py:78` sums lit items' `light_level`; `toggleable_items.py:62` flips states). Migration per item: ensure `light_source` tag exists, set `light_level` from `effect_amount` **if the item has no explicit `light_level`**, ensure a `toggle`/`light` action exists — THEN strip the legacy props. Items already carrying an explicit `light_level`: strip directly |
| anything else | leave untouched + report for manual review |

Script must be idempotent, dry-run by default (`--apply` to write), and print a
per-file before/after count.

### 2. Engine removal (after migration lands)

- Delete legacy read block `engine/item_actions.py:1552–1570`.
- Audit `engine/item_actions.py:1730–1732` (`effect_target == "connection"` on ways) —
  separate variant; confirm zero data hits before removing.
- Stop persisting the three keys in save serialization; scrub-on-load for old saves.

### 3. Docs

ScenarioCreationGuide §2.3 DEPRECATED banner → flip wording to "removed"; §20.6 stays as
the canonical pattern.

## Acceptance

- [ ] `rg "effect_stat|effect_amount|effect_target"` over `data/scenarios/`,
      `data/library/`, `engine/`, `static/js/` returns zero production hits.
- [ ] mansion2.json inventory items still restore vitals when used (spot-check 5).
- [ ] hand_lamp-style lights still work natively.
- [ ] Old saves containing the props load cleanly post-removal (scrub path).
- [ ] pytest green (`not mcp and not emote`).

## Reconnaissance (2026-10-02) — NOT started, measured, ready to execute

Re-surveyed `data/` (the 2026-08 numbers have drifted): **21 files, 625 objects
carry the keys** — 499 with `effect_stat: null` (strip, no behaviour lost),
102 functional vitals, 23 "light", 1 "connection".

- Functional stats: `Hunger` 27 (+14 lower-case), `Energy` 19 (+17), `Thirst`
  15 (+2), `Hygiene` 4, `HP` 4. Lower-case values are currently dead (the read
  block matches `player.vitals` keys exactly); migrating them normalises casing
  and makes them fire, which is the intent.
- Engine reads to remove: `engine/items/use_actions.py:187-205` (vitals,
  clamp 0..100, target self/player), `:419-426` (`effect_target ==
  "connection"` sets the used-on way's `current_state` from `effect_stat`);
  serialization writes at `engine/serialization_legacy.py:98-100` and
  `engine/serialization_template.py:160-162`.
- **Two storage shapes, and they need different output:**
  - Graph-format saves (`mansion2.json` 172, `pines.json` 97,
    `morphocene.json` 13) keep item props in `graph.nodes[id].properties`
    (a dict) → emit a `logic_trigger` node **and** a `triggers` edge
    (`graph.edges`). `item_registry` is empty; `areas` carry none.
  - Template-format saves (`corsair`, `apartment`, `testapartment`,
    `world_template`, `The Valerious Case`, …) keep items in
    `areas[].items[]` → append to the item's inline `triggers` array
    (read by `serialization_legacy.py:110` / `serialization_template.py:180`).
- **Light objects are not uniform.** Many have `tags: null` and no
  `light`/`extinguish` action, so the migration must add `light_source` + a
  toggle/light action; `effect_amount` is usually 20–80 (→ numeric
  `light_level` is legal — `lighting._item_light_stats` `int()`s it). But
  `emf_reader` has `amount: -5` (a dimming effect the native lit-item model
  cannot express) → needs an `adjust_environment {light: -5}` trigger or an
  explicit manual-review bucket.
- **The one connection object** (`data/scenarios/heist.json`) sets a used-on
  way's state from `effect_stat`. `handle_set_state` cannot target the used-on
  node (`engine/effect_handlers/state.py` calls `_resolve_effect_target` without
  `target_item_node`), so it needs either a target-aware `set_state` or a pinned
  `way_id`.
- Deliverable: `tools/migrate_legacy_item_effects.py` (idempotent, dry-run
  default, `--apply`), covering both shapes, then the read/serialization
  removal + scrub-on-load, then the acceptance spot-checks. All 15 minutes of
  design are done here; only execution + verification remain.

## Why

The legacy consumable shortcut `effect_stat` / `effect_amount` / `effect_target` is a second, parallel way to express what triggers already express — an item's effect is a trigger (`on_use`/`on_eat`/`on_drink` with `adjust_vital`), and the legacy props are a pre-trigger spelling of the same fact. Keeping both means two readers, two writers, and a data migration that has to be right twice. Re-surveyed 2026-10-02: 21 files, 625 objects carry the keys — 499 with `effect_stat: null` (pure save pollution, strip with no behaviour lost), 102 functional vitals, 23 light, 1 connection. Migrating normalises casing on lower-case stats that are currently dead (the read block matches `player.vitals` keys exactly), so the intent of those items finally fires. Reuse the native systems rather than grafting onto them: lights become `light_source` tag + `light_level` + a toggle/light action (`lighting.py:78` sums lit items' `light_level`), vitals become `adjust_vital` triggers. Two storage shapes need different output — graph-format saves emit a `logic_trigger` node plus a `triggers` edge, template-format saves append to the item's inline `triggers` array — and `emf_reader`'s `amount: -5` is a dimming effect the native lit-item model cannot express, so it needs an `adjust_environment {light: -5}` trigger or an explicit manual-review bucket. Player experience: items still restore vitals and lights still work, now through one mechanism. Editor experience: the obsolete props are gone from production data, so a new item cannot be authored in the dead spelling. Agent experience: `rg "effect_stat|effect_amount|effect_target"` over `data/`, `library/`, `engine/`, `static/js/` returns zero hits, so an agent cannot accidentally author a legacy effect.

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: load a mansion scenario → select consumables and lights in Inventory/Inspector → use/eat/drink them through their normal item actions → inspect the event stream and resulting vitals/light.

Current availability: legacy `effect_stat`/`effect_amount`/`effect_target` props are still the migration source recorded by this card. Trigger-based replacements and engine support removal are not claimed as complete.

Live steps when available:
1. Load `mansion2.json`; choose five inventory items that previously used the legacy stat-effect props. Use each through its normal action and inspect the affected character vitals.
   - expected: all five restore/apply the same authored vital effects via `on_use`/`on_eat`/`on_drink` triggers; no legacy prop is needed at runtime.
2. Turn a `hand_lamp` on and off, then inspect its light level and event output.
   - expected: the light still works through its native light behavior after the legacy item-effect path is removed.
3. Load an old save that still contains the legacy props and reopen the items.
   - expected: the migration/scrub path loads cleanly, preserves intended effects, and produces no 500 or silent data loss.
4. Inspect the item details and `/api/state` after actions.
   - expected: the trigger record is the single operational effect source and the obsolete props are absent from loaded production data.

This section is not a claim that the migration is complete or live-verified today.

## Refactor discipline (applies to this task)

Applies to every refactor in this repo, per the 2026-10-16 card refresh:

1. **Dedup & reuse pass (mandatory).** While working, scan the touched concern and its
   neighbours for duplicate logic, parallel data homes, and near-identical helpers;
   consolidate onto one owner instead of copying. Prefer reusing an existing seam over
   creating a second one. Record any dedup decision in the move table / notes.
2. **Agent-experience & cleanliness (mandatory).** Name modules/files by concern (not
   by size), keep each under ~600 lines where the seam allows, add a one-line module
   docstring stating its owner and public surface, and ensure a fresh agent session can
   understand it without reading the host. No new abstraction unless an existing seam
   already represents the concept.
3. **No behaviour change unless the card says so.** Extraction and consolidation only;
   keep public imports/API stable and re-export moved members as thin delegates.
4. **One file/concern at a time**, verified with a targeted test selection (never the
   full suite by default, never -q).
