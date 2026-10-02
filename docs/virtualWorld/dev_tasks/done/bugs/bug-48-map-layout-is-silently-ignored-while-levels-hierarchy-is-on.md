---
type: bug
status: done
area: bugs
priority: medium
---

# bug-48: Map layout is silently ignored while Levels (hierarchy) is on

**Filed:** 2026-09-26
**Related:** task-496 task-526

## Goal

loadGraphData only applies the painted-grid layout when !levelsOn, so with the Levels toggle on, clicking Map changes nothing and a painted zone keeps its hierarchical arrangement (looks like physics is on / nodes cramped). Decide the rule: Map should force Layout=free/off (or Levels should not be selectable in Map mode), and the two toolbar toggles must reflect a single source of truth. Add a test or documented invariant so 'Map does nothing' cannot recur.

## Acceptance

## Acceptance

- [x] **The rule is decided and documented in one place**: Levels places every
      node itself, so Map would silently do nothing. Map is therefore **refused**
      while Levels owns the layout, rather than Levels being refused in Map mode —
      which keeps hierarchical levels usable on a painted world, where they are
      the whole point.
- [x] **The refusal is visible, not silent**: the Map tab is `disabled` with a
      `title` explaining why, and the programmatic guard
      (`graphManager.toggleCardinalLayout`) toasts the same sentence and returns
      `false` if anything reaches for it.
- [x] **One source of truth**: `activeLayout()` returns `'graph' | 'map' |
      'levels'` and the segmented control and every disabled rule read that
      instead of consulting `_cardinalLayout` and `graphLayoutMode` separately.
- [x] **The rule is a pure function, so it is tested rather than remembered**:
      `GraphToolbar.mapTabDisabled(state)` decides from a plain state object, and
      `tools/unit/test_graph_toolbar.js` covers it —
      "Map is unavailable while Levels owns the layout" and "Map is available in
      the other two layouts" (graph, map, and an empty state).

## Notes

- This was **already fixed in the code** when the task was re-read; the work left
  was the acceptance above, which is what the task's "Add a test or documented
  invariant so 'Map does nothing' cannot recur" asked for. The implementation
  names bug-48 in `toggleCardinalLayout`, `mapTabDisabled` and the network load
  path, so the invariant and its origin stay together.

## Second live verification — 2026-10-02 (port 4471)

Real interactions on the segmented control:

| action | result |
|---|---|
| click **Levels** | `activeLayout() === 'levels'`; Map tab `disabled=true`, `title="Map is unavailable while Levels owns the layout — pick Graph first, then Map."` |
| programmatic `graphManager.toggleCardinalLayout()` while Levels on | returns `false`, layout stays `levels`, toast: `"❌ Map is unavailable while Levels owns the layout — pick Graph first, then Map."` |
| pick Graph again | `activeLayout() === 'graph'` |

No page errors. The refusal is visible (disabled + title) and programmatic
reaches are both refused and explained, not silent.
