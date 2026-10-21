---
type: task
status: review
area: refactor
priority: high
wiki: "[[AI & Narration/Agent Engine]]"
---

# task-491: Single source of truth for action verbs (scoped registry)

**Filed:** 2026-09-23
**Related:** task-299

## What

Action verbs are declared in six places and drift independently: `engine/triggers/ui.py:_get_available_actions` (per-item buttons), `action-normalizer.js` `VALID_VERBS` (79 entries, 78 unique - `grab` duplicated) plus `MATURE_VERBS` (8) and a local `MOVE_VERBS` (5), `contextual-actions.js` `BRACKET_ORDER` (13), hand-written prose in `system-prompt.js`, the ~1,100-line if/elif prefix chain in `action_handlers.py` (~70 verb prefixes), and the grouped if/elif in `engine/autocomplete.py`. `normalizeStructuredAction` consumes `use_on`, `consume` and `quaff` which are not in `VALID_VERBS`, so aliases are needed. One scoped registry - `VerbSpec(id, aliases, scope, target_schema, cost_key, mature_gate, bracket_order)` - that the dispatcher, trigger UI, agent normalizer, bracket builder, prompt prose and autocomplete all read, with the LLM verb list generated from it and a drift guard test that fails when a surface declares a verb the registry does not.

## Acceptance

- A verb is declared in exactly one place; the dispatcher (`routes/action_handlers.py`), `engine/triggers/ui.py`, `action-normalizer.js`, `contextual-actions.js`, `system-prompt.js` and `engine/autocomplete.py` all derive their sets from the registry.
- The registry carries scope + metadata (`aliases`, `scope`, `target_schema`, `cost_key`, `mature_gate`, `bracket_order`).
- The LLM verb list is generated from the registry; mature verbs are gated by the same flag as today's `MATURE_VERBS`.
- A drift guard test fails when a surface declares a verb the registry doesn't (or omits one its scope should expose).
- Behaviour is unchanged: every verb the command surface accepts today still resolves.

## Reconnaissance (2026-10-02) - NOT started, enumerated

The surface counts, so the registry can be built without guessing:

- `static/js/agent/action-normalizer.js:20-31` `VALID_VERBS`: **79 entries, 78
  unique** (`grab` duplicated); `:35` `MATURE_VERBS`: **8** (`kiss, caress,
  lick, suck, bite, pinch, blow, tickle`). `:49` also has a local `MOVE_VERBS`
  (5). `normalizeStructuredAction` (`:83-151`) is the mapping switch - it
  consumes `use_on`, `consume`, `quaff` which are **not** in `VALID_VERBS`, so
  aliases are needed (`use_on`→use+target, `consume`→eat, `quaff`→drink).
- `static/js/agent/prompt-builder/contextual-actions.js:32` `BRACKET_ORDER`:
  **13** (`take, use, use_on, open, close, eat, drink, read, wear, remove,
  toggle, drop, examine`) - the `bracket_order` metadata seed.
- `static/js/agent/prompt-builder/system-prompt.js`: hand-written verb prose
  (must be generated from the registry's scope lists).
- `engine/autocomplete.py:141-228`: verb **groups** in an if/elif (take/get/grab;
  examine/search/inspect/check/x/read; use; open/close/unlock/lock; drop/stow/put;
  combine; split; craft/make; eat/drink; toggle; attack/kill/speak/say/talk/whisper/shout;
  name/label; go/walk/move/enter; find/forage) - each group is a `scope`.
- `engine/pleasure_actions.py` `INTIMACY_VERBS` is the mature-gate source of
  truth for at least some intimacy verbs; `routes/action_handlers.py` imports it.
- `routes/action_handlers.py` `handle_take_action` is a ~1,100-line if/elif
  `cmd.startswith(...)` chain (~70 verb prefixes) plus `_ACTIVITY_ALLOWED` /
  `_ACTION_BLOCK_ALLOWED` / `_ACTIVITY_NON_INTERRUPTING` sets. The **mapping**
  is not data-shaped; only the **accepted set** can be derived without rewriting
  the dispatcher.
- `engine/triggers/ui.py:_get_available_actions` returns per-item buttons
  (`examine/take/drop/open/close/use/eat/drink/toggle`) - a `scope=item` view.

### Proposed implementation

1. `engine/action_verbs.py` - the one declaration:
   `VerbSpec(id, aliases, scope, target_schema, cost_key, mature_gate, bracket_order)`
   with `all_verbs()`, `mature_verbs()`, `verbs_for_scope()`, `bracket_order()`,
   `llm_manifest()`. Seed from the counts above; `use_on/consume/quaff` become
   aliases.
2. `tools/action_verbs_index.py` - writes `static/js/agent/action-verbs.generated.js`
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

## Why

Action verbs are declared in six places - `engine/triggers/ui.py:_get_available_actions`, `action-normalizer.js` `VALID_VERBS`/`MATURE_VERBS`, `contextual-actions.js` `BRACKET_ORDER`, hand-written prose in `system-prompt.js`, the ~1,100-line if/elif prefix chain in `action_handlers.py`, and the grouped if/elif in `engine/autocomplete.py`. Each one drifts on its own: a verb renamed in the dispatcher silently disappears from the UI, a mature verb added to one list leaks through another, and bracket order re-sorts itself between the command line and the Human Turn buttons. A drift guard test is the only thing that can notice, and it can only notice if there is one source to diverge from. Agents and editors pay for it too: the LLM verb list is hand-maintained prose, so an agent can be offered a verb the world will not accept, and an editor fixing one surface has to find and update five.

## How

1. Build `engine/action_verbs.py` - one declaration: `VerbSpec(id, aliases, scope, target_schema, cost_key, mature_gate, bracket_order)` with `all_verbs()`, `mature_verbs()`, `verbs_for_scope()`, `bracket_order()`, `llm_manifest()`. Seed from the 2026-10-02 counts: 79 VALID_VERBS (78 unique, `grab` duplicated), 8 MATURE_VERBS, 5 MOVE_VERBS, 13 BRACKET_ORDER; `use_on`/`consume`/`quaff` become aliases.
2. `tools/action_verbs_index.py` writes `static/js/agent/action-verbs.generated.js` (`window.ActionVerbs`); `--check` fails when stale (mirrors `way_property_index.py`). Needs a `@module`/`@contributes`/`@docs` header, an `@powers` string matching a `Feature Map.md` feature, and a `<script>` tag in `templates/index.html` **before** `action-normalizer.js`.
3. Rewire `action-normalizer.js`, `contextual-actions.js`, `system-prompt.js`, `engine/autocomplete.py` and `engine/triggers/ui.py` to read the registry.
4. Drift guard `tests/test_action_verbs.py`: parse the JS surfaces and the dispatcher prefixes; fail on any verb/alias absent from the registry, and on a registry `bracket_order` verb missing from `BRACKET_ORDER`.
5. Dispatcher: leave the mapping chain, gate recognition on the registry, and assert (test) every dispatch prefix is a registry verb. A full data-driven dispatch is a separate, larger refactor.

**Dedup / reuse / quality / experience (added 2026-10-16).** The point is not a new table - it is that the command line, the Human Turn buttons, the NL editor action list, the agent normalizer, the prompt prose and autocomplete all derive from **one** declaration, so a verb added once appears everywhere and a mature verb gated once is gated everywhere. Reuse the existing mature-gate source of truth (`engine/pleasure_actions.py` `INTIMACY_VERBS`) rather than inventing a second mature concept. Visual quality: keep bracket order and button ordering identical so the UI does not shuffle between surfaces. Agent experience: the generated LLM verb list comes from the registry, so an agent never sees a verb a surface would reject. Editor experience: the drift guard names the exact surface + verb that diverged instead of a silent mismatch. Player experience: unchanged - every verb the command surface accepts today still resolves.

## Steps to verify

1. Scoped registry and accessors
   - expected: engine/action_verbs.py declares VerbSpec with all verbs, aliases, scopes, costs, and gates.
   - observed: 76 canonical specs, 130 total names/aliases, 0 collisions, all tiers valid.
2. Code generator and client mirror sync
   - expected: tools/action_verbs_index.py --check verifies static/js/agent/action-verbs.generated.js is in sync.
   - observed: tools/action_verbs_index.py --check passes clean (exit code 0).
3. Drift guard tests
   - expected: tests/test_action_verbs.py validates all surfaces (dispatcher prefixes, autocomplete, normalizer, contextual actions).
   - observed: 12/12 passed in 0.5s.
4. JS unit test suite
   - expected: node tools/unit/run.cjs passes without regressions.
   - observed: 780 passed across 57 files.

## Files

- engine/action_verbs.py
- tools/action_verbs_index.py
- static/js/agent/action-verbs.generated.js
- tests/test_action_verbs.py
- static/js/agent/action-normalizer.ts
- static/js/agent/action-normalizer.js
- static/js/agent/prompt-builder/contextual-actions.ts
- static/js/agent/prompt-builder/contextual-actions.js
- static/js/agent/prompt-builder/system-prompt.ts
- static/js/agent/prompt-builder/system-prompt.js
- engine/autocomplete.py
- engine/action_tiers.py
- routes/action_handlers.py
- static/js/types/globals.d.ts
- templates/index.html
- tools/unit/run.cjs

## Browser UI and intended live verification

Intended UI home: game command line/autocomplete, Human Turn action buttons, and the NL editor's available-action list. These surfaces must all derive their verb options from the scoped registry and obey the same mature-content gate.

Current availability: the card records verb definitions duplicated across engine dispatch, trigger UI, agent normalization, prompt prose, and autocomplete. A single registry and drift guard are planned; no consolidation is claimed as implemented.

Live steps when available:
1. In the same scenario, open command autocomplete, the Human Turn action controls, and the NL editor action list; record the verbs each surface offers.
   - expected: every offered verb is present in the scoped registry with matching aliases and target schema; no surface adds or omits a valid verb unexpectedly.
2. Enable mature content and inspect the mature action list; disable it and repeat.
   - expected: mature verbs appear only when the shared gate allows them, consistently across all three surfaces and the generated LLM prompt list.
3. Invoke one movement verb and one item-scoped verb from the UI and command line.
   - expected: dispatch, UI affordance, autocomplete, and target validation agree on verb scope and cost; behavior remains unchanged from the pre-registry contract.
4. Introduce a test-only verb on one surface without registering it and run the drift guard.
   - expected: the guard names the exact surface and verb that diverged.

This section is not a claim that the planned registry exists or is wired today.

## Refactor discipline (applies to this task)

Applies to every refactor in this repo, per the 2026-10-16 card refresh:

1. **Dedup & reuse pass (mandatory).** While working, scan the touched concern and its
   neighbours for duplicate logic, parallel data homes, and near-identical helpers;
   consolidate onto one owner instead of copying. Prefer reusing an existing seam over
   creating a second one. Record any dedup decision in the move table / notes.
2. **Agent-experience & cleanliness (mandatory).** Name modules/files by concern (not
   by size), keep each under ~600 lines where the seam allows, add a one-line module
   docstring stating its owner and public surface, and ensure a fresh agent session can
   understand it without reading the host. No new abstraction unless an existing seam
   already represents the concept.
3. **No behaviour change unless the card says so.** Extraction and consolidation only;
   keep public imports/API stable and re-export moved members as thin delegates.
4. **One file/concern at a time**, verified with a targeted test selection (never the
   full suite by default, never -q).
