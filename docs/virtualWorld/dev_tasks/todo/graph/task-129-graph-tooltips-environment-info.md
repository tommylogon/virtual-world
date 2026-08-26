---
group: Graph & Area UX
---
# Graph Tooltips & Hover Info

**Filed**: 2026-07-30  
**Priority**: Low  
**Status**: Design  

---

## Summary

Show useful environment information in graph node tooltips on hover — temperature, light level, air quality, and other area properties — so users don't have to open the inspector to see area conditions at a glance.

---

## Problem

Currently, hovering a graph node shows only the node name and type (via vis-network's built-in tooltip). To see temperature, light level, or other environment data you must open the inspector panel. For worldbuilding and debugging, surface-level data should be visible on hover.

**Note**: General UI tooltips already exist (HTML `title` attributes + Tippy.js) — this task is specifically about enhancing graph node tooltips with environment data.

## Requirements

- **Area nodes**: tooltip shows temperature, light level, air status on hover
- **Item nodes**: tooltip shows weight, tags (armor/clothing/weapon), equip_slots
- **Character nodes**: tooltip shows current area, vitals summary (HP/Energy), state
- **Door/Way nodes**: tooltip shows state (open/closed/locked), to/from areas
- Format: compact, multi-line, readable at a glance
- Use vis.js `title` or custom tooltip rendering

## Feature Tooltips (separate from graph)

Global feature explanation tooltips:
- `title` or `data-tooltip` attributes on UI controls explaining what they do
- Vital tooltips: explain what each vital does on hover in the inspector
- Settings tooltips: explain embedding provider, ghost mode, etc.

## Related

- [[done/graph/task-100-graph-view-filters|task-100: Graph view filters]]
- `static/js/graph/network-manager.js`
