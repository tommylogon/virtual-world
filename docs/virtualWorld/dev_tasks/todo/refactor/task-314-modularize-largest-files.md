# Task 314 — Modularize the largest files

**Priority**: Medium
**Status**: Todo

---

## Summary

Line-count audit of `virtual_world/` (2026-08-19, excluding `node_modules`, `.kilo`, venvs; 190 project files, 59,528 lines) identified the files that have outgrown single-file ergonomics. Several are already over ~1,000 lines or sit in the 700–900 range where extracting focused modules pays off. This task tracks which files need refactoring and modularization, per layer.

**Already done / in flight (do not duplicate):**
- `virtual_world_engine.py` — was ~4,600 lines, already slimmed to a facade (756 now). Covered by task-83.
- `agent-engine.js` — extraction done in task-218 (action-normalizer, response-parser, threat-detector, agent-state, plan-tracker). Watch its growth; currently 752.

## Backend — Python

| File | Lines | Why / suggested split |
|------|-------|-----------------------|
| `engine/trigger_system.py` | 1,994 | The biggest engine module. Split trigger *evaluation* vs *execution/effects* vs *scheduling/state*. |
| `engine/effects.py` | 1,400 | Effect catalogue is huge. Group by effect category (state, memory, lore, spawn, etc.). |
| `player.py` | 989 | Player class absorbing vitals/conditions/skills. Extract condition-instance handling and skill resolution. |
| `engine/traits.py` | 842 | Traits + events. Split definition catalog from event dispatch logic. |
| `routes/action.py` | 835 | Biggest route module. Extract the command handlers it dispatches to. |

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

## Verification

- All touched JS files pass `node --check`.
- Pytest suite stays green (959 passed baseline).