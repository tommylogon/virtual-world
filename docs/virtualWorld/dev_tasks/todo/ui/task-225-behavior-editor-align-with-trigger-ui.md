---
group: UI - NPC Behaviors
---

# Behavior Editor — Align with Trigger Graph Editor UX

**Filed**: 2026-08-14
**Priority**: High
**Status**: Todo

---

## Problem

The behavior editor (`static/js/inspector/behaviors-view.js`) uses a legacy flat-form pattern that doesn't match the modern trigger graph editor's capabilities:

1. **Conditions are either flat or raw JSON** — simple mode supports one leaf condition; compound mode forces manual JSON editing. No visual subtree builder. The backend supports ~25 condition types but the UI only exposes 8 (17 hidden: `vital_above`, `vital_below`, `vital`, `uses_reached`, `uses_above`, `sound_heard`, `speech_matches`, `has_items`, `state_equals`, `skill_check`, `save_throw`, `temperature_below`, `temperature_above`, `area_temp`, `is_equipped`, `time_of_day`, `weather`).

2. **No drag-and-drop reordering** of actions or behaviors. Actions execute in insertion order only.

3. **No copy/duplicate behavior** — users must manually recreate similar behaviors.

4. **No preview/test** — you deploy and hope it works.

5. **Modal not draggable**, no keyboard shortcuts, inline styles everywhere.

6. **State machines are implicit** — transitions happen via `set_npc_state` actions scattered across behaviors. There's no visual state diagram showing how states relate.

The trigger graph editor (`trigger-graph.js`) already has a proven node-based paradigm: drag nodes from context menu, wire them together, edit inline properties. This task brings that same UX to behavior editing without losing any existing functionality.

---

## Design Goals

- Keep all existing behavior functionality working (same data format, same API contract)
- Match the visual language of `trigger-graph.js` (same colors, socket style, modal layout)
- Make complex condition trees visually composable instead of requiring raw JSON
- Support the existing behavior model: `{priority, trigger, interval, conditions, actions}`
- Do NOT change the backend — this is purely a frontend UX upgrade

---

## Proposed Approaches

### Option A: Enhanced Form (Lower Risk)

Keep the current modal+form structure but significantly improve it:

1. **Full condition type coverage** — expose all ~25 backend condition types in the simple mode dropdown
2. **Visual compound condition builder** — replace the raw JSON textarea with a nested card system where users can add AND/OR/NOT branches and attach leaf conditions to each branch. Each branch shows operator selector + sub-condition cards. Auto-generates the correct JSON.
3. **Drag-and-drop reorder** — add up/down buttons or drag handles on behavior cards and action cards
4. **Copy/duplicate** — right-click or button to clone a behavior
5. **Keyboard shortcuts** — Escape closes, Enter saves when focused
6. **Better styling** — extract inline styles to CSS classes

### Option B: Node-Based Graph View (Higher Impact)

Add a "Graph" toggle to the behavior editor modal (like the trigger editor has), using ComfyUI-style node layout:

```
┌─────────────────────────────────────────────────┐
│ Toolbar: [📝 Form] [Fit] [💾 Save] [✕ Close]   │
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────┐                                  │
│  │ ⚡ Trigger│── output →                       │
│  │ on_tick  │          ┌──────────┐            │
│  │ interval:3│         │ ❓ Cond  │── yes → ┌──────────┐    ┌──────────┐
│  │ priority:10│───────>│ eq       │        │ 💬 Message│    │ 🎭 Set   │
│  └──────────┘          │ npc_state│        │           │    │ State    │
│                        │ = idle   │        └──────────┘    └──────────┘
│                         └──────────┘             │
│                                   ── no →       v
│                              ┌──────────┐    ┌──────────┐
│                              │ 💬 Fail  │    │ (end)    │
│                              │ message  │    └──────────┘
│                              └──────────┘
│
└─────────────────────────────────────────────────┘
```

**Node types:**
- **Trigger node** (gold `#e3b341`) — defines trigger type, interval, priority. Single output socket.
- **Condition node** (red `#f85149`) — single condition with YES/NO bottom sockets. Supports all 25+ condition types.
- **Effect node** (blue `#58a6ff`) — action/effect. Chains linearly via right output socket. Supports all 9 behavior action types.
- **Branch node** (purple `#bc8cff`) — represents an entire behavior as a container. Has trigger config at top, then wires to conditions/effects below.

**Key differences from trigger graph editor:**
- Behaviors are naturally prioritized — each behavior = one branch starting from the trigger evaluation
- Multiple behaviors can exist in one graph, sorted by priority
- State transitions are visible as `set_npc_state` effect nodes, making state machines traceable
- Compound conditions become branching condition trees within a single condition node (or multiple cascaded condition nodes)

**Compilation:** Serialize the graph back to `{priority, trigger, interval, conditions, actions}` array format. One branch = one behavior entry.

---

## Recommended Path

Start with **Option A** as a standalone PR/improvement (fixes the immediate pain points). Then build **Option B** as a separate graph view that opens alongside the form view, with conversion between the two formats. This mirrors the trigger editor's dual-form/graph approach.

Phase 1 (this task): Option A enhancements to the existing form.
Phase 2 (separate task): Graph-based behavior editor inspired by trigger-graph.js.

---

## Files

- `static/js/inspector/behaviors-view.js` — primary file to refactor
- `static/js/shared/trigger-types.js` — source of truth for condition/effect types (reuse definitions)
- `static/js/inspector/agent-view.js` — renders behavior list cards, calls edit/add/delete
- `engine/npc_behaviors.py` — backend execution (no changes needed)
- `engine/trigger_system.py` — `_evaluate_conditions()` reference for all supported condition types

## See Also

- **task-226**: Unified Behavior/State Machine Graph Editor — the graph-based view that builds on these improvements

---

## Implementation Checklist (Option A)

- [ ] Expose all backend-supported condition types in simple mode (add missing 17 types)
- [ ] Build visual compound condition builder (replace JSON textarea)
  - [ ] Nested AND/OR/NOT branch cards
  - [ ] Add/remove leaf conditions per branch
  - [ ] Auto-generate valid JSON
  - [ ] Validate JSON before save, show inline errors
- [ ] Drag-and-drop reorder for behaviors (in the inspector list)
- [ ] Drag-and-drop reorder for actions (within behavior editor)
- [ ] Copy/duplicate behavior button
- [ ] Keyboard shortcuts (Escape close, Enter save)
- [ ] Extract inline styles to CSS classes
- [ ] Make modal draggable
- [ ] Add behavior validation summary (shows warnings like "no conditions = always fires")
