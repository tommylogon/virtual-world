---
type: task
status: todo
area: world
priority: medium
---

# task-651: Painter grid payload omits the floor and climate layers when they are empty

**Filed:** 2026-09-30
**Related:** 

## Goal

GET /api/world/scopes/<id>/grid returns layers with only 'biome' and 'road' keys populated; a 'floor' layer and a 'climate' layer are absent entirely rather than present-and-empty, while the layer selector offers four layers (biome, road, floor, climate). The editor has to treat a missing layer as 'nothing painted', which is indistinguishable from 'not implemented' for anything reading the payload -- including a lint. The same applies to names: {} with 30 locations named on the reference art.

## Acceptance

- TODO
