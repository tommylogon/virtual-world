---
type: task
status: review
area: ui
priority: medium
---

# task-722: Add breadcrumb navigation to inspector

**Filed:** 2026-10-06
**Related:** 

## Goal

Add breadcrumb navigation to the inspector so when navigating from a parent node (e.g., character) to a child node (e.g., inventory item), there is an easy way to navigate back. Maintain an inspection history stack and display clickable breadcrumbs at the top of the inspector panel.

## Acceptance

- Inspector displays a breadcrumb trail at the top (e.g., `Character > Inventory > Iron Sword`).
- Breadcrumb segments are clickable: clicking a segment navigates to that node's inspector.
- Inspection history is maintained on a stack: each new node inspection pushes to the stack; "Back" button pops and navigates.
- State is persisted per-inspector-session (no global storage needed).
- When opening an item from a character's inventory, the breadcrumb trail is: `Character: <name> > Inventory > <item name>`.
- Clicking the character segment in the breadcrumb returns focus to the character inspector.
- Clicking the inventory segment returns to the character's inventory view.

## Related Files

- `static/js/inspector.js`: add breadcrumb UI, history stack, click handlers.
- `templates/index.html`: add breadcrumb container markup above inspector content.
- `static/js/world-state.js`: optionally share inspection history if reused elsewhere.
