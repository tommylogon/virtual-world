# Task: Resistance & Weapon Rework

## Status

**Status**: In Review — implementation complete 2026-08-05. Single `resistance` tag + `resistances` dict (data/library/tags/resistance.json exists), no per-type tags remain in engine/frontend; combat.py parses damage_dice + damage_type + damage_skill + resisted_damage; item-view.js + item-library.js wired for resistance/weapon fields. Moved from inprogress.

## Goal

Replace per-type resistance tags (`fire_resistant`, `cold_resistant`, etc.) with a single `resistance` tag whose values live in the `resistances` property dict. Add weapon dice, skill, and damage type support.

## Changes

### 1. Tag Library
- **Create** `data/library/tags/resistance.json` — single `resistance` tag
- Remove per-type tag lookups from engine (no files to delete — they never existed as JSON)

### 2. Engine: `engine/equipment_bonuses.py`
- Remove `TAG_RESISTANCES` dict (per-type tag → damage_type mapping)
- Change resistance detection: `"resistance" in tags` gates reading the `resistances` property dict
- Add weapon properties: `damage_dice` (str like "1d6"), `damage_type` (str), `damage_skill` (str)

### 3. Engine: `engine/combat.py`
- Parse `damage_dice` format (e.g. "1d6+2") for weapon attacks
- Add `damage_type` to attack log messages
- Look up skill bonus from `damage_skill` instead of just STR for damage mod
- Apply resistance check when damage_type is set

### 4. UI: `static/js/inspector/item-view.js`
- Change tag onChange: `resistance` tag triggers resistance UI (was per-type list)
- Add weapon dice field, skill select, damage type select when `weapon` tag active
- Remove per-type resistance tag checks

### 5. UI: `static/js/item-library.js`
- Same tag onChange changes as item-view
- Add weapon dice/skill/type fields in editor and save payload
- Keep `damage` as a fallback (flat damage)

### 6. Tests
- Update `test_equipment_system.py` if needed
- Update `test_combat.py` for new weapon properties

## Files Modified
- `data/library/tags/resistance.json` (new)
- `engine/equipment_bonuses.py`
- `engine/combat.py`
- `static/js/inspector/item-view.js`
- `static/js/item-library.js`
- `docs/virtualWorld/Items & Inventory/Items Overview.md`
- `docs/virtualWorld/Items & Inventory/Equipment & Paperdoll.md`
