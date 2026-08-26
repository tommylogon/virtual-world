# Task 314 — Modularize the largest files

**Priority**: Medium
**Status**: In Progress (wave 1 landed 2026-08-26: trigger_system, effects, routes quartet. Wave 2 in flight: player/traits redo, facade trim, runner-ups, JS trio, test split.)

---

## Summary

Line-count audit of `virtual_world/` (2026-08-19, excluding `node_modules`, `.kilo`, venvs; 190 project files, 59,528 lines) identified the files that have outgrown single-file ergonomics. Several are already over ~1,000 lines or sit in the 700–900 range where extracting focused modules pays off. This task tracks which files need refactoring and modularization, per layer.

**Already done / in flight (do not duplicate):**
- `virtual_world_engine.py` — was ~4,600 lines, already slimmed to a facade (756 now). Covered by task-83.
- `agent-engine.js` — extraction done in task-218 (action-normalizer, response-parser, threat-detector, agent-state, plan-tracker). Watch its growth; currently 752.

## Backend — Python

| File | Lines | Why / suggested split |
|------|-------|-----------------------|
| `engine/trigger_system.py` | DONE 2026-08-26: 2,181 → **73** | Split into `engine/triggers/` package of mixins (constants, effect_resolution, evaluation, condition_tree, execution, behaviors, ui, testing). See Wave 1 below. |
| `engine/effects.py` | DONE 2026-08-26: 1,655 → **510** | Handler groups live in `engine/effect_handlers/<category>.py`, each exporting a HANDLERS dict; effects.py composes the registry and keeps shared helpers + handle_* wrappers. |
| `player.py` | 1,147 | Player class absorbing vitals/conditions/skills. Extract condition-instance handling and skill resolution. (First attempt died before touching files; redo queued.) |
| `engine/traits.py` | 934 | Traits + events. Split definition catalog from event dispatch logic. (Queued with player.py.) |
| `routes/action.py` | DONE 2026-08-26: 935 → **46** | Bodies moved whole to `routes/action_handlers.py` (838, still over 600, second-pass candidate). |

### DONE: `engine/item_actions.py` (2026-08-23)

1,892 → 135 lines. Verb-family split into a new `engine/items/` package of
mixin modules; `ItemActions` composes them and keeps the shared context
(graph/matching/triggers/equipment/ghosts/world) + capacity plumbing.
Public API re-exported unchanged (`normalize_item_actions`, carry-weight fns,
`BASE_CARRY_CAPACITY`, `INVERSE_ACTIONS`, `AmbiguousItemError`), so routes,
serialization and effects imports needed no changes.

| Module | Lines | What moved |
|--------|-------|------------|
| `items/take_drop_actions.py` | 475 | `take_item`, `drop_item`, `drop_held_items`, discovery + last-relation bookkeeping, `_auto_select_identical`. |
| `items/use_actions.py` | 390 | `use_item`, `use_item_on`, `_descriptive_target_failure`. |
| `items/examine_actions.py` | 366 | `get_item_desc`, `_describe_flavor_target`, `get_inventory`, `_render_node_desc`. |
| `items/place_actions.py` | 163 | `put_item_in_container`, `place_item`, `_clear_placement_edges`. |
| `items/transfer_actions.py` | 127 | `give_item`, `steal_item`. |
| `items/carry_weight.py` | 75 | Pure weight math: `sum_carry_weight`, `get_carry_load_ratio`, container recursion. |
| `items/consume_actions.py` | 64 | `eat_item`, `drink_item`, `_consume_item`. |
| `items/errors.py` | 6 | `AmbiguousItemError`. |

Also fixed the lying constructor while in there: `ItemActions(..., self, self)`
used to pass the world twice into params named `action_costs` and
`npc_behaviors`; it is now a single honest `world=` param (`self.world`),
internal reads renamed off `.game_state`/`.npc_behaviors`, test fixtures updated.
Test patch target moved: `patch("engine.items.transfer_actions.random.randint")`
for steal rolls.

**Runner-up**: `engine/movement.py` (639), `engine/serialization.py` (587), `engine/matching.py` (601), `engine/equipment.py` (536), `engine/tick_manager.py` (533).

## Frontend — JavaScript

| File | Lines | Why / suggested split |
|------|-------|-----------------------|
| `static/js/shared/trigger-editor.js` | 1,571 | Editor is a monolith. Split rendering vs validation vs serialization (related to task-216 inspector work). |
| `static/js/inspector/agent-view.js` | 1,478 | Largest inspector view. Break into sub-views (memory, plans, vitals, relationships). |
| `static/js/shared/trigger-graph.js` | 1,399 | Graph rendering of triggers. Split layout/rendering from node/edge editing. |
| `static/js/graph/network-manager.js` | 1,175 | Core graph module. Split persistence/sync from rendering from event handling. |
| `static/js/item-library.js` | 1,105 | Library browser monolith. Split list/editor/import from rendering. |
| `static/js/inspector/way-view.js` | 923 | Way editor view. Extract the trigger/connection editing it embeds. |
| `static/js/main.js` | 895 | App bootstrap + glue. Extract init wiring and cross-module event subscriptions. |
| `static/js/library-browser.js` | 824 | Overlaps item-library.js — decide ownership and merge/split. |
| `static/js/inspector/item-view.js` | 790 | Item editor view. Extract equip-slot / container / trigger editing sections. |

**Runner-up**: `static/js/event-stream.js` (775), `static/js/inspector/behaviors-view.js` (575), `static/js/graph-manager.js` (550), `static/js/ui-controller.js` (531).

## Tests

- `tests/test_trigger_system.py` (2,253) is the largest test file by far. Split by subsystem (evaluation, effects, conditions, scheduling) so failures isolate cleanly.

## Approach

1. **One file at a time** — pick the smallest "runner-up" first as a proof-of-pattern, then move up.
2. **No behavior change** in this pass — extraction only, keep public imports/API stable.
3. Verify each extraction: backend `python -m pytest tests/ -q -k "not mcp and not emote"`, frontend `node --check` on every touched JS file.
4. Follow the same shape as task-218 (module per concern, table of what moved, lines saved).

## Files changed

### Frontend — `static/js/graph/network-manager.js`

Progress as of 2026-08-20 (1,496 → 843 lines; −653):

| Extracted module | Lines | What moved |
|------------------|-------|-------------|
| **`graph/projector.js`** | 163 | `computeVisibleNodeIds()`, `edgeVisible()`, `applyVisibility()`, `_viewState()` — the pure visibility projection (unit-testable, no vis.js). |
| **`graph/overlays.js`** | 272 | The 5 ambient overlays (light/heat/sound/trigger/cardinal) + color maps + change-cached `computeAmbientLight()` (kills the old O(E·N) re-walk). |
| **`graph/tooltips.js`** | 224 | `buildTooltip()`, `buildTooltipHtml()`, `_escHtml()`, `findGraphEdge()`, `bindEdgeHoverTooltips()`, `attachNodeTooltips()`. |
| **`graph/focus.js`**  | 116 | Search focus: `applyFilter()`, `settleSearch()`, `_fitToSearchMatches()`, `_kickClusterPhysics()`, `filterNodes()` (debounced). |

`network-manager.js` keeps builders (buildNodeConfig/buildLegendHTML), tag-library
functions, reveal/hide state, init/load/shell — and re-exports each moved member as a
thin `@deprecated` delegate so every existing call site (`GraphNetwork.*`) keeps
working. `templates/index.html` gained `<script>` tags for projector/overlays/tooltips/
focus before `network-manager.js`.

Verified after each extraction: `node --check` on all touched JS; `test_inspector.cjs`
all pass; `test_ui.cjs` 24/25 (the 1 failure is the pre-existing `togglePhysics:
document is not defined` harness issue, unrelated).

Still on the table for a later pass (increasingly entangled with the shell): the
tag-library panel, legend HTML, and `buildNodeConfig` styling.

## Wave 1 landed (2026-08-26)

Four parallel extractions, verified per step and at the end: **1130 passed, 1 skipped**
(a rare second skip, `test_body_parts.py:215` "attack missed", is a d20-miss self-skip, not a regression).

| Original | Before → after | Extracted |
|----------|----------------|-----------|
| `engine/trigger_system.py` | 2,181 → **73** | `engine/triggers/`: constants (74), effect_resolution (49), evaluation (358), condition_tree (504), execution (491), behaviors (199), ui (138), testing (189). TriggerSystem stays defined in the original, inherits the mixins; tests patch instance attributes so seams survive. |
| `engine/effects.py` | 1,655 → **510** | `engine/effect_handlers/`: conditions (134), environment (67), equipment (186), memory (107), misc (89), properties (141), spawn (183), state (71), teleport (55), vitals (186). Each exports HANDLERS; effects.py merges dicts in original dispatch order, retains private self-based helpers and public handle_* wrappers. Zero mock.patch targets existed on this module. |
| `routes/action.py` | 935 → **46** | `routes/action_handlers.py` (838). |
| `routes/library_routes.py` | 958 → **85** | `routes/library_ops.py` (857). `_content_ref_id`, `_content_relation`, `graph_add_relation_edge`, `RELATION_EDGE_TYPES` re-exported (test_relation_edges imports them). |
| `routes/graph.py` | 730 → **88** | `routes/graph_ops.py` (655). |
| `routes/players.py` | 650 → **83** | `routes/player_ops.py` (603). |

Routes: blueprints, URL rules, endpoint names, status codes, response shapes untouched;
no url_for usage anywhere, no mock.patch against these route modules.

Second-pass candidates created by wave 1: `action_handlers.py` (838), `library_ops.py` (857),
`graph_ops.py` (655), `condition_tree.py` (504 ok), plus noted duplicates
(`test_trigger` template-context copy in triggers/testing.py vs execution.py).

## Wave 2 interrupted (2026-08-26, ~01:00)

Session cut short (parallel agents hit output limits mid-run; several died BEFORE editing,
a few half-landed). Current tree is GREEN: pytest 1130 passed, 1 skipped; node --check
passes on every touched JS file. State per target:

| Target | State |
|--------|-------|
| `player.py` | PARTIAL: condition-instance machinery extracted to `engine/player_conditions.py`, Player methods delegate, suite green. Skill resolution extraction NOT started. |
| `engine/traits.py` | NOT started (retry agent died pre-edit, twice). |
| `virtual_world_engine.py` (998, regrown facade) | NOT started. |
| `engine/trigger_validator.py` (742) | NOT started. |
| `engine/movement.py`, `serialization.py`, `matching.py` | NOT started. |
| `engine/equipment.py`, `tick_manager.py` | NOT started. |
| `static/js/inspector/agent-view.js` (1736) | ORPHAN: `static/js/inspector/agent/agent-header.js` (149 lines) exists but the host was never rewired and there is no script tag. Either finish the split next session or delete the dir. |
| `static/js/inspector/way-view.js` (1082) | Code split COMPLETE: `way-view-triggers.js` + `way-view-connections.js` expose `window.InspectorWayViewTriggers` / `window.InspectorWayViewConnections`; hosts and modules all pass node --check. BUT see urgent fix below. |
| `trigger-editor.js`, `trigger-graph.js`, `item-library.js` + `library-browser.js`, `main.js` | NOT started. |
| `tests/test_trigger_system.py` split | NOT started. |

### URGENT, first action next session (2 lines)

`templates/index.html` loads `way-view.js` (line 995) but not the two new modules, so
opening the way inspector's triggers/connections sections throws on an undefined
namespace. Add beside that line:

```
<script src="/static/js/inspector/way-view-triggers.js"></script>
<script src="/static/js/inspector/way-view-connections.js"></script>
```

### Resume notes

- Regression gate unchanged: `python -m pytest tests/ -q -k "not mcp and not emote"`
  must read exactly 1130 passed, 1 skipped (rare extra skip = `test_body_parts.py:215`
  d20-miss self-skip; rerun once to confirm if seen). JS gate: `node --check` per touched file.
- Re-dispatch dead scopes ONE agent per scope with strict short-report instructions;
  two agents died writing long reports, cap finals around 40 lines.
- Second-pass splits still owed from wave 1: `routes/action_handlers.py` (838),
  `routes/library_ops.py` (857), `routes/graph_ops.py` (655). Also `triggers/testing.py`
  duplicates the template-context block from `execution.py`.
- Perf smells collected from wave reports, none fixed yet: `_find_item_by_name` /
  `_find_target_node` full-graph scans inside trigger loops; effects spawn/give/destroy
  O(n^2) edge-scan patterns; `handle_schedule_trigger` linear node lookup;
  `graph_ops` multi-pass edge iteration per request; `player_ops` vital GETs recompute
  equipment aggregation + area temperature walk; `test_trigger` duplicated context block.
- Endpoint latency profiling still pending: server was down; the flat ~2s curl readings
  were Windows connect-refused retries, not real numbers. Re-measure after restart.

## Verification

- All touched JS files pass `node --check`.
- Pytest suite stays green (959 passed baseline).