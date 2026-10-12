---
type: task
status: review
area: ui
priority: high
wiki: "[[agent-overview]]"
---

# task-817: Clicking an agent in the agent/initiative list shows the inspector only after a full state fetch

**Filed:** 2026-10-12
**Related:** 

## What

ui-controller.selectAgent awaits ApiClient.setActivePlayer(name) and THEN awaits worldState.fetch() before it calls VW.inspector.showAgent(name). On a large scenario the state payload is multi-megabyte (kraktooth is 2763 nodes; task-748 measured /api/state at 14.0 MB), so the inspector appears several seconds after the click. The player data needed to render the agent is already in worldState.players from the last fetch, so the inspector should open immediately and let setActivePlayer/fetch run in the background, refreshing the panel when the round-trip lands.

## Why

TODO

## How

ui-controller.selectAgent now opens the inspector immediately from the already-loaded worldState.players, sets config.controllingPlayer, focuses the node, and then fires setActivePlayer without awaiting any state fetch.

The explicit worldState.fetch() was DELETED: app.py's after_request broadcasts world_changed for every mutating /api/ call (app.py:210-221), so the /api/events SSE (world-state.ts connectLiveEdits) already refetches state on the very same write. The explicit fetch was a second full /api/state download per click. This also removes one of the two renderAll(state) passes per click (main.ts worldState.on('update') plus ui-controller appEvents.on('state:updated')).

Files: static/js/ui-controller.ts (selectAgent).

## Steps to verify

1. Load the kraktooth goblin camp scenario. Open DevTools -> Network, filter /api/state.
   - expected: the app is up and the network list is visible
   - observed: TODO
2. Click a character row in the Agents (or Initiative) list.
   - expected (fixed): the inspector opens with that character near-instantly, before any round-trip completes
   - observed: TODO
3. Watch the Network list across the click.
   - expected (fixed): the POST /api/players/active triggers AT MOST one /api/state refetch (the SSE one); the old explicit second fetch is gone
   - observed: TODO
4. Confirm the downstream effects still land.
   - expected: the active player and the graph camera focus on the clicked character a moment later
   - observed: TODO

## Acceptance

- [ ] TODO

## Files

- TODO
