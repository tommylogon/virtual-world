---
type: task
status: todo
area: refactor
priority: high
---

# task-715: Live-update transport will not scale to multiple clients (SSE per tab + 1.5s full-state poll)

**Filed:** 2026-10-05
**Related:** task-387 (NL editor), task-384 (world_changed push)

## What

Replace the per-tab SSE stream plus unconditional 1.5 s `/api/state` poll with a
single multiplexed transport and an incremental delta, so N clients on one host
work today and online multiplayer does not deadlock later.

## Why this matters now

Found by accident while verifying the NL-editor commit fix (task-715 was found
while applying changes): with **three** tabs of the app open, every `fetch()`
from a page hangs indefinitely. It is not a slow server — `curl` to the same
endpoints answers in ~110 ms throughout.

Measured 2026-10-05 on `master` at 8cba8f2f, port 4444, 1280x720 viewport:

| Tabs open | Browser-side sockets to :4444 | `fetch('/api/state')` from a page |
|---|---|---|
| 1 | 4 | 444 ms (ok) |
| 2 | 5 | 458 ms (ok) |
| 3 | 7 | **> 30 s (hangs)** |

`curl http://localhost:4444/api/state` = 108 ms and
`curl -X POST /api/graph/batch` = 847 ms **while the pages were hung**, so the
server was healthy the entire time. Closing one tab restored the fetch
immediately (7 sockets -> 5, 458 ms).

Sampling `netstat` twice, 6 s apart, showed **all** sockets present in both
samples — there are no transient poll sockets. That is the tell: these are
long-lived streams, not the 1.5 s poll.

## Diagnosis

Two independent ceilings, both of which bind before "many players" does.

1. **Browser-side (what was actually observed).** `world-state.js` opens one
   `EventSource('/api/events')` per tab (`connectLiveEdits`), and
   `world-state.js:96` starts a 1.5 s `/api/state` poll per tab. A tab only
   needs one poll socket transiently, but the SSE socket is held open forever.
   Browsers cap ~6 concurrent connections **per origin**, shared across every
   tab on that origin. Three tabs' permanent SSE streams plus their polls cross
   that budget, so new requests queue indefinitely — they never fail, they just
   never get a socket. A reload does not clear it; closing a tab does.

2. **Server-side (matters more for multiplayer).** `routes/events.py` runs one
   **blocking** generator per subscriber and never returns. Flask's dev server
   is `threaded=True` (`app.py:237`), so each subscriber pins a thread for the
   life of the tab, parked in `q.get(timeout=15)`. There is no cap in
   `WorldEventHub` — `hub.subscribers_count()` exists but nothing enforces a
   limit. N concurrent players = N pinned threads, and this dev server is not a
   production server. `publish()` also fans out to every subscriber's
   `queue.Queue(maxsize=256)`; a client that cannot keep up gets
   `queue.Full` swallowed by the bare `except` in `publish`, so it **silently
   misses events** rather than falling back to a refetch.

## What is NOT the cause

- Not the Flask dev server being single-threaded — `curl` stayed at ~110 ms
  while three pages were hung, so threads were available and being served.
- Not `/api/state` being slow to produce — same evidence.
- Not the NL-editor change (that is what surfaced this, but `Apply` only calls
  `afterApply` after the batch resolves).

## Acceptance

- [ ] Opening 6+ tabs of the app on one host keeps `fetch('/api/state')`
      responsive. Verify by socket count + a timed in-page fetch, and record the
      numbers the way the table above does.
- [ ] `hub.subscribers_count()` has a documented cap, and exceeding it produces
      an explicit error instead of a pinned thread.
- [ ] A slow subscriber (`queue.Full` in `publish`) triggers a resync signal, not
      a silently dropped event.
- [ ] One transport per tab rather than one stream per concern: the `EditFeed`
      second-`EventSource` fallback (`ui/edit-feed.ts:123`) is dead in the normal
      path because `appEvents` exists — confirm whether it is still reachable.
- [ ] Decided and written down: for online multiplayer, is SSE the right
      transport at all, or does this need WebSockets plus an authoritative
      server-authoritative tick? This is the part that is genuinely undecided.
- [ ] `/api/state` is not the unit of change. At 2.48 MB per poll per client,
      the bandwidth alone caps the player count. Decide the delta format before
      building more on top of the full-state payload.

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: open the app in six browser tabs on one host; use the Network panel to count live connections and the DevTools console to time `fetch('/api/state')` while another tab edits the world.

Current availability: the card reports a per-tab SSE stream plus an unconditional 1.5-second full-state poll. A multiplexed transport and incremental delta are planned; no multi-client scalability improvement is claimed.

Live steps when available:
1. Open six tabs to the same scenario and record socket/EventSource counts and a timed in-page `/api/state` fetch in each tab.
   - expected: there is one shared transport per tab rather than separate streams per concern; every timed state fetch remains responsive under the six-tab load.
2. Edit a node from one tab and inspect the other tabs' visible graph and network activity.
   - expected: each tab receives the incremental change without a second full-state poll or duplicate event stream.
3. Simulate a slow subscriber until its queue fills; inspect the affected tab and transport events.
   - expected: it receives an explicit resync signal and catches up instead of silently missing the update.
4. Exceed the documented subscriber cap in a scratch run.
   - expected: the app reports a clear connection-limit error and remains responsive; it does not pin a thread or starve existing tabs.

This section is not a claim that the transport replacement is implemented today.
