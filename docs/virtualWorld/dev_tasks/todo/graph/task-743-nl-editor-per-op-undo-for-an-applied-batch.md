---
type: task
status: todo
area: graph
priority: medium
---

# task-743: NL editor: per-op undo for an applied batch

**Filed:** 2026-10-08
**Related:** task-461, task-387, task-458

## Goal

Today an NL-editor Apply records exactly ONE undo snapshot (task-387), so a single Undo reverts the whole batch; undoing one applied op is not offered anywhere (no route, no UI). Add per-op undo. Design decision required: (a) push one snapshot per op inside handle_graph_batch (routes/graph_ops.py:1286) so N single-step undos step back through the batch — simple, but changes the one-snapshot contract and multiplies whole-world snapshots by batch size against _MAX_UNDO_DEPTH=10; or (b) inverse ops. Pick one, keep the batch atomic-Undo behaviour as an option if users rely on it, add the endpoint, and surface a per-row Undo in the staged list. This was carved out of task-461 (its validation gate and property diff are done); do not change task-387's default without deciding the contract.

## Acceptance

- TODO
