---
id: 174
title: Fire Mechanic — Create Flame spawns a Heat-Source Ember
status: done
priority: high
created: 2026-08-02
updated: 2026-08-03
tags: [environment, fire, heat, triggers, gameplay]
---

# Task 174: Fire Mechanic — Create Flame spawns a Heat-Source Ember (F6)

**Status**: Done — verified 2026-08-03. All five root causes fixed; this was the "F6" fix referenced by task-170.

## Goal

Make Lyrie's `Create Flame` spell actually work: casting it spawns a fire/ember item in the room that radiates heat for ~3 turns then burns out. Previously: `use Create Flame` → "Something happens." — no ember, no warmth.

## Root Causes (all fixed)

1. `use_item` called `_execute_triggers` without `game_state` → `spawn_item` silently no-op'd.
2. Create Flame trigger's `message` effect had empty params → default "Something happens.".
3. `everflame_ember` spawned `unlit`; heat only applied for `lit`/`on` states.
4. Tick loop only depleted carried/equipped lit items — a dropped ember never burned down.
5. `handle_message` with empty message emitted the vague "Something happens.".

## Changes (all verified in current code)

### 1. `engine/item_actions.py` — pass `game_state` to trigger execution ✅
`_exec_triggers` helper (`item_actions.py:28-42`) threads the world as `game_state` into every `_execute_triggers` call — `spawn_item`/`consume_item`/`set_environment` effects now work everywhere.

### 2. Rewire Create Flame `on_use` trigger (`world_template.json`) ✅
`use Create Flame` spawns `everflame_ember` **lit** (`"current_state": "lit"`, world_template.json:4028) and emits: *"A small flame flickers in your palm and settles into a glowing ember at your feet. It radiates warmth and will burn for about 15 minutes."* (see also task-170 Issue 4).

### 3. `data/library/items/everflame_ember.json` ✅
`uses: 3` (≈3 ticks × 5 min = ~15 min), `current_state: "lit"`, `light_level: "dim"`, `target_temperature: 30`, `heating_rate: 0.5`, `heat_source`/`fire` tags, `on_tick` (decrement uses) + `on_depleted` ("gutters and dies.") triggers. Description states it burns ~15 minutes.

### 4. `engine/tick_manager.py` — burn down area-lit items ✅
Dedicated "Area lit items burn down" loop (`tick_manager.py:330-361`): scans each area's `EDGE_IN` items with state `lit`/`on`, skips `uses == -1` (permanent sources like the stove), runs `on_tick` (with `game_state`), and on depletion sets `unlit`, fires `on_depleted`, and removes the node.

### 5. `engine/effects.py` — empty message → no output ✅
`handle_message` returns `[]` for empty messages (effects.py:81-85) instead of "Something happens.".

## Verification

- Live simulation (throwaway script): spawn ember → `on_tick` 3→2→1→0 → `on_depleted` returns "The everflame ember gutters and dies." → tick_manager marks unlit and removes the node.
- Backend suite: `python -m pytest tests/ -q -k "not mcp and not emote"` → 431 passed, 1 skipped.
- Doc: `docs/virtualWorld/Environment/Temperature System.md` documents the heat-source mechanic (heat_source tag, environment_propagation.py, tick_manager).

## Files Modified

- `engine/item_actions.py`
- `engine/tick_manager.py`
- `engine/effects.py`
- `data/scenarios/world_template.json` (Create Flame trigger + ember spawn)
- `data/library/items/everflame_ember.json`
- `docs/virtualWorld/Environment/Temperature System.md`

## Related

- task-170 (fire spawn & content fixes) — follow-up gaps this left behind; all landed.
- `docs/virtualWorld/dev_tasks/done/environment/task-12-sound_propagation.md` — same graph-scan propagation pattern.
