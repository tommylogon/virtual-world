---
type: bug
status: done
area: graph
priority: high
---

# bug-50: Renaming a scope does not update the graph scope picker or breadcrumb, and one Undo after a rename does nothing

**Filed:** 2026-09-27
**Related:** task-397, task-539
**Fixed:** 2026-09-27

## Symptom

The author renamed a scope (`deep_woods_2` → "goblin camp") and the graph still
showed the old name — in the scope picker chip at the top of the canvas and in the
scope bar's breadcrumb. It only changed after a full page reload. The rename
itself was correct all along: `GET /api/world/scopes?flat=1` returned
`name: "goblin camp"`, and the WorldPainter breadcrumb (which fetches its own
payload) showed it.

## Cause 1 — nothing refreshed the derived labels

The picker and the breadcrumb are both derived from
`graphManager._scopeSummaries`, filled by `loadScopeFilterOptions()`. Nothing
called it after a rename, and the `world_changed` subscriber in `world-state.js`
only does `worldState.fetch()`, which does not carry scope names. So any rename —
from this app, from an agent over MCP, or reverted by Undo — left both labels
stale.

Fix: `graphManager._watchScopeChanges()` subscribes to the existing
`world:changed` app event and refetches the flat list, but only for routes that
can change a scope's name or place in the tree:

- `POST /api/world/scopes` (created), `…/rename`, `…/delete`
- the whole-world operations that can revert one: `/api/undo`, `/api/redo`,
  `/api/reset`, `/api/load`, `/api/load-game/…`

The predicate is deliberately narrow: painting, placing and the map-offset drags
also live under `/api/world/scopes/…` and fire the same event, so matching that
prefix would refetch the list on every stroke. (Verified: three paint strokes
produced **0** extra requests.)

## Cause 2 — `/rename`, `/delete` and `/offset` pushed two undo snapshots

Every WorldPainter scope handler pushes its own **pre**-state snapshot, and
`app.py`'s `after_request` hook must skip a second push for those paths, or the
first Undo pops the POST state and appears to do nothing. The skip list was
written as a set of suffixes (`== '/api/world/scopes'`, `endswith('/grid')`,
`'/grid/' in path`, and `/areas` added for task-539) and had missed the three
suffixes outside `/grid/`, so each of them double-pushed. task-539's `/areas`
was the same class of miss, which is how it was found.

Fix: one rule instead of a suffix list — any mutation under
`/api/world/scopes` pushes its own snapshot. Regression test:
`test_every_scope_route_is_one_undo_step` asserts a single stack entry, and that
**one** undo reverts, for rename / offset / paint / delete.

## Also fixed while here

The two scope-change messages printed the raw id ("Moved 3 area(s) into
deep_woods_2"), which reads as if the rename had not taken. Both now print the
scope's display name (`graph-manager._bulkScope`, `area-view` scope select).

## Verified

Live, with no page reload between any step: rename → picker and breadcrumb both
show "ZZ renamed camp"; one Undo → both back to "goblin camp"; Redo → both back
to "ZZ renamed camp". The camp was left named "goblin camp" and the test paint
was cleared.
