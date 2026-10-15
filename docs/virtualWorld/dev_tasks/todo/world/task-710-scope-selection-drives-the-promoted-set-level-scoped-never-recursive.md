---
type: task
status: todo
area: world
priority: high
---

# task-710: Scope selection drives the promoted set: level-scoped, never recursive

**Filed:** 2026-10-05
**Related:** task-399,task-411,task-418

## What

Selecting a scope in the graph editor's scope filter promotes that scope's residents and puts everyone else on the soak (backsim) tier. Whole world is the explicit no-backsim mode: everyone stays active until human players run a timeskip.

Semantics are LEVEL-scoped, matching what the picker already loads. `world` is 62 areas (roads, bridges, Murk Lake, Blackmarsh, Old Dwarven Ruins, Camp Entrance Trail) and its children `goblin_camp`/`test`/`west_woods`/`eldenford_interior` are NOT included. Measured on the live world: selecting world = 14 characters in, 12 out. Selecting goblin_camp = 12 in, 14 out.

The scaling case that fixes the semantics: a town scope with 2000 people, most of them inside their homes, which are child scopes. Looking at the town scope simplifies all of them; they only come back as they exit their homes into the town.

This task owns the resolution rule and the mode. It does NOT own the per-tick re-evaluation on movement (separate task).

## The load-bearing bug: `activate_scope` is recursive today

`promotion.activate_scope()` (`engine/promotion.py:198`) resolves the scope with
`world_scopes.area_ids_in_scope`, which **recurses into child scopes**. For
`world` that returns **207 areas — every area in the game — and all 26
characters**. Wiring the picker to it as shipped promotes everyone, which is the
exact opposite of the request, and nothing in the current code would fail loudly.

The fix is `world_scopes.own_area_ids(graph, scope_id)` — the level-scoped
function `area_ids_in_scope` already calls before it recurses, and the one the
graph view already uses to decide what to load (`GET /subgraph` without
`descendants=1` returns 62 areas for `world`, against 207 with it).

**Both functions are already tested. The acceptance test must pin level-scoped
specifically**, because "promotes the scope" passes either way.

## Acceptance

- [ ] `promotion.activate_scope` resolves with `own_area_ids`, not
      `area_ids_in_scope`. A regression test asserts a child scope's residents
      are **not** promoted when the parent is selected — the town-with-2000 case.
- [ ] Measured against the live world, selecting `world` queues exactly the 14
      characters in its 62 own areas and leaves the 12 camp goblins alone;
      selecting `goblin_camp` queues 12 and leaves 14.
- [ ] **Whole world is an explicit mode, not an absence of one.** With no scope
      selected, everyone is promoted and nobody is demoted, and they stay that
      way until a human timeskip. A null filter and a "promote all" filter are
      the same request to the server; the client must send the difference rather
      than send nothing.
- [ ] The editor sends the selection to the server. `_scopeFilter` is currently
      client-side only (`static/js/graph-manager.ts:548`), read solely to decide
      which subgraph to fetch — there is no route it reaches.
- [ ] Selecting a scope does **not** disturb characters holding an explicit soak
      order (`player.soak_order`); `activate_scope` already skips these and that
      must survive.
- [ ] Transitions stay atomic: queued and applied by `promotion.flush()` at one
      tick boundary, never mid-turn.

## Interaction with materialisation

`engine/structures.py:402` calls `promotion.offload(..., reason="materialize")`
when a resident is imported. In Whole-world mode a freshly materialised resident
has no `soak_order` to protect it, so it is backgrounded out from under the
no-backsim rule. Decide which holds — materialisation stops demoting, or
Whole-world re-promotes on the next tick — and record the answer here rather than
leaving it to whichever path runs first.

## Open

- Does the scope filter drive fidelity while *authoring*, or only in play? It
  changes on save/reload as well as on deliberate selection (see the companion
  filter bug), and if fidelity follows it then clicking around the graph moves
  the simulation.

## Related

- task-399 (promotion bridge), task-411 / task-418 (the designed selector, whose
  `attended_set` still has no production caller), task-397 (scope filter).

## Why

TODO

## How

TODO

## Steps to verify

1. TODO
   - expected: TODO
   - observed: TODO

## Files

- TODO

## Browser UI and intended live verification

Intended UI home: Graph editor → scope filter → choose `world` or `goblin_camp` → Agents list/promotion view. The displayed promoted set must be the exact level-scoped set the simulation processes.

Current availability: live measurements recorded by this card are `world`: 14 characters in and 12 out; `goblin_camp`: 12 in and 14 out. The required own-area-only promotion rule and explicit whole-world mode are still acceptance criteria, not newly claimed behavior.

Live steps when available:
1. Load the measured world and select `world` in the graph scope filter. Read the promoted/backsim counts in the Agents list and compare the IDs with `/api/state`.
   - expected: exactly the characters in the 62 areas owned by `world` are promoted (14 in); camp residents remain backsim (12 out); child scopes are not recursively included.
2. Select `goblin_camp` and inspect the promoted set again.
   - expected: 12 camp characters are promoted and the 14 world characters are out, matching the areas owned by the selected scope.
3. Clear the scope filter to explicit whole-world mode and inspect the roster and engine state.
   - expected: all characters are promoted, none are demoted, and they remain active until a human timeskip; an absent/null filter is not confused with this explicit request.
4. Reload the scenario and compare the selected mode with the resolved active set.
   - expected: UI and server agree on character IDs; child-scope residents do not leak into a parent selection.

This section is not a claim that planned UI exists or works today.
