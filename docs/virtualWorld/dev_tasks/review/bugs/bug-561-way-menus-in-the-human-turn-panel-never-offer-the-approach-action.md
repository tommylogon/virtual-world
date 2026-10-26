---
type: bug
status: review
area: bugs
priority: medium
wiki: "[[Gameplay/Turn Queue & Human Turns]]"
related: [task-783, task-352]
---

# bug-561: Way menus in the human turn panel never offer the Approach action

**Filed:** 2026-10-21
**Related:** task-783, task-352

<!-- deps:start -->
**Related:** [[task-783-approach-on-examine-and-take]], [[task-352-action-economy]]
<!-- deps:end -->

## What

The way context menu in the Human Turn Composer never offers `Approach`. The menu builder only pushes that entry when `atWayId !== way.way_id`, but the scene payload never populates either side of the comparison. `engine/scene_snapshot.py` publishes every way as `id` (the way node id) with no `way_id` key, and it builds `scene['you']` without an `at_way_id` key. The client reads `way.way_id` and `scene.you.at_way_id`, so both are `undefined` at runtime, the guard evaluates `undefined !== undefined`, and the Approach row is never pushed - for any way, including ways the character is not standing at.

Measured on 2026-10-21 (labs scenario, character `Jane two`, browser at http://localhost:4444):

- `GET /api/scene/Jane%20two` way entry keys: auto_close, desc, direction, id, known_blocked, known_locked, name, needs_force_known, prevent_close, requires, see_through, state, to, visible_in_direction. No `way_id`.
- the same payload's `you` keys: activity, carry_load, carrying, conditions, holding, known_abilities, name, recent_memories, vitals, wearing. No `at_way_id`.
- the character was standing at a way (`/api/state` players['Jane two'].at_way_id = `way_task_18__door_3`), so one side of the guard has a real value and the other side has none.
- the menu for `Task 18 - vent shaft 1` (a way the character is not at) held Examine and a disabled Go. The menu for `Task 18 - ventilation shaft to Task 18 - Room 3` held Examine, Go, Dash and Open. Neither held Approach.

## Why

`approach` is the minor-tier positioning verb that stops short of crossing a way. It is how a character reaches a door they are not standing at: `engine/action_tiers.py` records the decision that `open` is free only for something you are at, and reaching it costs `approach` (minor) or `go` (major). With no Approach row the panel can only spend a major action to reach or cross a way, so the minor slot is unusable from the panel and the cheaper positioning route is invisible.

The verb itself exists and is wired: `engine/action_verbs.py` declares `VerbSpec('approach', scope='way', cost_key='minor')` and the composer's typed verb list includes `approach`. So this is a payload field-name defect, not a missing mechanic. The client type `ScenePerson` already uses `id`; `SceneWay.way_id` is the odd one out, and `TurnSceneViewSceneYou.at_way_id` is declared as a required field the server never sends.

## How

Make the guard compare two real values:
1. In `engine/scene_snapshot.py`, populate `way_id: way_node.id` on each way entry and `at_way_id` on `scene["you"]` using `get_character_at_way(graph, player_node)`.
2. In `static/js/agent/turn-scene-view.ts`, update `buildWayMenu` to check `atWayId !== (way.way_id || way.id)` and update `SceneWay` / `TurnSceneViewSceneYou` types so `at_way_id` is optional and `id`/`way_id` are recognized.
3. Keep the guard semantics: omit Approach when standing at the way, offer `Approach <direction>` for other ways, drafting `approach <direction>`.

## Browser UI and intended live verification

Intended UI home: the Human Turn Composer panel - the 'Ways out' chip row in the scene view; click a way chip to open its context menu

Current availability: Verified in unit tests and python engine tests.

Live steps when available:
1. Open the Human Turn Composer for a character standing in a room with at least one way out and note the 'Ways out' chip row.
2. Click a way chip the character is NOT standing at and read the whole context menu: the menu must carry an 'Approach <direction>' row.
3. Click the way chip the character IS standing at and read the whole context menu: the Approach row must be absent there, because approaching the way you are at is a no-op.
4. Read `GET /api/scene/<character>`: each way entry must carry the way id the client compares against, and `you` must carry the character's current way id.

## Steps to verify

1. Open the Human Turn Composer for a character in a room with ways out and click a way the character is not at.
   - expected: the context menu offers an `Approach <direction>` row.
   - observed: Verified in `tools/unit/test_turn_scene_view.js` - `buildWayMenu` includes "Approach north" entry when standing at a different way.
2. Read the scene payload for the same character.
   - expected: the way entries carry the way id and `you` carries the character's current way id.
   - observed: Verified in `tests/test_scene_snapshot.py::test_scene_ways_and_you_carry_way_ids` - `way_id` matches `id` on all ways and `you.at_way_id` is populated.
3. Regression test: extend `tests/test_scene_snapshot.py` to assert the scene payload exposes both ids for a character standing at a way, and add a client-side test that the way menu offers Approach for a way that is not the current one and omits it for the current one.
   - expected: `python -m pytest tests/test_scene_snapshot.py` passes with the new assertions, and the client test passes.
   - observed: 15/15 tests pass in `tests/test_scene_snapshot.py`, and `tools/unit/test_turn_scene_view.js` passes in `run.cjs`.
4. Confirm the drafted verb: pick Approach from the menu and read the composer `do` row.
   - expected: the row reads `approach <direction>`, the minor-tier verb the engine dispatches.
   - observed: Verified in `tools/unit/test_turn_scene_view.js` and `turn-scene-view.ts:245` - drafts `{ action: 'approach', item: dirText || way.name }`.

## Acceptance

- [x] The scene payload and the client's scene interfaces agree on the way id and on the character's current way id, so the Approach guard compares two real values.
- [x] A way menu for a way the character is not standing at offers an Approach row; the way the character is at does not.
- [x] The Approach row drafts `approach <direction>`, the way-scoped minor verb declared in engine/action_verbs.py.
- [x] No other consumer of the scene payload still reads a way id key the payload does not publish.
- [x] A targeted regression test covers the payload keys and the menu contents.

## Files

- `engine/scene_snapshot.py`
- `static/js/agent/turn-scene-view.ts`
- `static/js/agent/turn-scene-view.js`
- `engine/action_verbs.py`
- `engine/character_spatial.py`
- `engine/player_manager.py`
- `engine/serialization.py`
- `tests/test_scene_snapshot.py`
- `tools/unit/test_turn_scene_view.js`
