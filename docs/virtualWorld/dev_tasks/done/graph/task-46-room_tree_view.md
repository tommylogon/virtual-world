---
group: Graph & Area UX
wiki: "[[World Building/Graph System]]"
---

# Area Tree Overview (under Analyze)

**Priority**: Medium

## Summary

Add a collapsible tree view to the existing Analyze button showing all rooms, their descriptions, exits, items, and characters present — a hierarchical overview of the complete world state.

## Requirements

- Replace the minimal current `showAnalysis()` (just room count + character locations) with a full tree
- Rooms sorted alphabetically, each expandable/collapsible
- Each room node shows:
  - Name, environment (temp/light/air)
  - Description (collapsible, first 120 chars then "...")
  - Exits list (with direction → room)
  - Items (with descriptions)
  - Characters/players currently in the room
- Use same inspector panel as existing analysis
- CSS: tree lines, indentation, expand/collapse icons
- No dependencies — pure DOM manipulation, no build step

## UI Mock

```
▶ Foyer (16°C, 40 light, stale)
  🚪 Exits: grand_stairs → Upstairs Hall, library_door → Library, ...
  📝 "The grand foyer stretches before you, a chandelier..."
  📦 Items: chandelier, rug, coat_rack
  👤 Elena Vance, Miki
▶ Kitchen (22°C, 60 light, greasy)
  🚪 Exits: kitchen_door → Dining Area, pantry_door → Pantry, ...
  📝 "A warm kitchen with a wood-burning stove..."
  📦 Items: stove, kettle, sink
  👤 Whiskers
```

## Audit

**Status**: Ready to test
**How to test**:
- Click the Analyze button. Verify a collapsible tree view appears showing all rooms, their descriptions (truncated at 120 chars with "more" link), exits with directions, items, and characters.
- Click ▶ toggles to expand/collapse room details. Click 📋 to copy tree to clipboard.

## Files Changed

- `static/js/graph-manager.js` — rewrite `showAnalysis()` with tree rendering + toggle
- `static/css/style.css` — add tree indentation, toggle, and item styles