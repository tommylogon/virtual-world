---
group: UI - NPC Behaviors
---

# Behavior Editor — Align with Trigger Graph Editor UX

**Filed**: 2026-08-14
**Priority**: High
**Status**: Cancelled — superseded by task-226 (Unified Behavior/State Machine Graph Editor)

## Why cancelled

This task's premise was "bring the trigger-graph node editor UX to behavior
editing". That is exactly what task-226 built (2026-08-23): the shared
`trigger-graph.js` extended with behavior-mode nodes — Behavior / Condition /
Action / State — compileToBehaviors()/behaviorsToGraph(), drag-reorder for
priority, copy/duplicate, live-verified save round-trip.

The flat `behaviors-view.js` form still exists alongside it (toggle views),
and the compound-condition plain-JSON area remains for authors who prefer it,
but the graph editor is the modern path. Any remaining gaps (blueprint mode,
dry-run) are tracked in task-226's deferred list.
