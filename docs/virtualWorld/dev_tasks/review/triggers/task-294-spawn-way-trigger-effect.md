# Task-294: Trigger Effect to Spawn a Way

**Status**: In Review — implemented 2026-08-30 (engine/effect_handlers/ways.py spawn_way + registry + EFFECT_TYPES + editor label; mirrors connect_areas topology incl. one_way; idempotent; tests in tests/test_trigger_effect_ways.py)
**Source:** discussion â€” triggers can currently `spawn_item` but not ways.

## Goal

Add a `spawn_way` trigger effect so triggers (and behaviours) can materialize a way
node at runtime â€” e.g. a hidden passage opens when a condition is met, or an item's
`on_use` collapses/creates a corridor.

## Notes / open questions

- Ways are the only node type with **connection edges** (area â†’ way with a `direction`,
  way â†’ area). Spawning one is not a single `EDGE_IN` â€” it needs wire-up like
  `serialization.py` (way node + `area_from`/`area_to` props + bidirectional
  `EDGE_CONNECTION` edges with `_connection_edge_props`), or reuse the
  `movement.connect_areas()` path.
- Params sketch: `way_id`, `area_from` / `area_to` (or direction + target), `state`
  (open/locked/hidden), `description`, `direction`, `one_way`.
- Library exists at `data/library/ways/*.json` (name, description, current_state,
  see_through, auto_close, tags) â€” hydrate from it like `_hydrate_item` does for items.
- Should a `spawn_way` also re-run exit/connection derivation (`_build_exits_for_area`)
  so the frontend exits list + matching immediately sees the new way?
- Undo/idempotency: spawning an already-existing way id â€” no-op, or reconnect?
- Options: generate the new area on the fly vs require an existing area id.

## Files

- `engine/effects.py` â€” add `handle_spawn_way` + `_hydrate_way` (mirror `_hydrate_item`).
- `engine/trigger_system.py` â€” `EFFECT_TYPES` + execution branch (or route through the
  shared effects path like `spawn_item`).
- `engine/trigger_validator.py` â€” schema/validation for the new params.
- `static/js/inspector/behaviors-view.js` + trigger editor â€” new effect entry + fields.
- `docs/virtualWorld/` trigger docs â€” list `spawn_way` as a supported effect type.
