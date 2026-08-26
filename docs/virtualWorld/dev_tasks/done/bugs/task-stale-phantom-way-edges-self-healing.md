---
group: Graph & Area UX
---

# Stale & Phantom Way Connection Edges — Self-Healing Reconnect

**Filed**: 2026-08-09  
**Priority**: High  
**Status**: In Review — implemented 2026-08-09, 4 new route tests pass, full suite 761 passed (same 11 pre-existing give-item failures).

---

## Summary

Some ways ended up wired to **three areas instead of two**, and edges pointed at **non-existent mixed-case node ids** (e.g. `area_Task_18_-_Room_4` while the node is stored as `area_task_18_-_room_4`). Symptoms seen in the way inspector: "side B shows the wrong room", "view from B to A got lost", "both cardinals read south", and direction fields showing as empty.

## Root causes

1. **`build_connect` never removed old edges.** The graph-editor connect (`POST /api/build/connect`) *added* 4 connection edges without deleting the way's existing ones. Connecting an already-wired way left a stale pair behind → 6 edges / 3 areas. (`reconnect_way` already removes all edges first, so the stale wiring came from a connect, not a reconnect.)
2. **Reconnect prop preservation was case-sensitive.** `reconnect_way` matched the canonical `area → way` edge with plain `==`. When the stored edge used a legacy mixed-case id and the request used the lowercase id, the match failed and `visible_in_direction` / `cardinal` were silently dropped.
3. **Nothing normalized edge endpoints on load.** Saves copied edges verbatim, so mixed-case phantom endpoints persisted forever and polluted serialization + editor edge parsing.

## Fixes

- `routes/graph.py` — `build_connect_legacy`: remove any existing connection edges for the way id (case-insensitive) before adding the 4, so re-connecting is idempotent.
- `routes/graph.py` — `reconnect_way`: find the way's connection edges and match the canonical edge **case-insensitively** so view/cardinal props survive a reconnect even with legacy mixed-case ids.
- `graph.py` — new `_normalize_edge_endpoints()` called at the end of `load_from_dict`: remaps every edge's source/target to the canonical stored node id (case-insensitive resolve). Saves reloading legacy worlds self-heal phantom endpoints.
- `static/js/inspector/way-view.js` — `_parseConnections` now prefers the way's `area_from` / `area_to` props (resolved to area nodes) when choosing side A/B, so stale 3rd-area edges no longer surface the wrong pair in the inspector.

## Manual repair workflow (how to fix a broken way in the editor)

Open the way → Connections → pick the two correct areas in the reconnect dropdowns → set directions → 🔄 Reconnect. The route deletes all existing connection edges and rebuilds exactly 4 for the chosen pair, preserving view/cardinal props case-insensitively.

Also: `tools/fix_way_edges.py` scans a world file or the live server (`--live`) and prints a per-way DROP/REMAP plan; `--apply` writes the changes. Useful for bulk-cleaning a scenario that accumulated stale wiring.

## Verification

- `tests/test_way_connect_repair.py` (new): reconnect preserves view/cardinal with mixed-case stored ids; build_connect is idempotent (no stale sides); build_connect to a new pair replaces the old side; load_from_dict rewrites mixed-case endpoints. 4/4 pass.
- Full suite: 761 passed, 11 failed (pre-existing `TestGiveItemEffect` give-item failures, confirmed on clean HEAD).

## Files Changed

- `routes/graph.py` — idempotent connect, case-insensitive reconnect prop preservation
- `graph.py` — `_normalize_edge_endpoints` on load
- `static/js/inspector/way-view.js` — `_parseConnections` prefers area_from/area_to
- `tools/fix_way_edges.py` — new dry-run/apply repair scanner
- `tests/test_way_connect_repair.py` — new route tests
