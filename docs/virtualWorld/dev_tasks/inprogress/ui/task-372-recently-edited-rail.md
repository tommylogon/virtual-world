---
type: task
status: inprogress
area: ui
priority: medium
---

# task-372: recently-edited-rail

**Filed**: 2026-08-30
**Status**: Not started (card complete; no implementation yet).
**Source**: docs/virtualWorld/Scenario Workflows & UI Audit.md — P1 — Recently-edited rail: last ~10 nodes touched this session (frontend records its PATCHes), click to jump back.

## Notes

See the audit doc for the full section and sequencing notes. Reuse existing machinery where noted; the guardrails are: CLI-free, undo-safe, and no new storage formats unless the audit says so.

## What

A rail listing the last ~10 graph nodes the author touched this session, newest
first, one row per node. Clicking a row focuses and selects that node in the
inspector — the "where was I?" answer after editing across several nodes.

## Why

Audit P1: after a batch of edits, returning to a node you touched means hunting
the graph or scrolling the outline. A session-scoped rail of what you just
edited is the cheapest jump-back affordance and needs no server change. It is
the front-end sibling of the undo-history dropdown (task-371) and the
changes-since-source panel (task-373): those answer "what changed", this answers
"where was I working".

## How

- Front-end session ring buffer only. Record an entry wherever the inspector
  PATCHes a node (the same save path that mutates a node) with
  `{ nodeId, label, ts }`; derive `label` from the node name/type the inspector
  already shows.
- Dedup by `nodeId`: re-editing a node moves it to the front rather than adding
  a second row. Cap at 10.
- Render as a rail/panel; click focuses the node in the graph and selects it in
  the inspector.
- Session-scoped: clear on load/reset; never persisted (no new storage format —
  the audit's guardrail). No server change.

## Steps to verify

1. Edit several different nodes (rename an area, change an item property, edit a way).
   - expected: the rail lists them newest-first, one row per node.
   - observed: TODO
2. Re-edit a node already in the rail.
   - expected: it moves to the top; no duplicate row.
   - observed: TODO
3. Click a row.
   - expected: the graph focuses that node and the inspector opens it.
   - observed: TODO
4. Load/reset the scenario, or refresh the page.
   - expected: the rail empties (session-scoped).
   - observed: TODO

## Acceptance

- [ ] The last ~10 nodes touched this session are listed newest-first, deduped by id.
- [ ] Clicking a row focuses the node and opens it in the inspector.
- [ ] Session-scoped only: cleared on load/reset, no new storage format.
- [ ] No regression to the inspector's save path or the undo stack.

## Files

- `static/js/inspector.ts` — record `{ nodeId, label, ts }` on each node PATCH.
- `static/js/ui/` — the rail module (new).
- `templates/index.html` — `<script>` tag for the new module.
- CSS for the rail.
