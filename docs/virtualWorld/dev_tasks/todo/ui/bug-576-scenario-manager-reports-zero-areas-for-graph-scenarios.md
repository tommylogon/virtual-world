---
type: bug
status: todo
area: ui
priority: medium
wiki: "[[World Building/World Painter & Scope Editor]]"
related: [task-385, bug-572]
---

# bug-576: Scenario Manager reports zero areas for scenarios storing areas in graph nodes

**Filed:** 2026-11-09
**Related:** task-385, bug-572

<!-- deps:start -->
**Related:** [[task-385-scenario-health-dashboard]], [[bug-572-worldpainter-area-picker-lost-placed-on-grid-grouping]]
<!-- deps:end -->

## What

In the Scenario Manager list modal (`ScenarioManager.render()`), modern scenarios that store areas as physical graph nodes or painted world scopes display `⛺ 0` for their room/area count (e.g. `kraktooth_goblin_camp ⛺ 0`, `Millwood ⛺ 0`). However, opening the exact same file in the Import Preview modal (`inspectImport()`) correctly counts and reports hundreds of rooms (`⛺ 331 rooms` or `⛺ 592 rooms`).

The defect is in the backend scenario summary endpoint `GET /api/scenarios` in `routes/saveload.py`:

```python
entry["areas"] = len(data.get('areas') or {})
```

In legacy authoring templates, areas were stored in a top-level dictionary `data["areas"]`. In all modern graph-based scenarios and saved world states, the authoritative world model stores area nodes in `data["graph"]["nodes"]` where `type == "area"` (or within the scope manifest `area_placements` / `unplaced_areas`).

Because `list_scenarios()` in `routes/saveload.py` only inspects `data.get('areas')`, it returns `areas: 0` for any modern graph scenario. In contrast, the frontend's `inspectImport()` in `static/js/ui/saveload-view.ts` correctly scans both:

```javascript
// Authoring templates store areas in `areas`; saved world states use
// graph area nodes as the single source of truth.
if (isTemplate) { ... }
Object.keys(nodes).forEach(function(id) {
    if (nodes[id]?.type === 'area') addArea(...);
});
```

## Why

Authors and players scanning the Scenario Manager list rely on the `⛺` count badge to know the size, scale, and density of a scenario before opening it. Reporting `⛺ 0` makes full, dense scenarios look completely empty or corrupted.

## How

1. In `routes/saveload.py: list_scenarios()`:
   - Count areas by checking both legacy top-level `data.get('areas')` and graph nodes:
     ```python
     graph_nodes = (data.get('graph') or {}).get('nodes') or {}
     if isinstance(graph_nodes, dict):
         graph_areas = sum(1 for n in graph_nodes.values() if isinstance(n, dict) and n.get('type') == 'area')
     elif isinstance(graph_nodes, list):
         graph_areas = sum(1 for n in graph_nodes if isinstance(n, dict) and n.get('type') == 'area')
     else:
         graph_areas = 0

     # Also count scopes/manifest area placements if graph is uncompiled
     manifest = data.get('world_manifest') or data.get('scopes') or {}
     manifest_areas = sum(len(s.get('area_placements') or []) for s in manifest.values() if isinstance(s, dict))

     entry["areas"] = max(len(data.get('areas') or {}), graph_areas, manifest_areas)
     ```
   - Similarly verify character count (`entry["players"]`) falls back to `type == 'character'` in `graph_nodes`.

## Browser UI and intended live verification

Intended UI home: Scenario Manager modal (`📁 Scenarios` in top bar).

Current availability: Reproducible on `localhost:4444`. Opening Scenario Manager shows `kraktooth_goblin_camp` with `⛺ 0` despite containing 592 area nodes.

Live steps when available:
1. Open `localhost:4444` and click **📁 Scenarios** in the top navigation bar.
   - expected: Scenario Manager modal opens displaying the list of saved scenarios.
2. Locate `kraktooth_goblin_camp` and `Millwood` in the scenario list.
   - expected: The area icon badge (`⛺`) displays the true area count (e.g. `⛺ 592` or `⛺ 331`) rather than `⛺ 0`.
3. Click the **Upload / Import** button and preview `Millwood.json`.
   - expected: The Import Preview room count and the Scenario Manager row area count agree.

This section defines intended access and live acceptance. It is not a claim that planned UI exists or works today. Current availability says what is implemented and verified now; the numbered steps say how to reach and test the intended surface once it is available.

## Steps to verify

1. Call `GET /api/scenarios` and check the `areas` field for `kraktooth_goblin_camp` and `Millwood`.
   - expected: `areas` reflects the number of graph area nodes (> 0).
   - observed: `areas` is 0 because `list_scenarios()` only reads `data.get('areas')`.
2. Open Scenario Manager modal in the browser.
   - expected: `⛺` count matches real scenario size.
   - observed: Displays `⛺ 0`.
3. Run scenario management unit tests: `pytest tests/test_saveload.py`.
   - expected: All tests pass.

## Acceptance

- [ ] `GET /api/scenarios` calculates `areas` from `graph.nodes` (where `type == 'area'`) and scope manifests when legacy `data['areas']` is empty.
- [ ] Scenario Manager modal displays accurate `⛺` area counts for all graph-based and painted scenarios.
- [ ] Import Preview and Scenario Manager list show consistent room/area numbers.

## Files

- `routes/saveload.py`
- `static/js/ui/scenario-manager.ts`
- `tests/test_saveload.py`
