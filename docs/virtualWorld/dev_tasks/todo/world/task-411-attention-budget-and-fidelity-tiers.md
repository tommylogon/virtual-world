---
type: task
status: todo
area: world
priority: medium
---

# task-411: Attention budget and fidelity tiers

**Filed:** 2026-09-19  
**Depends on:** task-407 (graph indexes); conceptually on task-397 (scopes).  
**Spec:** `docs/design/long-horizon-simulation-progress.md` §1;
`docs/design/reversibility-contract.md`.

## Where this sits (not the timeskip simulator)

Three separate things, easy to conflate:

- **task-411 (this) = the selector.** Decides *who* is attended (full fidelity)
  vs backgrounded, from player/editor focus + anchors + radius + cap. It does
  not simulate anyone.
- **task-399 / task-409 = the non-focus runner.** The deterministic
  supercharged-simple-NPC sim that actually lives out time for everyone *outside*
  the attended set.
- **task-414 = time advance ("timeskip").** Running many ticks in a batch.

Status changes (focus moves) are the promote/demote seam: 411 names the set,
412 does the handoff, 399/409 carries the off-screen time.

## Design

- **Anchors:** the focused character, the human player, pinned locations/items.
- **Radius:** graph-hop distance from anchors; within X rooms counts as attended.
- **Cap:** global maximum on attended characters, with deterministic eviction.
- **Hysteresis:** no flapping on a boundary; promote on approach and on
  trajectory for roamers.
- Multiple spread-out humans each get a set; the shared cap is the knob.

## Concrete shape

```json
{
  "cap": 8,
  "radius_hops": 2,
  "hysteresis": {"enter": 2, "exit": 3},
  "anchors": [
    {"kind": "character", "id": "player_gribba"},
    {"kind": "human", "id": "player_human"},
    {"kind": "item", "id": "item_water_skin"}
  ],
  "attended": ["player_gribba", "player_human", "player_krikka"]
}
```

**Selection algorithm** (uses task-407 indexes, no full scan):

1. Multi-source BFS from anchors over exits, bounded to `max(enter, exit)` hops.
2. Candidate priority (high → low): anchor, human, pinned, then proximity by
   hop, then recency of last foreground tick, then id.
3. Fill to `cap` in priority order.
4. Hysteresis: a character already attended is kept while within `exit` hops;
   a new character enters only within `enter` hops.
5. Evict the lowest priority when over cap; ties broken by id for determinism.

Proposed defaults (configurable): `cap 8`, `enter 2`, `exit 3`.

**Worked example.** 23 goblins, cap 8, a human at `Chief's Pit`, following
Gribba. BFS radius 2 from those two anchors reaches ~7 characters → all
attended, everyone else backgrounded. Move the human to `Blackmarsh`: Gribba
stays attended (anchor), the old pit neighbours cross the `exit` radius and
demote, Blackmarsh neighbours enter. Two humans far apart each get a radius but
share the cap, so the nearest/high-priority win and the rest stay background.

## Changes

1. Compute the attended set over the graph without a per-tick full scan (reuse
   task-407 indexes).
2. Promote on approach/trajectory; demote on distance with hysteresis.
3. Deterministic eviction ordering; anchors serialized.
4. Feed the attended set into the tick loop so only attended characters run the
   foreground policy; everyone else stays background (task-399).

## Acceptance

- Attended-set size stays ≤ cap regardless of population (fixture test).
- Two humans far apart each get a set; total ≤ cap and deterministic for a
  fixed state.
- No flapping across a boundary (hysteresis test).
- Attended set and anchors survive save/load.
- Promotion here feeds task-412's catch-up handoff, not a second state model.

## Non-goals

- Physical chunk unloading / cross-chunk simulation (task-401).
- Changing per-character decision rules.
- Simulating or advancing time (that is 399/409 and 414).

## Verification

- Unit: cap enforcement, eviction determinism, hysteresis, serialization.
- A populated fixture (e.g. 200 characters) proving the set stays bounded.
