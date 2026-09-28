---
type: task
status: done
area: world
priority: high
---

# task-418: Awareness channels — audibility replaces `radius_hops`

**Filed:** 2026-09-20  
**Amends:** task-411 (attention budget), specifically the `radius_hops` /
`hysteresis` design.  
**Depends on:** task-416 (area index), task-407 (indexes), `engine/sound.py`.  
**Related:** bug-30 (sound propagation path selection).

## Problem

task-411 selects the attended set using `radius_hops: 2` — graph-hop distance
from anchors. In a text/graph world with no Euclidean space, hop radius is an
arbitrary spatial fiction. Its only actual job is **bounding cost**: it is a
cheap proxy for "co-present at one remove."

That proxy is now unnecessary, because the world already has a principled
cross-area channel: **sound**. Sound is the only way characters interact through
a way. It is already implemented with per-way barriers (open 0.5 / see-through
0.75 / closed 1 / locked·blocked 1 / hidden 2) in `engine/sound.py` — which is exactly the sober
form of "one hop away," with the advantage that a locked door demotes someone
for a *physical* reason instead of an arbitrary `enter: 2`.

## Design

**Awareness is a set of channels, each answering one question: from this origin
area, what else can be perceived, and how strongly?**

```python
class AwarenessChannel:
    def propagate(self, graph, origin_area_id) -> dict[str, float]:
        """area_id -> strength (0..1), including the origin."""
```

Priority order for the attended set (highest first):

1. **Anchors** — the focused character, the human, pinned items/locations.
2. **Co-present** — same area as an anchor.
3. **Aware** — reachable through any channel above its threshold.
4. **Recency** — recency of last foreground activity.
5. **Hooks** — mid-plan, mid-quest, or inside a trigger's scope.

Fill to `cap`, evict deterministically by `(tier, recency, id)`.

### Channels

| Channel | Source | Notes |
|---------|--------|-------|
| `sound` | `engine/sound.py` propagation | Implement now. |
| `comms` | communication items (radio, phone) | Later; item-scoped, not area-scoped. |
| `magic` | scrying / sending spells | Later. |
| `sight` | spyglass / telescope, line-of-sight | Later; needs a sight model, not just barriers. |

`Radius_hops` is retired. Hysteresis, if kept at all, applies to a channel
threshold (avoid flapping when a door opens/closes), not to a hop count.

### Caching

Sound propagation is a graph walk. Cache the per-area aware set on **graph and
door-state revision**, exactly as `engine/lighting.py`'s
`recompute_area_lights()` caches on the graph revision. Never recompute per
character or per tick.

## Interaction with bug-30 — read before implementing

bug-30 notes that `engine/sound.py` uses a FIFO BFS that returns the *first*
path rather than the *least-damped* path, and the dev note on that bug argues
sound should behave like a **shockwave** (any surviving amplitude), not a
single cheapest route.

For attention this distinction is small: the question here is "is any route
audible above threshold," which is closer to the shockwave reading than to
shortest-path. Do not let this task silently depend on bug-30 being fixed — pick
the semantics deliberately and state which one the threshold means. If a
locked door must be able to cut a character out of attention, that requires the
route *not* being reachable by a cheap alternate path, which the current FIFO
walk may or may not give.

## Acceptance

- Attended set is derived without any hop-radius parameter.
- A character separated from all anchors by a locked/closed door sequence is
  **not** attended (barrier test with a fixture).
- Awareness results are cached and not recomputed per character per tick.
- The set stays ≤ cap and is deterministic for a fixed state.
- Removing `radius_hops` does not change which characters are *co-present*.
- Channel interface has one implemented channel (`sound`) and a test double for
  a second, proving the seam works without implementing comms/magic.

## Non-goals

- Implementing communication items, magic, or scrying (those are their own
  tasks; this task only defines the channel seam).
- Changing per-character decision rules.
- Simulating or advancing time (task-399/409, task-414).

## Verification

- Unit: fixture with A–B open, B–C locked → sound from A reaches B, not C.
- Unit: cap enforcement, eviction determinism, serialization of anchors.
- Perf: awareness cached; a 200-character fixture proves no per-tick full scan.

## Progress — 2026-09-28

`engine/awareness.py` (new, 34 tests in `tests/test_awareness_channels.py`) plus
`TickManager.attended_set()` / `TickManager.awareness()`.

### The seam

```python
class AwarenessChannel:
    def propagate(self, graph, origin_area_id, context=None) -> dict[str, float]:
        """area_id -> strength 0..1, including the origin."""
```

One implemented channel (`SoundChannel`) and one test double
(`_TeleportChannel`) proving the seam without implementing comms or magic. The
seam is duck-typed on purpose: `getattr(channel, "threshold", 0.0)` and
`getattr(channel, "name", None)`, so a channel that is not an
`AwarenessChannel` subclass but implements `propagate` is a valid channel. That
was not a free choice — the first version read `channel.threshold` directly and
a `try/except` silently swallowed the resulting `AttributeError`, so a
perfectly good second channel produced nothing and the tests failed for a
reason that had nothing to do with the test.

A channel that *raises* is still isolated (one broken channel must not blind the
others), which is why the `except` is there at all.

### bug-30 is already fixed — and the semantics are stated anyway

The task asks not to depend on bug-30. It no longer applies: `propagate_sound`
is a **Dijkstra on cumulative barrier**, explicitly documented as taking every
path and letting the least-damped route set the perceived loudness. That is the
shockwave reading the task asked to choose deliberately. The threshold is
defined against the *returned amplitude* rather than against the walk's
algorithm, so the choice does not silently depend on the walk staying as it is.

### A locked door is a latch, not a soundproof wall

The most useful thing the tests pinned. `engine/sound.py` gives locked and
closed the same barrier, because a lock adds no acoustic mass. The honest
consequences, both now asserted:

- A **shout crosses one locked door** (0.5 + 1 = 1.5, shout 2 → 0.5 survives).
- Exclusion comes from a **chain**: 0.5 + 1 + 1 = 2.5 stops a shout. Three doors
  in, the room is not audible; two doors in, it is.

A channel that treated a single locked door as cutting someone off would be
inventing physics, and the barrier arithmetic would be tuned to a lie. Every
barrier test names its `penetration` explicitly (whisper 0 / normal 1 / shout 2 /
scream 3; open 0.5 / see-through 0.75 / closed 1 / hidden 2) rather than relying
on a default, because the arithmetic *is* the test.

`SoundChannel` defaults to a **shout** with threshold 0: a character you are
aware of is one you could plausibly hear, and a whisper is the wrong bar for
"who is around". The cap, not the channel, is what bounds the result.

### Caching: two revisions, because a door is not topology

`graph.get_revision()` covers node and edge changes, but
`way.properties["current_state"] = "locked"` mutates in place and never bumps
it. Caching on the graph revision alone would keep a door's pre-lock awareness
after the door was locked — precisely the case the channel exists for. So the key
is `(graph_revision, door_fingerprint)`, the fingerprint being the
`(id, current_state, sound_barrier, see_through)` tuples of every way. Comparing
it short-circuits on the first door that actually moved, so the common case —
nothing changed — is one walk of the way list, not a Dijkstra per origin.

### Recency is a sort key, not a tier

The task lists recency as priority level 4, below "aware". Built that way it is
dead: anyone in the aware set is already tier *aware*, and a recency tier could
only restate co-presence at a lower rank. So recency is the **within-tier** key,
which is also exactly what the eviction order `(tier, recency, id)` says. Tiers
are anchor → co-present → audible → hook, and recency breaks ties inside one.
A hook is the one reason to attend someone you cannot perceive — a mid-plan, a
mid-quest, a trigger whose scope they are inside of.

### The scan follows awareness

`characters_by_area` is called once per **audible** area and never for an area
nothing perceives, so the cost is bounded by how much of the world is audible
from the anchors, not by the population. That is the whole point of retiring the
hop radius.

Measured through the real entry point with 200 characters in one room: the
attended set is 8 long and the roster dict is iterated **0** times. At 8
characters it is iterated 0 times too — the assertion is that the count does not
*grow*, which is what "no per-tick full scan" means.

Candidates come from task-416's `characters_in` presence buckets, so this task
depends on 416 exactly as its frontmatter says, and the two compose without a
new index.

### Not done

- task-411 keeps the **feed** into the tick loop (promote/demote, hysteresis on a
  channel threshold rather than a hop count, and the save/load of anchors). This
  task is authoritative for *selection* and stops there; nothing here writes
  fidelity state, so the two cannot disagree about who is in the set.
- No `hysteresis` parameter. A channel threshold is a plain float and flapping
  is a selection-policy question that belongs with the feed.

