---
group: Pleasure System
---

# Environmental & Clothing Effects (Wet/Transparency/Friction)

**Filed**: 2026-08-11
**Priority**: Low
**Status**: Re-scoped (2026-09-22) — description-driven, not prop-driven

---

## Status — re-scoped (2026-09-22)

**Decision (user):** the numeric `opacity` and `friction` clothing properties are
**cancelled**. `wet`, `comfort` and `coverage` remain usable. Where possible,
layer visibility / wetness / comfort should be carried by the **item's own
description**, not by new numeric props. This is a live-game presentation concern
(prompt quality), not backsim mechanics.

### What already exists (keep)
- **`coverage`** — read by `engine/body_parts.py:240` `is_exposed()` to decide
  skin contact; echoed by the appearance prompt. Numeric and load-bearing. Keep.
- **`wet`** — a character condition (task-190/231) applied via `set_wet`;
  `engine/equipment_bonuses.py:107` cuts insulation when soaked. Already works.
- **`current_state`** per item — echoed when it is a real state (not off/unlit).

### Shipped in this pass
- **Item descriptions now reach both equipment prompts.** `engine/equipment.py`
  adds `_item_description_text()` (renders `{param:x}` when possible, strips
  unresolved placeholders, cuts to one sentence) and `_equipment_description_lines()`:
  - `get_equipment_narrative()` (the "You are wearing…" agent context) appends an
    `ITEM DESCRIPTIONS:` block. For a **viewer** it filters to the outermost /
    visible items, so inner-layer detail cannot leak (`only_names`).
  - `_equipment_detail_lines()` (the appearance-description prompt, task-210)
    now leads each line with the item description and keeps `coverage` /
    `current_state`. `opacity` and `friction` are **no longer advertised**.
- Tests: `TestEquipmentItemDescriptions` in `tests/test_equipment_system.py`
  (self vs viewer, no-description, placeholder stripping, opacity/friction gone).

### Still open / deliberately not done
- **`comfort`** — not added as a property. If wanted, it should be description
  or tag flavor, not a number.
- **Rain → clothing wet → description regenerates** — the wet *condition* and
  the insulation penalty exist; automatically marking equipped clothing wet and
  re-running `_update_equipment_description()` on weather change is not wired.
- **task-208 friction trickle** — `engine/tick_manager.py:1019` still reads an
  item `friction` prop. No library item authors one, and the property is
  cancelled, so this is dormant debt. Left in place because `task-208`'s test
  suite covers it; retire it only alongside that decision.

---

## Original problem (for reference)

Clothing needs `comfort`/`friction`/`coverage`/`opacity` properties so the LLM can reason about layer visibility, and wet clothing should become more transparent + change friction. Environment needs weather/humidity to drive wetness.

## Related

- `task-232 humidity`, `task-210 description enrichment`, `task-208 release/edging/friction`
