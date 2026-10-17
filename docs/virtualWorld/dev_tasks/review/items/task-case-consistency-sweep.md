---
group: Items
related: [task-duplicate-item-loses-triggers-case-mismatch]
---

# Case-Consistency Sweep: toLowerCase Where It's Missing

**Filed**: 2026-08-09  
**Priority**: Medium  
**Status**: In Review — implemented 2026-08-09, full suite 752 passed (only the 11 pre-existing give-item failures), UI smoke 25/25.

---

## Summary

Follow-up to the duplicate-loses-triggers fix (see `review/items/task-duplicate-item-loses-triggers-case-mismatch.md`). Swept the codebase for spots that generate or match node/edge ids case-sensitively. Key insight: the **engine graph layer is already case-insensitive** (`graph.py:_resolve_id` + `get_edges_for_source` lowercase both sides), so runtime resolution was never the problem — the landmines were **id generation** (creating mixed-case data) and **frontend exact-match lookups** (hiding data in the UI).

## Fixes

- `static/js/item-library.js` — `_duplicateItem` new library id now `.toLowerCase()` (registry POST doesn't lowercase, so the frontend must).
- `engine/node_ids.py` — `NodeIDHelper.way_node_id` + `item_node_id` now lowercase (were the odd ones out vs `area_node_id`; `connect_areas` at movement.py:62 was generating mixed-case way ids, the exact source of the legacy Task-3 mixed-case orphans).
- Inspector exact-match edge lookups → case-insensitive:
  - `static/js/inspector/trigger-helpers.js` (buildTriggersHtml, _openGraphEditor, old-edge cleanup)
  - `static/js/inspector/item-view.js` (trigger edges, container weight via `worldState.getNode`)
  - `static/js/inspector/way-view.js` (connection edges)
  These directly caused the "duplicate item shows no triggers" symptom for mixed-case data.

## Not Changed (already safe / deliberate)

- `handle_unlock_way`/`spawn_item` — safe via case-insensitive `WorldGraph.get_node`.
- Player node ids (`player_<Name>`) — case-preserving by design, creation+lookup share `NodeIDHelper.player_node_id`.
- `engine/matching.py` — already lowercases all name matching.

## Verification

- `node --check` clean on all edited JS; `pytest tests/ -q -k "not mcp and not emote"` → 752 passed, 1 skipped (11 pre-existing give-item failures unchanged); `tools/test_ui.cjs` 25/25.

## Browser UI and intended live verification

Intended UI home: Library Browser → duplicate an item with uppercase letters in its name → open the duplicate's Inspector and Triggers; then inspect any connected way/containment edges.

Current availability: the card records case-insensitive ID generation and Inspector edge lookups as implemented, with historical UI smoke 25/25 and a 752-pass test run. A fresh browser run is not recorded here.

Live steps when available:
1. Duplicate an item and give the duplicate a mixed-case display name; open the new item Inspector.
   - expected: the generated node ID is lowercase and every copied trigger/containment edge resolves to that node.
2. Inspect the trigger list and then delete the duplicate.
   - expected: no trigger disappears because of case mismatch and no orphan edge remains under the mixed-case caller ID.
3. Open an existing mixed-case legacy item/way and inspect its edges.
   - expected: the Inspector resolves edges case-insensitively while preserving the original display name and player IDs' deliberate case behavior.
4. Run the project's UI smoke check after the interaction.
   - expected: all 25 smoke interactions still pass.

This section is not a claim that a fresh browser run has been performed today.
