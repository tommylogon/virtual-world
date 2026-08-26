---
group: Tech Debt & Testing
wiki: "[[World Building/Item System]]"
---

# Task 177: Consolidate `hidden` Boolean into `current_state`

## Status

**Filed**: 2026-08-04
**Priority**: High
**Status**: In Review — implementation complete (all engine reads use `current_state`, legacy `hidden` retained only as input-migration shim), full pytest suite passes (488 passed, 1 skipped). Moved from inprogress 2026-08-05.

## Bug

Item visibility is the last straggler of the boolean→`current_state` migration. Doors were migrated in `c40eb1f5` ("hidden is now a door state") and item `locked` in `3d2c0f83` (task-97). Item `hidden` still lives as a separate boolean `properties["hidden"]`, and the reads are **inconsistent**:

| File | Default | Effect |
|------|---------|--------|
| `area_description.py:97,199` | `False` | visible unless explicitly hidden |
| `narration.py:403` | `False` | visible unless explicitly hidden |
| `item_actions.py:439,466` | `True` | **invisible unless explicitly unhidden** |
| `matching.py:124,140,402,409` | `True` | **invisible unless explicitly unhidden** |
| `player_manager.py:153` | `True` | **invisible unless explicitly unhidden** |

So an item with no `hidden` property is listed in room descriptions but is **unmatchable / unexaminable**. That asymmetry is a silent footgun.

Worse: the UI already offers `hidden`/`visible` as valid item *states* (`item-library.js:714`, `trigger-editor.js:153`, `library-browser.js:227`), so setting an item's state to `hidden` in the editor does **nothing** — the engine only reads the boolean for item visibility.

## Canonical Rule

An item is **visible** iff `current_state != "hidden"`. Default (missing/any other state) = visible. This kills the default-asymmetry bug.

## Changes

### Engine (backend)

- `engine/item_actions.py:210` — examine un-hide: `cn.properties["hidden"] = False` → `cn.properties["current_state"] = "normal"` (only if it was `"hidden"`)
- `engine/item_actions.py:439,466` — `not properties.get("hidden", True)` → `properties.get("current_state") != "hidden"`
- `engine/matching.py:124,140,402,409` — same swap
- `engine/player_manager.py:153` — same swap
- `engine/area_description.py:97,199` — same swap (default flips to visible, matches intent)
- `engine/narration.py:403` — same swap
- `engine/effects.py:492` `handle_set_hidden` — set `current_state = "hidden"` / `"normal"` instead of the boolean; `handle_set_state` already covers it
- `engine/effects.py:186,196` — spawn from library: map `hidden` → `current_state`
- `engine/serialization.py:328,383,482` — on read: `"hidden": True` → `"current_state": "hidden"`; on write: emit `current_state` instead of boolean
- `routes/graph.py:247`, `routes/library_routes.py:148,217`, `routes/items_registry.py:86,207` — `hidden` field → `current_state`

### Frontend JS

- `world-state.js:191,225` — `!node.properties?.hidden` → `node.properties?.current_state !== 'hidden'`
- `prompt-builder.js:546,550,553,718` — same swap
- `inspector/item-view.js:253` — replace "Hidden" checkbox with state dropdown (or wire to `current_state`)
- `item-library.js:1129,1245,1270,1351` — `hidden` field → `current_state`
- `main.js:315,484` — fix item format hints (`"hidden":false` → `"current_state":"normal"`)

### Data migration

Script to convert every item node with `"hidden": true` → `"current_state": "hidden"` (and `"hidden": false` → drop the key or set `"current_state": "normal"`) in:
- `data/scenarios/labs.json`
- `data/autosave.json`
- `data/scenarios/world_template.json`
- `data/library/items/*.json`

### Tests

- Update `tests/test_spatial_edges.py` and `TestSpatialRelationExamine` (they exercise `hidden` heavily)
- New test: item with no `hidden`/`current_state` key is visible AND matchable/examinable (guards the asymmetry fix)
- New test: examine a container un-hides contents by setting `current_state` off `"hidden"`
- Verify full suite: `python -m pytest tests/ -q -k "not mcp and not emote"`

## Notes

- Glass-case case: a visible (`current_state != "hidden"`) item inside a container shows up in the initial prompt via the container loop (`world-state.js:225`). Correct.
- Hidden lives on the content node, state on the container node — no collision (closed toy_box with hidden contents is fine).

## Verification

- [x] No `properties.get("hidden"` / `properties["hidden"]` remains in any `.py` under `engine/`, `routes/`
- [x] No `"hidden":` remains in item nodes under `data/` (exits may keep `current_state: "hidden"`)
- [x] No `.hidden` / `properties?.hidden` remains in `static/js/` for items
- [x] Full pytest suite passes (455 passed, 1 skipped)
- [x] Manual: Task 4 — Ink Pen/Painting/rug/toy_box visible in agent prompt; toy_soldiers only after examining toy_box (toy_soldiers set `current_state: "hidden"` in labs.json + autosave.json)
