---
type: task
status: todo
area: triggers
priority: medium
---

# task-502: Trigger graph condition group nodes (AND/OR/NOT) and editable imported groups

**Filed:** 2026-09-24
**Related:** task-501, task-388

## Goal

Give OR/NOT condition groups a real node representation so an imported group is editable instead of refused by task-501's compile guard.

## Context

task-501 made the trigger graph honest about OR/NOT condition groups: an imported
group is stored on the trigger node (`condition_tree`) and re-emitted unchanged,
and editing its conditions is *refused* because the node graph only draws a
linear AND chain. This task gives groups a real node so they can be edited.

## Acceptance

- A condition node can represent a logical group (`and`/`or`/`not`) with child
  conditions, rendered and wired in the graph.
- An imported `condition_tree` round-trips through the graph and back without the
  `condition_tree` side-channel; editing a grouped condition is supported and
  the compile reflects the edit.
- `compileToEngine` no longer needs the "grouped condition edited" refusal once
  groups round-trip; the task-501 refusal is removed or narrowed to genuinely
  unrepresentable shapes.
- JS unit coverage for group add/edit/delete and for compiling each operator;
  `node --check` clean; `npm run lint`/`typecheck` clean.

## Non-goals

- Engine-side condition evaluation — already supports and/or/not.
- Blueprint runtime materialisation (task-442).
