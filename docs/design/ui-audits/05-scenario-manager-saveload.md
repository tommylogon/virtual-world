# Scenario Manager & Save/Load UI Audit & Redesign Specification

> **Status: UNVERIFIED DRAFT (2026-10-19).** Written from file headers and partial reads. Line counts, wireframes and several failure claims were NOT measured or reproduced live. Treat every claim here as a lead to check, not a finding. Verified findings live in the task cards, not in this document.


**Surfaces:**
- Scenario Manager Modal (`static/js/ui/scenario-manager.ts`) - 449 lines
- Save / Load View (`static/js/ui/saveload-view.ts`) - 390 lines
- Scenario Status Indicator (`static/js/ui/scenario-status.ts`) - 210 lines
**Rendering Tech:** Lit-html modal dialog mounted into `#scenario-manager-modal`.

---

## 1. Measured Ground Truth & Architecture

Controls scenario persistence, loading, cloning, and snapshotting under `data/scenarios/*.json`.
- **API Endpoints:**
  - `GET /api/scenarios` - Enumerates saved scenario files with area/player counts.
  - `POST /api/scenarios/load` - Swaps active world graph with target scenario.
  - `POST /api/scenarios/save` - Serializes current WorldGraph to disk.
  - `POST /api/scenarios/reset` - Reverts scenario to its clean authored baseline.

### Filter & Search State
- `task-598` improved filter retention: `_filterText` and `_filterOpts` survive re-renders.
- Multi-token fuzzy matching compares input against filename, scenario name, and area/player counts.

---

## 2. Usability & Layout Critique

### A. The "Silent Overwrite" Risk
- Saving an existing scenario lacks a clear visual diff between current simulation state and what is stored on disk.
- If an author made temporary debug edits or ran 50 ticks of background combat, clicking `Save` immediately commits dead bodies, changed vitals, and decayed items directly over the clean authored template.
- There is no distinction between "Save Authoring Template" vs "Save Simulation Checkpoint".

### B. Obscure Audit Icons (task-641)
- Each scenario card displays tiny badge icons for validator health (`✓`, `!`, `✕`).
- Clicking `Audit` runs the backend validator, but the output renders as an unformatted raw JSON log inside a nested preformatted box. Authors cannot tell if an error is a critical broken reference or a minor missing description.

### C. Reset Confusion
- The `Reset` button provides a generic browser `confirm("Are you sure?")`.
- It fails to state *which* scenario is being reset, what timestamp it will revert to, and that uncommitted in-memory changes will be irreversibly erased.

---

## 3. Redesign Specification & Layout Blueprint

### Target Layout: The Scenario Hub

```
+----------------------------------------------------------------------------------------------------+
| 📁 SCENARIO MANAGER                                                    [ + New Blank Scenario ] [X] |
+----------------------------------------------------------------------------------------------------+
| Search & Filters:                                                                                  |
| [ 🔍 Search by name, tags, or area count...                  ]  Sort: [ Last Modified ▾ ]          |
| Filter: [ All Types ▾ ]  Status: [ All ▾ ]  Health: [ Clean Only ▾ ]                              |
+----------------------------------------------------------------------------------------------------+
| SCENARIO CARDS GRID                                                                                |
|                                                                                                    |
| ┌──────────────────────────────────────────┐ ┌──────────────────────────────────────────┐         |
| │ 🏰 Eldenford Regional Valley    [ACTIVE] │ │ 🌲 Deep Woods & Goblin Camp              │         |
| │ File: data/scenarios/Eldenford.json      │ │ File: data/scenarios/Goblin_Camp.json     │         |
| │ Modified: 12 minutes ago                 │ │ Modified: Yesterday 18:40                │         |
| │                                          │ │                                          │         |
| │ • Areas: 42 across 3 scopes              │ │ • Areas: 18 in 1 scope                   │         |
| │ • Characters: 14 (3 Human, 11 NPC)       │ │ • Characters: 8 (All NPC)                │         |
| │ • Validator: ✓ Clean (0 warnings)        │ │ • Validator: ⚠ 2 unlinked ways           │         |
| │                                          │ │                                          │         |
| │ [ ↺ Revert to Authored ] [ 💾 Save As ]  │ │ [ ▶ Load Scenario ]  [ 📋 Duplicate ]    │         |
| └──────────────────────────────────────────┘ └──────────────────────────────────────────┘         |
+----------------------------------------------------------------------------------------------------+
| ACTIVE WORLD FOOTER:                                                                               |
| Currently Running: Eldenford Regional Valley · Unsaved Changes: 14 node mutations · [ Save Now ]   |
+----------------------------------------------------------------------------------------------------+
```

### Core Architecture Upgrades

1. **Clear Split: Authoring Master vs Play Savegame**
   - Provide explicit save actions:
     - `Save Template`: Strips runtime combat state, vital decay, and runtime queues; preserves authored layout.
     - `Save Play Snapshot`: Preserves active turn queue, memory dynamics, and current vitals.

2. **Visual Pre-flight Audit Summary**
   - Replace raw validator text dumps with structured pill badges:
     `[✓ 0 Broken Ways] [✓ Valid Topology] [⚠ 1 Unnamed Area]`.
