---
type: task
status: inprogress
area: ui
priority: medium
---

# task-383: wizard-append-mode

**Filed**: 2026-08-30
**Status**: Not started (card complete; no implementation yet).
**Source**: docs/virtualWorld/Scenario Workflows & UI Audit.md — P4 — Scenario-from-text append mode: draft merges into current world; per-room accept maps onto existing nodes.

## Notes

See the audit doc for the full section and sequencing notes. Reuse existing machinery where noted; the guardrails are: CLI-free, undo-safe, and no new storage formats unless the audit says so.

## What

Scenario-from-text append mode: the LLM draft merges into the current world
instead of replacing it. The per-room review cards gain accept / reject, and
accepted rooms map onto existing nodes where ids match.

## Why

Audit P4 #17: the wizard is replace-only. You cannot add an LLM-drafted wing to
a world you have already built — applying a draft throws the current world away.
Append makes the wizard additive, which is what "extend this town" actually
needs.

## How

- Add an append / replace toggle to the wizard's Apply step; **replace** stays
  the existing `/api/load` path (whole-world swap).
- Append needs a merge path that ADDS nodes / edges to the live graph rather
  than replacing it, mapped onto existing node ids where they match
  (per-room accept).
- Reuse the wizard's review cards; each room is accept / reject.
- Undo-safe: push a labeled snapshot before the merge.
- No new storage format.

## Browser UI and intended live verification

Intended UI home: World authoring wizard → Apply step → Append/Replace choice and per-room review.

Current availability: Append mode and its review/apply flow are still in progress.

Live steps when available:

1. Build a small scratch world, draft rooms in the wizard, and choose Append at Apply.
   - expected: Each draft room can be reviewed before any change is applied.

2. Accept two rooms, reject one, apply, and inspect the existing world.
   - expected: Only accepted rooms are added; existing nodes remain and the operation is undo-safe.

This section defines the intended access point and acceptance path. It is not a claim that the UI or complete behavior exists or works today; Current availability records the present state, and these steps describe how to verify the intended behavior when it is available.
## Steps to verify

1. Build a small world; open the wizard; draft a scenario; choose Append.
   - expected: the draft is reviewed per-room before anything is applied.
   - observed: TODO
2. Accept two draft rooms and reject a third; Apply.
   - expected: only the accepted rooms are added; the existing world is intact; the rejected room is absent.
   - observed: TODO
3. Undo once.
   - expected: the whole append is reverted.
   - observed: TODO

## Acceptance

- [ ] Append / replace toggle on the Apply step.
- [ ] Per-room accept / reject; accepted rooms map onto existing nodes where ids match.
- [ ] In append mode the existing world is not replaced.
- [ ] Undo-safe (one snapshot reverts the append).
- [ ] No new storage format.

## Files

- `static/js/scenario-wizard.ts` (and the review-card UI).
- `routes/` — a merge / append path distinct from `/api/load`.
- `tests/`.
