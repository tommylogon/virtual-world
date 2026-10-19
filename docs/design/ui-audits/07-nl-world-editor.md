# Natural Language (NL) World Editor UI Audit & Redesign Specification

> **Status: UNVERIFIED DRAFT (2026-10-19).** Written from file headers and partial reads. Line counts, wireframes and several failure claims were NOT measured or reproduced live. Treat every claim here as a lead to check, not a finding. Verified findings live in the task cards, not in this document.


**Surfaces:**
- NL Editor UI (`static/js/nl-editor/ui.ts`) - 674 lines
- NL Staging & Diffs (`static/js/nl-editor/staging.ts`, `diff.ts`) - 580 lines
- Ghost Nodes Canvas Overlay (`static/js/nl-editor/ghosts.ts`) - 410 lines
- Agent Loop Controller (`static/js/nl-editor/agent-loop.ts`) - 720 lines
**Rendering Tech:** Lit-html & DOM side-panel mounted in `#left-tab-nl-editor` with ghost projections on vis.js canvas.

---

## 1. Measured Ground Truth & Architecture

The NL Editor allows authors to mutate the WorldGraph using natural language prompts (e.g., *"Add a secret tunnel from the wine cellar to the forest clearing, locked with an iron grate"*).

### The Staging & Diff Architecture
- Prompts execute through an LLM agent loop that emits structured mutation operations (`create_node`, `connect_way`, `set_property`, `delete_node`).
- **Safety Guarantee:** Operations are never committed directly to the graph. They land in `staging.ts` as staged ops.
- `ghosts.ts` renders translucent projected "ghost" nodes on the vis.js canvas so the author can see where the new rooms and connections will land in space before accepting.

---

## 2. Usability & Layout Critique

### A. Context Payload Bloat (task-752)
- In early versions, every prompt sent the entire world graph (all 627 areas and 1,200 edges) to the LLM prompt context, blowing through token budgets and taking 12-15 seconds per turn.
- While task-752 scoped the summary to selected areas, the UI lacks an explicit "Context Scope" indicator. The author cannot see which rooms are currently in the LLM's working memory.

### B. Ghost Node Drift
- When ghost nodes are projected onto the canvas, if physics simulation is running, settled nodes drift while ghost nodes remain fixed at static coordinates, causing visual disconnection between ghost seams and real rooms.

### C. Selective Apply Cherry-Picking Hazards
- `ui.ts` allows authors to check/uncheck individual operations in the staged tray (`this._checked.set(op.id, bool)`).
- If an author checks `create_way (Cellar -> Tunnel)` but unchecks `create_node (Tunnel)`, clicking Apply results in an orphaned edge error that crashes the backend compiler.

---

## 3. Redesign Specification & Layout Blueprint

### Target Layout: The AI World Architect Panel

```
+----------------------------------------------------------------------------------------------------+
| 🪄 NATURAL LANGUAGE EDITOR                                              [ Context: 4 Areas | ▾ ]   |
+----------------------------------------------------------------------------------------------------+
| CHAT CONVERSATION STREAM (Scrollable)                                                              |
|                                                                                                    |
| 👤 Author: "Add a sunken tomb under the graveyard with a stone sarcophagus."                      |
|                                                                                                    |
| 🤖 Architect: "I've drafted 2 new areas and a traversal way:                                       |
|    1. Crypt Entrance (Area, dark, stone floor)                                                     |
|    2. Ancient Sarcophagus Chamber (Area, contains 'Stone Sarcophagus')                             |
|    3. Stone Stairway Way (Down: Graveyard -> Crypt Entrance, requires light)"                     |
|                                                                                                    |
+----------------------------------------------------------------------------------------------------+
| STAGED MUTATIONS TRAY (Ghost Nodes Active on Canvas)                                               |
|                                                                                                    |
| [x] + Area: Crypt Entrance (Coordinates: x=12, y=8)                                                |
| [x] + Area: Sarcophagus Chamber (Coordinates: x=12, y=9)                                           |
| [x] + Item: Stone Sarcophagus (Container: 4 slots)                                                 |
| [x] + Way: Graveyard ◄──[ Stairway (Darkness Gate) ]──► Crypt Entrance                            |
|                                                                                                    |
| Dependency Check: ✓ Clean (No dangling references)                                                 |
+----------------------------------------------------------------------------------------------------+
| INPUT & ACTIONS                                                                                    |
| [ Describe world changes, additions, or renames...                             ]                   |
|                                                                                                    |
| Token Budget: [ 3.2k / 16k used ]     [ ✕ Discard All ]    [ ✓ Commit Staged Changes (4 Ops) ]     |
+----------------------------------------------------------------------------------------------------+
```

### Core Architecture Upgrades

1. **Dependency Validation on Selective Apply**
   - In `staging.ts`, enforce graph topological ordering: unchecking a node creation automatically disables any way connections that reference that node ID.

2. **Visible Context Token Meter**
   - Provide a clear pill showing which parent scope or selected nodes are included in the LLM's prompt context.
