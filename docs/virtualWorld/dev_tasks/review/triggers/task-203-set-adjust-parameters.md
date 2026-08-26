---
group: Trigger System
---

# Set/Adjust Parameters via Trigger (All Node Types)

**Filed**: 2026-08-10
**Priority**: Medium
**Status**: In Review — implemented 2026-08-10. `set_parameter`/`adjust_parameter` effects target any node (item/way/area/character) via `_resolve_effect_target`. `{param:<key>}` now resolves in item/way/area descriptions at examine + room prompt (guarded so MagicMock fixtures fall back to raw). Frontend effect list + editor inputs added. 844 tests pass.

---

## Problem

There's no trigger effect to mutate the `parameters` key-value dict on a node, even though `{param:<key>}` already renders from it. Today you'd hand-edit node data to change a door's indicator from red→green→yellow, which defeats the whole trigger system.

Also, `{param:<key>}` context is only populated for the *triggering item* — not for ways, areas, or characters when they're described/examined.

## Goal

A `set_parameter` / `adjust_parameter` trigger effect that works on **any** node type (characters, items, ways, areas), plus rendering wiring so `{param:<key>}` resolves for ways/areas/characters in their descriptions and examine output.

## Example

A circular door whose description reads `... under the number is a {param:light} light.`
- `on_unlock` trigger → `set_parameter {key: light, value: green}`
- `on_lock` trigger → `set_parameter {key: light, value: red}`
- `on_open` / `on_close` → `yellow` / `green`

## Design

- **Effect handler(s)** in `engine/effects.py`:
  - `handle_set_parameter` — `params: {key, value, node_id|self|target_tag}`; uses `_resolve_effect_target()` (already resolves any node) and writes into `target_node.properties.setdefault("parameters", {})`.
  - `handle_adjust_parameter` — same but numeric delta (`params: {key, delta}`), for counters.
- **Targeting**: reuse `_resolve_effect_target` so `node_id`, `self`, and `target_tag` fan-out all work — items, ways, areas, characters all covered.
- **Rendering wiring** so `{param:key}` resolves for a described/examined node regardless of its type:
  - wherever a way/area/character description is rendered into template context, seed `item_params` (or a `node_params`) from that node's `properties.parameters`.
- **Register** the new effect types in the trigger editor's effect list (inspector.js + item-library.js, grouped appropriately).
- **Tests** in `tests/test_effects.py` / `tests/test_trigger_system.py`.

## Files

- `engine/effects.py` — add `handle_set_parameter`, `handle_adjust_parameter`
- `engine/trigger_system.py` — seed node params into render context for described/examined way/area/character
- `engine/area_description.py` — pass node parameters into description template context
- `static/js/inspector.js` — add new effect types to the editor list
- `static/js/item-library.js` — add new effect types to `EFFECT_TYPES`
- `tests/test_effects.py`, `tests/test_trigger_system.py` — tests
