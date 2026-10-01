---
type: task
status: review
area: graph
priority: medium
---

# task-659: Way properties drift: insulation and sound_barrier unreachable on the library spawn and refresh paths

**Filed:** 2026-10-01
**Related:** 596

## Goal

Four hand-maintained lists of the way property set have drifted. insulation is settable by engine/effect_handlers/ways.py:94 but appears in neither routes/library_ops.py spawn (706-708) nor refresh (911-918), nor in engine/sync.py mutable, so it cannot be synced from a library template. sound_barrier, jump_dc and climb_dc are read by engine/movement.py:543 and barriers.py but appear in no spawn list, so a trigger-spawned or library-spawned way silently loses them while a hand-authored save keeps them. The canonical list is now tools/way_properties.py, guarded by python tools/way_property_index.py --check with the present drift baselined in docs/virtualWorld/World Building/way-property-baseline.txt. Decide per key whether the engine is wrong or the list is incomplete, fix the list, then re-run --update-baseline.

## What was done

Every key was checked for a reader before anything was added, because the fix runs in
two directions and the wrong one is easy:

- `insulation` — read at `engine/environment_propagation.py:78` as a multiplier on the
  heat rate through the way. Real, so the lists were incomplete.
- `sound_barrier` — read at `engine/barriers.py:169` and `engine/awareness.py:158`.
  Already in the refresh map and `sync.py`, missing from library spawn.
- `climb_dc` / `jump_dc` — read at `engine/movement.py:543` via `f"{requires}_dc"`, so a
  grep for the literal key finds only a test. Missing from all three library lists.
- `refusal_message` — read at `engine/movement.py:572`.
- `blocked_description` — read at `engine/movement.py:1015`.
- `aliases` — read generically for any node at `engine/matching.py:106`, and
  `matching.py:276` names it "the way node's aliases".
- `cost` — read by movement; present on spawn, absent from the refresh map.

Added to `routes/library_ops.py` spawn, the refresh `prop_map`, and the `engine/sync.py`
mutable set. `tools/way_property_index.py --report` now reports **zero** drift across all
four lists, and `--check` is green with an empty baseline.

The checker was also tightened. It previously compared the declaration against every
list unconditionally, which reported 19 "omissions" from `effect_handlers/ways.py` that
were mostly properties its own props dict assigns two lines above the copy tuple, plus
view-layer keys (`image`, `physics_enabled`, `distance_from_parent`) and edge-layer keys
(`cardinal`, `visible_in_direction`) that are never library-synced. Each property now
declares an `expect`, and the checker only compares where the property belongs. A gate
that always cries wolf is a gate nobody runs.

## Evidence

- `python tools/way_property_index.py --report` — 0 drift, four lists agreeing.
- `tests/test_way_property_index.py` — 8 passed.
- `tests/test_library_refresh.py tests/test_way_connect_repair.py` — 22 passed.
- Full suite: 12 failed / 6588 passed, failure **names** identical to the documented
  baseline of 12.

## Not verified, and why

No library way template sets any of the corrected keys, so there is nothing to exercise
live. Per "content before instrumentation" the follow-up is to author one template that
does — a `draft_door` with `insulation` and `sound_barrier` would make both the spawn
path and this fix observable in the browser. Until then the fix rests on the four
extracting lists agreeing with the declaration, which is weaker than a live check.

The trigger spawn path is still narrow by design and is recorded in the generated page
rather than enforced; widening it is a separate decision.

## Acceptance

- [x] Every corrected key verified to have an engine reader before being added
- [x] `insulation`, `sound_barrier`, `climb_dc`, `jump_dc`, `refusal_message`,
      `blocked_description`, `aliases`, `cost` carried by all three library lists
- [x] Checker no longer reports false positives (per-property `expect`)
- [x] `--report` shows zero drift; `--check` green with an empty baseline
- [x] Regression suite green against the 12-failure baseline
- [ ] A library way template exercising these keys exists, so the spawn path is
      demonstrable in a browser rather than only by list comparison
