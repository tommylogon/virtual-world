---
type: task
status: review
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

## Acceptance

- [x] **The layer is whitelisted** in `engine/world_grid.py` `PAINT_LAYERS`,
      `static/js/worldpainter/grid-model.js` and the unit test. Checked the round
      trip the task warned about: a painted climate cell survives `normalise_grid`
      and is still there after save/reload, because the backend no longer drops an
      unlisted layer.
- [x] **One enum vocabulary of five** — `arctic`, `alpine`, `temperate`, `arid`,
      `tropical` — with a base °C each, in `CLIMATE_BASE_C`. Enum, not float: no
      save bloat, one brush instead of a value-and-falloff control, and the
      aggregation below stays a majority vote rather than a mean that invents a
      climate nobody painted.
- [x] **Two areas painted with different climates report different temperatures,
      with no forecast entry authored**: `arctic` compiles to
      `base_temperature: -8.0` and `tropical` to `27.0` on the same grid.
- [x] **The climate layer does NOT split areas.** Climate is absent from
      `identity()`, so a region keeps one place across a climate boundary — five
      forest cells with two of them tropical is still **one** area. A road still
      does split: forest/road/forest is three areas.
- [x] **Aggregation is majority of cells, ties broken by the region's first cell
      in row-major order.** Both halves earn their place: a majority is how a real
      climate is summarised, and the tie-break is what makes the answer
      *deterministic* — an even split of a two-cell region must not depend on
      iteration order, because a grid that compiles differently twice is the bug
      this task exists to prevent. Unpainted cells are not votes.
- [x] **Unpainted is `temperate` (21 °C), not "unknown"** — and, stronger than the
      acceptance asked, an area in a world with **no** climate layer gets *no*
      `climate` and *no* `base_temperature` key at all, so it reads the engine's
      long-standing 21 °C and a world that never chose a climate compiles exactly
      as it did before.
- [x] **An existing world with no climate layer compiles unchanged**, which follows
      from the two points above: nothing is written that was not painted, so there
      is nothing to differ.
- [x] **A disagreeing region is reported**, not silent:
      "1 area(s) had cells painted with more than one climate; the majority won".
- [x] **An unknown climate is a reported typo, not a silent temperate**:
      `WARNING: 1 unknown climate value(s) ignored: 'tropcial' at (1,1). Expected
      one of alpine, arctic, arid, temperate, tropical.` The cell still shows a
      distinct colour while painting, so it is visibly *not* one of the five.
- [x] **Only `world` scopes compile a climate.** A `town` or `interior` gets no
      `climate` and no `base_temperature`: the outdoor model is world-scoped (the
      same distinction task-525 makes for a storey step being a staircase rather
      than a rockface), and a hall is not −8 °C because someone painted arctic on
      it.
- [x] **A legend is shown while painting** — a colour chip per climate labelled
      with the °C it compiles to, plus "unpainted is Temperate", and a title
      explaining the majority rule and the world-scope limit.
- [x] **The server owns the values.** `/api/world/painter/vocabulary` ships
      `climates` and `default_climate` from the same table the compiler aggregates
      against, and the editor adopts them (`useClimatesFromVocab`), supplying only
      the *colour*. A palette showing one base °C while the compiler writes another
      is the kind of disagreement nobody notices until a painted mountain is the
      wrong temperature; a new climate is now a backend change and nothing else.
- [x] Unit tests: `PAINT_LAYERS` asserts the new layer, and three new tests cover
      the vocabulary, the colours (including the typo case) and the server-adoption
      path. `node tools/unit/run.cjs` — 371 passed, the 13 pre-existing
      `test_plan_tracker.js` failures unchanged.

## Notes

- **The deleted `elevation` layer's warning is respected, and the new layer dodges
  it.** `elevation` was removed because one word meant two things (a painted
  height *and* a storey). `climate` means exactly one thing — a coarse outdoor
  thermal band — and it is an enum so the per-region question has one answer
  rather than a continuum. If elevation ever comes back as a painted layer it
  still needs a different justification than the one it lost under.
- The climate values are the **mid-point of each band's range**, not its extreme:
  a painted arctic is cold without being the coldest thing on earth, and the
  diurnal and seasonal curve is added on top by task-553's model.
