---
type: task
status: inprogress
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

## Acceptance

- [ ] `data/library/tags/mature.json` registered and passes `scenario_tag_check.py`.
- [ ] Zero `"mature": true` booleans remain; the 19 entries carry the tag.
- [ ] All four readers match on the tag; no `.get('mature')` reads remain.
- [ ] At least one item (`ball_gag`) and the intended node types carry `mature`, so the
      gate fires on real data with `world.mature_content` off.
- [ ] `world.mature_content` off hides/gates tagged content end to end (listings and
      the dressing pool); on restores it.
- [ ] `tests/test_auto_dress.py` mature test exercises real tagged data, not a
      monkeypatched `_wearable_entries`.
- [ ] No second marker: the boolean is fully retired, not shadowed.
