# Task-295: Trigger Effect to Spawn a Character

**Status:** Done — implemented 2026-08-18.

## Goal

Add a `spawn_character` trigger effect so triggers and behaviours can introduce an
NPC/character node at runtime (and optionally a live agent) — e.g. a quest NPC arrives
at an area, or a summon/summoned-beast appears.

## What was implemented

- `engine/effects.py` — new `_hydrate_character()` (reads `data/library/characters/<id>.json`,
  builds a `Player` from the library dict) and `handle_spawn_character()` (hydrates, applies
  overrides, registers via `game_state.add_player()`, places in area, preserves active player).
- `engine/trigger_system.py` — added `"spawn_character"` to `EFFECT_TYPES`.
- `engine/trigger_validator.py` — added `CHARACTER_EFFECTS`, `_character_exists()`,
  `_library_character_exists()`, and validation branch.
- `static/js/shared/trigger-types.js` — added `spawn_character` to `EFFECT_TYPES`.
- `static/js/shared/trigger-editor.js` — param fields (character_id, display_name, area, message)
  in both the HTML template and the read-back/save logic.
- `static/js/inspector/behaviors-view.js` — added `spawn_character` to `BEHAVIOR_ACTION_TYPES`,
  form fields, and read-back logic.
- `static/js/shared/trigger-graph.js` — added `spawn_character` to trigger-mode effect dropdown
  and behavior-mode action dropdown, with dynamic param fields.
- `tests/test_trigger_system.py` — two new tests: `test_spawn_character_from_library`
  (hydrates Jake Halloway, places in area) and `test_spawn_character_unknown_id` (no-op).

## Params

- `character_id` — library file name (e.g. `jake`)
- `display_name` / `name` — optional name override
- `description` — optional description override
- `area` — optional area name override (blank = triggering actor's current area)
- `message` — optional narration, supports `{character_name}`

## Testing

- [x] `python -m pytest tests/ -q -k "not mcp and not emote"` → 976 passed, 1 skipped
- [x] `node --check` on all touched JS files — clean
- [x] `py_compile` on all touched Python — clean
- [x] Unit tests: `test_spawn_character_from_library` + `test_spawn_character_unknown_id` pass