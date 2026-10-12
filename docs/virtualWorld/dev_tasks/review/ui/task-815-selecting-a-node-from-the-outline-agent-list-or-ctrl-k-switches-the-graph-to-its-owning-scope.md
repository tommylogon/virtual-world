---
type: task
status: review
area: ui
priority: high
wiki: "[[World Scopes]]"
---

# task-815: Selecting a node from the outline, agent list or Ctrl+K switches the graph to its owning scope

**Filed:** 2026-10-12
**Related:** 

## What

Selecting a character, item, area or way from the outline (tree-view), the agent list (selectAgent) or the Ctrl+K command palette only moved the camera: graph-manager.focusNode fell back to fitView() when the node was not in the loaded scope, so the inspector showed the node while the graph never did. focusNode now resolves the node owning scope from the whole-world graph (worldState.graph) and switches to it, focusing once that scope subgraph has loaded. Known limitation, intentionally not handled: a node that resolves to the CURRENT scope but is still absent from the loaded subgraph (a level-scoped projection that excluded it) does not reload, so it is left unfocused rather than shown.

## Why

The graph loads one scope at a time (task-397/400), so a node in another scope is not in graphManager.nodes. Selecting it from the outline, the agent list or Ctrl+K set the inspector correctly but left the graph on the wrong scope; the old fallback (fitView) showed an unrelated subgraph. The owning scope is already derivable from data /api/state ships: world_scope_id / generated.scope_id on the node, or the containment chain up to the area that declares one. No new endpoint is needed.

## How

Add ScopeOptions.resolveScopeForNode(nodeId, nodes, edges) in shared/scope-options.ts: read the node own declaration via the canonical ScopeOptions.nodeScopeId, else walk the spatial edges (in/on/under/behind/at, NOT beside/carrying/equipped/connection/triggers) up to a node that declares a scope; cycle-safe and bounded (12 hops). graph-manager.focusNode resolves against worldState.graph (the whole world, not the loaded map) and calls setScopeFilter(scope), focusing after the subgraph loads. GraphLayoutEngine.nodeScopeId now delegates to ScopeOptions.nodeScopeId so the declaration read has one home.

Follow-up fix (2026-10-12, found live): setScopeFilter never updated the #graph-scope-filter picker — only GraphToolbar.loadScope did, and it did so before calling here. focusNode calls setScopeFilter DIRECTLY, so the graph loaded the new scope while the dropdown kept the old label. That is exactly the operator report "scope did not change, but the nodes did appear". setScopeFilter now sets the picker value itself (one home for it, mirroring what loadScope used to do), and loadScope's duplicate write is removed.

## Steps to verify

1. Load a multi-scope scenario (kraktooth goblin camp). Pick a scope OTHER than the one a known character lives in.
   - expected: the character is not on the visible graph (it belongs to another scope)
   - observed: operator 2026-10-12 — confirmed; the camp characters are absent from the world scope
2. Press Ctrl+K, type the character/area name, select the entry.
   - expected: the graph switches to the owning scope, selects the node and centres it
   - observed: TODO
3. Repeat the selection from the Outline panel and from the Agent list.
   - expected: same scope switch and focus from all three entry points
   - observed: operator 2026-10-12 — from the Agent list the graph DID switch (the camp nodes appeared) but the picker LABEL stayed on world. That was the setScopeFilter picker bug, now fixed; re-check that the picker now reads the new scope.
4. Select a node with no declared scope and no spatial parent (a free-floating inventory item).
   - expected: the scope is left unchanged; the old fit-all fallback runs
   - observed: TODO
5. After a switch, check whether the camera lands on the node's settled position.
   - expected: the node is centred where it finally sits, not at a transient pre-settle position
   - observed: operator 2026-10-12 — the nodes move on the scope load (the full-load re-seed, task-764); watch whether the focus lands correctly

## Acceptance

- [x] `node tools/unit/run.cjs` green, including the new test_scope_options.js resolveScopeForNode cases (own scope, generated fallback, containment walk, in-before-at priority, beside/carrying/equipped/connection/triggers excluded, cycle-safe, hop cap, Map input).
- [x] `GraphLayoutEngine.nodeScopeId` delegates to `ScopeOptions.nodeScopeId`; test_graph_layout_engine.js and test_scope_options.js both green.
- [ ] Live: selecting a node in another scope from the outline, the agent list or Ctrl+K switches the graph scope and focuses the node. (The agent-list switch works and the picker fix now reflects it; Ctrl+K and outline still to confirm.)
- [ ] Live: a scope-less node leaves the current scope unchanged (fallback, no switch).

## Files

static/js/shared/scope-options.ts
static/js/graph-manager.ts
static/js/graph/toolbar.ts
static/js/graph/layout-engine.ts
tools/unit/test_scope_options.js
