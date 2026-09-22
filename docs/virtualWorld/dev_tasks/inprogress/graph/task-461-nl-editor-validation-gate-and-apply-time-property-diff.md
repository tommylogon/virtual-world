---
type: task
status: inprogress
area: graph
priority: medium
---

# task-461: NL editor validation gate and apply-time property diff

**Filed:** 2026-09-22
**Related:** task-438, task-422, task-458

## Goal

Validate staged ops before Apply (known fields and registered trait ids, edge endpoints exist, id casing, no duplicate area names) and show a property-level diff per op instead of generic ghost nodes, so a misspelled trait or wrong shape cannot silently no-op. Add per-op undo for an applied batch. Shares the validator with task-438 phase 5.

## Acceptance

- [x] Shared validator `engine/nl_editor_validation.py:validate_ops` — one
      definition used by the batch route and the pre-Apply endpoint. Checks:
      op structure/type, node existence (tracking creates/deletes as the batch
      replays), unknown trait ids (error), unknown item actions (warning), id
      casing (warning), duplicate area display names (warning), dangling
      attach/detach endpoints, bulk selector/patch emptiness, library registry
      + id slug + mature gate.
- [x] `POST /api/graph/batch/validate` dry-run endpoint (`handle_graph_validate`).
- [x] Apply gate: `handle_graph_batch` validates first; with
      `strict_validation: true` it returns 422 and applies nothing when there
      are errors. Other callers keep the previous permissive behaviour and just
      receive `validation` as advisory data.
- [x] The NL editor sends `strict_validation`, keeps every op staged on a 422,
      and shows the findings (`staging.js`, `index.js`,
      `ui.js:showValidationIssues`).
- [x] Property-level diff per op: `static/js/nl-editor/diff.js`
      (`opDiff`/`diffPairs`/`summaryLines`) renders "traits.dark_vision: — → true"
      under each staged row, flags a no-op patch, and lists each bulk target.
- [x] Tests: `tests/test_nl_editor_validation.py` (9) and
      `tools/unit/test_nl_editor_diff.js` (8).

## Remaining

- [ ] Per-op undo for an applied batch (the batch still undoes as ONE snapshot;
      undoing a single applied op is not yet offered).

