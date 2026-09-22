---
type: task
status: review
area: graph
priority: medium
---

# task-459: NL editor roster and aggregate reads

**Filed:** 2026-09-22
**Related:** task-458, task-457

## Goal

Give the NL editor real read coverage of the cast and contents: a list_characters / list_nodes tool with kind+tag+area filters, counts and pagination; extend list_world_summary beyond areas; support 'who is in area X' and relation traversal ('all characters with an in edge to area_x'). Complements search_graph_nodes (currently capped at 15 and without roster/aggregate semantics).

## Acceptance

- [x] `list_nodes` tool: `kind`, `tags`/`tag` (+ `require_all_tags`), `area`
      (nodes with an `in` edge to it — "who is in area X"), `name_contains`,
      with a total `count` and `page`/`page_size`/`pages` (`static/js/nl-editor/tools.js`).
- [x] Selector core `OverlayGraphView.matchNodes` is shared with
      `update_matching_nodes`, so the reviewed affected set and a roster read
      use one definition and one server-mirrored shape.
- [x] `list_world_summary` extended beyond areas: per-type counts and a
      character roster with current area.
- [x] Relation traversal ("all characters with an `in` edge to area_x") is the
      `area` filter on the same selector.
- [x] Prompt guidance updated (agent-loop rule 9) so the agent prefers
      `list_nodes` for roster/aggregate reads over the fuzzy, 15-capped
      `search_graph_nodes`.
- [x] Tests: `tools/unit/test_nl_editor.js` (`matchNodes` by kind/tag, area,
      explicit ids).

