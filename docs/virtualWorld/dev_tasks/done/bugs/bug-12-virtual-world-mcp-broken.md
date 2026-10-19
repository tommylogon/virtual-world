# Bug 12: Virtual World MCP server broken (wrong path, dead routes, bad payloads)

**Filed**: 2026-08-05
**Priority**: High
**Status**: Fixed

## Summary

The `virtual-world` MCP server (FastMCP proxy to the Flask API on `:4444`) was broken and
unusable. Three separate issues:

1. The server was not registered in the opencode config at all, and the kilo config pointed
   at a non-existent Python interpreter — so the MCP process never even spawned.
2. `reconnect_way` called a dead route (`/api/graph/door/reconnect`), renamed to
   `/api/graph/way/reconnect` backend-side but never updated in the MCP server.
3. `set_player_memories` and `set_world_lore` sent bare lists as the JSON body, but the
   routes expect a wrapper object — both 4xx/5xx'd at runtime.

## Root Cause

1. **Config**: `.kilo/kilo.jsonc` used `C:\ProgramData\miniconda3\python.exe` which does not
   exist (real interpreter is `C:\Users\TommySlaatbraaten\miniconda3\python.exe`). The
   project's opencode config (`.opencode/opencode.jsonc`) had no `virtual-world` entry at all,
   so the server was never loaded in opencode sessions.
2. **Route**: `routes/graph.py:451` registers `/api/graph/way/reconnect` (renamed in
   task-58), but `mcp_server.py:452` still called the old `/api/graph/door/reconnect` → 404.
3. **Payloads**: `routes/memories.py:28` reads `data.get("memories")` and
   `routes/world_lore.py:23-25` reads `data.get("lore")` — both require an object body.
   `mcp_server.py:306` and `:528` sent the raw list instead → AttributeError/400.

## Files

- `mcp_server.py:452` — `reconnect_way` → `/api/graph/way/reconnect`
- `mcp_server.py:306` — `set_player_memories` → `{"memories": memories}`
- `mcp_server.py:528` — `set_world_lore` → `{"lore": entries}`
- `.opencode/opencode.jsonc` — added `virtual-world` MCP server entry
- `.kilo/kilo.jsonc:7` — fixed Python path

## Verification

- `mcp_server` imports cleanly with `C:\Users\TommySlaatbraaten\miniconda3\python.exe`
- Both config files parse as valid JSON
- All 47 MCP endpoint calls matched against registered Flask routes (0 missing)
- Flask server health OK on `:4444`

## Note

MCP servers load at editor startup — a session restart is required for the new config to
take effect.
