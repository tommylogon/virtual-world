---
type: task
status: todo
area: refactor
priority: medium
---

# task-656: Remove verified dead definitions (unused functions and constants)

**Filed:** 2026-09-30
**Related:**

## Goal

Delete definitions that appear exactly once in the codebase (their own definition)
and are referenced nowhere. Each entry below is a static-analysis candidate with
its measured evidence, not a fix instruction: re-count before deleting.

## Method (how "not in use" was confirmed)

A repo-wide word-boundary scan (`\bNAME\b`) across every `.py`/`.js`/`.cjs`/`.mjs`/
`.html`/`.json`/`.md` file, excluding `.git`, `node_modules`, `.kilo`, venvs and
caches. An identifier is listed only when it occurs **exactly once** — at its own
`def`/`const` line — so no caller, test, template attribute, JSON key or doc
reference exists. Decorator-registered handlers (Flask `@app.route`, MCP
`@mcp.tool`) were filtered out because their name never repeats; the filter's one
miss, `routes/world_grid.py:83 world_scope_grid_boundary_override` (a two-line
decorator), was caught by hand and is **not** dead, so it is excluded.

Known limits: a name reached only through `getattr`/string dispatch in the Python
case, or `window[...]`/inline `on*` handlers in the JS case, would not be seen. The
scan included `.html` and `.json`, so no inline-handler reference exists for the JS
entries. Treat every line as a candidate to re-verify, not as proof.

## Python — module-level constants (14)

| File:line | Name | Note |
|---|---|---|
| `vital_rates.py:66` | `COLD_MODERATE_ENERGY` | |
| `vital_rates.py:67` | `COLD_MODERATE_HP` | |
| `graph.py:609` | `EDGE_REQUIRES` | value `"requires"` is live as a literal property key; only the constant is unused |
| `engine/grapple.py:29` | `GRAPPLE_SAVE_BASE_DC` | |
| `engine/trigger_validator.py:110` | `ITEM_NAME_KEYS` | |
| `engine/sound.py:63` | `NOISE_LEVELS` | |
| `engine/sound.py:64` | `WAY_BARRIER_SEE_THROUGH` | |
| `engine/traversal.py:31` | `ROUTINE` | |
| `engine/checks.py:63` | `SKILL_NAMES` | |
| `engine/fear.py:172` | `SOURCE_ABSENT` | value `"source_absent"` is *also* unreferenced — possible unwired mechanic, see below |
| `engine/traits.py:29` | `VITAL_MOD_PER_TICK` | value `"vital_mod_per_tick"` is also unreferenced |
| `engine/weather_forecast.py:88` | `WIND_SCALE` | |
| `engine/activities.py:118` | `_ALLOWED_WHILE_BLOCKED` | |
| `engine/character_appearance.py:238` | `_HAIR_LENGTHS` | |

## Python — functions/methods (25)

| File:line | Name |
|---|---|
| `virtual_world_engine.py:458` | `_get_light_int` |
| `virtual_world_engine.py:461` | `_get_ambient_light` |
| `virtual_world_engine.py:465` | `_can_see_in_dark` |
| `virtual_world_engine.py:497` | `_check_ghost_action` |
| `virtual_world_engine.py:337` | `_item_node_id` |
| `virtual_world_engine.py:663` | `_log_llm_call` |
| `engine/items/take_drop_actions.py:185` | `_clear_last_relation` |
| `engine/triggers/execution.py:24` | `_find_item_by_name` |
| `engine/zones.py:103` | `_gateway_scopes` |
| `engine/library_nodes.py:62` | `_get` |
| `engine/grapple.py:162` | `_grappled_targets` |
| `engine/item_actions.py:126` | `_sum_carry_weight` |
| `engine/world_grid.py:552` | `climate_at` |
| `engine/agent_memory.py:183` | `consolidation_summary` |
| `engine/conditions.py:38` | `effective_periodic` |
| `engine/conditions.py:46` | `effective_ends_on` |
| `engine/conditions.py:332` | `get_condition_instances` |
| `engine/conditions.py:356` | `get_active_conditions` |
| `graph.py:460` | `get_characters_by_tag` |
| `player.py:1113` | `get_memory_context_nl` |
| `player.py:628` | `update_emotion_from_outcome` |
| `engine/activities.py:274` | `has_activity` |
| `engine/body_parts.py:153` | `region_definition` |
| `engine/derive.py:258` | `relationship_block` |
| `engine/character_spatial.py:727` | `set_position_using_target` |

## JavaScript — DONE (removed 2026-09-30)

All 12 below were deleted. Each was re-checked for a **superseding live path**
rather than a bare name count; 10 had one; `explainAction` and the `dom-utils`
trio are "nothing calls it, no replacement named" and were removed on explicit
instruction (the "see if anything breaks" experiment).

| Removed | Was at | Superseding live path |
|---|---|---|
| `setActiveCharacter` | `static/js/main.js` | `ui-controller.selectAgent` / `ApiClient.setActivePlayer` |
| `openItemLibrary` | `static/js/main.js` | inline `itemLib.open()` in `templates/index.html` |
| `closeItemLibrary` | `static/js/main.js` | inline `itemLib.close()` |
| `nudgeCharacter` | `static/js/main.js` | `agent.nudge` (`agent-engine.js:1142`) via the inspector |
| `explainAction` | `static/js/main.js` | none found — see note below |
| `escapeForJsSingleQuoteString` | `static/js/shared/dom-utils.js` | none (only `escapeForHtmlAttribute` is used) |
| `sanitizeToDomId` | `static/js/shared/dom-utils.js` | none |
| `createDomElement` | `static/js/shared/dom-utils.js` | none |
| `diffModalTag` | `static/js/shared/diff-modal.js` | file renders via `window.Lit.unsafeHTML` |
| `initTooltip` | `static/js/ui-helpers.js` | direct `tippy()` + `data-tippy-content` |
| `_gridPayloadFor` | `static/js/graph/graph-background.js` | inline `ApiClient.getWorldGrid` + `_cacheGrid` |
| `_wireKeys` | `static/js/worldpainter/editor.js` | `state._keyDown` handler (editor.js) |

Gates after removal: `node tools/unit/run.cjs` (465 pass), `npm run lint`,
`npm run typecheck`, `python tools/js_module_index.py --check` — all clean.

**Open question from this pass:** `#why-panel` (`templates/index.html:1156`) had
`explainAction` as its only writer, so it is now unwritten. If the "why this
action" panel is meant to work, that is an unwired feature and belongs in its own
task; if it was abandoned, delete the element and its CSS rule.

## Note: two values, not just names, are unreferenced

`SOURCE_ABSENT = "source_absent"` (`engine/fear.py:172`) and
`VITAL_MOD_PER_TICK = "vital_mod_per_tick"` (`engine/traits.py:29`) are the only
occurrences of their string values in code. That is the AGENTS.md
"never infer runtime behaviour from existence" pattern: a named mechanic (a fear
`ends_on` reason; a per-tick trait vital modifier) that may be intended but is
wired to nothing. Before deleting these, decide whether the *mechanism* is meant to
exist; if so, this is an engine/authoring gap and belongs in its own task, not in a
dead-code sweep. Deleting just the constant is safe either way.

## Acceptance

- [ ] For every listed entry, re-run `rg -w "<name>"` across the repo (excluding
  `.git`/`node_modules`/`.kilo`) and confirm exactly **one** hit — the definition.
  Drop any entry whose count has grown (something now uses it).
- [ ] Remove only the unused definitions; make no other behaviour change.
- [ ] Confirm no `__all__`, `from x import *`, or module attribute exposes a removed
  name (none is expected from the counts, but check on removal).
- [ ] Python suite green — compare FAILED **names** against the pre-change run, not
  counts.
- [ ] For the JS entries: `node tools/unit/run.cjs`, `npm run lint` and
  `npm run typecheck` green.
- [ ] Record in the task which entries were dropped on re-verification and why.
