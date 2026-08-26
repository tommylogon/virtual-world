---
group: Graph & Area UX
wiki: "[[World Building/Graph System]]"
---

# Graph / Visual Alternatives

**Filed**: 2026-07-15
**Priority**: Low
**Status**: In Review — implemented (code-verified 2026-08-11). Three view modes in `static/js/graph-manager.js` (🔮 Graph / 🗺 Map / 📋 Outline), toolbar toggles at `index.html:77-109`. Audit section below already says "Ready to test".

---

## Summary

The vis.js network graph is the primary visualization, but it can become cluttered with many nodes/edges. Alternative views are needed for different use cases: room-focused layout, item hierarchies, character locations.

## Proposed Views

### 1. Area Map View (top-down layout)

A simplified 2D map showing rooms as boxes, doors as connections, with characters shown inside rooms. This is the most intuitive view for world navigation.

- Rooms arranged in a grid based on their exit directions (north/south/east/west)
- Click a room to inspect it
- Characters shown as icons inside their current room
- Items shown as small icons
- Filterable: hide items, show only doors

### 2. Item Hierarchy View (tree layout)

Show containment relationships: room → container → items inside container.

- Tree layout rooted at each room
- Expandable/collapsible branches
- Shows container nesting
- Drag items between rooms/containers

### 3. Character-Centric View

Show a character and their surroundings:
- Character at center
- Current room around them
- Exits to adjacent rooms
- Inventory items
- Other characters in the same room

### 4. Text-Based Outline

A simple collapsible tree view in the left or right panel:

```
🏠 Mansion
├── 📦 Items
│   ├── iron_key (in living room)
│   └── crystal_skull (in foyer)
├── 🚪 Doors
│   ├── front_door → Garden (locked)
│   └── kitchen_door → Kitchen (open)
└── 🧍 Characters
    ├── Tommy (Living Area)
    └── Cat (Kitchen) [NPC]
```

### Implementation Approach

**Option A (Recommended)**: Add a toggle toolbar above the graph that switches between:
- "Graph" (current vis.js network)
- "Map" (simplified room layout using vis.js with custom physics)
- "Outline" (text-based panel)

**Option B**: Replace vis.js entirely with a custom canvas/SVG renderer that supports multiple layouts. Higher effort but more control.

**Option C**: Keep vis.js but add layout presets that the user can switch between (hierarchical, grid, radial).

## Audit

**Status**: Ready to test
**Evidence**: Three view modes fully implemented in `graph-manager.js`:
- **🔮 Graph**: vis.js force-directed graph with node type coloring (room box, item diamond, door triangle, character ellipse), door/item state coloring, edge type coloring, physics toggle, fit view, search/filter, legend
- **🗺 Map**: SVG-based room map using BFS room layout from compass directions (N/S/E/W/up/down), room cards with click-to-inspect, SVG connection lines with direction labels
- **📋 Outline**: Collapsible text tree with rooms/exits/items/characters, copy-to-clipboard
- Toolbar buttons (`index.html:77-109`) toggle between all three modes
**How to test**: Click the 🔮 Graph / 🗺 Map / 📋 Outline buttons in the graph toolbar. In Map view: verify rooms are positioned by compass direction and connection lines appear. In Outline view: verify collapsible tree with rooms → items → characters. In Graph view: right-click any node to see context menu.

## Files Affected

- `static/js/graph-manager.js` — add view mode switching
- `static/css/style.css` — styles for alternative views
- `templates/index.html` — toolbar toggle buttons