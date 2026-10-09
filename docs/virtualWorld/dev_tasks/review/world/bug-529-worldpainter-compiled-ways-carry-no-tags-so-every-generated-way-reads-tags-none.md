---
type: bug
status: review
area: world
priority: medium
---

# bug-529: WorldPainter-compiled ways carry no tags so every generated way reads Tags: none

**Filed:** 2026-10-08
**Related:** task-496 task-522 task-659

## Goal

way_props in engine/world_compile.py:2023-2070 and _way_edges set no tags, so all 378 generated ways in data/scenarios/kraktooth_goblin_camp.json carry none (measured), while authored ways can (engine/effect_handlers/ways.py:94) and the edge tooltip reads props.tags (static/js/inspector/way-authoring.ts:257). Decide the tag source (painted biome/road feature, kind, terrain class, scope) and have the compiler write it, or document that generated ways are intentionally untagged. Test: a compiled way over a painted road cell carries the chosen tags.

## Acceptance

- [x] `emit_passage` writes `tags` = union of both cells' feature tags + biome tags, plus `outdoor` (world mode) and `door`/`stairs` (from `kind`).
- [x] `area_description` reads `outdoor` via `area_tags.is_open_sky`, so the compiled open-air path reads "is clear" (fixed the spelling set `{"exterior","natural"}`).
- [x] `tests/test_way_tags.py` (5): forest path carries `forest`+`woods`+`outdoor`; the emitted tag satisfies the reader predicate; an interior way is not open sky; a road cell tags the way `road`; a storey step tags the way `stairs`.
- [x] `tests/test_world_compile.py` + `test_way_blocking.py` + `test_way_property_index.py` + `test_open_sky.py` pass (196); `way_property_index --check` clean.
- [ ] Live: a compiled open-air path shows "is clear" in the exit list on a running world.

## Design

`docs/design/way-tags.md` — the writer/reader doctrine, the compiler inputs, the
three-tier vocabulary, and the systems that read way tags (with the follow-up
consumers: hazard-on-the-crossing, plans-toward-a-route, trigger-written
condition tags — each filed/owned separately, not bolted on here).

## Landed 2026-10-08

`engine/world_compile.py` `emit_passage` (tags before `nodes.append`);
`engine/area_description.py` exit line. Vocabulary comes from
`data/worldpainter/biomes.json` — no new vocabulary. `tags` is already a declared
way property (`tools/way_properties.py`), so the gate is unaffected.
