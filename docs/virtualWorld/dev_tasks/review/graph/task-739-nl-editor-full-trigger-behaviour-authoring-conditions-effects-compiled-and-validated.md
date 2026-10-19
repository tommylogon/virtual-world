---
type: task
status: review
area: graph
priority: high
---

# task-739: NL editor: full trigger + behaviour authoring (conditions/effects, compiled and validated)

**Filed:** 2026-10-08
**Related:** 

## What

create_node can mint an empty logic_trigger but the editor cannot author its logic. Expose the existing condition/effect schema and the graph->behaviour compile (shared/trigger-graph.ts compileToBehaviorsWithIssues) so the editor can create AND validate a trigger. Reuse engine/triggers; do not invent a second format. See docs/design/nl-editor-full-authoring.md.

## Acceptance

- [x] The condition/effect/event vocabulary is exposed to the editor: read tool
      `get_trigger_schema` returns `trigger_types`, `condition_types` and
      `effect_types` from `window.TriggerTypes` (the single source of truth that
      already mirrors the engine), plus a note on the trigger shape.
- [x] Trigger logic is validated, not just minted: `engine/nl_editor_validation.py
      _trigger_issues` rejects an unknown `trigger_type`, an effect type outside
      `EFFECT_TYPES`, an unknown legacy `effect_type`, and a malformed condition
      tree (bad operator, group with no children, node that is neither operator
      nor leaf), for `create_node`/`update_node`/`update_matching_nodes` on a
      `logic_trigger`.
- [x] Prompt rules 13 (trigger authoring) + 14 (player state vs edges) tell the
      agent to call the schema tool first and use real values.
- [x] The editor can **materialise** a trigger, not just mint a bare node: new
      `create_trigger` op (`owner_id` + `trigger` definition) writes the
      `logic_trigger` node **and** the `triggers` edge with props on both, via
      `engine/triggers/materialize.py` - the same materialiser the recipes use.
      Validated (`owner_id` must resolve; logic through `_trigger_issues`).
- [x] **The behaviour half.** The editor can now read, compile/validate and write
      a character's behaviours:
      - `get_behaviours(character)` - reads the live `player.behaviors` array.
      - `compile_behaviours(nodes, wires)` - exposes
        `TriggerGraph.compileToBehaviorsWithIssues`, returning
        `behaviors` + `compile_error` so a behaviour-mode graph can be VALIDATED
        before staging.
      - `update_player` gained a `behaviors` patch key (validated: list of
        `{actions:[{type,...}]}`; written to `player.behaviors`).
      - Prompt rule 15.
- [ ] **Follow-up (not blocking):** condition/effect **param** shapes are still
      only type-checked, not shape-checked; blueprint save/load (the
      `data/library/triggers/*.json` picker) is not exposed to the NL editor.

## Landed (2026-10-08)

- `static/js/nl-editor/tools.ts` - `get_trigger_schema` (read) + `create_trigger`
  (materialise) tools. Tool count 31 → 33.
- `engine/nl_editor_validation.py` - `_trigger_issues`, wired into the three
  node-mutating ops **and** `create_trigger`; reuses `engine/triggers/constants`
  (`TRIGGER_TYPES`, `EFFECT_TYPES`) so there is no second vocabulary.
- `routes/graph_ops.py` - `create_trigger` batch op via `materialize_trigger`
  (`_BATCH_PHASE['create_trigger'] = 1`).
- `static/js/nl-editor/agent-loop.ts` - prompt rules 13/14.
- `static/js/nl-editor/tools.ts` - `get_behaviours` + `compile_behaviours` read
  tools; `update_player` accepts `behaviors`. Tool count 33 → 35.
- `engine/nl_editor_validation.py` + `routes/graph_ops.py` - `behaviors` patch key
  (structural validation + write to `player.behaviors`).
- Tests: `tests/test_nl_editor_trigger_authoring.py` (**8 passed**) - well-formed
  trigger valid; unknown trigger_type / effect type / bad condition operator /
  operatorless condition flagged; update on a trigger validates its patch; a
  non-trigger node's `effects` key is not misread; `create_trigger` writes the
  node **and** the edge with props on both; owner/logic validation.
  `tests/test_nl_editor_player_ops.py` (**7 passed**) - adds behaviours shape
  checks and a behaviours write.

**Live-verified 2026-10-09** against a second server copy on :4445 (camp loaded):
`POST /api/graph/batch {strict_validation:true}` with `create_trigger` on `belt_leather`
created `trigger_belt_leather_on_use_1791548346731_170` - a `logic_trigger` node **and**
a `triggers` edge from the owner (confirmed in the next `GET /api/state`). The gate is
live: an unknown `trigger_type` in the same batch returned **422** (*"Unknown
trigger_type 'on_nonsense'."*). Not yet exercised: the three read tools
(`get_trigger_schema`, `get_behaviours`, `compile_behaviours`) invoked by the agent -
they are served and loaded (`tools.js` contains them, `window.NlEditorBudget` /
`TriggerTypes` load) but were not driven end-to-end.

## Why

While the NL editor could previously create bare logic_trigger nodes, it lacked the ability to author trigger logic (events, conditions, effects) or validate condition trees. LLMs were forced to invent trigger structures that frequently failed runtime validation or corrupted trigger edges. Exposing schema tools, trigger materialization, and behavior graph compilation enables the NL editor to safely construct, validate, and attach functional gameplay triggers and NPC behaviors directly from natural language prompts.

## How

1. In static/js/nl-editor/tools.ts, add tools get_trigger_schema, create_trigger, get_behaviours, and compile_behaviours.
2. In engine/nl_editor_validation.py, implement _trigger_issues validating trigger types, effect types, condition operators, and parameter structures against engine/triggers/constants.py.
3. In routes/graph_ops.py, implement create_trigger batch operation delegating to engine/triggers/materialize.py to create both the logic_trigger node and triggers edge with properties.
4. Support behaviors patch key in update_player allowing NPC behavior lists to be compiled, validated, and updated.

## Steps to verify

1. Call create_trigger via POST /api/graph/batch on an item (e.g. belt_leather).
   - expected: Materializes a logic_trigger node and a triggers edge with valid condition/effect properties in GET /api/state.
   - observed: Tested live 2026-10-09: trigger node and triggers edge created.
2. Submit batch with unknown trigger_type (e.g. on_nonsense).
   - expected: Validation halts and returns HTTP 422 with specific error message.
   - observed: Verified live: returned 422 with 'Unknown trigger_type'.
3. Run trigger authoring and player ops test suites (python -m pytest tests/test_nl_editor_trigger_authoring.py tests/test_nl_editor_player_ops.py).
   - expected: All 15 unit tests pass.
   - observed: 15 passed.

## Files

- static/js/nl-editor/tools.ts
- engine/nl_editor_validation.py
- 
outes/graph_ops.py
- engine/triggers/materialize.py
- 	ests/test_nl_editor_trigger_authoring.py
- 	ests/test_nl_editor_player_ops.py
