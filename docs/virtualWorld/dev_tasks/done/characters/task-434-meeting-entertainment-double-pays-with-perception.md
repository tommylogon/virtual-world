---
type: task
status: done
area: characters
priority: low
---

# task-434: Meeting Entertainment double-pays with perception novelty

**Filed:** 2026-09-21  
**Found in:** task-420's notes, carried into task-423 and left unfixed there
because it needs a small refactor that task-423 did not require.  
**Relates:** task-403 (observation memories), task-425 (novelty curve),
task-423 (background social).

## Outcome (2026-09-21)

Fixed, and it turned into three fixes because the first one exposed two more.

**1. The node id.** `Player.node_id_for(name)` is now the single definition of
the character-node-id convention; `Player.node_id` is derived from it at
construction (so it survives reload — the deserializer builds Players without
going through `PlayerManager.add_player`, which is why deriving beats assigning)
and `PlayerManager.get_player_node_id` delegates to it. Relationships key by name
and observation memories key by node id, so this is the bridge the novelty grant
needed.

**2. The grant is now one path.** `_grant_meeting_entertainment` goes through the
shared novelty curve keyed on the counterpart's node id, and it both **reads and
records** the observation. Recording is what makes it idempotent in either order:
perception-first reads a fresh tick and pays nothing; meeting-first records, so a
later perception pays nothing. The flat +10 (and its duplicate trait logic) is
gone. *(My first attempt only read, and the test caught it — meeting first then
perceiving would still have paid twice.)*

**3. Which exposed the real problem: perception novelty never paid at all.**
`_grant_arrival_entertainment` called `grant()`, which *recomputes* freshness
from the tick `observe_area` had just refreshed — so it measured 0 for every
subject on every arrival. Perceived novelty had been silently paying nothing since
task-425; the camp's Entertainment came from the fixtures and (later) social
conversations. The fix is `grant_freshness`, which pays the value `observe_area`
reported. My task-425 tests checked `grant` and `observe_area` separately and
never the composition, which is exactly how it hid.

**4. Which exposed two more, in the novelty curve itself.** Both measured, both
fixed:

- **The window was measured in the wrong unit.** `freshness` compared a tick
  delta against a window authored in *game minutes*, so the "2 hour" window was 2
  hours only at 1 min/tick — at 15 min/tick it was 30 hours. It showed up as
  Entertainment 59 at 15 min/tick vs 89 at 1 min/tick. `Player.minutes_per_tick`
  is now refreshed by the tick loop and the window is derived in ticks.
- **The window guards bouncing but not roaming.** With 31 areas a character
  revisits a given one only after ~5 hours, so *every arrival* is a fresh subject
  and pays. Measured with only the area subject paying and social switched off, a
  single day still pinned Entertainment at 81 average. `NOVELTY_DAILY_BUDGET = 30`
  (below Entertainment's ~43/day decay, so novelty is a top-up and *things* hold
  the meter up) now bounds it. This is task-425's own "diminishing returns within
  a day" option, which the measurement showed was needed **alongside** the window,
  not instead of it.

**5. People came off the arrival path.** Paying for characters on sight saturated
the meter (a crowded camp re-observes 5-10 people per arrival, all going stale
within the window): 87 avg / 100 max with the authored fixtures never firing.
`observe_area` now records the **area and its items** only; a person is claimed by
`register_first_meeting`, which is also what pays for meeting them.

Result, one week, 23 background characters, 23/23 alive:

| | 1 min/tick | 15 min/tick |
|---|---|---|
| Entertainment | **49.1** (40-68) | **50.1** (29-70) |
| Social | 81.4 | 81.4 |
| Hygiene | 72.4 | 74.3 |

Entertainment was 0, then pinned at 100, and now settles mid-range with the
recreational fixtures doing real work. Perf also improved (86-105 ticks/s vs
34-58) because perception observes fewer subjects.

## Problem

Two code paths pay Entertainment for the same experience — meeting someone:

1. **Perception novelty (task-425).** `observe_area` records a `character`
   subject for everyone standing in the area and `_grant_arrival_entertainment`
   pays the novelty curve for each, so walking into a room with a stranger pays.
2. **`Player._grant_meeting_entertainment`** (flat +10, curious ×1.5, homebody 0),
   called from `register_first_meeting` and from `update_relationship` when it
   creates a record.

A character who walks into a room and meets someone therefore gets both. It is
invisible in a background soak — the rendering paths that call
`register_first_meeting` (`engine/area_description.py`, `engine/scene_snapshot.py`)
only fire for the attended player, and a soak has no attended character taking
turns — so it matters for a human session, not for the soak numbers.

## Why it was not fixed in place

`engine/novelty.py` keys by **subject graph id** (`player_<name>`, the id
`observe_area` records), while `_grant_meeting_entertainment` is called with a
bare **name** and `Player` has no way to resolve one to the other — it does not
know the graph or the player manager. Task-423 populated `entity_ids` with node
ids on the *memory* side, but the novelty call site still cannot resolve one.

Options:

- **Set `node_id` on `Player`** when it is added to a world
  (`world.add_player` / the deserializer already know it via
  `player_manager.get_player_node_id`). Cleanest, and useful beyond this task —
  a character knowing its own graph id is generally handy.
- Pass the id down from the callers, which already have `world`/`graph` in scope.
- Keep a name-keyed novelty map, which reintroduces exactly the kind of parallel
  structure task-425 deleted.

Prefer the first, and only if the deserializer path can set it too, or a reloaded
character would silently stop being idempotent.

## Acceptance

- Meeting someone new pays novelty **once**, through `engine/novelty.py` —
  `_grant_meeting_entertainment` no longer has a flat boost of its own. **Done.**
- A character entering a room holding a stranger pays exactly the same as meeting
  one who walks in later (the ordering must not decide who gets paid). **Done, by
  the meeting grant recording the observation — and now also because arrival does
  not pay for people at all.**
- `curious` / `homebody` scaling still applies, since the novelty curve already
  carries it. **Done.**
- A reloaded save behaves identically to a fresh load. **Done** — `node_id` is
  derived from the name, not persisted, so it cannot go stale.
- A background week soak is unchanged (this should have no effect on it, which is
  also the check that nothing else leaned on the old path). **Not unchanged —
  it got better, because fixing this uncovered that perception novelty had never
  paid anything (see the outcome).**

## Non-goals

- Noticing a character who walks into the room you are already in. That is the
  perception trigger task-425 deferred, and it needs a perception pass on the
  *observer*, not a novelty change.
- Any change to the novelty curve itself.
