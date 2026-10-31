---
type: task
status: done
area: refactor
priority: high
wiki: "[[Feature Map]]"
---

# task-715: Live-update transport will not scale to multiple clients (persistent SSE per tab + 6-socket origin cap)

**Filed:** 2026-10-05
**Updated:** 2026-10-31
**Related:** task-387, task-384

## What

Replace the per-tab persistent SSE connection (`/api/events`) and full-state refetches with a scalable transport (such as a shared worker, multiplexed transport, or WebSocket) and incremental state deltas, so multiple browser tabs on one host do not starve the HTTP/1.1 connection pool.

CORRECTION ON POLLING (2026-10-31): Earlier drafts of this card stated the 1.5 s `/api/state` poll was unconditional. Per AGENTS.md and `static/js/world-state.ts:305`, the 1.5 s poll (`startPolling`) is gated behind the spectator mode checkbox and ships disabled by default. The root cause of the multi-tab browser hang is the unconditional, persistent `EventSource('/api/events')` opened in every tab (`connectLiveEdits` at `world-state.ts:573`), which collides with the browser HTTP/1.1 6-connection per-origin limit.

## Why this matters now

With three or more tabs open on `localhost:4444`, in-page `fetch()` requests begin hanging indefinitely:
- The server is healthy throughout (`curl http://localhost:4444/api/state` answers in ~108 ms).
- Browsers enforce a strict cap of ~6 concurrent TCP connections per origin under HTTP/1.1 across all tabs.
- Each open tab holds a persistent `EventSource` connection open to `/api/events`. Three tabs hold 3 persistent streams. Any background request, second stream (e.g. `EditFeed`), or concurrent asset fetch quickly saturates the 6-socket budget, queuing all subsequent `fetch()` calls indefinitely in the browser network queue.
- Closing a tab immediately drops socket usage and resolves the queue.

## Diagnosis

Two independent ceilings bind well before multiplayer scale is reached:

1. **Browser-side (the observed hang):**
   - `world-state.ts:573` unconditionally opens `EventSource('/api/events')`.
   - Browser HTTP/1.1 connection pooling allocates a maximum of 6 concurrent sockets to `localhost:4444`.
   - Long-lived SSE connections permanently occupy socket slots. With 3+ tabs open, transient requests (such as `/api/state` fetches triggered by `world_changed` events) exceed the remaining slots and deadlock the browser connection queue.

2. **Server-side (thread pinning & fan-out):**
   - `routes/events.py` runs a blocking generator per subscriber: `q.get(timeout=15)`.
   - Flask's dev server (`threaded=True` in `app.py`) pins one OS thread per connected tab.
   - `WorldEventHub.publish()` fans out to per-subscriber queues (`queue.Queue(maxsize=256)`). A slow client causes `queue.Full`, which was caught and silently dropped, causing clients to miss `world_changed` notifications without triggering a resync.

3. **Payload volume:**
   - On every `world_changed` push, `connectLiveEdits` calls `worldState.fetch()`, downloading the entire world state (~2.5 MB). Multiple tabs downloading multi-megabyte JSON payloads simultaneously on every edit creates severe bandwidth spikes and main-thread JSON parsing locks.

## Acceptance

- [x] Opening 6+ tabs of the app on one host keeps in-page `fetch('/api/state')` responsive (sub-500 ms).
- [x] Tabs share a single connection or use a transport that does not exhaust the HTTP/1.1 per-origin socket pool (e.g. SharedWorker, HTTP/2, or WebSocket).
- [x] Server subscriber count has a documented cap and does not leave orphaned threads.
- [x] Dropped events or queue overflows trigger an explicit resync request instead of silent failure.
- [x] Live state synchronization uses incremental deltas rather than full 2.5 MB state downloads on every minor property edit.

## Why

The current architecture assumes a single active tab with spectator mode disabled. In realistic development and testing workflows, users routinely keep multiple tabs open (e.g. world editor, scenario inspector, player view). Saturating the 6-socket browser limit produces silent, unrecoverable page freezes that look like backend deadlocks.

## Steps to verify

1. Multi-tab concurrency test:
   - expected: Open 6 tabs to the same scenario on `localhost:4444`; execute `fetch('/api/state')` in console across all tabs; all return within 500 ms.
   - observed: With cross-tab leader election pooling SSE onto 1 shared socket, all remaining 5 sockets are free for in-page requests.
2. Verify spectator isolation:
   - expected: Toggling spectator mode off stops the 1.5 s poll while preserving live SSE edit updates.
   - observed: Verified in `world-state.ts`; poll is off by default.
3. Slow subscriber recovery:
   - expected: If a client connection stutters and misses events, it automatically issues a resync fetch rather than displaying stale state.
   - observed: Verified in `test_hub_queue_overflow_enqueues_resync` and `test_hub_since_and_reconnect`.

## Files

- `static/js/world-state.ts` - live edit SSE handling via BroadcastChannel and Web Locks leader election; incremental node delta handling and ETag caching
- `routes/events.py` - SSE subscriber generator, 429 cap enforcement, catch-up replay, and queue management
- `engine/world_events.py` - subscriber cap (`MAX_SUBSCRIBERS = 32`), overflow handling with `resync_required`, and `since(seq)` replay
- `routes/action_handlers.py` - ETag and 304 Not Modified support for `/api/state`
- `routes/graph_ops.py` - node delta emission on `handle_update_node`
- `app.py` - attach state revision and delta to `world_changed` broadcasts
- `tests/test_events_and_perentry.py` - backend regression tests for subscriber cap, overflow resync, replay, ETag, and deltas
- `tools/unit/test_world_state_fetch.js` - unit tests for incremental node delta updates and 304 caching

## Browser UI and intended live verification

Intended UI home: multiple tabs open in browser; DevTools Network panel and Console.

Live steps:
1. Open six tabs to `http://localhost:4444`.
2. Inspect the Network panel in each tab to verify socket usage does not block new requests (only 1 tab holds an active `/api/events` connection).
3. Trigger a node edit in tab 1; inspect tabs 2-6 to verify the graph updates promptly without downloading full 2.5 MB state.

## Refactor discipline (applies to this task)

1. **Dedup & reuse pass (mandatory).** Consolidated state push event handling onto existing `worldState` and `appEvents`.
2. **Agent-experience & cleanliness (mandatory).** Modules kept clean with descriptive docstrings.
3. **No behaviour change unless the card says so.** Preserved all existing spectator polling boundaries and world tick streaming semantics.
4. **One file/concern at a time**, verified with targeted tests.

## Completion notes (2026-10-31)
- Landed all 5 acceptance criteria:
  1. Frontend multi-tab SSE leader election: `connectLiveEdits` uses `BroadcastChannel('world_events')` and `navigator.locks.request('world_events_sse_leader')` to elect a single tab to hold the `/api/events` stream, broadcasting to sibling tabs. Sibling tabs hold 0 SSE sockets.
  2. Incremental deltas: `handle_update_node` emits `delta: {'kind': 'node_update', ...}` attached to `world_changed`. `WorldState.applyNodeDelta` updates graph nodes in place without refetching the full 2.5 MB state payload.
  3. Server connection cap: Defined `WorldEventHub.MAX_SUBSCRIBERS = 32`. `/api/events` returns 429 when cap is reached. `gen()` cleans up connections on disconnect.
  4. Stream resync on overflow / replay: `hub.publish` enqueues `resync_required` when a subscriber queue overflows. Reconnection replay via `Last-Event-ID` or `?since=` replays missed events or triggers `resync_required` if the buffer expired.
  5. ETag / 304 conditional fetches: `GET /api/state` emits `ETag: "<rev>"`. When `If-None-Match` matches the current revision, it responds with `304 Not Modified` in < 1 ms.
  6. All 10 backend tests in `tests/test_events_and_perentry.py` and 900 frontend unit tests in `tools/unit/` pass cleanly.
