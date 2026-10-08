---
type: task
status: todo
area: graph
priority: high
---

# task-739: NL editor: full trigger + behaviour authoring (conditions/effects, compiled and validated)

**Filed:** 2026-10-08
**Related:** 

## Goal

create_node can mint an empty logic_trigger but the editor cannot author its logic. Expose the existing condition/effect schema and the graph->behaviour compile (shared/trigger-graph.ts compileToBehaviorsWithIssues) so the editor can create AND validate a trigger. Reuse engine/triggers; do not invent a second format. See docs/design/nl-editor-full-authoring.md.

## Acceptance

- TODO
