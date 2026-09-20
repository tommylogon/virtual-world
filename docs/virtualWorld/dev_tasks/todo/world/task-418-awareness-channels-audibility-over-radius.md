---
type: task
status: todo
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
