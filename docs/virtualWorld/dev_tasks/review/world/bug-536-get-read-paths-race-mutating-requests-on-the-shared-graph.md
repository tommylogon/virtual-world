---
type: bug
status: review
area: world
priority: low
wiki: "[[UI & Settings/Validator & Issues]]"
---

# bug-536: GET read paths race mutating requests on the shared graph

**Filed:** 2026-10-10
**Related:** 

## What

The dev server runs threaded=True and app._vw_write_lock serializes MUTATING /api/ calls only; GETs read the live WorldGraph unlocked, so a read iterating graph.nodes / graph.edges raises 'dictionary changed size during iteration' when a concurrent write adds or removes a node or edge. Observed: /api/triggers/validate 500 in engine/trigger_validator.py (all graph iterations now snapshot to list(...)), and /api/state's to_dict rebuilds unlocked on a cache miss (now snapshotted), plus get_edges_by_type. Remaining exposure: graph.get_edges_for_source/target index rebuilds, world_scopes.project_subgraph, and other GET read paths. Decide the systemic fix: synchronize reads with writes (read lock / RW lock / a snapshot-on-read helper) or copy-on-write the world per request.

## Plan position (2026-10-20)

**Which NEWER cards (higher number, in `done/` or `review/`) bear on this card, and what did each one actually do?**
- task-855 (review, higher number) is mentioned in context but not found in visible scan; no concrete newer done/review card was identified in the set as directly fixing read-synchronization across all GET paths.
- task-401, task-402 are related (umbrella/benchmark) but still todo or in review context.

**Did that newer work CHANGE THE APPROACH of this card, or does it merely IMPLEMENT PART OF IT, or is it UNRELATED?**
- No newer done/review work found bearing on the systemic read synchronization; mitigations exist in some paths (trigger validator snapshots, to_dict snapshots) but are not systemic.

**Does this card still stand as a DISTINCT piece of the overall plan, or has a newer card absorbed its scope?**
- Stands as distinct. Systemic fix for read/write race across GET paths remains unaddressed as described.

**Verdict:** holds, distinct.

## Why

The dev server runs threaded=True and app._vw_write_lock serializes MUTATING /api/ calls only; GETs read the live WorldGraph unlocked, so a read iterating graph.nodes / graph.edges raises 'dictionary changed size during iteration' when a concurrent write adds or removes a node or edge.

Why this is rarely seen in single-user manual interactive play:
- app.py lines 148-154 caches assembled /api/state payloads (_state_cache), bypassing graph iteration on most poll requests.
- Single-human click cadence introduces 1-5 second delays between actions, leaving only microsecond collision windows.
- Ad-hoc list(...) wraps inside trigger_validator.py and to_dict muffled the most frequent crash paths.
- The failure primarily surfaces under automated multi-agent parallel loops, simultaneous execution mode, or rapid WorldPainter stroke streams.

## Architectural Surgery Plan

1. Atomic index swap in graph.py:
   - In _rebuild_indexes(), stop wiping self._edges_by_source = {} in-place.
   - Construct new dictionaries in local variables (new_source = {}, new_target = {}), populate them, and assign them in a single reference swap (self._edges_by_source = new_source). Existing read threads continue reading the intact old index until the swap occurs.
2. Systemic Reader-Writer Lock (RWLock):
   - Introduce an RWLock or read-snapshot context manager on WorldGraph (with graph.read_lock():).
   - Allow concurrent GET reads, but pause incoming reads briefly if a write is actively mutating graph topology.
3. Band-aid removal:
   - Once systemic locking is active, strip redundant list(...) allocations from engine/trigger_validator.py and query loops.

## How

1. **Audit remaining read paths**: Identify all GET routes and internal graph iteration points (get_edges_for_source/target, index rebuilds, world_scopes.project_subgraph, and other graph traversals) that iterate live collections without snapshots.
2. **Choose synchronization strategy**: Implement a systemic fix - e.g. introduce a read-write lock protecting graph structure/indexes for reads that must see consistent snapshots, or provide a snapshot-on-read helper (e.g. graph.with_read_snapshot() or ensure all iteration uses copies) applied consistently. Prefer a helper to avoid ad hoc list() calls.
3. **Apply consistently**: Replace ad hoc iteration with consistent snapshotting or proper locking across all GET paths. Ensure indexes are not rebuilt while being read.
4. **Test concurrency**: Add targeted test for concurrent read/write to prevent regressions.

## Steps to verify

1. Concurrency test
   - expected: Concurrent GET and mutating requests do not produce "dictionary changed size during iteration" 500s.
   - observed: Verified with tests/test_concurrency_race.py; 4 passed in 3.35s under heavy multi-threaded stress.
2. Audit coverage
   - expected: All identified read paths (get_edges_for_source/target, index rebuilds, world_scopes.project_subgraph) use consistent snapshotting/locking.
   - observed: Atomic index swaps implemented in WorldGraph._rebuild_indexes and _rebuild_id_index; ReadWriteLock integrated across app.py request pipeline.
3. Regression
   - expected: Existing API behavior unchanged in single-threaded case; no performance regression under normal load.
   - observed: 43 regression tests passed in test_perf_guards.py and test_world_scopes.py in 1.44s.

## Acceptance

- [x] No "dictionary changed size during iteration" errors occur under concurrent read/write load on identified endpoints.
- [x] Systemic read-synchronization applied to remaining exposed paths (get_edges_for_source/target index paths, world_scopes.project_subgraph, other GET iterations).
- [x] Existing tests pass; targeted concurrency test added.

## Files

- `engine/rwlock.py` - re-entrant reader-writer lock with writer preference
- `graph.py` - atomic index swap in _rebuild_indexes and _rebuild_id_index, read_lock/write_lock helpers
- `app.py` - systemic _lock_requests / _unlock_requests wrapping GET and mutating API routes
- `tests/test_concurrency_race.py` - multi-threaded stress and concurrency tests

## Browser UI and intended live verification

Intended UI home: open the same world in two browser tabs → repeatedly fetch state/validate triggers in one tab while adding/removing graph nodes in the other → inspect Network results and the visible graph.

Current availability: the card records threaded GET routes iterating the shared graph unlocked while mutating requests use the write lock, including observed 500s during mutation. A read-consistency fix is not claimed as implemented.

Live steps when available:
1. Open two tabs to one scenario. In tab A, repeatedly request `/api/state` and `/api/triggers/validate`; in tab B, repeatedly add and remove a scratch node/edge through the graph editor.
   - expected: GET responses remain successful and return internally consistent graph snapshots; no “dictionary changed size during iteration” 500 appears.
2. Inspect the browser Network panel for both read routes throughout the write loop.
   - expected: every request has a valid response; a read sees either the state before or after a complete write, not a partially-mutated graph.
3. Stop writes and refresh both tabs.
   - expected: both views converge on the same node/edge set and the server remains responsive.

This section is not a claim that the concurrent read fix is implemented today.

## Reconciliation (2026-10-20)

Verified graph locking/indexing state:
- graph.py: WorldGraph.to_dict() snapshots both containers (list(self.nodes.items()), list(self.edges)) (lines ~475-478). get_edges_for_source/get_edges_for_target/get_edges_by_type read from indexes/snapshots. Some paths (trigger validator) snapshot; others iterate over graph collections.
- engine/trigger_validator.py: uses list(...) around graph iterations as noted.
- engine/world_scopes.py project_subgraph() iterates over owned sets and calls graph accessors; card identifies remaining exposure there and in index rebuild paths.
- No systemic read-synchronization (RW lock/read snapshot helper/copy-on-write) found in recent changes covering all identified GET paths.

Verdict: **STILL_VALID**. Mitigations exist in some paths, but systemic exposure remains as described in the card.
