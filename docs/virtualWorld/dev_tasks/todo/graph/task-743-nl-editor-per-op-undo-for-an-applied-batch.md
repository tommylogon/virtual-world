---
type: task
status: todo
area: graph
priority: medium
wiki: "[[World Building/Graph System]]"
---

# task-743: NL editor: per-op undo for an applied batch

**Filed:** 2026-10-08
**Related:** task-461, task-387, task-458

## What

Today an NL-editor Apply records exactly ONE undo snapshot (task-387), so a single Undo reverts the whole batch; undoing one applied op is not offered anywhere (no route, no UI). Add per-op undo. Design decision required: (a) push one snapshot per op inside handle_graph_batch (routes/graph_ops.py:1286) so N single-step undos step back through the batch — simple, but changes the one-snapshot contract and multiplies whole-world snapshots by batch size against _MAX_UNDO_DEPTH=10; or (b) inverse ops. Pick one, keep the batch atomic-Undo behaviour as an option if users rely on it, add the endpoint, and surface a per-row Undo in the staged list. This was carved out of task-461 (its validation gate and property diff are done); do not change task-387's default without deciding the contract.

## Acceptance

- TODO

## Why

TODO

## How

TODO

## Steps to verify

1. Open the NL editor and stage a batch containing two independent graph
   operations, such as renaming one area and adding a tag to another node.
   Apply the batch and inspect both nodes in the graph and their inspectors.
   - expected: both operations are applied; the staged list records each
     operation separately with its own Undo affordance.
2. Click Undo on only the second operation's row, then inspect both nodes and
   the remaining staged/applied rows.
   - expected: only the second operation is reversed; the first operation
     remains applied and the rest of the batch is not rolled back.
3. Click Undo for the first operation and inspect both nodes again.
   - expected: the first operation is then reversed, leaving the graph at its
     pre-batch values.
4. Repeat with a batch where the second operation fails validation.
   - expected: a rejected operation has no Undo action and does not alter or
     undo the successfully applied operation.

## Browser UI and intended live verification

Intended UI home: NL editor → stage a multi-operation batch → Apply → the
applied-operation rows in the staging tray. Each successful row owns its own
Undo control; the existing global batch Undo contract must remain explicit.

Current availability: task-387's batch Apply records one snapshot, so one Undo
reverts the entire batch. Per-operation Undo is not currently offered by this
card's report. The implementation choice (per-operation snapshots or inverse
operations) must be settled before changing that contract.

Live steps when available:
1. Stage two successful operations against different nodes and Apply. Count the
   applied rows and verify the changed node values in their Inspectors.
   - expected: two applied rows each have a distinct Undo control.
2. Undo the second row only, then inspect both nodes and the first row.
   - expected: the second change is reversed, the first remains, and only the
     second row is marked undone/removed.
3. Undo the first row and compare both node values with their pre-batch values.
   - expected: the graph returns to its original state without creating extra
     nodes or reverting unrelated edits.
4. Run one invalid operation in the batch and inspect its row after Apply.
   - expected: the invalid row explains its error and cannot undo a successful
     sibling operation.

These steps describe the intended NL-editor surface. They do not claim
per-operation Undo is available today.

This section is not a claim that planned UI exists or works today.

## Files

- TODO
