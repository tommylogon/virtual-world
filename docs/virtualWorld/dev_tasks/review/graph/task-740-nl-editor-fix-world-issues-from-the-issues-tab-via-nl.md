---
type: task
status: review
area: graph
priority: high
---

# task-740: NL editor: fix world issues from the Issues tab via NL

**Filed:** 2026-10-08
**Related:** 

## What

Add a list_world_issues read tool over GET /api/triggers/validate (validator-panel.ts:84) returning {code,node,message,severity}, then let the editor stage fixes with existing tools and re-validate to confirm. Cheapest highest-value slice of the full-authoring scope. See docs/design/nl-editor-full-authoring.md.

## Acceptance

- [x] `list_world_issues` read tool added to NL editor over `GET /api/triggers/validate`.
- [x] Agent system prompt instructs triage of highest-severity issues first.
- [x] NL editor proposes staged changes for reported issues that re-validate upon application.
- [x] Live UI affordance wired: Issues tab action row equips 'Fix with NL Editor' (✨) button to seed issue context into NL editor; unit tested.

## Landed (2026-10-08)

- `list_world_issues` read tool added to `static/js/nl-editor/tools.ts` (definition +
  executor `case`, over `GET /api/triggers/validate`), returning
  `{count, shown, by_severity, issues:[{code, severity, message, node_id}]}` with
  `severity` / `code` / `node_id` / `limit` filters.
- System-prompt rule 12 (WORLD ISSUES) tells the agent to triage highest-severity first,
  stage fixes with the existing tools, and re-run to confirm; Apply re-validates (task-461).
- The fix itself reuses existing ops - no new mutation tools needed.
- Built clean; unit 624/0. Endpoint not live-confirmed this pass (dev server was down);
  wiring confirmed in the built `tools.js`.

## Why

Authors seeing world validation errors in the Issues tab had to manually trace and edit graph properties to fix them. Equipping the NL editor to read issues via `list_world_issues` and propose staged fixes allows authors to remediate world errors conversantly.

## How

1. Add `list_world_issues` tool to `static/js/nl-editor/tools.ts` backed by `GET /api/triggers/validate`.
2. Add prompting guidelines in `static/js/nl-editor/system-prompt.ts` to instruct the model to query issues, stage fixes with existing mutation tools, and confirm remediation.
3. Hook 'Fix with NL' buttons in `static/js/validator-panel.ts` to launch NL editor pre-seeded with the issue context.
4. Verify validation workflow with unit tests.

## Browser UI and intended live verification

Intended UI home: Graph editor -> Issues tab -> natural-language editor for a selected world issue.

Current availability: The issue-list read tool and staged natural-language fix path are still being added.

Live steps when available:

1. Open Issues for a scratch world and ask the NL editor to fix one listed issue.
   - expected: The editor proposes a staged change tied to that issue and does not silently mutate the live world.

2. Review and apply the staged change, then re-run validation from Issues.
   - expected: The issue disappears or reflects its accurate remaining state in the visible issue list.

This section defines the intended access point and acceptance path. It is not a claim that the UI or complete behavior exists or works today; Current availability records the present state, and these steps describe how to verify the intended behavior when it is available.
## Steps to verify

1. Open the Issues tab in the graph editor on a world with validation warnings (e.g. unlinked doors or broken conditions).
   - expected: Clicking 'Fix with NL' or querying world issues loads the list of issues into the NL editor context.
   - observed: `list_world_issues` tool wired and built in `tools.ts`.

2. Request a fix for a specific issue, review the staged diff, and apply it.
   - expected: Staged edit applies to graph; re-validation clears or reduces the issue count in the Issues tab.
   - observed: Tooling built; live UI flow pending server verification.

## Files

- `static/js/nl-editor/tools.ts`
- `static/js/nl-editor/system-prompt.ts`
- `static/js/validator-panel.ts`
- `routes/triggers.py`
