---
group: Graph & Area UX
---

# Reconnect Wipes Way View-from / Cardinal Edge Props

**Filed**: 2026-08-09  
**Priority**: High  
**Status**: In Review — implemented 2026-08-09, verified live against :4444 (reconnect to same rooms now preserves `visible_in_direction` + `cardinal` on both sides).

---

## Summary

Pressing the 🔄 Reconnect button in the way inspector (or calling `POST /api/graph/way/reconnect`) cleared the **View from A → B** and **Cardinal (A→B)** fields on side A of the way — even when reconnecting to the exact same two areas. Reported while editing way nodes: "the view from a to b got cleared out, and the cardinal a to b got cleared out."

## Root cause

`visible_in_direction` and `cardinal` live on the **area → way** connection edge (the canonical edge the engine reads — see `engine/movement.py:532` and `engine/area_description.py:142`). The reverse **way → area** edges carry only a stale copy of `direction`.

`reconnect_way` (`routes/graph.py`) preserved old edge props with:

```python
for e in way_edges:
    if e.source == new_area_a or e.target == new_area_a:
        old_props_a = dict(e.properties)
```

Matching by area picks the **last** edge in iteration order, which for side A is the reverse `way → area` edge (no view/cardinal). Those props were then dropped when the edges were rebuilt — reproduced live: side A lost both fields, side B survived (order-dependent).

## Fix

Match the canonical edge specifically:

```python
if e.source == new_area_a and e.target == way_id:
    old_props_a = dict(e.properties)
if e.source == new_area_b and e.target == way_id:
    old_props_b = dict(e.properties)
```

When reconnecting a side to a *new* room, that edge won't exist, so the new side correctly starts with no inherited view/cardinal.

## Verification

- Repro script before fix: `A->way` lost `visible_in_direction` + `cardinal` after same-room reconnect.
- After fix: both sides keep view + cardinal through same-room reconnect.
- Test data cleaned up; world state restored.
- Full pytest: 748 passed / 11 failed — the 11 failures are pre-existing `test_trigger_system.py::TestGiveItemEffect` give-item tests, confirmed failing on clean HEAD too (unrelated to this change).

## Files Changed

- `routes/graph.py` — `reconnect_way`: preserve props from the canonical `area → way` edge
