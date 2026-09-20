---
type: task
status: todo
area: world
priority: medium
---

# task-421: Light propagation barrier parity with sound

**Filed:** 2026-09-20  
**Relates:** `engine/lighting.py`, `engine/sound.py`, task-418 (awareness
channels), bug-30.

## Problem

The world now has two propagation systems with **different barrier semantics**:

- **Sound** (`engine/sound.py`) respects way state: open 0.5 / see-through 0.75
  / closed 1 / locked·blocked 1 / hidden 2.
- **Light** (`engine/lighting.py`) does not. `_neighbour_light` /
  `_best_spill` / `recompute_area_lights` spill light to neighbour areas with no
  check on the connecting way.

So a lit room bleeds a full light contribution through a **closed, locked**
door. That is physically wrong, it makes the light level of a corridor
depend on rooms it cannot actually see into, and it will quietly break any
future stealth or darkness mechanic that trusts area light level.

## Design

1. Apply the same barrier table to light spill as to sound. A locked door should
   produce approximately zero spill; a closed door a small fraction; an
   open or see-through way most of it.
2. Put the barrier table in **one** place and have both modules import it, so the
   two systems cannot drift apart again. If sound and light genuinely need
   different values, that is fine — but it must be two named tables side by
   side, not one hard-coded and one absent.
3. Keep the existing caching behaviour: `recompute_area_lights()` stamps on the
   graph revision. Barrier state (door open/closed) must therefore be part of the
   revision or the cache key, or the stamp will be stale when a door moves.
4. Preserve the "effective light = highest single source, not the sum" rule from
   the lighting work. This task changes *spill*, not the aggregation rule.

## Acceptance

- Light spill through a locked/closed way is gated by the same barrier values as
  sound, with a fixture test: two areas joined by one door, door open vs closed
  vs locked → three distinct spill results.
- A single shared barrier table exists; changing a value changes both systems.
- Light recomputation still happens on the revision stamp, and opening/closing a
  door invalidates it.
- No change to the per-area "highest single active source" aggregation.

## Non-goals

- Line-of-sight / shadow casting within an area (that would be a sight channel,
  task-418, and is not needed now).
- Changing how light is authored on items or areas.
- Fixing bug-30 (sound path selection) — separate concern.

## Verification

- Unit: barrier gating for open / see-through / closed / locked.
- Unit: cache invalidation on a door state change.
- Regression: existing lighting tests still pass with the aggregation rule
  unchanged.
