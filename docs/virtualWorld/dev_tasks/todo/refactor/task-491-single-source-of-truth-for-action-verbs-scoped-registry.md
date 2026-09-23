---
type: task
status: todo
area: refactor
priority: medium
---

# task-491: Single source of truth for action verbs (scoped registry)

**Filed:** 2026-09-23
**Related:** task-299

## Goal

Consolidate the action-verb definitions that currently drift across engine/triggers/ui.py:_get_available_actions, static/js/agent/action-normalizer.js VALID_VERBS/MATURE_VERBS, static/js/agent/prompt-builder/contextual-actions.js BRACKET_ORDER, static/js/agent/prompt-builder/system-prompt.js prose, routes/action_handlers.py dispatch, and engine/autocomplete.py. One scoped registry (id, aliases, scope command/item/meta/social/movement/mature, target_schema, cost_key, mature_gate, bracket_order) that the dispatcher, UI buttons, agent normalizer, bracket builder, prompt prose and autocomplete all read. Generate the LLM verb list instead of hand-maintaining prose; add a drift guard test.

## Acceptance

- A verb is declared in exactly one place; the dispatcher (`routes/action_handlers.py`), `engine/triggers/ui.py`, `action-normalizer.js`, `contextual-actions.js`, `system-prompt.js` and `engine/autocomplete.py` all derive their sets from the registry.
- The registry carries scope + metadata (`aliases`, `scope`, `target_schema`, `cost_key`, `mature_gate`, `bracket_order`).
- The LLM verb list is generated from the registry; mature verbs are gated by the same flag as today's `MATURE_VERBS`.
- A drift guard test fails when a surface declares a verb the registry doesn't (or omits one its scope should expose).
- Behaviour is unchanged: every verb the command surface accepts today still resolves.
