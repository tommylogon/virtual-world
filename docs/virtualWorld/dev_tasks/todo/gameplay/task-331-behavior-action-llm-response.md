# Task-331: Behavior Action — LLM-Generated Response

**Status**: Todo
**Filed**: 2026-08-23

## Summary

Behavior-side twin of task-330: new behavior action type `llm_respond` (name TBD)
in `_execute_behavior_actions()` so simple NPCs (shopkeepers, merchants, mirrors)
can generate a spoken reply from instructions in the behavior's parameters, without
being full agents. Same browser-side-LLM architecture as task-330 — read that file
first for the constraint and sketch; this task is the executor + editor wiring on
the behavior path.

## Motivation (Tommy's examples)

- A shopkeeper whose haggling replies vary with what the customer actually said.
- Any `simple_npc` that should react to `on_speech_heard` with characterful
  dialogue beyond canned messages.

## Behavior-specific differences vs task-330

- Executor lives in `engine/npc_behaviors.py` `_execute_behavior_actions()`
  (flat-dict action shape: `{type: 'llm_respond', instructions, fallback_message}`,
  NOT `{type, params}` like trigger effects).
- Behaviors already carry conditions (`speech_matches`, `eq npc_state`, ...) and
  priority/interval — the same password-gate pattern applies, but the action can
  also be priority-stacked against other behaviors of the NPC.
- Editor surface is BOTH the behaviors form (`inspector/behaviors-view.js` action
  dropdown + param fields) and the behavior graph editor's Action node
  (`shared/trigger-graph.js` NODE_DEFS.action — add type + dynamic fields).
- Attribution question is simpler: the NPC speaks as itself via its normal speak
  pipeline.

## Proposed shape

```json
{
  "trigger": "on_speech_heard",
  "priority": 10,
  "conditions": {"type": "speech_matches", "value": "..."},
  "actions": [
    {"type": "llm_respond", "instructions": "You are a tired taco bell cashier.",
     "fallback_message": "Welcome to Taco Bell.", "max_words": 30}
  ]
}
```

## Files likely touched

- `engine/npc_behaviors.py` — action registration + pending-request enqueue
- `static/js/inspector/behaviors-view.js` — form dropdown + fields
- `static/js/shared/trigger-graph.js` — Action node type + fields
- Shared frontend pickup/generation with task-330 (build once, both consume)

## Open questions

Same list as task-330 (attribution, memory, cooldown) plus:
- Does an NPC mid-response block its other behaviors for a tick?
- Interaction with `npc_action_interval` — respond immediately or next tick?
