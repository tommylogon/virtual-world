# Modularize app.py into Route Modules

**Filed**: 2026-07-16
**Priority**: Medium
**Status**: Done — fully executed (app.py is a slim register_* dispatcher over routes/ modules; audited 2026-08-03)

---

## Summary

Split `app.py` (1560 lines, 69 routes in one `register_routes()` function) into per-domain modules under a `routes/` package. Each module exports a `register_<domain>_routes(app)` function that the main `register_routes()` calls.

**Approach: sub-register functions (not Blueprints).**
This keeps every route handler unchanged — no need to rewrite `app.world` → `current_app.world` or handle conditional registration differently. Each route function still captures `app` by closure, exactly as it does today. The split is purely organizational.

---

## Module Structure

```
app.py                         # create_app() + imports + top-level register_routes() dispatcher
routes/
  __init__.py                  # empty or just metadata
  pages.py                     # 4 routes: favicon, /, /GLM, /deepseek
  action.py                    # 3 routes: /api/state, /api/action (260-line dispatcher), /api/turn/apply
  registry.py                  # 7 routes: items CRUD, traits, characters, import, build-item-from-library
                              #   + helpers: handle_registry_post, load_registry, save_registry
  players.py                   # 7 routes: players CRUD, move, speak, update, import-character
  graph.py                     # 12 routes: nodes/edges CRUD, reconnect, rename, build-room/item/connect, update-edge
  save_load.py                 # 3 routes: /api/save, /api/load, /api/reset
                              #   + helper: _save_world_template
  settings.py                  # 7 routes: ghost_mode GET/POST, narration GET/POST/context/inject, time_per_tick GET/POST
  debug.py                     # 2 routes: /api/debug/save_log, /api/debug/state
  llm.py                       # 2 routes: /api/llm/tools, /api/llm/call (with enabled/disabled variants)
  world.py                     # 4 routes: world lore CRUD
  memories.py                  # 6 routes: per-player memory CRUD
```

Also:
- `routes/helpers.py` — shared helpers: `load_registry`, `save_registry`, `_save_world_template`

---

## File Sizes After Split

| File | Lines (est.) | Routes |
|---|---|---|
| `app.py` | ~90 | 0 (just factory) |
| `routes/helpers.py` | ~40 | — |
| `routes/pages.py` | ~20 | 4 |
| `routes/action.py` | ~280 | 3 |
| `routes/registry.py` | ~140 | 7 |
| `routes/players.py` | ~180 | 7 |
| `routes/graph.py` | ~370 | 12 |
| `routes/save_load.py` | ~60 | 3 |
| `routes/settings.py` | ~130 | 7 |
| `routes/debug.py` | ~40 | 2 |
| `routes/llm.py` | ~60 | 2 (x2 variants) |
| `routes/world.py` | ~60 | 4 |
| `routes/memories.py` | ~80 | 6 |

---

## Migration Steps

### Step 1: Create package structure
- Create `routes/` directory
- Create `routes/helpers.py`

### Step 2: Extract helpers to `routes/helpers.py`
- Move `_save_world_template(world)` from global scope (line 1527)
- Move `load_registry(data_dir, filename)` (line 1538)
- Move `save_registry(data_dir, filename, data)` (line 1549)
- Update imports in all route modules

### Step 3: Create each route module
For each domain:
1. Create `routes/<domain>.py`
2. Copy the relevant `@app.route(...)` functions from `register_routes()`
3. Wrap them in `def register_<domain>_routes(app):`
4. Import needed helpers from `routes.helpers`

### Step 4: Update `register_routes()` in `app.py`
Replace the entire function body with calls to each sub-register:

```python
def register_routes(app):
    """Dispatch to per-domain route modules."""
    from routes.pages import register_pages_routes
    from routes.action import register_action_routes
    from routes.registry import register_registry_routes
    from routes.players import register_players_routes
    from routes.graph import register_graph_routes
    from routes.save_load import register_save_load_routes
    from routes.settings import register_settings_routes
    from routes.debug import register_debug_routes
    from routes.llm import register_llm_routes
    from routes.world import register_world_routes
    from routes.memories import register_memories_routes

    register_pages_routes(app)
    register_action_routes(app)
    register_registry_routes(app)
    register_players_routes(app)
    register_graph_routes(app)
    register_save_load_routes(app)
    register_settings_routes(app)
    register_debug_routes(app)
    register_llm_routes(app)
    register_world_routes(app)
    register_memories_routes(app)
```

### Step 5: Handle conditional LLM route registration
The LLM routes have an `if app.config["LLM_ENABLED"]:` guard. In the module, move the conditional inside `register_llm_routes(app)` and register both variants conditionally just like current code.

### Step 6: Update imports
- `app.py`: remove imports only used by routes (items, areas, etc.) — but keep if used in `create_app()`
- Each route module: import what it needs (Flask, engine classes, helpers)

### Step 7: Verify
- Run `python app.py` and check startup logs for errors
- Test core routes: load page, get state, take action, etc.
- Run the Playwright test script if available (`node tools/test_ways.cjs`)
- Check Flask auto-reload picks up changes in `routes/*.py` files

---

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Circular imports | Each module only imports Flask + helpers + domain classes. No module imports another route module. The `register_routes()` dispatcher is the only integration point. |
| Flask debug reload misses new files | Flask monitors imported modules by default. Since `register_routes()` imports from `routes.*`, any change in those files triggers reload. |
| Nested helper `handle_registry_post` uses `request` closure | It's defined inside `register_routes()` and captures `request` by closure. Moving it to module scope works because Flask's `request` is a proxy that works outside route context. |
| `take_action` captures `add_output` closure | `add_output` is defined inside the route function. Moving the function to a module doesn't affect this — closures work the same way. |
| Dead code `_build_narration_context_for_current_area` | It's defined but never called. Leave it in the original location (move with action.py) or remove. Recommend moving as-is to avoid behavioral changes. |

---

## Future Options

Once the file is modularized, each module can be individually:
- Upgraded to Flask Blueprints for URL prefixing
- Unit-tested independently with mocked `app`
- Refactored (e.g., splitting `take_action` into a command-pattern dispatcher)
