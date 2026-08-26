---
group: Equipment & Inventory
wiki: "[[Items & Inventory/Equipment & Paperdoll]]"
---
# Paperdoll Icon Art — game-icons.net SVGs

**Filed**: 2026-07-21
**Priority**: Medium
**Status**: Draft

---

## Summary

The paperdoll in the Equipment tab currently uses text labels only. Add SVG icon art from game-icons.net (CC0/CC BY 3.0) to make each slot visually distinctive with fantasy/RPG-themed icons.

## Current State

Paperdoll has 13 slots in CSS grid human silhouette, each showing a text label ("Head", "Neck", "Torso", etc.) and the equipped item name. No visual icons.

## Icons Selected

| Slot | Icon | Author | License |
|------|------|--------|---------|
| Head | visored-helm | Lorc | CC BY 3.0 |
| Neck | gem-necklace | Lorc | CC BY 3.0 |
| Arms | forearm | Delapouite | CC BY 3.0 |
| Torso | breastplate | Lorc | CC BY 3.0 |
| Hands | gauntlet | Delapouite | CC BY 3.0 |
| Legs | leg-armor | Delapouite | CC BY 3.0 |
| Feet | boots | Lorc | CC BY 3.0 |
| Back | backpack | Delapouite | CC BY 3.0 |
| Waist | belt-armor | Delapouite | CC BY 3.0 |
| Hand Left | mailed-fist | Lorc | CC BY 3.0 |
| Hand Right | mailed-fist | Lorc | CC BY 3.0 |
| Accessory | diamond-ring | Delapouite | CC BY 3.0 |

All SVGs saved to `static/icons/` with `fill="currentColor"` for theme compatibility.

## Implementation

1. Create `static/icons/` directory
2. Save each SVG file with `fill="currentColor"`
3. Update inspector.js paperdoll rendering to reference SVGs inline or via `<img>` tags
4. CSS: slot icon color from `var(--text-dim)` when empty, `var(--accent)` when filled

## Attribution

All icons sourced from [game-icons.net](https://game-icons.net) under CC BY 3.0.
- Lorc: https://lorcblog.blogspot.com
- Delapouite: https://delapouite.com & contributors

## Icon Files

SVGs saved to `static/icons/` with `fill="currentColor"` for dark theme compatibility.
Each icon maps to a paperdoll slot in `static/js/inspector/paperdoll-view.js`.

## Attribution in readme

The project readme now includes the following section:
```
## Icons

Icons used in this project are from [game-icons.net](https://game-icons.net/).
Authors: Lorc, Delapouite & contributors
License: CC BY 3.0
```

## Status Update (July 2026)

- `static/icons/` directory now contains the game-icons.net archive with license and icon files
- SVGs are available in the archive — need to extract individual SVG files to `static/icons/` with `fill="currentColor"` modification for dark theme
- Paperdoll view at `static/js/inspector/paperdoll-view.js` — still needs to be updated to reference SVGs instead of text labels
- Readme attribution section added and pushed

**TODO**: Extract SVGs from archive, modify `fill` attributes, wire into paperdoll-view.js

## Files Affected

- `static/icons/` — SVG icon files
- `static/js/inspector/paperdoll-view.js` — slot-to-icon mapping
- `virtual_world/readme.md` — attribution section
