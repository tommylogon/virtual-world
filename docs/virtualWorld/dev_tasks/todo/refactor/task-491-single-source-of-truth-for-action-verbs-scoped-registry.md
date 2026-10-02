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

## Reconnaissance (2026-10-02) — NOT started, enumerated

The surface counts, so the registry can be built without guessing:

- `static/js/agent/action-normalizer.js:20-31` `VALID_VERBS`: **79 entries, 78
  unique** (`grab` duplicated); `:35` `MATURE_VERBS`: **8** (`kiss, caress,
  lick, suck, bite, pinch, blow, tickle`). `:49` also has a local `MOVE_VERBS`
  (5). `normalizeStructuredAction` (`:83-151`) is the mapping switch — it
  consumes `use_on`, `consume`, `quaff` which are **not** in `VALID_VERBS`, so
  aliases are needed (`use_on`→use+target, `consume`→eat, `quaff`→drink).
- `static/js/agent/prompt-builder/contextual-actions.js:32` `BRACKET_ORDER`:
  **13** (`take, use, use_on, open, close, eat, drink, read, wear, remove,
  toggle, drop, examine`) — the `bracket_order` metadata seed.
- `static/js/agent/prompt-builder/system-prompt.js`: hand-written verb prose
  (must be generated from the registry's scope lists).
- `engine/autocomplete.py:141-228`: verb **groups** in an if/elif (take/get/grab;
  examine/search/inspect/check/x/read; use; open/close/unlock/lock; drop/stow/put;
  combine; split; craft/make; eat/drink; toggle; attack/kill/speak/say/talk/whisper/shout;
  name/label; go/walk/move/enter; find/forage) — each group is a `scope`.
- `engine/pleasure_actions.py` `INTIMACY_VERBS` is the mature-gate source of
  truth for at least some intimacy verbs; `routes/action_handlers.py` imports it.
- `routes/action_handlers.py` `handle_take_action` is a ~1,100-line if/elif
  `cmd.startswith(...)` chain (~70 verb prefixes) plus `_ACTIVITY_ALLOWED` /
  `_ACTION_BLOCK_ALLOWED` / `_ACTIVITY_NON_INTERRUPTING` sets. The **mapping**
  is not data-shaped; only the **accepted set** can be derived without rewriting
  the dispatcher.
- `engine/triggers/ui.py:_get_available_actions` returns per-item buttons
  (`examine/take/drop/open/close/use/eat/drink/toggle`) — a `scope=item` view.

### Proposed implementation

1. `engine/action_verbs.py` — the one declaration:
   `VerbSpec(id, aliases, scope, target_schema, cost_key, mature_gate, bracket_order)`
   with `all_verbs()`, `mature_verbs()`, `verbs_for_scope()`, `bracket_order()`,
   `llm_manifest()`. Seed from the counts above; `use_on/consume/quaff` become
   aliases.
2. `tools/action_verbs_index.py` — writes `static/js/agent/action-verbs.generated.js`
   (`window.ActionVerbs`), `--check` fails when stale (mirrors
   `way_property_index.py`). Needs a `@module`/`@contributes`/`@docs` header and
   an `@powers` string matching a `Feature Map.md` feature, plus a script tag in
   `templates/index.html` **before** `action-normalizer.js`.
3. Rewire `action-normalizer.js`, `contextual-actions.js`, `system-prompt.js`,
   `engine/autocomplete.py` and `engine/triggers/ui.py` to read the registry.
4. Drift guard `tests/test_action_verbs.py`: parse the JS surfaces and the
   dispatcher prefixes; fail on any verb/alias absent from the registry, and on
   a registry `bracket_order` verb missing from `BRACKET_ORDER`.
5. Dispatcher: leave the mapping chain, but gate recognition on the registry and
   assert (test) every dispatch prefix is a registry verb. If a full data-driven
   dispatch is wanted, that is a separate, larger refactor.
