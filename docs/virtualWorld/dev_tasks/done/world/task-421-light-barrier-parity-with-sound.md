---
type: task
status: done
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

## Progress — 2026-09-28 (in `review`)

### The task's premise was stale, and the real defect was narrower

`lighting.py` did **not** spill light through a locked or closed door. Both
`_best_spill` and `recompute_area_lights` had a binary gate —
`current_state == "open" or see_through` — so a solid door already blocked spill
completely. Measured before changing anything, in a two-room fixture with one
door and a blinding neighbour:

| state | sound barrier | ambient light in the dark room |
|---|---|---|
| open | 0.5 | 40 |
| closed | 1.0 | 10 (no spill) |
| locked | 1.0 | 10 (no spill) |
| blocked | 1.0 | 10 (no spill) |
| closed + `see_through` | 0.75 | **40 — as much as an open door** |

So the claim that "a lit room bleeds a full light contribution through a closed,
locked door" is false on `master`. What was actually wrong, and worse in practice,
is three other things:

1. **A see-through way leaked exactly as much as an open one.** A window is not a
   missing door, and sound rated a window *worse* than an open doorway (0.75 vs
   0.5) — so the two systems disagreed about the one thing a window is.
2. **A closed door leaked nothing at all.** A shut door has a frame. Zero is a
   discontinuity, not a model, and it made a lit corridor and a sealed one
   differ by no amount at all.
3. **The light cache never noticed a door move.** `recompute_area_lights` stamped
   `graph.get_revision()`, but mutating a way's `current_state` in place does not
   bump the revision — and `engine/effect_handlers/ways.py:handle_set_way_view`
   does exactly that (`way_node.properties.update(changes)` then
   `self.graph.nodes[way_id] = way_node`, a plain dict assignment). So sealing a
   door left every area reading the light it had before it was sealed. Verified:
   revision stayed at 7 across the mutation and the cached reading did not move.

### What landed

**`engine/barriers.py`** — one module holding one shared **state ladder**
(`open → see_through → closed → locked → blocked → hidden`) and two named tables
over it, which is what the task permits: "two named tables side by side, not one
hard-coded and one absent."

The numbers are **not** shared, and forcing them to be would be wrong. Sound's
barrier is a *cost* (summed along the cheapest route, higher is worse); light's
is a *transmission* (the fraction of a lit neighbour that reaches you, higher is
better). So:

| state | sound cost | light transmission |
|---|---|---|
| open | 0.5 | 1.0 |
| see_through | 0.75 | 0.75 |
| closed | 1.0 | 0.25 |
| locked | 1.0 | 0.1 |
| blocked | 1.0 | 0.0 |
| hidden | 2.0 | 0.0 |

What cannot drift anymore is the part that had: which states exist, and the
resolution order. A test asserts both tables are non-increasing along the shared
ladder, so a state added to one and forgotten in the other fails.

**`engine/sound.py`** now delegates to the shared table. **Its behaviour is
unchanged, byte for byte** — including the slightly surprising part of the
existing order that the existing tests pin: a *declared* solid state gates the
per-door `sound_barrier` override, so `{"closed", see_through: True,
sound_barrier: 2}` is 2.0, while `{"closed", see_through: True}` is 0.75. I got
this wrong on the first attempt (I made the solid state win over `see_through`,
which changed three existing sound tests) and reverted it rather than edit sound
tests to match a change this task did not authorise.

**`engine/lighting.py`** replaces the binary gate with the shared transmission,
in both `_best_spill` and `recompute_area_lights`, and the per-area "highest
single source" aggregation (task-407) is untouched — pinned by its own test.

**The cache.** `get_ambient_light` now validates the stamp against
`(graph revision, barrier signature)`, where the signature is a sorted
fingerprint of every way's `current_state`, `see_through` and the two per-door
overrides. It is sorted so a differently-ordered node dict still hits the cache,
and it is compared, never parsed. This closes the in-place-mutation gap without
either an O(V) walk on every read or a change to `graph.py`.

**Per-door `light_barrier`** is a *transmission*, matching the word: 0.1 means "a
tenth of the light gets through". Copying the sound number's meaning would have
made the override read backwards.

**Engine Config** gains `light.way_open` / `_see_through` / `_closed` / `_locked` /
`_blocked` / `_hidden` in `DEFAULTS` and the schema, alongside the existing
`sound.way_*` set.

### New tests — `tests/test_light_barriers.py` (27)

Open/closed/locked producing **three distinct spill results** (measured on the
spill contribution, since a pitch-black room floors the ambient reading and a
locked door legitimately passes almost nothing); the same three doors moving the
room's reading; a closed door leaking a little; blocked and hidden admitting
nothing; a window no longer worth as much as a missing door; `see_through`
outranking state in **both** systems; a shut window rated as a window unless the
author gave it mass; sound reading the shared table and keeping its numbers; a
configured value moving its own system and not the other; both tables on one
ladder; the per-door override direction; an unrecognised state being passable;
closing and re-opening a door invalidating the cache; the signature being stable
and order-independent; the cache staying warm on untouched doors; the
highest-single-source rule; and the module importing with no graph loaded.

### A pre-existing order-dependent suite bug, found and fixed

The new tests passed alone and failed in a full run, which is never a sign about
the new tests. `tests/test_engine_config.py::test_sound_and_light_reflect_override`
saves `sound.way_open = 0.9`, and its `isolated_config` fixture restored the
config *path* but not the in-memory `_values` — so every later test in the
session, in any file, read 0.9. `engine/sound.py` and `engine/lighting.py` tests
were order-dependent on `master` and nobody had noticed because they pass in
isolation. Fixed by snapshotting and restoring `_values` in the fixture. The new
test file also pins its own defaults, so it does not depend on that fix holding.

### Still open

- A per-way state change in any writer other than
  `engine/effect_handlers/ways.py` is caught by the barrier signature, so no
  further `graph.py` change is needed. If someone later adds a cheaper cache, the
  signature is the thing that must be kept.
