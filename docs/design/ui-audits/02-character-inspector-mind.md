# Character Inspector & Mind Panel UI Audit & Redesign Specification

> **Status: UNVERIFIED DRAFT (2026-10-19).** Written from file headers and partial reads. Line counts, wireframes and several failure claims were NOT measured or reproduced live. Treat every claim here as a lead to check, not a finding. Verified findings live in the task cards, not in this document.


**Surfaces:**
- Agent Inspector (`static/js/inspector/agent-view.ts`, `paperdoll-view.ts`, `memory-view.ts`) - 2,852 lines
- Mind Panel (`static/js/inspector/mind-view.ts`, `agent-view.ts`) - 1,400+ lines
**Rendering Tech:** Lit-html hybrid string-concatenation mounted into side drawer `#inspector-panel`.

---

## 1. Measured Ground Truth & Architecture

When a character is clicked in the vis.js network, `InspectorAgentView.showAgent()` mounts.

### The String-Concatenation & Lit Hybrid Trap
- `agent-view.ts` builds 90% of its markup via literal string concatenation:
  ```ts
  return `<div class="inspector-card">` + htmlString + `</div>`;
  ```
- However, newer sub-components (gravity controls, alias editors, paperdoll) return Lit-html `TemplateResult` objects.
- To bridge the gap, the codebase invented `_deferredRenders` (lines 39-49): empty placeholder `div` tags are injected with random IDs (`agent-gravity-${cleanId}`), and a deferred callback finds them via `document.getElementById` to run `Lit.render()`.
- If an update occurs while switching tabs, IDs collide or deferred renders throw errors silently caught in `_runDeferredRenders()`.

### Inventory of 4 Massive Tabs
1. **Bio Tab:**
   - Identity & Room datalist input (lines 347-368).
   - Vitals: HP, Stamina, Mana, Sanity, Body Temp (lines 400-520).
   - Core Stats (STR, DEX, CON, INT, WIS, CHA) + 12 Skills table.
   - Traits list + asynchronous trait picker modal (line 219).
   - Interests & Fears tags.
   - Relationships table.
2. **Inventory Tab:**
   - Visual Paperdoll with equipment slots (Head, Chest, Main Hand, Off Hand, Feet, Rings).
   - Bag / Carried items listing.
3. **Images Tab:**
   - Expression pack manager (happy, sad, angry, surprised, neutral portraits).
   - Sprite sheet slicer.
4. **Advanced Tab:**
   - Graph physics controls (spring length, node gravity).
   - Persona schema compiler.
   - Raw JSON editor / export.

---

## 2. Usability & Layout Critique

### A. The Vitals Numerical Stepper Maze
- Vitals (Hunger, Thirst, Stamina, Temperature) are presented as tiny numeric inputs with `+` and `-` buttons.
- Temperature displays raw internal floats: `22.000000000000003 °C`.
- When an author wants to inspect how cold a character is, they see an incomprehensible decimal instead of a color-coded vital bar with semantic state ("Shivering - Mild Hypothermia").

### B. Condition Badges Dropdown Chaos
- Active conditions (`poisoned`, `exhausted`, `unconscious`) render as interactive pill chips with inline onclick handlers (lines 313-329).
- Clicking a condition pill injects a popup card with `z-index: 99` inside an `overflow-y: auto` drawer. As a result, the condition detail popup gets clipped by the inspector drawer's boundary and requires horizontal scrolling to read duration.

### C. The Area Move Input Hack
- Moving a character to another room uses an HTML `<input list="room-list">` with `<datalist>` (line 347).
- In a world with 627 areas, this datalist dumps 627 options into the browser's native autocomplete dropdown, stalling keystrokes on low-end machines and offering zero hierarchy (you see 8 areas named "Bridge" with no parent scope name).

### D. Separation of Bio and Mind
- The Character Inspector has a "Bio" tab, but also a separate floating "🧠 Mind" button (line 365) which opens an entirely separate dialog (`InspectorMindView`).
- Authors are constantly jumping between the Inspector Bio tab (to see traits/fears) and the Mind Panel (to see active thoughts/motives), even though they represent the same cognitive state.

---

## 3. Redesign Specification & Layout Blueprint

### Target Layout: The Unified Character Dossier

```
+-------------------------------------------------------------------+
| [Portrait]  THORNE IRONBARK                    [Mode: Human | v]  |
|             Lvl 4 Fighter · Eldenford Guards   [State: Healthy]   |
+-------------------------------------------------------------------+
| NAV: [ Overview ] [ Equipment ] [ Mind & Social ] [ Raw Data ]    |
+-------------------------------------------------------------------+
| VITALS HUD                                                        |
| Health:  [========================] 48/50 HP                      |
| Stamina: [================] 62/100                                |
| Temp:    22.4°C [Comfortable] · Hunger: [Sated]                   |
+-------------------------------------------------------------------+
| LOCATION & MOVEMENT                                               |
| Current: [ Eldenford Barracks (Armory)  | Switch Scope/Room ▾ ]   |
+-------------------------------------------------------------------+
| ACTIVE CONDITIONS (Horizontal Pill Rail)                          |
| [! Poisoned (3t left) | x]  [z Exhausted (Lvl 1) | x]  [+ Add]   |
+-------------------------------------------------------------------+
| TAB CONTENT: OVERVIEW                                             |
| ┌ Abilities (d20) ───────────┐ ┌ Key Traits ────────────────────┐ |
| │ STR: 16 (+3)   DEX: 12 (+1)│ │ • Brave: Immune to basic fear  │ |
| │ CON: 15 (+2)   INT: 10 (+0)│ │ • Heavy Sleeper                │ |
| │ WIS: 14 (+2)   CHA: 08 (-1)│ │ [+ Add Trait...]               │ |
| └────────────────────────────┘ └────────────────────────────────┘ |
| ┌ Recent Memories (Mind Stream) ────────────────────────────────┐ |
| │ • 2m ago: Heard strange noises from the northern cellar       │ |
| │ • 1h ago: Received 50 gold from Mayor Sterling                │ |
| │ [View Full Cognitive Graph ->]                                │ |
| └───────────────────────────────────────────────────────────────┘ |
+-------------------------------------------------------------------+
```

### Core Architecture Upgrades

1. **Retire String Concatenation**
   - Refactor `agent-view.ts` to 100% Lit templates (`Lit.html`).
   - Eliminate `_deferredRenders` and DOM ID hacks completely.

2. **Scoped Room Hierarchy Picker**
   - Replace the flat `<datalist>` of 600+ rooms with a grouped tree dropdown:
     `Scope > Sub-scope > Area Name (with cell coordinate)`.

3. **Consolidate Mind and Bio**
   - Integrate `InspectorMindView` directly as the "Mind & Social" tab inside the inspector drawer instead of a separate floating window.
