---
type: task
status: review
area: library
priority: medium
---

# task-573: Lint biome coverage from biomes.json

**Filed:** 2026-09-27
**Related:** 

## Goal

tools/lint_library.py never opens data/worldpainter/biomes.json. Its only area-adjacent check is area_tag_gaps (:223-229), which asks whether an area has ANY tags -- not whether the tag vocabulary meets the biomes. Add a check reporting every biome whose resource_distribution tags resolve to no library item, so the gap in task-569 surfaces as a countable list rather than a silent one.

## Acceptance

- [x] `tools/lint_library.py` reads `data/worldpainter/biomes.json`.
- [x] It reports every biome whose `resource_distribution` entry resolves to no
      library item, as a countable list.
- [x] It mirrors the consumer's matching rule (tag intersection, with the
      `forage` curated pool), so a "covered" verdict means a search finds
      something.

## What was done 2026-10-02

New warning check `biome_coverage` loads the sibling
`<data>/worldpainter/biomes.json` (so fixture `--data-dir` still works) and, for
each `resource_distribution` entry, intersects its tags with the item tag index
exactly as `engine/foraging.py::_pick_item` does — once any item carries
`forage`, only tagged items are eligible. A warning, not an error: coverage may
legitimately be authored after the biome.

Evidence:

- `python tools/lint_library.py --check biome_coverage` — current tree is
  `0 errors, 0 warnings` (all 16 wild biomes resolve today; the guard is for the
  next biome or the next item removal).
- `python -m pytest tests/test_library_lint_biomes.py -q` — 4 passed, including a
  fixture that plants an uncovered biome and asserts it is reported.
