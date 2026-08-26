---
group: UI - NPC Behaviors
---

# Unified Behavior/State Machine Graph Editor

**Filed**: 2026-08-14
**Priority**: Medium-High
**Status**: In Review — core graph editor complete 2026-08-23 (Phases 1–3 + most of 4). Live-verified: behavior graph save round-trip byte-identical, drag-reorder flips priority order (priority derived from Y stack: top = highest; engine only compares relative priorities so rank normalization is lossless), state summary panel traces set_npc_state transitions, 🧩 Graph buttons in behaviors-view modal + agent-view Advanced tab. Deferred: blueprint behavior-mode toggle, dry-run test button (backend endpoint is trigger-only).

---

## Problem

Simple NPC behaviors are currently defined as a flat array of `{trigger, interval, priority, conditions, actions}` objects. State machines are implicit — transitions happen via `set_npc_state` actions scattered across behaviors. There's no visual way to see how states connect or how the full AI behaves as a system.

The trigger graph editor (`static/js/shared/trigger-graph.js`) already has a proven ComfyUI-style node editor paradigm. This task extends that paradigm to cover behavior editing and state machine visualization.

---

## Goal

Build a **Behavior Graph Editor** that:

1. Works alongside the existing form-based behavior editor (toggle between views)
2. Visualizes each behavior as a branch in the graph
3. Shows state transitions explicitly (via `set_npc_state` nodes)
4. Supports all existing behavior functionality without loss
5. Can export/import as standard behavior JSON format
6. Eventually supports **explicit state machine definitions** separate from behaviors

---

## Architecture

> **UPDATE (2026-08-16):** Decided to EXTEND `trigger-graph.js` with mode-aware behavior/state nodes instead of a separate `behavior-graph.js`. Proven canvas/wire/modal tooling is shared; only node types, context menu, and compile/serialize differ by `mode`. Trigger mode is untouched.

### File(s): `static/js/shared/trigger-graph.js` (extended) and shared trigger-types/helpers

```
trigger-graph.js       — main module, modal, canvas, node rendering
                       — wire drawing (SVG bezier curves)
                       — context menu for spawning nodes (mode-aware)
                       — compileToBehaviors() — graph → behavior array
                       — behaviorsToGraph()   — behavior array → graph
```

### Node Types(behavior mode)

| Node | Color | Sockets | Purpose |
|------|-------|---------|---------|
| **Behavior** | `#e3b341` gold | Right: `output →` | Top-level container. Configures trigger type, priority, interval. Each behavior = one branch. |
| **Condition** | `#f85149` red | Left: `input ↓`, Bottom: `yes ✓`, Bottom: `no ✗` | Condition evaluation (now full condition coverage incl. behavior types: eq, in_area, tick_since_state, proximity). YES path leads to effects/next condition, NO path unused in behavior model. |
| **Action** | `#58a6ff` blue | Left: `input →`, Right: `output →` | Behavior action/effect execution (flat dict). Chains linearly. |
| **State** | `#bc8cff` purple | Left: `input →`, Right: `output →` | Special action node for `set_npc_state`. Visually distinct to show state boundaries. |

### Layout Model

```
┌──────────────────────────────────────────────────────┐
│  ┌──────────┐    ┌──────────┐                        │
│  │ ⚡ Be h #1│    │ ⚡ Be h #2│    ← priority-sorted │
│  │ pri:10   │    │ pri:5    │    ← side by side     │
│  │ on_enter │    │ on_tick  │                        │
│  └────┬─────┘    └────┬─────┘                        │
│       │               │                              │
│  ┌────▼─────┐    ┌────▼─────┐                        │
│  │ ❓ Cond  │    │ ❓ Cond  │                        │
│  │ prox:0   │    │ eq:state │                        │
│  └────┬─────┘    └────┬─────┘                        │
│   yes │    no      yes │    no                       │
│  ┌────▼─────┐    ┌────▼─────┐                        │
│  │ 🎭 State │    │ 💬 Msg   │                        │
│  │ fleeing  │    │ hello!   │                        │
│  └────┬─────┘    └──────────┘                        │
│       │                                             │
│  ┌────▼─────┐                                        │
│  │ 🚶 Go    │                                        │
│  │ Kitchen  │                                        │
│  └──────────┘                                        │
│                                                      │
│  Legend: [🟡 Behavior] [🔴 Condition] [🔵 Action] [🟣 State]│
└──────────────────────────────────────────────────────┘
```

Each Behavior node is independent — they don't wire to each other. Priority ordering is visual (top-to-bottom) and serialized back to the `priority` field.

### Compilation: Graph → Behavior Array

```javascript
BG.compileToBehaviors(graph) {
  // For each Behavior node:
  // 1. Read trigger_type, interval, priority from node props
  // 2. Follow output wire to first child
  // 3. If child is Condition:
  //    - Trace YES path → collect all Actions into actions[]
  //    - Trace NO path → optional fail_message
  // 4. If child is Action (no condition):
  //    - Collect all chained Actions
  // 5. Return [{ trigger, interval, priority, conditions, actions }, ...]
}
```

### Conversion: Behavior Array → Graph

```javascript
BG.behaviorsToGraph(behaviors) {
  // For each behavior object:
  // 1. Create Behavior node with trigger/priority/interval props
  // 2. If conditions exist:
  //    - Create Condition node wired to Behavior output
  //    - Wire YES → chain of Action nodes
  //    - Wire NO → FailMessage Action (if applicable)
  // 3. If no conditions:
  //    - Wire Behavior output directly to Action chain
  // 4. Position nodes vertically per behavior, stacked by priority
}
```

---

## Features

### Core
- Right-click context menu to spawn Behavior, Condition, Action, State nodes
- Drag nodes to reposition
- Wire sockets together (left input / right output / bottom yes/no)
- Inline property editing on each node
- Delete selected node(s) with Delete key
- Fit View button
- Save/Load from character data

### Behavior-Specific
- **Priority sorting** — behaviors visually stacked top-to-bottom by priority; drag reorder changes priority value
- **Trigger configuration** — dropdown for behavior trigger types (on_tick, on_player_enter_area, etc.)
- **Interval & priority inputs** — on each Behavior node header
- **Action type selector** — all 9 behavior action types with dynamic parameter fields
- **Condition type selector** — all ~25 backend condition types (including the 17 hidden from current form)
- **Compound condition support** — nested condition trees rendered as cascaded Condition nodes with logical operator indicators

### State Machine Visualization
- **State boundary markers** — when a `set_npc_state` action is placed, it renders as a purple State node with the state name prominently displayed
- **State flow tracing** — users can visually trace how an NPC transitions between states by following wires through State nodes
- **State summary panel** — collapsible sidebar listing all discovered states and their transitions (auto-generated from graph)

### Testing
- **Preview mode** — compiles graph to behavior array, validates against engine schema, shows any errors
- **Test button** — sends compiled behaviors to `/api/triggers/test` equivalent endpoint for dry-run evaluation

### Data Persistence
- **Save** — serializes graph to behavior array, PATCHes character via `ApiClient.updateCharacter()`
- **Load** — fetches character behaviors, converts to graph, opens editor
- **Blueprint save/load** — same library system as trigger graph editor

---

## Relationship to Existing Systems

```
┌─────────────────────────────────────────────────────┐
│                  Inspector (agent-view.js)           │
│                                                      │
│  NPC Bio Tab                                         │
│  ├── Behavior List Cards                             │
│  │   ├── Edit → opens behavior-modal (form view)     │
│  │   │   └── Toggle [🧩 Graph] → opens behavior graph│
│  │   └── Add → opens behavior-modal (new behavior)   │
│  └── [▶ Open Full Graph Editor] → opens behavior graph│
│       (shows ALL behaviors for this NPC at once)      │
├─────────────────────────────────────────────────────┤
│                  trigger-graph.js                    │
│  Item/Area/Way triggers → logic_trigger nodes        │
│  (existing, unchanged)                               │
├─────────────────────────────────────────────────────┤
│              behavior-graph.js (NEW)                 │
│  NPC behaviors → Behavior/Condition/Action nodes     │
│  Mirrors trigger-graph.js architecture               │
└─────────────────────────────────────────────────────┘
```

### Integration Points

1. **agent-view.js** — add "Open Graph Editor" button to NPC inspector bio tab (shows all behaviors at once instead of one-at-a-time)
2. **behaviors-view.js** — add "🧩 Graph" button to behavior edit modal footer (opens graph view pre-loaded with this single behavior)
3. **trigger-types.js** — extend to include behavior-specific action types alongside trigger effect types
4. **inspector.js** — add `_openBehaviorGraph(charName)` delegation method

---

## Future: Explicit State Machine Definition

After the basic behavior graph works, consider adding explicit state machine support:

```json
{
  "states": {
    "idle": {
      "transitions": [
        { "to": "foraging", "condition": {"type": "tick_since_state", "min_ticks": 30} },
        { "to": "fleeing", "condition": {"type": "proximity", "max_areas": 0} }
      ],
      "actions": [
        { "type": "message", "text": "The rat sits still..." }
      ]
    },
    "foraging": { /* ... */ }
  }
}
```

This would be a **separate data structure** from behaviors, not a replacement. Behaviors remain event-driven rules; states define default idle/fallback behavior within each state. Together they form a hybrid system:

- **States** = persistent mode (what the NPC does by default while in this state)
- **Behaviors** = event-driven reactions (what happens when something triggers)

Example: A guard is in `patrol` state by default (walks route). When `on_player_alerted` fires, a behavior switches them to `chase` state. While in `chase`, another behavior handles combat.

This goes beyond the scope of this task but the graph editor should be built with this possibility in mind — each Behavior node could eventually have a "parent state" property linking it to a state definition.

---

## See Also

- **task-225**: Behavior Editor form alignment — prerequisite UX improvements (condition type coverage, compound builder) that the graph editor will build on

## Files

- `static/js/shared/trigger-graph.js` — **extended** (behavior/action/state node types, behaviorsToGraph/compileToBehaviors, mode flag) — mirrors original trigger architecture
- `static/js/shared/trigger-graph.js` — reference implementation for node editor patterns
- `static/js/shared/trigger-types.js` — extend with behavior action types
- `static/js/inspector/behaviors-view.js` — added "🧩 Graph" toggle opening behavior graph mode
- `static/js/inspector/agent-view.js` — add "Open Full Graph Editor" button (Pending)
- `static/js/inspector/inspector.js` — add delegation method
- `engine/npc_behaviors.py` — no changes needed (frontend-only)
- `engine/trigger_system.py` — no changes needed

---

## Implementation Phases

### Phase 1: Skeleton
- [x] Create behavior node type in `trigger-graph.js` with modal, canvas, basic node rendering
- [x] Implement ContextMenu for spawning behavior/condition/action/state nodes (mode-aware)
- [x] Implement drag-and-drop positioning (shared with trigger mode)
- [x] Implement SVG wire drawing (shared)
- [x] Basic serialize/deserialize round-trip (behaviorsToGraph / compileToBehaviors)

### Phase 2: Conditions & Actions
- [x] Add Condition node coverage (all behavior condition types: eq, in_area, tick_since_state, proximity, random_chance, has_item, has_trait, has_tag, + shared types)
- [x] Add Action node type (all 9 behavior action types)
- [x] Add socket wiring (input/output/yes/no) (shared)
- [x] Inline property editing on Condition and Action nodes (shared)
- [x] Compile single behavior → behavior object

### Phase 3: Multi-Behavior Support
- [x] Multiple Behavior nodes in one graph (verified: 2-behavior round-trip)
- [x] Priority-based vertical stacking (behaviorsToGraph sorts by priority desc; compileToBehaviors derives priority from Y stack — top = highest)
- [x] Drag reorder behaviors → update priority values (Y-derived; verified swap flips order)
- [x] Full compile: all behaviors → behavior array
- [x] Full load: behavior array → graph with proper layout

### Phase 4: Polish & Integration
- [x] State node styling (purple `set_npc_state` nodes)
- [x] State summary sidebar panel (🗺 States toolbar button, behavior mode only; auto-refreshes on canvas changes)
- [x] Fit View, keyboard shortcuts, validation (shared; validation hidden in behavior mode)
- [x] Integrate with agent-view.js (🧩 Graph button in Advanced tab Behaviors header)
- [x] Integrate with behaviors-view.js (graph toggle in modal)
- [ ] Blueprint save/load (library integration) — shared, needs behavior-mode toggle (Deferred)
- [ ] Test/dry-run button (shared endpoint is trigger-only; Deferred)
