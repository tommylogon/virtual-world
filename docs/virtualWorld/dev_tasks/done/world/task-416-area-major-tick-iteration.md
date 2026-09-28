---
type: task
status: done
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

## Progress — 2026-09-28 (the presence index and the area-major sweep)

Shipped in `engine/tick_manager.py`, with `tests/test_area_major_ticks.py` (12).

### Co-presence is a reverse index, kept live

`_presence_reset` builds `area name -> {registry key: player}` once per turn.
`_presence_sync` re-files a character the moment it changes area (O(1), and it
also refreshes the cached object), so the index is *live* rather than a
snapshot — a lookup returns exactly what the old inline scan would have
returned at that moment, in the same roster order. `_presence_resync` does a
full pass after a phase that can move anyone (the NPC / soak / background
block, and the sound pass); it rebuilds wholesale only if the roster changed
size.

Both ad-hoc scans are gone: the social co-presence read in the character loop,
and the per-hearing-area character filter in `_process_sound_sources`.

### The acting queue is untouched

The character loop still walks `player_manager.players` in registry order, so
log-entry order, need-threshold messages and death handling are byte-for-byte
unchanged. Area grouping is used only for scoped evaluation — which is the
non-negotiable constraint, not a compromise.

### The area-major item sweep

The two whole-graph passes are now one sweep, `_sweep_area_items`:

- a lit object left in a room and a plain item owning an `on_tick` trigger
  (the task-406 bush / nest / shrine) both belong to their *area*, so they run
  together, **sorted by area id and then by node id**;
- areas with no characters, no lit object and no `on_tick` item are never
  visited;
- placement (`_standing_items_by_area`) is cached against the graph revision
  plus node/edge counts, so the per-area in-edge lookup is no longer paid every
  tick. Item *state* is never cached — it is read fresh each turn.

An `on_tick` item the world has not placed anywhere still fires (it has no area
to belong to), id-sorted, after the area sweep — `test_trigger_system.py::
TestTriggerEventIndex::test_standing_item_on_tick_fires_once_per_tick` pins that
and caught the first version of the sweep, which silently dropped it.

### Two determinism bugs the new tests found

Both were pre-existing and invisible, because the old passes walked graph
*insertion* order: the standing sweep inherited insertion order within an area,
and the trigger-source tail walked a `set`. Sorting both makes the sweep a pure
function of the graph.

### Measurement, honestly

Co-present read, best-of-200 per call, same world, index vs. the old scan:

| characters | index µs/call | scan µs/call |
|---|---|---|
| 10 | 35.6 | 38.7 |
| 40 | 36.2 | 37.3 |
| 160 | 32.5 | 45.0 |

The index is flat; the scan grows. The win is the *removal of the quadratic
term*, and at fixture scale the whole tick is dominated by unrelated
per-character work, so end-to-end throughput differences sit inside the noise
(fresh world per measurement, 123 characters: 34.2 vs 38.4 ms/tick, run-to-run
spread ±10 ms). An earlier measurement suggesting a 5x regression was an
artefact of letting each arm inherit the previous arm's mutated world.

`is_undead_ghost` is now the hot part of the read — three Python calls per
co-present other, ~27 per character. Precomputing it into the index would cut
that, but a tag granted mid-turn would be missed, so it stays live.

### Not done

- The tick-loop shape guard lives in `tests/test_area_major_ticks.py`, not in
  `tests/test_perf_guards.py` as the Verification section says: that file
  carries another lane's lighting guards, and WT-0 does not edit other lanes'
  files. The assertion is the intended one — the number of wholesale roster
  passes per tick must not grow with the population.
- A whole-session two-run/same-seed trace diff is still owed. The sweep order is
  now a pure function of the graph, but `_process_wind_extinguish` and the
  trigger system still consume unseeded `random`, so a session-level
  determinism test belongs with that work rather than here.

