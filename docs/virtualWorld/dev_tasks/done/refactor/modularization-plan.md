# Modularization & Clean Code Plan (COMPLETED)

Branch: `refactor/modularization-plan`

All modules extracted. 22 Python engine modules, 13 route modules, 52 JS modules.
Bugs found and fixed during this phase are documented in the extraction bug-fix commits.

**Current status**: 100/104 tests pass (4 remaining are backend server restart needed for trigger_system routing fixes).

---

## Python Side

### `virtual_world_engine.py` (~5000 lines → ~20 files)

The biggest file in the project. Currently one `VirtualWorld` class with 22+ functional areas.

**Splitting approach:** Bottom-up. Pure functions first, then graph helpers, then mechanical subsystems, then game logic, then orchestration.

| Phase | Module | What goes in it | Est. lines |
|-------|--------|----------------|------------|
| 1 | `engine/node_ids.py` | `_area_node_id()`, `_way_node_id()`, `_item_node_id()`, `_player_node_id()` | 40 |
| 1 | `engine/skills.py` | `roll_dice()`, `skill_check()`, `_render_template()` | 120 |
| 1 | `engine/logging_events.py` | `add_log_entry()`, `record_turn_event()`, `clear_turn_events()`, `get_turn_events_for_area()`, `broadcast_speech()`, `save_run_log()` | 120 |
| 2 | `engine/matching.py` | `_match_exit_direction()`, `_match_item_name()`, `_find_item_node()` | 140 |
| 2 | `engine/location.py` | `_get_current_area_id()`, `_set_player_area()`, `_is_item_reachable()` | 40 |
| 2 | `engine/lighting.py` | `_light_to_level()`, `_get_light_int()`, `_get_ambient_light()`, `_can_see_in_dark()` | 100 |
| 2 | `engine/legacy_compat.py` | `areas` property, `current_area` property, `player` property, `_build_exits_for_area()` | 80 |
| 3 | `engine/action_costs.py` | `apply_action()`, `action_calculation()` | 50 |
| 3 | `engine/player_manager.py` | `add_player()`, `set_active_player()`, `get_players_in_area()`, `get_all_dead_players()`, etc. | 50 |
| 3 | `engine/area_manager.py` | `add_area()`, `set_current_area()`, `connect_areas()`, `_set_exit_state()` | 60 |
| 3 | `engine/agent_memory.py` | `plan()`, `remember()`, `recall_all()`, `recall()` | 60 |
| 3 | `engine/ghost.py` | `_check_ghost_action()`, `_spawn_body_item()` | 120 |
| 4 | `engine/trigger_system.py` | `_execute_triggers()`, `TRIGGER_TYPES`, `EFFECT_TYPES`, condition evaluation | 380 |
| 4 | `engine/effects.py` | ALL effect type handlers (damage, heal, spawn, set_state, teleport, etc.) | 400 |
| 4 | `engine/toggleable_items.py` | `toggle_item_status()`, `_remove_item_effect()`, `_sync_active_effects()` | 80 |
| 4 | `engine/equipment.py` | `equip_item()`, `unequip_item()`, `get_equipment_narrative()`, `_update_equipment_description()` | 300 |
| 5 | `engine/combat.py` | `_player_attack()`, `_find_weapon_in_inventory()`, `is_slasher()` | 80 |
| 5 | `engine/description.py` | `get_area_description()`, `get_area_items()`, `get_item_desc()` | 340 |
| 5 | `engine/movement.py` | `move_to_area()`, `toggle_way()`, `toggle_way_by_id()` | 250 |
| 5 | `engine/item_actions.py` | `take_item()`, `drop_item()`, `get_inventory()`, `eat_item()`, `drink_item()`, `use_item()`, `use_item_on()`, `_consume_item()` | 450 |
| 5 | `engine/npc_behaviors.py` | `process_simple_npcs()`, `hunt()`, `_get_path_to_area()` | 200 |
| 6 | `engine/tick_cycle.py` | `tick_turn()`, `tick()`, `advance_clock()`, `get_current_time()`, `rest()` | 300 |
| 6 | `engine/narration.py` | `process_emote()`, `get_narration_context_for_area()`, `inject_narration()`, `fumble_around()` | 200 |
| 6 | `engine/serialization.py` | `to_dict()`, `to_scenario_dict()`, `load_from_dict()`, legacy conversion | 400 |
| — | `engine/engine.py` | Slim VirtualWorld class, imports and delegates to all modules | 100 |

**Key decisions:**
- **Approach A: Dependency Injection.** Each module receives only the shared state it needs (graph, players dict, etc.), not the entire engine.
- **Event bus for cross-cutting concerns.** Movement → NPC behavior (player enters room triggers NPC reaction) goes through an event bus, not direct calls.
- **No file > 500 lines** after extraction.

### `app.py` (~2200 lines → `routes/` package)

| Module | Routes | Est. lines |
|--------|--------|-----------|
| `routes/helpers.py` | — (shared utilities) | 50 |
| `routes/pages.py` | 4 (HTML pages) | 20 |
| `routes/action.py` | 4 (state, action, emote, turn) | 320 |
| `routes/players.py` | 12 (player CRUD, speak, kill, import) | 350 |
| `routes/graph.py` | 14 (nodes/edges CRUD, legacy build) | 390 |
| `routes/saveload.py` | 8 (save game, load, reset) | 150 |
| `routes/registry.py` | 8 (items, traits, characters registry) | 160 |
| `routes/settings.py` | 10 (ghost, narration, time, embed) | 160 |
| `routes/llm.py` | 4 (tools, call + disabled variants) | 60 |
| `routes/world.py` | 5 (lore CRUD) | 60 |
| `routes/memories.py` | 6 (memory CRUD) | 80 |
| `routes/debug.py` | 2 | 30 |

**Pattern:** Each module exports a `register_<domain>_routes(app)` function. `app.py` calls each one.

---

## JavaScript Side

### Shared utilities (new files)

| File | What | Used by |
|------|------|---------|
| `shared/dom-utils.js` | `escHtml()`, `escJsStr()` — unified HTML/JS escaping | All files |
| `shared/json-utils.js` | `parseJSONFromResponse()` — code fence stripping + JSON parsing | agent-engine, item-library, main |
| `shared/trigger-editor.js` | Overlay modal + effects/conditions grid | inspector, item-library (replaces 400 duplicated lines) |
| `shared/ai-generator.js` | System message builder + LLM call + form population | item-library, main (replaces 200 duplicated lines) |

### `inspector.js` breakdown (~3500 lines → 11 files)

| File | Responsibility |
|------|---------------|
| `inspector/index.js` | Thin router (showNode/showAgent → dispatches to views) |
| `inspector/agent-view.js` | Stats, skills, vitals, bio, personality, export/import |
| `inspector/room-view.js` | Area description, environment, exits, room event log |
| `inspector/item-view.js` | Item metadata, actions grid, properties, tags |
| `inspector/door-view.js` | Way state, descriptions, cardinals, auto-close |
| `inspector/paperdoll-view.js` | Equipment grid, stacking popup, equip picker |
| `inspector/inventory-view.js` | Carried items grid, add-item picker |
| `inspector/behaviors-view.js` | NPC behavior editor |
| `inspector/memory-view.js` | Memory CRUD |
| `inspector/lore-view.js` | World lore editor |
| `inspector/helpers.js` | Shared HTML builders, gravity control, tag helpers |

### `agent-engine.js` breakdown (~1250 lines → 5 files)

| File | Responsibility |
|------|---------------|
| `agent/engine.js` | Orchestrator: step(), start/stop, turn queue |
| `agent/prompt-builder.js` | ALL `_build*Context()` and `_build*Prompt()` methods (~600 lines) |
| `agent/response-parser.js` | `_parseObservation()`, `_parseReaction()`, etc. + shared JSON extraction |
| `agent/plan-manager.js` | `generatePlan()`, plan state tracking |
| `agent/agent-memory.js` | `reflect()`, entity index, store memory |

### `graph-manager.js` breakdown (~1205 lines → 5 files)

| File | Responsibility |
|------|---------------|
| `graph/manager.js` | vis.js network lifecycle, init, load, click handlers |
| `graph/context-menu.js` | Right-click menu HTML + action dispatch |
| `graph/layout-engine.js` | BFS cardinal layout algorithm (shared with map view) |
| `graph/map-view.js` | SVG map rendering |
| `graph/tree-view.js` | Outline view + world tree + clipboard |

### `main.js` cleanup (~1654 lines)

| Change | Impact |
|--------|--------|
| Remove duplicate `generateWithAI` → use shared `ai-generator.js` | -200 lines |
| Move create modal forms to `ui/create-modal.js` | -220 lines |
| Move legacy global wrappers to event delegation | -500 lines |
| Move settings UI to `ui-controller.js` | -150 lines |
| Keep bootstrap/init in `main.js` | ~120 lines final |

---

## Variable Renaming (All Files)

The following cryptic names appear across the codebase and will be renamed:

| Old | New | Files affected |
|-----|-----|---------------|
| `p` (player) | `player` | engine.py (200+), app.py, agent-engine.js |
| `n` (node) | `node` | engine.py (200+), inspector.js, graph-manager.js |
| `e` (edge/event) | `edge` or `event` | engine.py (100+), app.py |
| `d` (direction) | `direction` | engine.py (50+) |
| `c` (condition) | `condition` | engine.py (30+) |
| `k` (key) | `key` | engine.py (20+) |
| `v` (value) | `value` | engine.py (30+) |
| `o` (output) | `output` | engine.py (50+) |
| `tn` | `target_node` | engine.py |
| `tp` | `trigger_properties` | engine.py |
| `rn` | `area_node` | engine.py |
| `ep` | `effect_params` | engine.py |
| `gs` | `grid_slot` | inspector.js |
| `esc` (function) | `escHtml` or `escJsStr` | All JS files |
| `escName` | `escaped_name` | inspector.js |
| `escId` | `escaped_id` | inspector.js |

**One-time pass:** Rename only when modifying a file for another reason (boy-scout rule from AGENTS.md).

---

## Package Suggestions

### None required for Python.

The modularization is pure file-splitting with imports. No new dependencies. The existing `graph.py`, `player.py`, `room.py`, `item.py` already follow a clean data-model separation.

### None required for JavaScript.

The existing architecture (ES6 modules via `<script>` tags, no bundler) works fine for this scale. The files are small enough individually that HTTP/1.1 connection overhead isn't a concern. A build step (Webpack/Vite) would add complexity without solving any real problem.

**What would help (already loaded via CDN):**
- Tippy.js (tooltips) — ✅ already loaded
- Notyf (toasts) — ✅ already loaded  
- Choices.js (multi-select) — ✅ already loaded

**What I'd avoid:**
- React/Vue/Svelte — would require a full rewrite of the HTML-in-JS pattern
- TypeScript — no build step, adds compilation complexity. JSDoc comments could provide typing without a compiler.
- Webpack/Vite — not needed at this scale, adds a bundler requirement
