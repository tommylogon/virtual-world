---
type: task
status: todo
area: world
priority: medium
---

# task-567: A building's interior can be generated from its type, then edited

**Filed:** 2026-09-27
**Related:** task-398 task-561 task-560

## Goal

Hand-painting a building's interior is a lot of cells: the Millbrook map's apartment block alone is 20 rooms across three storeys, and the Downtown district is 14 buildings. If a building TYPE generated its own interior - a fast-food place gets counter, kitchen, dining room and restroom; an apartment gets a corridor, N rooms per storey and a stairway; a mansion gets a hall and named rooms - then the author paints one cell per building and edits what the generator made. That is task-398's mandate (the generator is the only sanctioned way to mint an unmade scope, reproducible and editable afterwards), extended to paint: a generated interior must be deterministic from (type, seed, storeys) and must survive a re-generate without losing the author's edits. Decide how edits are protected (a per-cell author lock, or a recorded divergence list) before generating anything.

## Acceptance

- TODO
