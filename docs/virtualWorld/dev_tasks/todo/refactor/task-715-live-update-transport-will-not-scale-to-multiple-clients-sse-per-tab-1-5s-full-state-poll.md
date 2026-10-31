---
type: task
status: todo
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
   - `WorldEventHub.publish()` fans out to per-subscriber queues (`queue.Queue(maxsize=256)`). A slow client causes `queue.Full`, which is caught and silently dropped, causing clients to miss `world_changed` notifications without triggering a resync.

3. **Payload volume:**
   - On every `world_changed` push, `connectLiveEdits` calls `worldState.fetch()`, downloading the entire world state (~2.5 MB). Multiple tabs downloading multi-megabyte JSON payloads simultaneously on every edit creates severe bandwidth spikes and main-thread JSON parsing locks.

## Acceptance

- [ ] Opening 6+ tabs of the app on one host keeps in-page `fetch('/api/state')` responsive (sub-500 ms).
- [ ] Tabs share a single connection or use a transport that does not exhaust the HTTP/1.1 per-origin socket pool (e.g. SharedWorker, HTTP/2, or WebSocket).
- [ ] Server subscriber count has a documented cap and does not leave orphaned threads.
- [ ] Dropped events or queue overflows trigger an explicit resync request instead of silent failure.
- [ ] Live state synchronization uses incremental deltas rather than full 2.5 MB state downloads on every minor property edit.

## Why

The current architecture assumes a single active tab with spectator mode disabled. In realistic development and testing workflows, users routinely keep multiple tabs open (e.g. world editor, scenario inspector, player view). Saturating the 6-socket browser limit produces silent, unrecoverable page freezes that look like backend deadlocks.

## Steps to verify

1. Multi-tab concurrency test:
   - expected: Open 6 tabs to the same scenario on `localhost:4444`; execute `fetch('/api/state')` in console across all tabs; all return within 500 ms.
   - observed: With 3 tabs holding SSE streams, fetches in a 4th tab queue indefinitely.
2. Verify spectator isolation:
   - expected: Toggling spectator mode off stops the 1.5 s poll while preserving live SSE edit updates.
   - observed: Verified in `world-state.ts`; poll is off by default.
3. Slow subscriber recovery:
   - expected: If a client connection stutters and misses events, it automatically issues a resync fetch rather than displaying stale state.
   - observed: Currently dropped silently in `publish()`.

## Files

- `static/js/world-state.ts` - live edit SSE handling and state fetching
- `routes/events.py` - SSE subscriber generator and queue management
- `app.py` - server threading and transport options

## Browser UI and intended live verification

Intended UI home: multiple tabs open in browser; DevTools Network panel and Console.

Live steps when available:
1. Open six tabs to `http://localhost:4444`.
2. Inspect the Network panel in each tab to verify socket usage does not block new requests.
3. Trigger an edit in tab 1; inspect tabs 2-6 to verify the graph updates promptly without hanging.

## Refactor discipline (applies to this task)

1. **Dedup & reuse pass (mandatory).** Scan touched concerns for duplicate logic; consolidate onto one owner.
2. **Agent-experience & cleanliness (mandatory).** Keep modules under ~600 lines where seams allow; add one-line module docstrings.
3. **No behaviour change unless the card says so.** Extraction and consolidation only.
4. **One file/concern at a time**, verified with a targeted test selection.

## Reconnaissance (2026-10-31)
- Measured: Spectator polling (`startPolling`) is off by default; confirmed in `world-state.ts:305`. Persistent `/api/events` SSE stream in `world-state.ts:573` is unconditional. The 6-socket HTTP/1.1 origin limit causes multi-tab starvation.
- Verdict: STILL_VALID with corrected diagnosis. Status remains todo.
