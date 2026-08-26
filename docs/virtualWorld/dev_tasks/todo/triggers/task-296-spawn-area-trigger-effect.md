# Task-296: Trigger Effect to Spawn an Area

**Status:** In backlog — filed 2026-08-18.
**Source:** discussion — triggers can currently `spawn_item` but not areas.

## Goal

Add a `spawn_area` trigger effect so triggers and behaviours can create a whole new area
node (with environment) at runtime — e.g. an area that only exists after a ritual, or
when a character crosses a threshold.

## Notes / open questions

- Areas are graph nodes (`type="area"`) built with `description` + `environment`
  subdict (light/temperature/air/smell/noise) — see `movement.add_area()` /
  `serialization.py:331`.
- Library exists at `data/library/areas/*.json` — hydrate like `_hydrate_item`. May carry
  full area content (items, ways), so spawning may need to materialize child nodes +
  connection edges, not just the area node itself (scope decision).
- Options: spawn area into the world unconnected (reached only by teleport), or wire it
  with a `spawn_way`-style connection from the current area — needs a direction or a
  follow-up `spawn_way` effect.
- New area needs `area_from`/`area_to`/exits derivation so matching and the frontend see
  it; confirm whether spawn should regenerate `_build_exits_for_area`.
- Duplicate area id/name on spawn — error, no-op, or re-enter existing?

## Files

- `engine/effects.py` — add `handle_spawn_area` + `_hydrate_area`.
- `engine/trigger_system.py` — `EFFECT_TYPES` + execution branch.
- `engine/trigger_validator.py` — schema/validation for new params.
- `static/js/inspector/behaviors-view.js` + trigger editor — new effect entry + fields.
- `docs/virtualWorld/` trigger docs — list `spawn_area`.