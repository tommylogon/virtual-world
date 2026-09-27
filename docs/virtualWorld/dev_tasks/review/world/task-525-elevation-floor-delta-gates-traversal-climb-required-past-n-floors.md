---
type: task
status: review
area: world
priority: low
---

# task-525: Storey delta gates traversal (climb required past N storeys)

**Filed:** 2026-09-26
**Related:** task-496 task-498

## Goal

Exterior grid steps stay compass moves. When the **storey** delta between two
adjacent exterior cells exceeds a threshold (suggested >3 storeys), the step is no
longer a plain walk: it needs a climb (a narrative feature-entry direction), and
steep drops/climbs may be blocked unless a feature (ledge, cave, rockface)
provides the move. Decide the threshold source (per-scope? per-biome? global
config), whether it blocks or just costs extra time, and how the area description
phrases it. Depends on the observer-view/narrative-direction description work
(task-496 rewrite) and the floor layer already stored on areas
(`properties.floor`).

**Terminology (corrected with the author, 2026-09-27):** the unit is *storeys*,
not heights and not floor materials. `properties.floor` is the storey index — 0 is
the ground plane, 1 one up, -1 one down, and it is **unbounded** (three stacked
rooms, a lake bottom at -2, an 80-storey tower, a hole to hell at -900). Ground
*material* is `properties.surface`. The old `elevation` layer / `properties.elevation`
is gone, and `CLIFF_FLOOR_DELTA = 2` is a *storey* delta — which is why the prose
promotion is restricted to `world` scopes: a storey step inside a town or interior
is a staircase, not a rockface. The gate should follow suit and only apply where a
storey step really is terrain (outdoors), so an interior can stack rooms freely.

## Acceptance

## Acceptance

- [x] **Exterior grid steps stay compass moves.** A step of `threshold` storeys or
      fewer is `kind: "open"` and is walked. The threshold is
      `DEFAULT_MAX_STOREY_STEP = 3`, so an ordinary building is free (a house with
      a cellar is two).
- [x] **Past the threshold the step needs a path**: the way carries a `climb`
      record, `climb_required: true`, `current_state: "closed"` and a
      `refusal_message` naming the storeys — so `engine/movement.py` refuses it
      with the author's own sentence rather than walking a character off a cliff.
- [x] **Threshold source decided: per scope**, as `record.climb.max_storey_step`,
      defaulting to 3. A wilderness world wants three (a cliff is a cliff) and a
      mountain range wants eight; a global setting makes one of those two wrong
      for the other.
- [x] **Interiors are never gated** — the rule is `mode: "world"` only, so a town
      or interior can stack rooms freely and a cellar four storeys under a hall is
      not a trap. This is the correction the task itself records: a storey step
      indoors is a staircase, not a rockface.
- [x] **"Unless a feature provides the move" is the road layer.** A `road` painted
      across the step is a built path and carries you: the same pair of cells
      compiles as a closed climb or an open one depending on the paint. No new
      `ledge` vocabulary was invented for it.
- [x] **It is worded, not silent**: the generate report says how many steps were
      gated and how to open them, and a scope with a custom threshold that gated
      nothing still reports the number it is using.
- [x] A hand-placed area on a cliff obeys the same gate — its boundary ways are
      emitted through the same `climb` path.

## Notes

- **Block, not cost extra time.** The task left this open. A steep step is
  refused outright because the engine has no travel-cost vocabulary for a grid
  edge to charge more, and inventing one here would have been a second, silent
  mechanic. The refusal names the reason, so the author can paint a path.
- Storey *sign* is recorded (`climb.rising`) so prose can say climb or drop, but
  the magnitude is `abs()`, matching task-562's `floor_step`.
