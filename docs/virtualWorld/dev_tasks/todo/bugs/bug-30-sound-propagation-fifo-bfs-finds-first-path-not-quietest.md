# Bug 30 — Sound propagation uses FIFO BFS over weighted barriers: finds first path, not quietest

**Status**: Todo — filed 2026-08-27 from code review (engine/sound.py).

## Found

`engine/sound.py:177-218`: BFS accumulates barrier weights per way
(open 0.5 / see-through 0.75 / closed 1 / locked·blocked·hidden 2) — good
model — but the traversal is plain FIFO breadth-first. FIFO visits in
insertion order and a node once, so the FIRST route to reach an area wins, not
the route with the lowest accumulated damping. A nearer path through two
closed doors beats a farther mostly-open corridor in the result even when its
total weight is worse.

Related hygiene in the same file while touching it:

- `:123,:302` use raw string `"in"` edges instead of `EDGE_IN` constant.
- `:64-66` module-level `SPEECH_LEVELS/WAY_BARRIERS/NOISE_LEVELS` are frozen
  import-time snapshots of what the comment claims stay config-live.

## Impact

Per-door sound barriers (task-329) under-report bleed-through whenever a cheap
route exists beyond the expensive one; whispers arrive audible (or vice versa)
based on graph insertion order rather than acoustics. Also affects any future
feature reusing this walk (task-173 sounds-heard-here UI).

## Fix sketch

Switch to Dijkstra / heap-based shortest-path on cumulative weight (node count
is small; cost trivial). Then import-time snapshot → live lookup (property or
function call into runtime_config), replace `"in"` literals with `EDGE_IN`.

## Verify

Unit test: three rooms A-B-C chained plus A-D-C where B path has one locked
door (weight 2+0.5=2.5) and D path two open ways (1.0 total). Sound from C
must reach A via D-dominant damping, not B's single heavy door.
Existing suite `tests/test_sound*.py` (if present) extended to cover it.
