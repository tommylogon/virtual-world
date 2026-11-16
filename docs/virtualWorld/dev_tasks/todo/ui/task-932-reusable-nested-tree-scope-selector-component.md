---
type: task
status: todo
area: ui
priority: medium
wiki: "[[World Building/World Painter & Scope Editor]]"
related: [task-397, task-531, task-627]
---

# task-932: Reusable nested tree ScopeSelector component across toolbar, WorldPainter, and inspectors

**Filed:** 2026-11-09
**Related:** task-397, task-531, task-627

<!-- deps:start -->
**Related:** [[task-397-world-scope-hierarchy-and-projection]], [[task-531-graph-workspace-contextual-scope-bar-breadcrumb-counts-generate-clear]], [[task-627-outline-panel-hierarchical-scope-tree-rendered-as-a-flat-option-list]]
<!-- deps:end -->

## What

Replace the fragmented, flat scope dropdowns with a single reusable, nested tree-view **ScopeSelector** component (`static/js/shared/scope-tree-picker.ts`) used across all surfaces:

1. **True Hierarchical Tree View**:
   - Instead of a native HTML `<select>` that flattens scopes under a generic "Zones" `<optgroup>`, render a structured, collapsible tree popover showing the true parent-child hierarchy:
     `🌍 Whole world` -> `🏘️ District / Zone` -> `🏫 Building / Compound` -> `🚪 Interior Floor / Room Scope`.
   - Each branch displays expand/collapse chevrons (`▸` / `▾`), depth indentation guides, scope icons by mode/kind, and child area/node counts.
   - Includes a quick search filter to immediately jump to any nested scope by name.
2. **Reusable Component (MVC Architecture)**:
   - **Model**: Leverages the pure tree construction logic in `static/js/graph/scope-tree.ts` (`buildTree`, `visibleRows`, `rowLabel`) reading `GET /api/world/scopes?flat=1`.
   - **View**: A custom popover widget with accessible ARIA tree attributes (`role="tree"`, `role="treeitem"`, `aria-expanded`), clean dark glass styling, and compact chip display.
   - **Controller**: Dispatches standard `scope-selected` events, supports keyboard navigation (`ArrowDown`, `ArrowUp`, `ArrowRight` to open, `ArrowLeft` to close, `Enter` to commit), and maintains unified state.
3. **Unified Across All Callers**:
   - Graph toolbar: replaces `#graph-scope-filter`.
   - WorldPainter: replaces the separate chooser dialog in `editor.ts`.
   - Area Inspector: replaces the flat `scope_id` select element.

## Why

HTML `<select>` elements cannot nest `<optgroup>`s under the HTML standard. In `static/js/shared/scope-options.ts`, all depth-1 scopes are lumped under a hardcoded label "Zones", and deeper interior scopes (such as school floors or basement scopes) appear detached or flattened. Furthermore, having three separate implementations for picking scopes across the toolbar, WorldPainter, and Area Inspector duplicates logic and creates inconsistent navigation.

## How

1. In `static/js/shared/scope-tree-picker.ts`:
   - Implement `ScopeTreePicker` class conforming to standard Web Component or lightweight custom controller pattern.
   - Render button trigger showing current scope chip (`icon + name + ▾`).
   - On click, mount an anchored floating popover with search input and tree list.
   - Support keyboard navigation (`ArrowUp`, `ArrowDown`, `ArrowLeft`, `ArrowRight`, `Enter`, `Escape`).
2. Integrate in `static/js/graph/toolbar.ts` (and `templates/index.html`):
   - Replace `<select id="graph-scope-filter">` with `<div id="graph-scope-filter-container">` hosting `ScopeTreePicker`.
   - Wire `onSelect` to call `graphManager.setScopeFilter(scopeId)`.
3. Integrate in `static/js/worldpainter/editor.ts`:
   - Replace custom `showChooser()` modal with `ScopeTreePicker` to switch between active scopes.
4. Integrate in `static/js/inspector/area-view.ts`:
   - Use `ScopeTreePicker` in compact mode for assigning an area's owning scope.
5. Add unit tests in `tools/unit/test_scope_tree_picker.js`.

## Browser UI and intended live verification

Intended UI home: Main graph toolbar (top bar scope chip), WorldPainter scope header, and Area Inspector scope dropdown.

Current availability: Prototype scope tree exists in `static/js/graph/scope-tree.ts` beside the graph, but all pickers still use flat native `<select>` dropdowns with hardcoded "Zones" optgroups.

Live steps when available:
1. Open `localhost:4444` on a scenario with multi-level nested scopes (e.g. `Millwood` with town, school, and floors).
   - expected: Top toolbar displays the ScopeSelector chip showing active scope.
2. Click the ScopeSelector chip.
   - expected: A clean tree popover opens with search input, showing nested tree branches (`Whole world` -> `west millwood` -> `millwood public school` -> `Millwood High 1F`).
3. Click the chevron `▸` next to a building scope.
   - expected: The branch expands to reveal its interior floors with depth indent lines.
4. Type `1F` into the search box.
   - expected: The tree filters instantly to matching scopes with parent breadcrumbs highlighted.
5. Press `Enter` or click `Millwood High 1F`.
   - expected: Popover closes; graph loads the selected scope; ScopeSelector chip updates its label and icon.
6. Open WorldPainter and Area Inspector.
   - expected: Both surfaces use the exact same nested tree picker component.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. In the top toolbar, click the scope selector on a scenario with nested scopes.
   - expected: Dropdown displays hierarchical tree with chevrons and depth indentation rather than a flat list under "Zones".
   - observed: Flat native `<select>` with single generic `<optgroup label="Zones">`.
2. Inspect Area Inspector and WorldPainter scope selection.
   - expected: Consistent reusable component across all three surfaces.
   - observed: Separate disconnected implementations.
3. Run targeted unit tests: `node tools/unit/run.cjs`.
   - expected: All unit tests pass.

## Acceptance

- [ ] ScopeSelector renders genuine nested tree hierarchy with expand/collapse affordances and depth indent guides.
- [ ] Tree popover provides instant name search filtering.
- [ ] Keyboard navigation fully supported (`Arrow` keys, `Enter`, `Escape`).
- [ ] Single reusable component shared between Graph toolbar, WorldPainter, and Area Inspector.
- [ ] Zero em-dashes introduced in code, tasks, or docs.

## Files

- `static/js/shared/scope-tree-picker.ts`
- `static/js/graph/scope-tree.ts`
- `static/js/graph/toolbar.ts`
- `static/js/worldpainter/editor.ts`
- `static/js/inspector/area-view.ts`
- `templates/index.html`
- `tools/unit/test_scope_tree_picker.js`
