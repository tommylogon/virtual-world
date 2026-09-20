---
type: task
status: todo
area: world
priority: high
---

# task-416: Area-major tick iteration

**Filed:** 2026-09-20  
**Depends on:** task-407 (graph indexes).  
**Enables:** task-417 (meeting gate), task-419 (positional fidelity), task-411
(attendance).  
**Spec:** `docs/design/long-horizon-simulation-progress.md`.

## Goal

Restructure the per-tick sweep from entity-major to **area-major**:

```
for area in areas (sorted):
    for character in characters_in(area):
        ...
    for item in on_tick_items_in(area):
        ...
```

Co-presence stops being a repeated ad-hoc filter and becomes the loop
structure. Today `engine/tick_manager.py` iterates
`player_manager.players.items()` and reconstructs "who else is here" inline
(`:449` does exactly this: `op.current_area == player_area_name`). That is O(n)
per character with a linear scan per site, and there are several sites
(`:197`, `:205`, `:449`, `:851`).

## Non-negotiable constraint

**Do not conflate iteration order with turn order.** These are two different
things and only one of them is currently a contract:

- **Area-major iteration** decides the order in which area-scoped evaluation
  runs: building the co-presence index, standing-item / `on_tick` trigger
  evaluation, ambient effects, presence lists.
- **Turn order / the queue** decides who *acts*, and includes the human slot
  blocking round completion. That behaviour is user-verified and must not
  change.

If area-major iteration reorders who acts, the change is wrong. Keep the acting
queue exactly as-is and use area grouping only for scoped evaluation, unless a
separate task explicitly renegotiates turn order.

## Changes

1. Build an **area → [character]** index once per tick from
   `player.current_area` (and the graph `in` edges for items). Reverse index,
   not a scan per character.
2. Iterate areas in **sorted id order**; characters within an area in the
   existing queue order. Determinism must be provable: a fixed seed and fixed
   state must replay identically.
3. Standing-item / `on_tick` trigger evaluation moves inside the area loop so
   an area's items fire together with its characters.
4. Replace the ad-hoc co-presence scans (`tick_manager.py:449` and siblings) with
   a lookup into the index.
5. Skip empty areas cheaply; do not visit areas with no characters and no
   on-tick items.

## Acceptance

- Identical simulation outcome for a fixed seed vs. the current implementation
  on the camp fixture (same events, same order).
- Co-presence lookups are O(1) per character after the index build.
- Human turn-slot blocking behaviour is unchanged.
- Standing-item `on_tick` triggers fire exactly once per tick, in a
  deterministic area order.
- Perf: no regression on the 10,080-tick week soak (currently ~181 ticks/s).

## Non-goals

- Changing turn order, action costs, or the action-resolution rules.
- Chunk unloading (task-401) or scope projection (task-397).
- Multi-minute ticks (that is config: `time_per_tick_minutes`).

## Verification

- Fixture test: characters in the same area share one index entry; characters in
  different areas never appear in each other's co-present set.
- Determinism test: two runs, same seed, identical trace.
- Regression: `tests/test_perf_guards.py` extended to assert the tick loop does
  not scan all characters per character.
