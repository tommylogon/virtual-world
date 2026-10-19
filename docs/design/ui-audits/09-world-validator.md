# World Validator & Sanity Triage UI Audit & Redesign Specification

> **Status: UNVERIFIED DRAFT (2026-10-19).** Written from file headers and partial reads. Line counts, wireframes and several failure claims were NOT measured or reproduced live. Treat every claim here as a lead to check, not a finding. Verified findings live in the task cards, not in this document.


**Surfaces:**
- Validator Panel (`static/js/validator-panel.ts`) - 624 lines
- Scenario Status (`static/js/ui/scenario-status.ts`) - 210 lines
**Rendering Tech:** Lit-html mounted into `#validator-panel` drawer.

---

## 1. Measured Ground Truth & Architecture

Runs static and topological analysis on the active scenario via `GET /api/triggers/validate`.
- **12 Registered Issue Codes (lines 36-49):**
  - `empty_trigger`, `orphan_trigger_edge`, `dangling_trigger_edge`, `trigger_edge_wrong_target_type`, `stale_trigger_copy`, `missing_effect_item`
  - `way_missing_pass_message`, `way_missing_cardinal`, `way_missing_view_direction`
  - `mechanical_tag_missing_props`, `library_mismatch`, `orphaned_node`
- **Dismissal Persistence:** Dismissing an issue writes `ignored_issues: [code]` into the node's properties so it survives reloads.

---

## 2. Usability & Layout Critique

### A. The 254-Issue Wall of Text
- In large scenarios, opening the validator presents a massive scrollable list with 250+ individual rows.
- While "Group by Code" collapses identical categories, authors lack an actionable visual map showing *where* these errors are geographically clustered.

### B. Broken Quick-Fix Reversibility
- The "Fix All" button executes bulk string fixes (e.g. populating missing cardinal directions with defaults).
- However, if the algorithm guesses wrong (e.g. assigning "north" to a diagonal corridor), there is no single-click batch undo from within the panel.

---

## 3. Redesign Specification & Layout Blueprint

### Target Layout: World Health Inspector

```
+----------------------------------------------------------------------------------------------------+
| 🛡️ WORLD SANITY & TRIAGE                                              [ ⟳ Run Audit ] [ Close ]   |
+----------------------------------------------------------------------------------------------------+
| HEALTH SCORE: 88 / 100                                                                             |
| [============================================================------] 12 Warnings · 2 Errors        |
+----------------------------------------------------------------------------------------------------+
| TRIAGE MODES: [ Group by Severity ]  [ Group by Scope ]  [ Group by Issue Code ]                   |
| Filter Type:  [ All Nodes ▾ ]        Show Dismissed: [ ]                                           |
+----------------------------------------------------------------------------------------------------+
| ACTIVE ISSUES LIST                                                                                 |
|                                                                                                    |
| ✕ CRITICAL ERRORS (Must fix before compile)                                                        |
|   ├── 📍 Way: cellar_to_tomb                                                                       |
|   │   Target area 'tomb_chamber' does not exist in graph!                                          |
|   │   [ 🔍 Jump to Node on Canvas ]  [ 🗑 Delete Way ]                                              |
|                                                                                                    |
| ⚠ TOPOLOGY WARNINGS                                                                                |
|   ├── 📦 Item: rusted_key_01 (Orphaned Node)                                                       |
|   │   Node has no containment edge and no area parent. Floating in void.                           |
|   │   [ 📍 Drop in Selected Area ]   [ 🗑 Remove Item ]                                             |
|                                                                                                    |
| ℹ INFORMATIONAL NUDGES                                                                             |
|   ├── 🚪 14 outdoor ways missing 'cardinal' orientation                                            |
|   │   [ ⚙ Auto-Assign from Spatial Coordinates (Batch Fix) ]                                       |
+----------------------------------------------------------------------------------------------------+
```

### Core Architecture Upgrades

1. **Spatial Heatmap Overlay**
   - Provide a toggle `[ Highlight Errors on Canvas ]` that tints invalid nodes and disconnected ways in bright red/yellow on the vis.js network view.

2. **Scoped Batch Fixes**
   - Allow "Fix All" to run per-scope (e.g. fix only ways inside `Eldenford Town`) instead of forcing an irreversible world-wide batch commit.
