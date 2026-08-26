---
group: Items & Crafting
wiki: "[[Items & Inventory/Items Overview]]"
---
# Procedural Item Placement: Tag-Chain Area Population Engine

**Filed**: 2026-07-17  
**Rewritten**: 2026-08-21 (concept draft â†’ implementation plan after equip_slots/tag groundwork landed)  
**Priority**: Medium  
**Status**: Planned â€” blocked by task-326, task-323, task-324

---

## Summary

Auto-populate areas with fitting items from the library by walking a three-level
tag chain: **area domain tags â†’ display/storage furniture that shares the domain
tag â†’ items that share it**, choosing the spatial edge per furniture role
(`in` for wardrobes/cabinets, `on`/`beside` for racks/shelves/tables).

This is the hub task for the procedural population work. Satellites:

| Task | Role | Depends on |
|------|------|-----------|
| task-326 | Character interest-tag data pass (+ dup char cleanup) | â€” |
| task-323 | Library lint validator (`tools/lint_library.py`) | â€” |
| task-324 | Domain tag schema + area/furniture tagging pass | task-323 |
| task-325 | Auto-dressing characters from interests | task-326 |
| **task-9** | **Population engine (this task)** | **322, 323, 324** |

## Current State (verified 2026-08-21)

- âœ… All 60 wearable library items have `equip_slots` (tools/fix_item_equipment.py)
- âœ… Item tags lowercased/deduped; 204 distinct item tags exist
- âœ… `_spawn_library_item_node` (routes/library_routes.py:130) transfers `tags`,
  `equip_slots`, materializes `contents` recursively **with per-child spatial
  relations** (`_content_relation`: in/on/under/beside/behind/at) â€” old gap #2 is FIXED
- âœ… MCP tool `build_item_from_library` + route `library_place_item` exist
- âš ï¸ Areas: only 23/58 library areas have tags, and current values are *setting*
  flavored (`fantasy`, `school`), not domain flavored (`store`, `clothing`)
- âŒ No population module, no display-furniture role tag, no density/placement rules

## Design: The Tag Chain

Same domain tag at all three levels â€” matching is plain set intersection:

```
Area  "Clothing Store"   tags: [store, clothing]
  â””â”€ Rack                tags: [furniture, display, clothing]   â†’ items placed ON/BESIDE
  â””â”€ Wardrobe            tags: [furniture, container, storage, clothing] â†’ items placed IN
       â””â”€ Dress          tags: [clothing, outerwear]
```

1. Read target area's tags â†’ domain set D.
2. Find furniture in the area (or spawn it from library) whose tags âˆ© D â‰  âˆ… and
   which carries a role tag: `display` (surface placement) or `container`/`storage`
   (containment).
3. For each furniture piece, select candidate items: library items whose tags âˆ© D â‰  âˆ…,
   filtered by role compatibility (clothing on racks, small items in cabinets).
4. Place via existing relation edges; respect per-furniture capacity.

### Placement rules

- Edge choice by furniture role: `display` â†’ `on` (fallback `beside` when full);
  `container` â†’ `in`; bare floors/tables without role â†’ `at`/`on` sparingly.
- Surface items are already reachable by `take` (graph.py edge expansion) â€” no
  engine change needed for reachability.
- Density knobs (per-area item counts) read from `engine/runtime_config.py`
  DEFAULTS + SCHEMA so the Engine Config UI picks them up (see AGENTS.md gotcha).
- Idempotent: re-running on a populated area tops up to density instead of duplicating.
- Deterministic option: seedable RNG for reproducible scenario generation.

### Out of scope (later phases)

- LLM-hybrid selection ("what fits a Blizzard clearing?") â€” phase 2, after the
  deterministic chain works.
- NPC equipment generation from room context (guardsâ†’armor) â€” belongs with
  task-325 auto-dressing once this lands.
- Co-occurrence statistics â€” needs populated-world data first.

## Work Plan

1. `engine/population.py` (new, <600 lines per file-size rule):
   - `plan_population(graph, area_id, rng) -> [Placement(item_lib_id, furniture_id, relation)]`
   - `apply_population(...)` using `_spawn_library_item_node` + relation edges
   - capacity tracking per furniture node (count existing `in`/`on` children)
2. **Furniture seeding** â€” population of an *empty* area must spawn the display/
   storage furniture itself before filling it: select library items tagged
   `furniture` + role tag + domain tag âˆ© area domains, place 1â€“3 pieces via
   spatial edges (`at`/`beside` walls is fine for v1), then run item fill.
   Without this step only pre-furnished areas benefit.
3. Route: `POST /api/populate/area/<node_id>` (density + seed params) in a routes module
4. MCP tool exposure in `mcp_server.py` (`populate_area`)
5. Editor button (area inspector) â€” thin UI pass, separate commit
6. Tests: fixture graph with tagged empty area; assert furniture gets seeded,
   relations chosen by role, idempotency, density cap (pattern:
   tests/test_item_actions.py fixtures)

## Verification

- `python -m pytest tests/ -q -k "not mcp and not emote"`
- Manual: populate the mansion kitchen + a store area; `look` shows items on/in
  furniture; `take` works on surface-placed items
- task-323 lint reports no dead tags introduced

## Refactoring Impact

Item creation lives in static/js/ui/create-modal.js, routes/library_routes.py,
engine/item_actions.py. Population logic goes in **engine/population.py** (new);
do not grow item_actions.py past the file-size rule.
