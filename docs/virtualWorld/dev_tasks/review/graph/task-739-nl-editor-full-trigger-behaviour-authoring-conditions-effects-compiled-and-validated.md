---
type: task
status: review
area: graph
priority: high
---

# task-739: NL editor: full trigger + behaviour authoring (conditions/effects, compiled and validated)

**Filed:** 2026-10-08
**Related:** 

## Goal

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
      `engine/triggers/materialize.py` — the same materialiser the recipes use.
      Validated (`owner_id` must resolve; logic through `_trigger_issues`).
- [x] **The behaviour half.** The editor can now read, compile/validate and write
      a character's behaviours:
      - `get_behaviours(character)` — reads the live `player.behaviors` array.
      - `compile_behaviours(nodes, wires)` — exposes
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

- `static/js/nl-editor/tools.ts` — `get_trigger_schema` (read) + `create_trigger`
  (materialise) tools. Tool count 31 → 33.
- `engine/nl_editor_validation.py` — `_trigger_issues`, wired into the three
  node-mutating ops **and** `create_trigger`; reuses `engine/triggers/constants`
  (`TRIGGER_TYPES`, `EFFECT_TYPES`) so there is no second vocabulary.
- `routes/graph_ops.py` — `create_trigger` batch op via `materialize_trigger`
  (`_BATCH_PHASE['create_trigger'] = 1`).
- `static/js/nl-editor/agent-loop.ts` — prompt rules 13/14.
- `static/js/nl-editor/tools.ts` — `get_behaviours` + `compile_behaviours` read
  tools; `update_player` accepts `behaviors`. Tool count 33 → 35.
- `engine/nl_editor_validation.py` + `routes/graph_ops.py` — `behaviors` patch key
  (structural validation + write to `player.behaviors`).
- Tests: `tests/test_nl_editor_trigger_authoring.py` (**8 passed**) — well-formed
  trigger valid; unknown trigger_type / effect type / bad condition operator /
  operatorless condition flagged; update on a trigger validates its patch; a
  non-trigger node's `effects` key is not misread; `create_trigger` writes the
  node **and** the edge with props on both; owner/logic validation.
  `tests/test_nl_editor_player_ops.py` (**7 passed**) — adds behaviours shape
  checks and a behaviours write.

**Live-verified 2026-10-09** against a second server copy on :4445 (camp loaded):
`POST /api/graph/batch {strict_validation:true}` with `create_trigger` on `belt_leather`
created `trigger_belt_leather_on_use_1791548346731_170` — a `logic_trigger` node **and**
a `triggers` edge from the owner (confirmed in the next `GET /api/state`). The gate is
live: an unknown `trigger_type` in the same batch returned **422** (*"Unknown
trigger_type 'on_nonsense'."*). Not yet exercised: the three read tools
(`get_trigger_schema`, `get_behaviours`, `compile_behaviours`) invoked by the agent —
they are served and loaded (`tools.js` contains them, `window.NlEditorBudget` /
`TriggerTypes` load) but were not driven end-to-end.
