---
type: task
status: todo
area: library
priority: medium
---

# task-573: Lint biome coverage from biomes.json

**Filed:** 2026-09-27
**Related:** 

## Goal

tools/lint_library.py never opens data/worldpainter/biomes.json. Its only area-adjacent check is area_tag_gaps (:223-229), which asks whether an area has ANY tags -- not whether the tag vocabulary meets the biomes. Add a check reporting every biome whose resource_distribution tags resolve to no library item, so the gap in task-569 surfaces as a countable list rather than a silent one.

## Acceptance

- TODO
