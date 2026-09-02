# Patch Notes — 2026-09-02

## Summary
Massive working-tree sweep covering environment/time/weather engine work, trigger-graph UX overhaul, NPC behavior expansion, character data cleanup, library template additions, and Lyrie spell-item design.

## Engine

### Environment / Time / Weather
- **New module**: `engine/area_statuses.py` — area status definitions + persistence.
- **New module**: `engine/environment_propagation.py` — temperature/light propagation.
- **New effects**: `engine/effect_handlers/environment.py` — set/adjust environment handlers.
- **Tick integration**: `engine/tick_manager.py` — environment decay and propagation wired into the tick loop.
- **Serialization**: `engine/serialization.py` — area status + environment fields survive save/load.
- **Trigger validator**: `engine/trigger_validator.py` — new effect/condition catalog entries.

### NPC Behaviors
- **`engine/triggers/behaviors.py`** (+899 lines): added `add_memory`, `set_emotion`, `set_flag`, `hide_in`, `hide_behind`, `hide_under` action types; broadened behavior script vocabulary.

### Triggers / Conditions
- **`engine/triggers/condition_tree.py`** — condition tree evaluation expanded.
- **`engine/triggers/constants.py`** — new trigger/effect/condition constants.

### Player / Vitals
- **`player.py`** — vitals/condition/trait plumbing updates.

## Frontend

### Trigger Graph Editor
- **`static/js/shared/trigger-graph.js`** (+1097 lines): pan, zoom, grid, left-in/right-out sockets, YES/NO wire colors, field datalists, multi-type trigger support, compile-honesty badges, viewport persistence.
- **`static/js/shared/trigger-editor.js`** — form editor parity updates.
- **`static/js/shared/trigger-types.js`** — full 33-trigger / 42-effect catalog sync.
- **`static/js/inspector/behaviors-view.js`** — behavior action card rebuild, priority fixes, drag-to-connect rewrites.
- **`static/js/inspector/area-view.js`** — area inspector updates.
- **`static/js/inspector/agent-view.js`** — agent inspector tweaks.
- **`static/js/inspector/way-view.js`** — minor way-view fix.
- **`static/js/event-stream.js`** — event stream updates.
- **`static/js/shared/env-presets.js`** — new env preset UI module.

### Scenario / World
- **`data/scenarios/mansion.json`** — scenario schema migration (player/area/presence restructured).
- **`world_template.json`** — template updated to match new scenario schema.
- **`templates/index.html`** — minor template update.

## Library Items & Triggers

### New Templates
- `template_adjust_forecast.json`
- `template_apply_area_status.json`
- `template_clear_area_status.json`
- `template_forecast_override.json`
- `template_set_date.json`
- `template_set_time.json`
- `template_set_weather.json`
- `template_set_wet.json`

### New Triggers / Docs
- `data/library/triggers/untitled.json` — active trigger-authoring scratch file.
- `docs/Trigger-Condition-Effect-Cheat-Sheet.md` — authoritative trigger/condition/effect reference.

## Characters

### Lyrie
- **`data/library/characters/Lyrie.json`** — normalized equipment slots from string refs to full item objects; memory schema cleanup (`salience_override`, tick normalization, text formatting); vitals corrected (`Hunger 94→6`, `Thirst 94→6`); removed stray markdown artifact from `personality`.

### Whiskers
- **`data/library/characters/whiskers.json`** — character data updates.

## Tasks / Docs

### Reorganization
- Moved 10 environment task files from `docs/virtualWorld/dev_tasks/todo/environment/` → `done/environment/` or `cancelled/`.
- New task files:
  - `task-388-trigger-graph-editor-overhaul.md`
  - `task-389-npc-behavior-phase1-memory-emotion-hide.md`
  - `task-390-npc-behavior-phase2-sensory-faction-attack.md`
  - `task-391-lyrie-spell-items.md` — 15 Lyrie-themed spell items with full JSON specs and engine proposals.

### Reference Updates
- **`docs/virtualWorld/dev_tasks/dev_Task_sequence.md`** — bumped next-available task number to 392; logged 388–390.
- **`docs/virtualWorld/dev_tasks/inprogress/triggers/task-351-trigger-graph-editor.md`** — added Phase 1/2 follow-up notes for task-388.
- **`docs/Actions-Cheat-Sheet.md`** — expanded player/NPC verb reference.

## Tests / Tools
- `tests/test_area_statuses.py`
- `tools/test_trigger_graph_viewport.cjs`
- `tools/test_behavior_action_cards.cjs`
- `tools/_probe_parity.cjs`

## Net Change
- 37 files modified, ~20k insertions, ~16k deletions.
- No secrets or credentials detected in diff.
