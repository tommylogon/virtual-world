---
type: task
status: todo
area: ui
priority: medium
wiki: "[[UI Reference/Rendering & UI Modules]]"
---

# task-384: per-edit-undo-feed

**Filed**: 2026-08-30
**Status**: Not started (card complete; no implementation yet).
**Source**: docs/virtualWorld/Scenario Workflows & UI Audit.md - P4 - 'World edited' feed with per-edit undo: bind EventSource world_changed entries to undo snapshots (labels).

## Notes

See the audit doc for the full section and sequencing notes. Reuse existing machinery where noted; the guardrails are: CLI-free, undo-safe, and no new storage formats unless the audit says so.

## What

A "World edited" feed: every mutation (including external / MCP edits) appears
as a labeled row bound to its undo snapshot, with a one-click restore to that
point.

## Why

Audit P4 #18: the live-edit push is "a log line only; no per-edit undo binding,
no edit feed". The undo stack already records a labeled per-edit snapshot
(task-371), so the data exists - this surfaces it as a feed where an edit is
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

- `static/js/ui/undo-history.ts` (task-371) - extend into the feed.
- `routes/saveload.py` - undo endpoints (`/api/undo`, `/api/undo/list`).
- `templates/index.html`.
- `tests/`.

## Audit note (2026-10-16)

Moved from inprogress back to todo: it was not being worked. No uncommitted changes in the working tree or in any of the eight git worktrees touch this card's files, and nobody is editing it. The card itself says 'Not started (card complete; no implementation yet)'; 0 of its acceptance boxes are checked and no commit references it. static/js/ui/undo-history.ts already exists (last commit 2026-10-10); check what it covers before building a second feed.

## What already exists (2026-10-16)

`static/js/ui/undo-history.ts` (`UndoHistory`, the history button in the graph toolbar, `templates/index.html:209`) is the task-371 dropdown (done) and covers part of this card. Read from source on 2026-10-16; it was not exercised live.

- Labelled list: `GET /api/undo/list` (`routes/saveload.py:331`) returns every undo entry newest first, index 0 being the next undo. A mutation appears only if its route pushes a snapshot or paint delta (`_push_undo_snapshot` / `_push_undo_delta`, called from `graph_ops.py`, `saveload.py`, `settings.py`, `world_grid_ops.py` and `app.py`). Which mutating routes skip the push was not enumerated, so "every mutation appears" is unverified.
- Per-entry restore is met: a row posts `POST /api/undo` with `steps = index + 1`, then calls `worldState.fetch()`. It is a multi-step undo through the existing stack, not a jump to an independent snapshot.
- External and MCP edits via `world_changed` are not met. The module never subscribes to `world_changed`; the list is fetched only when the dropdown opens, so it is a dropdown and not a live feed. `mcp_server.py` only exposes reset, undo and redo.
- Reuses the undo stack with no new storage: met.
- No unit test exists for it (no `*undo*` file in `tools/unit`).

The remaining scope of this card is a live-updating feed and coverage of external edits, not a second list.


## Reconnaissance (2026-10-20)
- Measured: static/js/ui/edit-feed.js exists and subscribes to world_changed SSE; undo-history.js also exists. routes/saveload.py has /api/undo/list and /api/undo.
- Verdict: PARTLY_DONE. Live feed + world_changed subscription implemented (edit-feed.js). Card scope largely covered but some details may need polish; keep todo, update scope to reflect landed implementation.
