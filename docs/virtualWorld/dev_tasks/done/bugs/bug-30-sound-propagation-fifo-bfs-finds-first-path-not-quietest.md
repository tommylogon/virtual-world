# Bug 30 — Sound propagation uses FIFO BFS over weighted barriers: finds first path, not quietest

**Status:** Done — fixed 2026-09-22.

## Found

`engine/sound.py` `propagate_sound` accumulated barrier weights per way
(open 0.5 / see-through 0.75 / closed, locked, blocked 1 / hidden 2) but
traversed with a plain FIFO BFS and a first-touch `visited` set. A node was
finalised the first time any route reached it, so the FIRST route won, not the
route with the lowest accumulated damping. A nearer path through a closed door
could beat a farther mostly-open corridor even when its total weight was worse.

Resolution of the dev note ("sound should be like a shockwave, not only the
cheapest path"): sound is a pressure wave that takes every path, so the loudness
a listener perceives is set by the **strongest (least-damped) route** — which is
exactly a shortest-path (Dijkstra) walk. FIFO-first was wrong for the shockwave
model too.

## Fix (2026-09-22)

- `propagate_sound` is now a least-cost (Dijkstra) walk on cumulative barrier
  using a `heapq` priority queue and a `best` map. A route only re-expands an
  area when it is quieter (lower accumulated barrier) than any earlier route, so
  `hearing_areas` carries the strongest channel's remaining penetration and
  first-hop direction. A monotonic tie-breaker keeps the heap from comparing the
  direction strings.
- Stale docstring on `get_way_barrier` corrected (locked/blocked share the
  closed value; hidden = 2).
- Busy-work hygiene from the same filing: raw `"in"` literals replaced with
  `EDGE_IN` (`get_area_noise_level`, `get_sound_sources_in_area`), and the
  misleading "stays live" comment on the module-level `SPEECH_LEVELS` /
  `WAY_BARRIERS` / `NOISE_LEVELS` snapshots corrected (live lookups go through
  the `_*` helpers).

## Tests

`tests/test_sound.py::TestLeastDampedPath` builds a diamond (A→B→C through one
closed door vs A→D→C through two open ways, heavy route inserted first) and
asserts the result uses the cheaper route's remaining penetration and direction.
Existing `test_sound.py` (33) all green.
