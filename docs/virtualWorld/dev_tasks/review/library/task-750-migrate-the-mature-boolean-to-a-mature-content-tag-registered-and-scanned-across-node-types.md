---
type: task
status: review
area: library
priority: high
---

# task-750: Migrate the mature boolean to a mature content tag, registered and scanned across node types

**Filed:** 2026-10-09
**Related:** task-660 (auto-dress mature gate), task-206 (mature_content toggle), task-213/462 (mature traits/conditions hiding)

## Goal

Replace the `mature` **boolean property** with a `mature` **tag**, so the same
`mature` marker works uniformly on items, characters, areas and ways and reuses
the existing tag-scanning machinery instead of adding a new property-resolution
path in every consumer.

Evidence that tags are the established gate mechanism here (the reason for this
task): `light_source` (`engine/lighting.py:104`, `engine/toggleable_items.py:50,93`),
`heat_source`, `undead`/`ghost` (`engine/undead.py:_has_tag`) are all tags scanned
inline. A tag is the idiomatic cross-cutting marker; the boolean is the outlier.

Current state — the boolean is real and read in four places:

- `routes/library_ops.py:_filter_mature_entries` — `value.get('mature')` (traits/conditions listing)
- `engine/dressing.py:_wearable_entries` / `_apply_mature_gate` — `data.get("mature")` (items; currently unauthored, see task-660)
- `engine/nl_editor_validation.py:481` — `entry.get("mature")` (library_upsert write gate)
- `engine/player_conditions.py` (definitions set `mature: True`; `:747` reads it) and `engine/traits.py` (8 traits)

Data: 19 entries author `"mature": true`; traits/conditions carry no `tags` field today.

## Plan

1. Register `data/library/tags/mature.json` (`applies_to` covering item, character,
   area, way, trait, condition) so `scenario_tag_check.py` validates it.
2. Migrate the 19 `"mature": true` entries to `tags: ["mature"]`.
3. Repoint the four readers off `.get('mature')` onto the tag.
4. Tag the content that should be gated (e.g. `ball_gag`) so the gate is
   **authored**, not just wired. This closes the task-660 mature-gate acceptance
   that is currently a monkeypatched-fixture no-op.
5. Remove the now-dead boolean reads; do not leave both markers.

Decisions taken up front: the tag will be visible to `has_tag` triggers and to
`auto_dress._tag_matched`'s interest intersection (same as `light_source`; accepted),
and `remove_tag` can strip it at runtime (same as any tag; accepted).

## Resolution (2026-10-09)

- Registered `data/library/tags/mature.json` (applies_to items/characters/areas/ways/traits/conditions).
- Migrated 48 JSON files: the 11 `"mature": true` conditions and 8 traits now carry
  `"tags": ["mature"]`; the `"mature"` key was removed from all 40 conditions
  (11 true + 29 false) and 8 traits. No `"mature"` key remains in `data/`.
- Python: `engine/traits.py` (8 traits) and `engine/player_conditions.py` now set the
  tag (`_MATURE_CONDITION_IDS` → tags; `_CONDITION_BASE` key is `tags`), reader
  `MATURE_CONDITIONS` matches the tag.
- Readers repointed: `routes/library_ops.py` (`_filter_mature_entries`), `engine/dressing.py`
  (`_apply_mature_gate`), `engine/nl_editor_validation.py`, `engine/player_conditions.py`.
- Authored `data/library/items/ball_gag.json` (the missing template its labs.json instance
  references) with `tags: ["mature"]`.

## Acceptance

- [x] `data/library/tags/mature.json` registered. `scenario_tag_check.py --check` reports no
      mature-tag finding; its 15 findings are pre-existing `dead_interests` on the camp cast,
      a stale-baseline issue unrelated to this tag.
- [x] Zero `"mature": true` booleans remain; the 19 entries carry the tag.
- [x] All four readers match on the tag; no `get('mature')` reads remain.
- [x] `ball_gag` (item) and the intended node types (traits/conditions) carry `mature`.
- [x] `world.mature_content` off hides/gates tagged content (library listing filter + the
      dressing pool) and on restores it — covered by tests.
- [x] `tests/test_auto_dress.py` mature test now exercises the real tagged `ball_gag`, not a
      monkeypatched `_wearable_entries`.
- [x] No second marker: the boolean is fully retired.
