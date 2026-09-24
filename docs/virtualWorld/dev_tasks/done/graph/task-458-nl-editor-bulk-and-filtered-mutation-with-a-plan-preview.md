---
type: task
status: done
area: graph
priority: high
---

# task-458: NL editor bulk and filtered mutation with a plan preview

**Filed:** 2026-09-22
**Related:** task-438, task-457

## Goal

Add a deterministic bulk staging op so one intent ('give all goblins darkvision') becomes one reviewable patch: update_matching_nodes (and a set_character_field convenience) filtered by kind/tag/area, an explicit affected-entity list shown before Apply, dict-field merge, per-target failure reporting, and idempotent re-run. Extends the batch vocabulary (_BATCH_PHASE in routes/graph_ops.py) and ToolRouter/TOOL_DEFINITIONS.

## Acceptance

- [x] `update_matching_nodes` op in the batch vocabulary
      (`routes/graph_ops.py`: `_BATCH_PHASE`, `_apply_batch_op`,
      `_select_nodes`, `_apply_node_patch`) — one intent, one reviewable op.
- [x] Selector by `kind`/`type`, `tags`/`tag` (+ `require_all_tags`),
      `area`/`area_id` (via `in` edge), `name_contains`, or explicit `ids`.
- [x] Explicit affected-entity list before Apply: the frontend tool resolves
      matches immediately (`OverlayGraphView.matchNodes`), stores
      `matched_ids`/`matched` on the op, names them in the op summary, and
      restyles/patch-previews each matched live node.
- [x] Dict-field merge: `_merge_dict_props` folds dict values key-by-key so
      patching one trait/environment key does not drop the others; the overlay
      preview mirrors it (`_mergeProps`). The same helper now backs the PATCH
      `update_node` route.
- [x] Per-target failure reporting: the op returns `matched`/`updated`/
      `failed:[{node_id,error}]`; a no-match selector is a reported error.
- [x] Idempotent re-run: re-staging/re-applying the same selector+patch is a
      no-op merge.
- [x] ToolRouter/TOOL_DEFINITIONS + agent-loop prompt guidance updated.
- [x] Tests: `tests/test_graph_batch.py` (6 new) and
      `tools/unit/test_nl_editor.js` (bulk selector/preview).

## Implementation notes

- Also fixed a latent undo bug the new test exposed: batch/patch property
  writes used to mutate `node.properties` in place, which also mutated the undo
  snapshot's shared reference, so one Undo did not revert a property edit. The
  merge helpers now assign a fresh top-level dict.
- `staging.js` fallback (stale server) reports bulk ops as an error instead of
  dropping them silently.

