---
group: Gameplay
wiki: "[[dev_tasks/level-design-workflow]]"
---

# Serialize Exits from Graph Only (Remove Duplicate exits Cache)

**Filed**: 2026-08-13  
**Priority**: Medium  
**Status**: Todo

---

## Problem

Saved scenarios contain **two representations** of the same exit data:

1. **Graph** — area→way connection edges (`direction`, `visible_in_direction`) + way nodes
2. **`areas` / `rooms` `.exits` dict** — snapshot written on serialize

Runtime already uses graph only:

```110:111:engine/area_description.py
    def build_exits_for_area(self, area_name: str) -> Dict[str, Any]:
        """Reconstruct the exits dict for a area from graph connections."""
```

Authors editing one UI field update the graph. Opening raw JSON (e.g. `labs.json`) can show **different** `visible_in_direction` text in `graph.edges` vs `rooms[].exits` for the same ladder — confusing even when gameplay is correct.

## Goal

Single source of truth: **graph**. Serialized files either omit per-area `exits` or always rebuild on load and never read stale copies.

## Options

### A. Stop writing `exits` on save (preferred)

- `engine/serialization.py` — remove `exits` from `rooms_serialized` / player-facing area dict OR write empty `{}`
- API responses still include `exits` built live via `build_exits_for_area()` (already happens in serialize path line ~107)
- Frontend `worldState.areas[].exits` continues to work — always computed

### B. Rebuild on load, ignore file exits

- On template/scenario load, delete incoming `exits` from JSON before applying to graph
- One-time migration script to strip exits from `labs.json`, `world_template.json` graph-heavy saves

### C. Keep exits as export-only cache

- Write on save but mark `_exits_cache: true` and overwrite on every load from graph
- Document as derived — never hand-edit

## Migration

- `tools/strip_exits_cache.py` — optional: remove exits blocks from scenario JSON, verify graph intact
- Backward compat: load path must not **create** ways from stale exits if graph already has way nodes (audit `serialization.py` lines ~314–356 legacy path)

## Files

- `engine/serialization.py`
- `engine/area_description.py` (no change expected)
- `data/scenarios/labs.json` — migrate after script
- `world_template.json` — if exits duplication exists
- `tests/test_serialization.py` — round-trip: edit edge view → save → load → exits match

## Verification

- [ ] Edit ladder view in way inspector → save → reload → agent lens shows one consistent text
- [ ] Grep saved JSON: no duplicate `visible_in_direction` under `rooms.*.exits` OR clearly documented as derived empty
- [ ] Existing pytest serialization tests pass

## Related

- [[todo/ui/task-219-agent-lens-left-panel|task-219]]
- [[dev_tasks/level-design-workflow|Level design workflow hub]]
