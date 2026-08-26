---
group: Graph & Area UX
---
# Graph UX Polish — Changes

## Files modified

- static/js/graph-manager.js — +100 lines: signature-based skip, position preservation on reload, physics toggle, fit view, legend overlay, search/filter, edge label toggle
- templates/index.html — +8 lines: Physics, Fit, Search input, Legend, Labels toolbar buttons
- static/css/style.css — +28 lines: legend overlay and search input styles
- static/js/graph/network-manager.js — edge labels now toggleable via `graphManager._showEdgeLabels`
- static/js/ui-helpers.js — Choices.js `removeItemButton` default changed from `false` to `true` so multi-select tags are removable

## Features

1. No more jitter — graph only reloads when nodes/edges actually change (checks node structure hash) - okay, editing nodes does no longer reload, only when characters move or items move  guess -accepted
2. Physics toggle — freeze/unfreeze node positions so dragging stays put - ok
3. Legend — shows node type colors/shapes and state border colors (toggleable) - ok
4. Fit view — zooms to show all nodes - ok
5. Search — dims non-matching nodes, clears on empty input - ok
6. Edge labels — default behavior unchanged (only unlocks/contains show text), but now toggleable via 🏷 Labels button to show all edge type labels - ok
7. Equipment slot multi-select — Choices.js chips now have remove buttons so slots can be deselected - ok
