---
type: feature
feature_id: 27
status: wired
section: in-game
tags: [status/wired, surface/in-game, system/characters]
---

# NPC behaviour

**What you can do:** Autonomous states: idle, forage, eat, flee, hide

## What it is

Simple NPCs are background characters the world runs for you. Mark a character
`simple_npc` and it acts on its own — wandering, drinking, hunting, fleeing,
defending a kill — with no LLM in the loop and no API cost. You author what it
does as a small list of behaviours, each one a trigger, a set of conditions and a
list of actions, evaluated every tick and on a few world events. A shadow-pelt
worg can patrol the treeline at night, drink at the river when its thirst drops,
hunt the forest when it is hungry, and run for its den when it is badly hurt —
all from its `behaviors[]` array.

## How it works

- [[NPC Behavior System]] — the deep guide: the `simple_npc` flag, the runner,
  the trigger / action / condition vocabulary, the state machine, the legacy
  `npc_behavior` fallback, and the hunt system.

A behaviour runs when its `trigger` matches the event the runner was called
with, its `interval` falls on this tick, and its `conditions` pass. The runner is
[[NPC Behavior System|`NPCBehaviorSystem.process_simple_npcs()`]], the action
executor is `_execute_behavior_actions()`, and conditions are evaluated by
`_evaluate_conditions()`.

Actions are one vocabulary, not two. A behaviour action that is not one of the
executor's own verbs (message, speak, go, set_npc_state, attack, …) is dispatched
to the engine's [[Triggers & Effects|effect registry]] (`engine/effects.py`
`HANDLERS`) — the same registry an item or way trigger runs. That is what lets a
behaviour use `adjust_vital`, `apply_condition`, `start_activity` and
`spawn_character` exactly as a trigger does, instead of silently doing nothing.
An action type in neither vocabulary is a quiet no-op.

The [[NL Editor]] Apply gate rejects a staged behaviour that would be dead — a
`trigger` in the node vocabulary (`on_take`, `on_night`, `on_enter`) instead of the
runner's, an unknown action type, or a known action with the wrong keys.

## Where it lives

- `engine/npc_behaviors.py` — `NPCBehaviorSystem.process_simple_npcs()`, the runner
- `engine/triggers/behaviors.py` — `_execute_behavior_actions()`, the action executor and effect-registry fallback
- `engine/triggers/condition_tree.py` — `_evaluate_conditions()`
- `engine/effects.py` — the `HANDLERS` effect registry a behaviour action falls back to
- `engine/nl_editor_validation.py` — `NPC_BEHAVIOUR_TRIGGERS` / `_behaviour_issues`, the vocabulary gate
- `data/library/characters/*.json` — authored `behaviors[]` (e.g. `Shadow-Pelt.json`)
- `static/js/shared/trigger-graph.js` — the behaviour graph editor
- `static/js/inspector/behaviors-view.js` — the Advanced → Behaviors form

## Connected

- Feature Map: [[Feature Map|row 27]] (In a game)
- Sibling features: [[look-around]], [[examine]], [[move]], [[open-close]], [[take-drop-give]], [[use-use-on]]
- All features: [[Features Overview]]

> [!note] Status — `wired`
> Recorded from [[Feature Map|the Feature Map]] on 2026-10-05. This page is an entry point; the
> deep documentation is linked under **How it works**.
