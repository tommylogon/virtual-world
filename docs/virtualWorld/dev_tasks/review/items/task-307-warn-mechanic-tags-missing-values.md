---
group: Items
---
# Warn on Mechanic Tags Missing Values or Equip Slots

**Filed**: 2026-08-19
**Priority**: High
**Status**: In Review — implemented 2026-08-19 (mechanical category + backend validator)

---

## Idea

Editor warning when an item has a mechanic tag (insulation, weapon, clothing, etc.) but no values set for it, or is missing equip slots for tags that should have them.

## Decisions (owner-confirmed 2026-08-19)

- Mechanical tags = the tags the **backend reads and requires values for** (derived from engine code), set to `category: "mechanical"` in `data/library/tags/`:
  `light_source` (light_level), `heat_source` (target_temperature/heating_rate), `sound_source` (sound_level/sound_pattern), `toggleable` (current_state), `insulation` (insulation), `weapon` (damage), `clothing` + `armor` (equip_slots), `container` (max_weight_capacity), `electric`, `exterior`, `magic`, `transit`.
- `transit` and `armor` did not exist in the tag library (both used/read by the engine) — **created**.
- `outdoor`/`electronic` NOT included — no backend code reads them.
- `category` is display-only in the UI, so the change is safe.

## Implemented

- `data/library/tags/*.json` — 11 tags recategorized to `mechanical`; `transit.json` + `armor.json` created.
- `engine/trigger_validator.py` — `MECHANICAL_REQUIREMENTS` map + `_validate_mechanical_items()` pass (`mechanical_tag_missing_props`).
- Surfaced in the left panel `#validation-section` via `/api/triggers/validate`.
- Tests: `TestMechanicalTagWarnings`.

**Verified**: full suite 980 passed (+9 validator tests).

## Notes

- Authoring-time validation: a `weapon` tag with no damage values, or `clothing` with no `equip_slots`, is a broken item that produces silent wrong behavior.
- Family of warnings: `task-305` (ways), `task-306` (empty triggers), `task-307` (this one).
- Ties into the equipment system (`equip_slots`, `equipment_bonuses`).

## Related

- `developer ideas.md` line 14
- Item editor/inspector (`static/js/inspector.js`, `static/js/item-library.js`), `engine/equipment.py`
