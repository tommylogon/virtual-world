# Task 320: Scry / Far-Sight Effect — see into other areas via items
**Status**: In Review — implemented 2026-08-31. New scry trigger effect: engine/scry.py builds a frozen distant-area view (rendered description + ambient light + exits) — the shared observer path is untouched (no agent-prompt drift). Registered in EFFECT_TYPES + effect handler + trigger-types.js + trigger editor (target area select + lead-in/fail messages).

**Audit 2026-08-31** — NOT IMPLEMENTED; no `scry` effect type; beyond_visibility is an adjacent-area glimpse only. Effort M: register effect, engine/scry.py + handler, parameterize shared describe_area with an is_scry guard so look/examine output is unchanged.


**Status**: todo
**Priority**: Medium
**Filed**: 2026-08-20
**Group**: Gameplay / Triggers

## Summary

Add a new trigger effect `scry` that resolves a *target area* (by name, by tag, or by
directional chain-follow) and returns that area's description to the player — full room
detail or a concise glimpse, configurable per item. Gives items like spyglasses, magic
farsight, and spirit-veils the ability to see into otherwise unreachable areas.

## Interaction model

Reuses the existing `use [item] on [target]` flow (`on_use_on`):

- `use spyglass on north` → chain-follow north up to N hops, only through open/see-through ways
- `use farsight on the graveyard` → resolve the area by name (works globally, no way needed)
- `use spirit veil on the ethereal realm` → same as farsight — the area just isn't physically
  connected; the item IS the access

No coordinate grid needed — "3 areas north" is a chain-follow across `area → way → area`
edges, hopping while the way's `cardinal` matches the asked direction. Separate from
task-99 (intra-room grids) and task-313 (relative facing map).

## Effect schema

Add `"scry"` to `EFFECT_TYPES` in `engine/trigger_system.py` and
`static/js/shared/trigger-types.js`.

| param | type | meaning |
|-------|------|---------|
| `area` | string | target area name (exact, then fuzzy/alias) |
| `tag` | string | find first area node carrying this tag |
| `direction` | string | cardinal to chain-follow (`north`, `south`, `ne`, `up`...) |
| `range` | int | max hops when chaining (default `1`) |
| `mode` | `glimpse` \| `full` | output detail (default `full`) |
| `open_only` | bool | only hop through `open`/`see_through` ways (default `true`; `false` = magic sees through walls) |
| `reveal_hidden` | bool | allow scrying into `hidden` areas (default `false`; magic can, mundane can't) |
| `message` | string | optional flavor prefix (template-rendered) |

Resolution precedence: `area` param → `tag` param → `direction` param → fallback to
`context["target_name"]` (the `on_use_on` target string), which itself tries area-name
match → cardinal word → tag match. Nothing resolves → narrative failure ("You can't make
out anything in that direction.").

## Implementation

1. **New module `engine/scry.py`** — all real logic:
   - `resolve_scry_target(params, context, game_state) -> Node | None` — area lookup by
     name/tag + direction chain-follow with a direction-alias map (`n`/`north`, `s`/`se`,
     `ne`, `up`/`down`, ...).
   - `build_glimpse(area_desc, area_node, observer) -> str` — one short block: light level,
     temperature line, noise/smell, "X, Y are here", notable items, open exit handles.
   - `build_full(area_desc, area_node, observer) -> str` — the full room description.
2. **`engine/effects.py`** — thin `handle_scry` delegate (~20 lines) calling the module
   (keeps the existing monolith from growing).
3. **`engine/area_description.py`** — refactor `get_area_description()` into a
   parameterized `describe_area(area_node, observer, is_scry=False)`; the current method
   delegates to it. Guards when `is_scry`: skip `apply_action("look")`,
   `register_first_meeting`, and spatial-position changes (scrying must not walk the
   player or trigger meetings). Lighting/temp/noise read from the *target* area's
   environment.
4. **Frontend** — `trigger-editor.js`: `scry` param block in `_buildEffectRowHtml` (mode
   select, area search-select `data-kind="areas"`, tag search-select `data-kind="tags"`,
   direction select, range number, open_only + reveal_hidden checkboxes, message input) +
   matching reads in `_collectData`.
5. **Agent prompt** — small addition to `static/js/agent/prompt-builder/system-prompt.js`:
   scry/sight items can be used with `use_on` on a direction or place name to see into it.

## Tests

- `tests/test_scry.py` (new): name resolution, tag resolution, direction chain-follow with
  range, open_only blocking, dark/empty target handling, glimpse vs full output shape.
- Extend `tests/test_trigger_system.py`: `scry` effect fires through `on_use_on` with
  target_name, and fails gracefully on unresolvable targets.

## Files affected

- `virtual_world/engine/scry.py` (new)
- `virtual_world/engine/effects.py`
- `virtual_world/engine/area_description.py`
- `virtual_world/engine/trigger_system.py`
- `virtual_world/static/js/shared/trigger-types.js`
- `virtual_world/static/js/shared/trigger-editor.js`
- `virtual_world/static/js/agent/prompt-builder/system-prompt.js`
- `virtual_world/tests/test_scry.py` (new)
- `virtual_world/tests/test_trigger_system.py`