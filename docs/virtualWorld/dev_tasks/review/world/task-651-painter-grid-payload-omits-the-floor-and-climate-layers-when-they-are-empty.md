---
type: task
status: review
area: world
priority: medium
---

# task-651: Painter grid payload omits the floor and climate layers when they are empty

**Filed:** 2026-09-30
**Related:** 

## Goal

GET /api/world/scopes/<id>/grid returns layers with only 'biome' and 'road' keys populated; a 'floor' layer and a 'climate' layer are absent entirely rather than present-and-empty, while the layer selector offers four layers (biome, road, floor, climate). The editor has to treat a missing layer as 'nothing painted', which is indistinguishable from 'not implemented' for anything reading the payload -- including a lint. The same applies to names: {} with 30 locations named on the reference art.

## Acceptance

- [x] `_grid_payload` (`routes/world_grid_ops.py`) always returns all four
      `world_grid.PAINT_LAYERS` keys, each present and possibly `{}`; `names` was
      already present-and-empty.
- [x] `names` is populated for the Eldenford art as part of task-650 (29 names).
- [x] Regression test `test_grid_payload_presents_every_paint_layer` asserts an
      unpainted scope has all four keys and that painting one leaves the other
      three present-and-empty.
- [x] Live proof: the payload's `layers` keys are `biome, climate, floor, road`
      with `floor` and `climate` empty rather than absent.
