---
type: task
status: todo
area: world
priority: high
---

# task-400: Pines vertical slice for grouped generation and background life

**Filed:** 2026-09-08  
**Depends on:** task-397, task-398, task-399; task-323/task-324/task-9 for
tag-aware furnishing.

## Goal

Make `data/scenarios/pines.json` the first end-to-end proof of the scalable
world model. This is deliberately small: it proves semantics and authoring
workflow, not million-node performance.

## Scenario changes

1. Add a Millbrook Falls scope manifest with Downtown and The Pines hierarchy.
2. Assign existing Pines areas to their floor/building scopes.
3. Add an unmade `Apartment 3B` scope with recipe `apartment.v1` and a stable
   seed.
4. Add only the tag fixtures and library entries necessary for a credible
   residential apartment population test. Do not attempt a global library
   backfill in this scenario task. This is mandatory: the current Pines areas
   have no domain tags, so an untagged population demo would not validate the
   intended feature.
5. Add background schedules for five existing Pines characters, chosen for
   different outcomes: sleeping at home, working remotely, walking to work,
   consuming food/drink, and waiting/meeting.

## Demonstration script

1. Load Pines and open the Millbrook → Downtown → The Pines scope path.
2. Confirm the graph view returns only that projection; default UI does not
   reveal contained items.
3. Put five residents in background mode and advance eight hours.
4. Inspect their compact logs: location, activity, vitals, resource changes,
   and any deferred result.
5. Generate Apartment 3B from preview and walk from Hallway 3 into all its
   new areas.
6. Activate Miki; inspect her new `background` memory and full active prompt.
7. Save/reload; repeat scope navigation and prove no duplicate generated nodes
   or duplicate summary memories.

## Success criteria

The demo is successful only if generation, ordinary movement/item interaction,
background progression, and reactivation all use existing canonical data.
Hard-coded UI-only counts, narrative-only generated rooms, or direct mutation
that bypasses normal graph edges do not count.

## Explicitly not demonstrated

- Whole Millbrook generation.
- Multiple loaded chunks or disk eviction.
- Long road grids, fast travel, or cross-town route materialization.
- More than five background residents.
