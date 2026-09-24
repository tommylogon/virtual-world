---
type: task
status: done
area: triggers
priority: high
---

# task-406: Trigger dispatch by event index, standing-item ticks, lazy context

**Filed:** 2026-09-19  
**Depends on:** nothing. Additive; must not change trigger semantics.  
**Evidence:** goblin soak profile; `virtual_world_engine.py:971`/`:984`;
`engine/tick_manager.py:635–692`; `engine/triggers/execution.py:277`;
`engine/legacy_compat.py:57`.

## Goal

Make trigger dispatch **event-driven across every node type**, give standing
items a real tick path, and stop paying for triggers that do not exist — without
changing what any trigger does.

## Problem

1. `_fire_turn_triggers` (`virtual_world_engine.py:971`) and
   `_fire_time_triggers` (`:984`) iterate **every** node and skip
   `node.type not in ("area", "way", "character")`. Two consequences:
   - Every tick visits ~106 nodes even when **zero** carry a tick/time trigger
     (the goblin scenario has 0; its 11 triggers are `on_drink` / `on_eat` / …),
     so the whole sweep is waste.
   - `on_turn_start` / `on_turn_end` / time-of-day / moon triggers on an
     **item** never fire — only area/way/character are swept.
2. **Item `on_tick` is inconsistent, not absent** (corrects an earlier claim).
   `engine/tick_manager.py` fires `on_tick` for exactly two item states:
   - carried or equipped items (`:635–643`);
   - items sitting in an area with `current_state` in `("lit", "on")`
     (`:665–692`, the burn-down path).

   A **standing** item — a bush, nest, shrine — that is neither carried nor lit
   is never ticked, so an `on_tick` growth/regrowth trigger on it does nothing.
   Carried and lit items keep working and must not be double-fired.
3. `_execute_triggers` (`engine/triggers/execution.py:277`) builds the full
   template context (lines 323–375) **before** it fetches trigger edges
   (line 378). On the common no-match path all of that work is discarded.
4. Two context keys read the expensive `game_state.current_area` legacy
   property (`:341`, `:371`), which rebuilds an `Area` and its exits on every
   access (`engine/legacy_compat.py:57`) — so building a discarded context can
   rebuild the exits of the active area.

## Changes

1. **Event index.** Maintain a map from trigger event/type → set of source node
   ids, built from trigger edges (`trigger_type`, scalar or list), covering
   **all** node types. Owner: `graph.py`. Rebuild on
   `add_edge` / `remove_edge` / `load_from_dict` / `clear`.
2. **Index-driven sweep.** `_fire_turn_triggers` / `_fire_time_triggers` iterate
   the ids registered for the requested type(s) instead of
   `graph.nodes.values()`. Empty index → no work.
3. **Standing-item tick.** Register items carrying an `on_tick` trigger so they
   are ticked regardless of carry/lit state, without double-firing items already
   served by the carried/equipped or lit/on paths (dedupe by node id per tick).
4. **Short-circuit + lazy context.** In `_execute_triggers`, fetch and filter
   matching trigger edges first; return `[]` if none match. Build the context
   only when something will execute, and only fill keys referenced by the
   matched triggers' templates/effects.
5. **Cheap area in context.** Replace both `current_area` property reads with
   the already-resolved area id/name/environment (e.g. `_get_current_area_id()`
   + `graph.get_node`), so trigger context never rebuilds exits.

## Acceptance

- A standing, non-lit, non-carried item with an `on_tick` trigger is ticked
  exactly once per tick.
- Carried/equipped and lit/on items keep firing exactly as today (no double
  fire) — `test_carried_item_fires_on_tick` still passes.
- An item carrying an `on_turn_start`/`on_turn_end` or time-of-day trigger now
  fires.
- No behaviour change for area/way/character triggers; existing trigger tests
  pass unchanged.
- With the goblin scenario, a tick performs no trigger-context construction;
  the trigger path shows ~0 in the profiler.
- `_execute_triggers` on a node with no matching edge does not read
  `game_state.current_area`.

## Non-goals

- Changing the trigger authoring format, condition trees, or effect handlers.
- Removing or globally reworking the `current_area` property (see task-407).

## Verification

- Unit: standing-item `on_tick`; no double-fire when also carried/lit; item
  turn/time trigger; no-match `_execute_triggers` returns `[]` without context;
  index stays correct across add/remove/load.
- Profile: before/after `cProfile` over 100 ticks (ranking only, not timing).

## Progress — 2026-09-19

Implemented.

- `graph.py`: trigger-event index (`_trigger_index`, `get_trigger_sources`) built
  from `triggers` edges that carry a non-empty `trigger_type`; maintained on
  add/remove/load/clear. Faithful to `_execute_triggers`, so legacy-shape edges
  that never matched still do not match.
- `virtual_world_engine.py`: `_fire_turn_triggers` / `_fire_time_triggers` are
  now index-driven (visit only trigger owners, any node type) instead of
  sweeping every node.
- `engine/tick_manager.py`: standing items (not carried/equipped, not lit/on)
  now get `on_tick`, exactly once, without disturbing the carried/equipped and
  lit/on paths (`test_carried_item_fires_on_tick` still green).
- `engine/triggers/execution.py`: `_execute_triggers` fetches trigger edges and
  applies a cheap type pre-filter before building context; the expensive
  `current_area` property is replaced by area-id/node resolution with a
  duck-typed fallback.

Verified: 255 targeted tests + full suite (2835 passed, excluding pre-existing
`test_mcp_*`). One-week background soak: 10,080 ticks in 9m49s (17.1 t/s),
23/23 alive.

## Progress — 2026-09-24

Closed the verification gap: the implementation shipped without the acceptance
tests named below. Added `TestTriggerEventIndex` in `tests/test_trigger_system.py`
— standing item fires `on_tick` exactly once; carried and lit/on items are not
double-fired; an item `on_turn_start` trigger now fires; a no-match
`_execute_triggers` call returns `[]` without touching `game_state.current_area`
(asserted with an exploding stub); and the graph trigger index stays correct
across add / remove / load / clear, including list-valued `trigger_type` and the
legacy no-`trigger_type` shape.

Focused run: 6 new tests pass; trigger suites 191 passed. Moved to review.
