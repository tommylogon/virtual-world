# Task-171: Hide Intrinsic Abilities on Character Examine

**Status:** REVIEW — implemented 2026-08-03, backend tests green, uncommitted.
**Source:** Design note from playtest planning — "if Kaelen examines Lyrie, he should not see that she is carrying Create Flame."

---

## Goal

Intrinsic abilities (spells, talents) should **never** show up in another character's examine output, while physical items that merely contain magic (scrolls, spell books) stay visible.

## Design / Tag convention

- Items tagged with any of **`spell`, `ability`, `innate`, `intrinsic`, `power`** are treated as intrinsic abilities → hidden from other characters.
- Physical magic items (scrolls, spell books) should be tagged `scroll` / `book` (plus `magic` if desired) and **not** `spell` / `ability` → they remain visible.
- The player themselves still sees everything (self-examine uses the full equipment view).

## Changes

- **`engine/equipment.py`**
  - New module constant `INTRINSIC_ABILITY_TAGS` (frozenset above).
  - `get_visible_equipment` now filters out equipped items carrying an intrinsic tag — this is the "what others see at a glance" view used by the other-character examine narrative (`get_equipment_narrative` with a `viewer_name`).
  - New helpers `_is_intrinsic_ability(node)` and `_drop_intrinsic_abilities(full, player_name)`.
  - `_update_equipment_description` drops intrinsic abilities from the equipment list before generating the character's visible appearance (LLM prompt + fallback), so they can't leak through `base_desc` either.
- No other surface lists a character's carried/equipped items to other players, so the examine-character path is fully covered.

## Tests (added to `tests/test_equipment_system.py`)

- `test_other_narrative_hides_intrinsic_abilities` — equipped `Create Flame` (tags `fire,spell,magic`) hidden from other narrative, still visible in self narrative.
- `test_other_narrative_shows_physical_magic_items` — equipped `Scroll of Fireball` (tags `scroll,magic`) still visible.

## Verification

- `python -m pytest tests/test_equipment_system.py -q` → 37 passed.
- Full backend suite: `python -m pytest tests/ -q -k "not mcp and not emote"` → **407 passed, 1 skipped**.

## Notes / Open Items

- **Follow-up landed 2026-08-03:** the area-description "People here" `[holding: ...]` list now also filters intrinsic-ability items (`engine/area_description.py`, `_is_intrinsic_ability` helper) — Create Flame no longer leaks there either. Covered by new tests in `tests/test_area_description.py`.
- Currently `Create Flame` is *carried* by Lyrie (carrying edge), not equipped — it was already invisible in the viewer narrative; this fix makes the rule robust for equipped intrinsic abilities and establishes the tag convention going forward.
- Data check: ensure no scroll/book items accidentally carry the `spell` or `ability` tag (`rg -l '"spell"' data/library data/scenarios`), otherwise they'd be hidden too.
