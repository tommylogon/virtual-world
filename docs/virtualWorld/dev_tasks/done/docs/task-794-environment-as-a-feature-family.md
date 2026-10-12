---
type: task
status: done
area: docs
priority: medium
effort: L
wiki: "[[Environment/Light System]]"
blocked_by: [task-791]
---

# task-794: Environment as a feature family

**Filed:** 2026-10-12
**Related:** 

<!-- deps:start -->
**Blocked by:** [[task-791-feature-mechanic-and-system-page-standard]]
<!-- deps:end -->

## What

Make **Environment** a feature *family*: an umbrella page over subpages. Environment covers light, heat/temperature, time/weather/sun/moon/seasons/forecast, plus the world-building cluster (worldpainter, areas, ways, connections, scopes, item placement, biomes, heightmaps, settlements, interiors, structures).

## Why

Environment spans many independent authoring surfaces — light has its own inspector + Engine Config sliders, weather its own schedule, heat its own config. The Feature Map splits it across rows 23/24/25/36. One page is unreadable; the reader should be able to land on 'Environment' and navigate down.

## How

Umbrella page per the new standard, linking its family; each subpage follows the standard. Decide the boundary with World Building (the Map already treats WorldPainter/Grid-to-Graph/Scopes as editor features).

## Steps to verify

1. Open the Environment umbrella.
   - expected: links to light, temperature, weather, and the world-building cluster.
   - observed: TODO

## Acceptance

- [ ] an Environment umbrella links a family of subpages
- [ ] each subpage follows the feature/mechanic/system standard
- [ ] the Map rows 23/24/25/36 map onto the family

## Files

- `docs/virtualWorld/Environment/`
- `docs/virtualWorld/World Building/`
- `docs/virtualWorld/Feature Map.md`
