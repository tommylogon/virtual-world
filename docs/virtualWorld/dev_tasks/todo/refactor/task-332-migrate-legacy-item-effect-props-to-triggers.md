---
id: 332
title: Migrate Legacy Item Effect Props to Triggers, Then Remove Support
status: todo
priority: medium
created: 2026-08-23
updated: 2026-08-23
tags: [refactor, engine, items, deprecation, data-migration]
---

# Migrate Legacy Item Effect Props to Triggers, Then Remove Support

## Summary

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

## Implementation

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

## Acceptance Criteria

- [ ] `rg "effect_stat|effect_amount|effect_target"` over `data/scenarios/`,
      `data/library/`, `engine/`, `static/js/` returns zero production hits.
- [ ] mansion2.json inventory items still restore vitals when used (spot-check 5).
- [ ] hand_lamp-style lights still work natively.
- [ ] Old saves containing the props load cleanly post-removal (scrub path).
- [ ] pytest green (`not mcp and not emote`).
