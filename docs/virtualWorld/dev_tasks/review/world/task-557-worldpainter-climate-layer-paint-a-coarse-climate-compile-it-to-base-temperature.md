---
type: task
status: todo
area: world
priority: medium
---

# task-557: WorldPainter climate layer: paint a coarse climate, compile it to base_temperature

**Filed:** 2026-09-27
**Related:** task-553, task-497, task-496

## Goal

One coarse climate paint layer (arctic / temperate / arid / tropical /
alpine) whose cells compile to a per-area `base_temperature`, so outdoor
temperature varies across the map.

**Depends on task-553.** Do not start this until `base_temperature` exists and
is load-bearing; otherwise this task has nothing to write into.
Design: `docs/design/weather-world-integration.md` §5, §6 step 5.

## Measured (2026-09-27) — three separate obstacles, all measured

**1. The layer whitelist is a hard gate.** `engine/world_grid.py:70`:

```python
PAINT_LAYERS = ("biome", "road", "floor")
```

and `normalise_grid` (`:151-174`) iterates exactly that tuple, **dropping any
layer not in it**. A new layer that is not whitelisted is silently discarded on
save — the author paints, the world forgets. Mirrored in
`static/js/worldpainter/grid-model.js:25` and asserted in
`tools/unit/test_worldpainter.js:345`.

**2. Painted cells do not survive compilation.** `engine/world_compile.py:559`
flood-fills cells of the same *identity* into regions, and `compile_grid`
(`:639`) makes one area per region. So a climate value painted on a cell has to
be **aggregated** into the area, and the rule is a design decision with gameplay
consequences invisible on the painted map. For an enum layer the answer is
easy — majority of cells, ties broken by the region's first cell in the
compiler's stable order. This is a large part of why the layer should be an
**enum and not a continuous value**.

**3. Elevation was tried and removed, for a different reason.** The old
0..1 `elevation` paint layer was folded into the storey index via
`LEGACY_LAYER_KEYS = {"elevation": "floor"}` (`world_grid.py:78`) because one
word meant two things. Elevation today lives per *area* as a description input
(`world_compile.py:829`) and never reaches the climate model. If elevation ever
comes back as a painted layer, it needs a different justification than the one
it lost under — "it drives temperature, which drives biome fit" would be one.

## What to change

1. Whitelist the layer (`world_grid.py:70`, `grid-model.js:25`,
   `test_worldpainter.js:345`).
2. One enum vocabulary of 5 values. Enum, not float: no save bloat, one brush
   instead of a value+falloff control, and the aggregation rule above stays
   trivial.
3. The compiler reads the layer, **excludes it from region identity** (climate
   must not split areas the way a road does), aggregates per region, and writes
   `base_temperature`.
4. A legend/toggle in the WorldPainter so the climate is visible while painting.

## Explicitly not here

Continuous per-cell temperature, wind as a flow field, and per-area seasons all
stay out. Continuous numeric paint layers are exactly what the deleted
`elevation` layer warns about, and the save/diff cost scales with fields.

## Acceptance

- Painting a climate cell survives save → reload → compile.
- Two areas painted with different climates report different outdoor
  temperatures, with no forecast entry authored.
- The climate layer does **not** split areas: a climate change across a region
  keeps one area, and a road still does.
- Unpainted is `temperate` (today's 21 °C behaviour), not "unknown".
- An existing world with no climate layer compiles byte-identically.
