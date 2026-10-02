---
type: task
status: todo
area: testing
priority: high
---

# task-572: Integration test layer

**Filed:** 2026-09-27
**Related:** 

## Goal

3239 unit tests, but NO integration or E2E layer: no save/load round-trip, no timeskip determinism, no trigger fan-out, no scope load/unload, no perf baseline. The unit tests are strong; the seams between systems are untested, and the seams are where the remaining bugs are. Add a harness covering at minimum: save/load round-trip preserving two same-named areas in different scopes (the task-446 defect), same-seed trace equality (the 17 bare random call sites), and a compiled-region generation benchmark (task-402).

## Acceptance

- [x] A save/load round-trip preserves two same-named areas in **different
      scopes** (the task-446 defect), asserting against the graph, not the
      name-keyed `areas` projection.
- [x] Same-seed trace equality over a full turn, plus a different-seed control
      proving the trace actually covers RNG-driven state.
- [x] A compiled-region generation benchmark with a published node/edge count and
      same-seed recompile equality (task-402's foundation).

## Outcome (2026-10-02)

`tests/test_integration_layer.py`, 5 tests against the engine seam (no Flask):

1. `test_two_same_named_areas_survive_a_save_load_round_trip` — builds two areas
   both named `Hollow` in the `town` and `crypt` scopes, round-trips
   `to_dict()`/`load_from_dict()`, and asserts both ids, both `world_scope_id`
   stamps and both scope-membership entries survive.
2. `test_the_areas_projection_is_name_keyed_and_collapses_the_pair` — pins the
   documented **task-439** defect: `to_dict()["areas"]` is keyed by display name,
   so the pair collapses to one entry while the authoritative graph keeps both.
   This is the seam bug the task names; the fix lands in task-439.
3. `test_the_same_seed_replays_the_same_trace` — seeds the global RNG, opts the
   rat's behaviour tree in (so the ~19 bare `random.` tick-path draws are
   exercised), runs 20 full turns, and compares positions/vitals/log.
4. `test_different_seeds_diverge` — the control that keeps (3) from passing
   vacuously.
5. `test_a_compiled_region_has_a_published_and_deterministic_shape` — compiles a
   painted 9x9 region: **81 areas / 272 ways / 1088 edges** (published in the
   failure message and stdout, per task-402), and the same seed recompiles to the
   same node ids. This is the harness task-402's larger benchmark can grow from;
   no arbitrary latency target is asserted.

**Not done here:** task-402's ≥100k-node synthetic generator and the
scoped-endpoint out-of-scope guard. The compiler seam is covered; the scale
fixture is its own task.
