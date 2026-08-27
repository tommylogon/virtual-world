# Bug 31 — Save-load filename path traversal + two adjacent hardening fixes

**Status**: Todo — filed 2026-08-27 from code review. Local-only app, but these
are ten-minute fixes that remove process-level footguns entirely.

## Found

1. **Path traversal** — `routes/saveload.py:129-152`: `/api/load-game/<filename>`
   and its DELETE do `os.path.join(saves_dir, filename)` on the raw URL segment.
   `..%2F..%2F` style input escapes the saves dir (Windows backslash encoding
   too). Note `_save_game`/`_save_scenario` already sanitize correctly via
   `routes/helpers.py:228,250` — reuse exactly that helper on the load/delete
   side.
2. **Guaranteed-500 error path** — `routes/action_handlers.py:118-119`:
   `handle_get_state` catches an exception inside the handler then falls off
   the end returning None → Flask raises TypeError → 500 for a handled error.
   Return a proper error JSON + status.
3. **debug=True by default** — `app.py:134`: Werkzeug debugger exposed means
   arbitrary code execution for anything local that can reach :4444. Gate on
   env var (`VW_DEBUG=1`) or config default False.

MCP server trust model (localhost agent can delete saves etc.) is explicitly
OUT of scope here — local-trust is a documented decision.

## Fix sketch

- saveload: resolve final path, assert `Path(path).resolve().is_relative_to(
  Path(saves_dir).resolve())` before any file op (Python 3.9+: use os.path
  commonpath or parent check).
- get_state: return jsonify(error=...) status 500 after logging.
- app.run: debug flag read once at startup.

## Verify

pytest: request `/api/load-game/<encoded traversal>` → 400/404, no file access
outside saves dir (tmp_path test); `/api/state` failure injection returns JSON
not 500 TypeError; boot without env var shows debugger off in log line.
