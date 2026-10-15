---
type: task
status: inprogress
area: ui
priority: medium
---

# task-384: per-edit-undo-feed

**Filed**: 2026-08-30
**Status**: Not started (card complete; no implementation yet).
**Source**: docs/virtualWorld/Scenario Workflows & UI Audit.md — P4 — 'World edited' feed with per-edit undo: bind EventSource world_changed entries to undo snapshots (labels).

## Notes

See the audit doc for the full section and sequencing notes. Reuse existing machinery where noted; the guardrails are: CLI-free, undo-safe, and no new storage formats unless the audit says so.

## What

A "World edited" feed: every mutation (including external / MCP edits) appears
as a labeled row bound to its undo snapshot, with a one-click restore to that
point.

## Why

Audit P4 #18: the live-edit push is "a log line only; no per-edit undo binding,
no edit feed". The undo stack already records a labeled per-edit snapshot
(task-371), so the data exists — this surfaces it as a feed where an edit is
visible by name and revertible by name.

## How

- The `after_request` hook already pushes a labeled snapshot per mutation
  (task-371) and `GET /api/undo/list` exposes the stack; `/api/events`
  `world_changed` announces each edit (see AGENTS.md: the SSE opens
  unconditionally, independent of the spectator poll).
- Render a feed: subscribe to `world_changed`, refresh the undo list, show each
  edit with its label; a row's action restores to that snapshot via
  `POST /api/undo {steps:N}`.
- Reuse / extend the undo-history UI (task-371) rather than a parallel list.
- External / MCP edits arrive through the same `world_changed` path.
- No new storage.

## Browser UI and intended live verification

Intended UI home: World editor → per-edit Undo/Changes feed.

Current availability: The per-edit feed and restore path are still in progress.

Live steps when available:

1. Make several GUI edits and one supported API/MCP edit, then inspect the feed.
   - expected: Each mutation appears once with a useful label, including external changes from the shared world-changed event.

2. Restore one feed entry and inspect the world.
   - expected: The selected snapshot is restored through existing undo machinery without new state storage.

This section defines the intended access point and acceptance path. It is not a claim that the UI or complete behavior exists or works today; Current availability records the present state, and these steps describe how to verify the intended behavior when it is available.
## Steps to verify

1. Make several edits in the GUI.
   - expected: each appears in the feed with a label.
   - observed: TODO
2. Trigger an edit from outside the GUI (an MCP / API call).
   - expected: it appears in the feed too.
   - observed: TODO
3. Click a row's restore.
   - expected: the world returns to that snapshot.
   - observed: TODO

## Acceptance

- [ ] Every mutation appears with its label.
- [ ] Per-entry restore returns the world to that snapshot.
- [ ] External / MCP edits are included (via the same `world_changed` event).
- [ ] Reuses the undo stack; no new storage.

## Files

- `static/js/ui/undo-history.ts` (task-371) — extend into the feed.
- `routes/saveload.py` — undo endpoints (`/api/undo`, `/api/undo/list`).
- `templates/index.html`.
- `tests/`.
