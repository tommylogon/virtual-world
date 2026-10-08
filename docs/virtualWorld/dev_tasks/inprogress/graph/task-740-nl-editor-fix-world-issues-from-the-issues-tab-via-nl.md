---
type: task
status: inprogress
area: graph
priority: high
---

# task-740: NL editor: fix world issues from the Issues tab via NL

**Filed:** 2026-10-08
**Related:** 

## Goal

Add a list_world_issues read tool over GET /api/triggers/validate (validator-panel.ts:84) returning {code,node,message,severity}, then let the editor stage fixes with existing tools and re-validate to confirm. Cheapest highest-value slice of the full-authoring scope. See docs/design/nl-editor-full-authoring.md.

## Acceptance

- TODO

## Landed (2026-10-08)

- `list_world_issues` read tool added to `static/js/nl-editor/tools.ts` (definition +
  executor `case`, over `GET /api/triggers/validate`), returning
  `{count, shown, by_severity, issues:[{code, severity, message, node_id}]}` with
  `severity` / `code` / `node_id` / `limit` filters.
- System-prompt rule 12 (WORLD ISSUES) tells the agent to triage highest-severity first,
  stage fixes with the existing tools, and re-run to confirm; Apply re-validates (task-461).
- The fix itself reuses existing ops — no new mutation tools needed.
- Built clean; unit 624/0. Endpoint not live-confirmed this pass (dev server was down);
  wiring confirmed in the built `tools.js`.

