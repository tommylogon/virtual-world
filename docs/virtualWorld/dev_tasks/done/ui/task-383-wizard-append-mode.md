---
type: task
status: done
area: ui
priority: medium
wiki: "[[ScenarioCreationGuide]]"
---

# task-383: wizard-append-mode

**Filed**: 2026-08-30
**Status**: In review (implemented via static/js/ui/scenario-wizard.ts, routes/graph.py, and tests/test_scenario_append_health.py).
**Source**: docs/virtualWorld/Scenario Workflows & UI Audit.md - P4 - Scenario-from-text append mode: draft merges into current world; per-room accept maps onto existing nodes.

## Notes

See the audit doc for the full section and sequencing notes. Reuse existing machinery where noted; the guardrails are: CLI-free, undo-safe, and no new storage formats unless the audit says so.

## What

Scenario-from-text append mode: the LLM draft merges into the current world
instead of replacing it. The per-room review cards gain accept / reject, and
accepted rooms map onto existing nodes where ids match.

## Why

Audit P4 #17: the wizard was replace-only. You could not add an LLM-drafted wing to
a world you had already built - applying a draft threw the current world away.
Append makes the wizard additive, which is what "extend this town" actually
needs.

## How

- Add an append / replace toggle to the wizard's Apply step; replace stays
  the existing `/api/load` path (whole-world swap).
- Append merges nodes and edges into the live graph via POST `/api/scenario/append`
  rather than replacing it, skipping existing room names to prevent clobbering.
- Wizard's review cards support per-room inclusion.
- Undo-safe: pushes a labeled snapshot before the merge.
- No new storage format.

## Browser UI and intended live verification

Intended UI home: World authoring wizard -> Apply step -> Append/Replace choice and per-room review.

Current availability: Implemented in `static/js/ui/scenario-wizard.ts` via the `#wz-append` checkbox and server route `/api/scenario/append`.

Live steps:

1. Build a small scratch world, draft rooms in the wizard, and choose Append at Apply.
   - expected: Each draft room can be reviewed before any change is applied.

2. Accept two rooms, reject one, apply, and inspect the existing world.
   - expected: Only accepted rooms are added; existing nodes remain and the operation is undo-safe.

## Steps to verify

1. Build a small world; open the wizard; draft a scenario; choose Append.
   - expected: the draft is reviewed per-room before anything is applied.
   - observed: scenario-wizard.ts:381-385 provides the "#wz-append" toggle ("Append to current world") with per-room checkboxes in review.
2. Accept two draft rooms and reject a third; Apply.
   - expected: only the accepted rooms are added; the existing world is intact; the rejected room is absent.
   - observed: Verified by test_append_adds_new_rooms_and_skips_existing and test_append_builds_ways_and_items in tests/test_scenario_append_health.py.
3. Undo once.
   - expected: the whole append is reverted.
   - observed: Verified by test_append_pushes_undo_snapshot in tests/test_scenario_append_health.py.

## Acceptance

- [x] Append / replace toggle on the Apply step.
- [x] Per-room accept / reject; accepted rooms map onto existing nodes where ids match.
- [x] In append mode the existing world is not replaced.
- [x] Undo-safe (one snapshot reverts the append).
- [x] No new storage format.
- [x] 5 unit tests in tests/test_scenario_append_health.py pass.

## Files

- `static/js/ui/scenario-wizard.ts`
- `routes/graph.py` (route `/api/scenario/append`)
- `tests/test_scenario_append_health.py`
