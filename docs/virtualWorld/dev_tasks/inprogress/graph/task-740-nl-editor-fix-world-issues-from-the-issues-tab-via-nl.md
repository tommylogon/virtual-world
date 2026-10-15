---
type: task
status: inprogress
area: graph
priority: high
---

# task-740: NL editor: fix world issues from the Issues tab via NL

**Filed:** 2026-10-08
**Related:** 

## What

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

## Why

TODO

## How

TODO

## Browser UI and intended live verification

Intended UI home: Graph editor → Issues tab → natural-language editor for a selected world issue.

Current availability: The issue-list read tool and staged natural-language fix path are still being added.

Live steps when available:

1. Open Issues for a scratch world and ask the NL editor to fix one listed issue.
   - expected: The editor proposes a staged change tied to that issue and does not silently mutate the live world.

2. Review and apply the staged change, then re-run validation from Issues.
   - expected: The issue disappears or reflects its accurate remaining state in the visible issue list.

This section defines the intended access point and acceptance path. It is not a claim that the UI or complete behavior exists or works today; Current availability records the present state, and these steps describe how to verify the intended behavior when it is available.
## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO
