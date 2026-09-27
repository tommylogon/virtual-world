---
type: task
status: todo
area: world
priority: high
---

# task-569: Biome resource distribution consumer

**Filed:** 2026-09-27
**Related:** 

## Goal

Wire data/worldpainter/biomes.json resource_distribution (line 1818) into a spawner that places items into compiled areas. The data is authored and validated (engine/biomes.py:397-416) but has ZERO runtime consumers -- a repo-wide grep finds only the data, the loader, the validator and the tests. Blocked by the item-affinity vocabulary task and by task-504 (quantity/pooled nodes). Populate GenerationReport.unresolved_tags (generation.py:48) when a tag resolves to nothing. task-497 is filed done but its acceptance criteria read as behaviour; its own note admits no engine behaviour change. Trust the code, not the folder.

## Acceptance

- TODO
