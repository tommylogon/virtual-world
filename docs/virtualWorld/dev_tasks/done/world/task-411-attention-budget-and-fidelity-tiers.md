---
type: task
status: review
area: world
priority: medium
---

# task-411: Attention budget and fidelity tiers

**Filed:** 2026-09-19  
**Depends on:** task-407 (graph indexes); conceptually on task-397 (scopes).  
**Spec:** `docs/design/long-horizon-simulation-progress.md` §1;
`docs/design/reversibility-contract.md`.

> **Amended by task-418.** `radius_hops` is superseded. In a text/graph world
> a hop radius is an arbitrary spatial fiction whose only real job is bounding
> cost; attendance now derives from **awareness channels** (sound first,
> reusing `engine/sound.py`'s per-way barriers), plus co-presence, recency and
> hooks. Keep the anchors, cap, and eviction determinism from this task;
> treat `radius_hops` / `hysteresis` as retired. task-418 is authoritative for
> the attended-set selection.

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

## Progress — 2026-09-28 (in `review`)

### This task and task-418 are one piece of work, and 411 is the half 418 delegates to

411 is amended twice: its own amendment retires `radius_hops` / `hysteresis` and
says attendance derives from awareness channels, then task-418 (filed later,
`high`, still `todo`) is declared authoritative for the selection and specifies
the `AwarenessChannel` seam. 411's hand-off target, task-412, is **cancelled**.

So the two tasks describe the same module. Rather than build 411 against a spec
418 is about to replace — the churn the amendment explicitly warns about — 411 is
built as the half 418 delegates to:

- **418 supplies the channels.** `AwarenessChannel` is the seam it specifies, and
  `SoundChannel` is its one headline channel.
- **411 supplies the budget**: the cap, the ordering, the eviction, hysteresis as
  a channel threshold, and the save/load state.

`tests/test_attention.py` includes a second channel implementation (`_RopeChannel`,
standing in for a future `comms`) precisely so the seam is proven to work without
comms, magic or sight existing — 418's own acceptance line.

**Recommendation, not mine to make: 411 and 418 should be closed into one task.**
Shipping both as written would duplicate `engine/attention.py`. Posted to the
board.

### `radius_hops` is gone, and so is hop hysteresis

The selection takes no radius parameter and holds no hop-shaped state; a test
asserts neither the class source nor its instance state contains one, and that the
serialised form does either. Hysteresis moved onto the **channel threshold** the
amendment asked for: entering needs strength ≥ `aware_threshold`, staying needs
≥ `aware_threshold - ENTER_MARGIN`. A character balanced on the boundary is
promoted once and then kept, so a door swinging in the draught cannot make the set
churn. The asymmetry is one-way and tested both ways — a newcomer below the floor
does not sneak in when somebody else leaves.

### Three decisions the tests forced, none of which were free

**Awareness orders, the cap decides — awareness does not filter.** This is the
one a reader assumes the opposite of, so it is stated in the module and pinned by
`test_awareness_orders_rather_than_filters`. A character behind a locked door is
ranked below everybody the door cannot separate them from; they end up backgrounded
when the cap is full, which is the case a budget exists for. Making awareness
*exclude* would make attention grow and shrink with world topology rather than
with the cap, and would leave a quiet afternoon attended by nobody at all. Every
"is not attended" fixture is therefore deliberately oversubscribed.

**The threshold sits where the door states separate.** With strength
`1/(1 + cumulative_barrier)`:

| route | cost | strength | aware (≥ 0.55)? |
|---|---|---|---|
| the same room | 0 | 1.00 | yes |
| one open door | 0.5 | 0.67 | yes |
| one window | 0.75 | 0.57 | yes, faintly |
| one closed / locked / blocked door | 1.0 | 0.50 | **no** |
| one hidden panel | 2.0 | 0.33 | no |
| two open doors | 1.0 | 0.50 | no |

The last two rows are the same number and that is not a defect: two open doors
really do attenuate exactly as much as one closed door. A cost-based channel
cannot tell them apart, and pretending otherwise would mean the threshold was not
measuring what it says. `1/(1+cost)` was chosen over `remaining/penetration`
because the latter puts the threshold at a different place for every penetration
value, making it a knob whose *meaning* moves when somebody turns it.

**Sound takes the strongest route, and that is a stated choice.** task-418 warned
not to depend on bug-30 being fixed. It was (2026-09-22, `propagate_sound` is a
least-cost Dijkstra walk), so the dependence is real and satisfied rather than
assumed. The consequence is tested: a locked door only demotes somebody when
**no** quiet alternate reaches them — shut the door but leave a window, and they
stay aware; shut both and they go.

### What the model reads, and what it does not

`select()` takes the roster as an argument (`{id: {area_id, recency}}`) rather
than reading a global, so the selection is a pure function of its arguments and
testable with no engine running. Awareness is **seeded from the anchors' and the
already-attended characters' areas**, not from every area in the world — probing
all 200 would be 200 graph walks to answer a question about a handful of rooms,
which is the cost this task exists to bound. A 200-character star fixture proves
the set stays at the cap, and `channel_walks` is exposed so a test can assert the
cache holds rather than inferring it from timing.

**A live bug this task's own test caught.** `AttentionBudget._channel_signature`
called `channel.signature()` without passing the graph, so `SoundChannel` fell
back to its stateless short form and the cache key reduced to the graph revision
alone — the exact task-421 trap, reproduced a second time because the same mistake
is easy to make twice. A door closing would have served a stale aware set
forever. Fixed, and the test asserts on the awareness *value* and the walk count
rather than the attended set, precisely because a broken cache would still have
produced the right attended set when the cap had room.

### Serialisation

`to_state` carries the budget, the anchors, the humans, the pinned and the
attended set — and `DERIVED_KEYS` names what must **never** be saved: awareness is
derived from the graph and goes stale the moment a door moves, so a save that looks
resumable while quietly disagreeing with its world is worse than one that clearly
re-derives. `from_state` returns the inputs rather than mutating the budget, so
two budgets with different caps can read the same save — a save is a fact about a
world, not about the reader's settings.

### New tests — `tests/test_attention.py` (31)

The amended acceptance rather than the original: no hop parameter anywhere; the
cap holding at every population from 0 to 200; byte-identical sets for a fixed
state; eviction invariant under a *reordered* roster (so a save/load that reorders
a dict cannot change the world); the anchor and the human surviving an
oversubscribed cap even when far away and maximally stale, and a stale anchor id
ignored rather than reserving a slot; the locked-door and window barriers;
awareness ordering rather than filtering; the no-flap boundary in both directions;
promotion and demotion reported so a caller can hand off; the cache holding across
20 reselects; a single walk for a single anchor; a door close invalidating the
cache with the revision pinned; a new area invalidating it; a second graph with the
same revision not serving the first's cache; the second-channel seam; the strongest
channel winning; an unimplemented channel refusing to be used; and the task's own
worked example (23 goblins and a human, cap 8).

### Not done here

Nothing calls `select()`. Feeding the attended set into the tick loop is
task-399/409 (WT-C) and the time advance is task-414 (WT-0) — both outside this
lane, and 411's own non-goals say so. The module is a selector with no caller
until one of those lands.
