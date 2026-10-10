---
type: task
status: done
area: ui
priority: medium
---

# task-722: Add breadcrumb navigation to inspector

**Filed:** 2026-10-06
**Related:** 

## What

Add breadcrumb navigation to the inspector so when navigating from a parent node (e.g., character) to a child node (e.g., inventory item), there is an easy way to navigate back. Maintain an inspection history stack and display clickable breadcrumbs at the top of the inspector panel.

## Acceptance

- [x] breadcrumb trail at the top of the inspector (verified). - [x] earlier segments clickable (BUTTONs). - [x] history stack + Back button. - [x] trail grows on each navigation.

## Related Files

- `static/js/inspector.js`: add breadcrumb UI, history stack, click handlers.
- `templates/index.html`: add breadcrumb container markup above inspector content.
- `static/js/world-state.js`: optionally share inspection history if reused elsewhere.

## Steps to verify

- expected: inspector breadcrumb trail with clickable ancestors and a Back button.
- observed (2026-10-10 live): #inspector-breadcrumb shows 'Back < acorn_meal > player_Arix > Animal Pens > Frost-Crusted Berry Bush'; every earlier stop is a clickable BUTTON, the current node an aria-current SPAN.

## Why

TODO

## How

TODO

## Files

- TODO
