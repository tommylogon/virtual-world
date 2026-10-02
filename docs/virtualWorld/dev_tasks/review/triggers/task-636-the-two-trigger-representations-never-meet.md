---
type: task
status: review
area: triggers
priority: high
---

# task-636: The two trigger representations never meet

**Filed:** 2026-09-30
**Related:** 

## Goal

logic_trigger nodes and trigger arrays on items coexist with no compiler between them in the UI, so a mechanic authored one way is invisible the other way.

## Interpretation (2026-10-02)

A trigger is physically stored twice: on the `triggers` **edge** and on the
target `logic_trigger` **node**. The engine reads the edge first and falls back
to the node (`engine/triggers/execution.py`). Each UI surface previously read
only one copy — `item-library._extractTriggersFromEdges` read the edge,
`trigger-helpers._getNodeTriggerData` read the node — so the two representations
had no single compiler and could disagree invisibly.

## Acceptance (implemented 2026-10-02)

- [x] One graph→definition compiler, `TriggerGraph.triggerDefFromEdge(edge,
      nodes)` / `TriggerGraph.triggersFromGraphEdges(edges, nodes, sourceId)`:
      merges both copies with the engine's precedence (edge wins, node
      fallback), normalises `effects[]` vs legacy `effect_type/effect_params`,
      and normalises tree / flat-list / singular conditions.
- [x] The item library (`_extractTriggersFromEdges`) and the inspector
      (`_openGraphEditor`, `_getNodeTriggerData`, `buildTriggersHtml`,
      `_applyTriggerDiff`) all derive their trigger sets from that compiler —
      no surface reads one copy directly any more.
- [x] The reverse direction already existed (`TriggerGraph.triggerToGraph` +
      `compileToEngine`), so inline array → graph → array round-trips.
- [x] `node tools/unit/run.cjs` green, incl. `test_trigger_representations.js`
      (edge-only, node-only, edge-wins-per-field, flat→tree, singular→AND,
      legacy effect, full OR round-trip, source/type filtering).

## Remaining / not in this slice

- Trigger **arrays** in library JSON are still the authoring source and the
  graph nodes the runtime source; a linked world node is exported to the
  library via the shared compiler on "Save to library", not continuously.
- The inspector graph editor still edits the **first** trigger of a node
  (warns and defers the rest to ✏️) — a separate UX limitation.
- No data migration was attempted for already-divergent edge/node copies; the
  compiler defines which one wins if they disagree.

## Evidence

- Commit `9a0348f`; `node tools/unit/run.cjs` = 497 passed / 0 failed.
