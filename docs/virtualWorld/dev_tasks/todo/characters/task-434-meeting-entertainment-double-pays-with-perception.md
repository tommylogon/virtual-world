---
type: task
status: todo
area: characters
priority: low
---

# task-434: Meeting Entertainment double-pays with perception novelty

**Filed:** 2026-09-21  
**Found in:** task-420's notes, carried into task-423 and left unfixed there
because it needs a small refactor that task-423 did not require.  
**Relates:** task-403 (observation memories), task-425 (novelty curve),
task-423 (background social).

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

- Meeting someone new pays novelty **once**, through
  `engine/novelty.py` — `_grant_meeting_entertainment` is deleted, not merely
  made conditional.
- A character entering a room holding a stranger pays exactly the same as meeting
  one who walks in later (the ordering must not decide who gets paid).
- `curious` / `homebody` scaling still applies, since the novelty curve already
  carries it.
- A reloaded save behaves identically to a fresh load.
- A background week soak is unchanged (this should have no effect on it, which is
  also the check that nothing else leaned on the old path).

## Non-goals

- Noticing a character who walks into the room you are already in. That is the
  perception trigger task-425 deferred, and it needs a perception pass on the
  *observer*, not a novelty change.
- Any change to the novelty curve itself.
