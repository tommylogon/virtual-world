---
type: task
status: done
area: graph
priority: medium
---

# task-376: draw-a-door-wizard

**Filed**: 2026-08-30
**Status**: Todo
**Source**: docs/virtualWorld/Scenario Workflows & UI Audit.md — P3 — Draw-a-door wizard: select two areas → creates way node + 4 connection edges (connect_areas behavior) with name/cardinal/hidden/one-way options.

## Notes

See the audit doc for the full section and sequencing notes. Reuse existing machinery where noted; the guardrails are: CLI-free, undo-safe, and no new storage formats unless the audit says so.

## What already existed (measured, not assumed)

The GUI half of this already shipped: `ui/create-modal.js::_buildConnectionForm`
(the "Connect Rooms" modal) posts to `POST /api/build/connect` →
`routes/graph_ops.py::handle_build_connect_legacy`, which creates the way node
plus the 4 connection edges. Counting the 22 visible controls in that form on a
live instance found the three real gaps the audit lists:

| Audit asks for | State before | Evidence |
|---|---|---|
| select two areas | present | `conn-roomA` / `conn-roomB` |
| way node + 4 edges + defaults | present | `handle_build_connect_legacy` |
| hidden | present | `conn-state` option `👻 Hidden` |
| **name** | **missing** | `hasName: false`, no name field |
| **cardinal** | **missing** | `conn-dir1`/`conn-dir2` were free-text `INPUT` |
| **one-way** | **missing** | `hasOneWay: false` |

`one_way` was fully honoured by the engine all along — `movement.py:541`
(`raise ValueError(f"The {direction} is one-way — you can't go back that way.")`),
`npc_behaviors.py:776/849/888`, and the Way inspector's own checkbox
(`way-view.js:334`). Only the *create* form lacked it, so this is wiring
existing machinery, not a new mechanic.

## Changes

- `ui/create-modal.js` — `Way Name` field; a 10-entry cardinal `<datalist>` on
  both direction inputs (suggestions only, directions stay free text); a
  `One-way (Area A → B only)` checkbox in Way Behavior that disables + clears
  the B → A direction and explains the guard; Area B now defaults to the
  *second* area.
- `main.js` / `graph/event-handlers.js` — forward `name` + `one_way`; both
  callers reject `room1 === room2` with a toast.
- `routes/graph_ops.py` — `handle_build_connect_legacy` uses an authored
  `name`, falling back to the historical `"{room}-{dir}"`.

### Bug found while doing it

Both area selects defaulted to the first area, so submitting the form untouched
produced a **self-referential way** (Area A == Area B). Fixed by defaulting
Area B to the second area *and* rejecting the same-area case at submit.

## Verification — live browser, not unit tests

Second instance on port 4445 (the running 4444 server was left alone; it has no
auto-reload and holds a play session).

Created a door through the actual UI (`connectRoomsViaGraph`, not
`openCreateModal` bare — the latter takes no submit callback and silently does
nothing, which is what made my first attempt look like a failure):

- ways went **20 → 21**, header `21 ways · 240 loaded`, stream logged
  `Connected rooms`.
- New node `way_abandoned_hunter's_cabin_east`: `name: "Rope Ladder"` (the
  authored name won), `one_way: true`, `area_from: "Abandoned Hunter's Cabin"`,
  `area_to: "Bathroom"`, `current_state: open`.
- Way inspector → **Passage** tab shows `ONE-WAY` checked and `east` as the
  command from the cabin; the **Behavior** tab has no one-way row, so it is
  worth knowing it lives on Passage.
- Console clean apart from one 404 that was my own bad `fetch('/api/graph')`.

Gates: `npm run lint` clean · `npm run typecheck` clean · `node tools/unit/run.cjs`
465 passed / 0 failed · `pytest tests/test_movement.py test_way_connect_repair.py
test_way_orientation_cleanup.py test_way_gates.py test_way_blocking.py
test_area_id_case.py` → 107 passed.

## Known pre-existing issue, not introduced here

The Way inspector's one-way input id is built from a JS-escaped node id, so a
node id containing an apostrophe yields `way_abandoned_hunter\'s_cabin_east` —
a literal backslash in the id. Harmless for lookup but it breaks naive
`getElementById`. Untouched.

