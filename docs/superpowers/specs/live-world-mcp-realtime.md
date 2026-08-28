# Live World Editing via MCP + Real-Time GUI Updates

## Yes — the repo already ships an MCP server

mcp_server.py is a FastMCP servers that proxies an agent's tool calls to the
running VirtualWorld Flask app (http://localhost:4444). It is registered as a
regular MCP server in Claude Code / opencode / kilo / any MCP client. It exposes
~60 tools covering:

- Core commands: look, go, take, drop, use, examine, inventory, stats, speak.
- World state: get_state, graph nodes/edges, players, pathfind, game time.
- Player management: create/set-active/update/delete/kill/move/import.
- Memory system: get/set/add/update/delete/clear player memories.
- Graph CRUD: create/update/rename/delete nodes and edges.
- High-level builders: build_area, build_item, connect_areas, reconnect_way,
  move_item, build_item_from_library.
- Library registries: items, traits, characters.
- World lore, save/load/reset, settings, turn management.

So an external agent ALREADY can live-edit, connect, and update the loaded world:

    connect_areas('Elm Street', 'Oak Street', 'east', 'west')
    build_item_from_library('Oak Street', 'monster_energy_drink')
    update_player('Miki', current_area='Elm Street')
    add_player_memory('Jake', 'Met Miki at the corner.', importance=7)

To run it, register mcp_server.py in your MCP client config (see the design spec
docs/superpowers/specs/2026-07-18-virtual-world-mcp-server-design.md).

## The gap this work closes: real-time visibility

The GUI's event stream was client-generated from agent actions; edits made by an
external agent through the API would not appear until a manual refresh. We added
a server->client push channel + a broadcast hook so edits (yours OR an agent's)
show up live:

### 1. World event hub — engine/world_events.py

A process-global fan-out bus (WorldEventHub) with a rolling buffer. publish()
boradcasts a dict to every subscriber; subscribe()/unsubscribe() manage SSE
clients; recent(n) returns the last n events for snapshot reads.

### 2. Broadcast hook — app.py after_request

For every mutating /api/ call (POST/PATCH/DELETE/PUT) the server publishes:

    { type: 'world_changed', method, path, editor }

editor comes from the X-WV-Editor request header, which the MCP server sets to
its VIRTUAL_WORLD_EDITOR env value (default 'mcp-agent'). That's how you see
WHO made the edit.

### 3. SSE endpoint — routes/events.py

GET /api/events streams the live events (text/event-stream).
GET /api/events/recent?count=50 returns the buffer as a snapshot.

### 4. GUI live handler — static/js/event-stream.js

On load it opens EventSource('/api/events'); when a world_changed arrives it
refetches world state (worldState.fetch(), debounced) and logs a thin 'World
edited by <editor> — POST /api/...' line when a non-local editor acted.

### 5. MCP tools — mcp_server.py

- get_recent_world_events(count): snapshot of recent edit events.
- resource virtualworld://events: readable snapshot of the same buffer.

## Result

1. Point an agent at the MCP server and set its editor name:
   env VIRTUAL_WORLD_EDITOR=deepseek-agent  (or your agent's name).
2. The agent creates a room in Elm Street, places Miki, wires the Monster
   Crossing trigger. Every API call broadcasts a world_changed event.
3. The GUI you're watching refetches state in real time and the stream shows
   'World edited by deepseek-agent — POST /api/build/item'.

## Note on the running server

The Python changes (app.py hook, routes/events.py, engine/world_events.py,
library_ops.py per-entry apply) require a Flask restart to take effect. The
Static JS changes (diff-modal.js, library-browser.js, template-sync.js,
event-stream.js, api.js, agent-view.js) load fresh on a browser refresh.

## Tests

tests/test_events_and_perentry.py covers the hub, the broadcast hook, the
recent endpoint, and the per-entry refresh apply. Run with:

    python -m pytest tests/test_events_and_perentry.py -q
