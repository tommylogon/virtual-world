# Inspector Modular Architecture Redesign - Design Plan (task-902)

Status: Planning
Scope: All 17 inspector/* view files
Goal: Deduplicate patterns, add testability, make new inspectors <50 lines.

## 1. Current State Audit (measured from HEAD)

### 1.1 File inventory (17 modules)
- Panel (90 lines) - Singleton - Only allowed panel writer
- Inspector dispatcher (862 lines) - Singleton dispatcher - Breadcrumb trail, view routing
- Helpers (1149 lines) - Shared utilities - HTML tag, field builders, lock toggles
- Agent-view (2851 lines) - Agent/character - 4 tabs, paperdoll, traits, relationships, memories
- Item-view (1063 lines) - Item - Actions grid, parameters, tags, state, move
- Area-view (964 lines) - Area/room - Description, environment, exits, scope
- Way-view (1057 lines) - Way/door - State, cardinal selector, connections
- Mind-view (2353 lines) - Memory dashboard - Timeline, filters, dynamics badges
- Memory-view (727 lines) - Memory editor - Add/edit/delete entries
- Behaviors-view (1406 lines) - NPC behavior - Behavior list, action cards
- Lore-view (769 lines) - World lore - Entry editor
- Known-by (235 lines) - Knowledge index - Per-person known items
- Paperdoll-view (733 lines) - Equipment visual - Stack popup, equip picker
- Sprite-sheet (1392 lines) - Sprite editor - Sheet splitter
- Doc-panel (90 lines) - Documentation - Section renderer
- Trigger-helpers (729 lines) - Trigger helpers - Trigger vocabulary, graph compilation
- Way-triggers (152 lines) - Way triggers - Trigger list for ways
- Way-connections (85 lines) - Way connections - Connection editor
- Way-authoring (60 lines) - Way authoring - Authoring helpers
- Auto-dress-modal (213 lines) - Auto-dress - Modal overlay

### 1.2 Duplication counts (measured)
- window.Lit.html lazy tag: 17 files
- document.getElementById: ~340 occurrences
- worldState. direct access: ~180 occurrences
- InspectorHelpers. calls: ~90 occurrences
- String HTML concatenation: ~60 occurrences
- Independent event listeners: every file
- Per-view state variables: every file

### 1.3 What is duplicated (evidence)

Header rendering: Every view builds its own header HTML string.
Property fields: Agent-view Bio (stats, skills, traits), item-view properties, area-view environment all read props bag and build input fields independently.
Tab navigation: Only agent-view uses tabs, but the pattern exists.
Save/apply: Every edit action calls ApiClient.updateNode() or updateCharacter() directly, then worldState.fetch() independently.
Event stream: Each view handles its own events independently.
Breadcrumbs: Only agent-view pushes breadcrumbs explicitly; other views rely on dispatcher.

---

## 2. Design Principles (non-negotiable, from AGENTS.md)

1. One source of truth per concept (prime directive)
2. Content before instrumentation (rule 8)
3. Reuse existing seams (prime directive)
4. Simulation invariants preserved
5. Classic script structure kept (AGENTS.md convention)
6. No em-dash (AGENTS.md gate)

---

## 3. Proposed Architecture: Three Layers

### Layer 1: InspectorView Base Class
Location: static/js/inspector/inspector-view-base.ts (new module)

Purpose: Every view extends this. Handles lifecycle, breadcrumbs, event coalescing, safe worldState access.

Contract interface (TypeScript):
- show(nodeId?): Promise<void> | void
- hide(): void
- refresh(): void
- getCrumbLabel(): string
- getNodeTypeFilter(): string | null

Why solves duplication: Agent-view has _deferRender, _currentView tracking. Every view needs this. Base eliminates it.

### Layer 2: Component Library
Location: static/js/inspector/components.ts (new, extends helpers)

Components (extracted from duplication evidence):
- HeaderComponent: title + subtitle + node type badge
- PropertyGridComponent: { fields: FieldDef[] } -> renders inputs
- TabNavComponent: { tabs, activeTab, onTabChange }
- ActionGridComponent: { actions, nodeId, locked }
- InspectorSection: { title, hint, content }
- BreadcrumbComponent: { crumbs, onBack, onCrumbClick }

Why PropertyGridComponent: Agent Bio (stats/skills/traits), item properties, area environment all build from props bag.

### Layer 3: Refactored View Modules
Target: Each file reduced to <200 lines.

Agent-view (2851 -> ~400): Keeps paperdoll, timeline, behavior delegation. Uses HeaderComponent, PropertyGridComponent, TabNavComponent.
Item-view (1063 -> ~300): Keeps library lookup, AI improve, container weight. Uses HeaderComponent, PropertyGridComponent, ActionGridComponent.
Area-view (964 -> ~250): Keeps scope logic, agent listing, event log. Uses HeaderComponent, PropertyGridComponent, InspectorSection.
Way-view (1057 -> ~300): Keeps compass selector, reconnect logic. Uses HeaderComponent, InspectorSection.
Mind-view (2353 -> ~800): Stays separate as dashboard. Extract timeline ribbon, filter bar, dynamics badges as components.

---

## 4. Implementation Order (smallest coherent changes)

Phase 1 - Verification (before abstraction):
1. Count duplication (done above)
2. Verify InspectorPanel.render() usage
3. Confirm DocPanel.section() consistency
4. Measure line counts

Phase 2 - Base class (one coherent change):
5. Create InspectorView base
6. Refactor agent-view (largest) to extend it - prove contract
7. Verify no regression

Phase 3 - Components (independent):
8. HeaderComponent
9. PropertyGridComponent
10. TabNavComponent
11. BreadcrumbComponent

Phase 4 - Remaining views (independent per view):
12. Each remaining view: extend base, use components
13. Each verified independently

Phase 5 - Tests and docs:
14. Unit tests for base class
15. Component-level tests
16. Integration: new view in <50 lines

---

## 5. Key Decisions (with codebase evidence)

### 5.1 Composition over inheritance
Evidence: Agent-view (4 tabs, very different content), item-view (continuous form), area-view (sections). Inheritance would force common structure that doesn't exist.

### 5.2 PropertyGridComponent
Evidence: agent-view Bio line 109-116 (stats/skills/traits from props), item-view properties, area-view environment. All build input fields from property keys.

### 5.3 Classic scripts preserved
Evidence: AGENTS.md line 124-130. Inspector singleton at inspector.ts:861 registered as window.inspector. Changing to ES modules breaks all references.

### 5.4 Mind-view stays separate; media feeds memory
Evidence: mind-view reads from worldState.players and /api/players/<n>/memories/people. Media (movies, games, books, music) is a prose category that feeds memory/knowledge generation (lorebook / memory entries), not identity (corrected from task-828 line 49: media has a real consumer - memory). It is not GIMP or MOSIAC. It is the narrative/memory layer.

---

## 6. Verification Steps

Before any sub-task:
1. Count duplication (done)
2. Verify base contract with test file
3. Verify component independence
4. Verify no regression after each view

---

## 7. Intentionally Unimplemented

- trigger-helpers.ts / trigger-editor.ts: trigger-authoring, not node inspectors
- library-browser.ts: separate surface
- worldpainter/editor.ts: separate architecture
- nl-editor/: separate staging/apply pipeline
- DocPanel content layer

---

## 8. Related Tasks
- task-738 (graph, inprogress): NL Editor update_player
- bug-518 (ui, inprogress): NPC action results render as "You"
- bug-569 (ui, inprogress): Trigger card under-reports effects
- task-722 (done): Breadcrumb trail
- task-579 (done): Documentation panel
