"""Awareness channels — audibility replaces a hop radius (task-418).

A text/graph world has no Euclidean space, so "within two rooms" is a spatial
fiction: hop radius was only ever a cheap proxy for *co-present at one remove*.
Sound is not a proxy. It is already implemented in `engine/sound.py` with a
per-way acoustic barrier (open 0.5 / see-through 0.75 / closed 1 / hidden 2), so
a locked door demotes a room for a physical reason instead of an arbitrary
``enter: 2``.

An **awareness channel** answers one question from one origin area: *what else
can be perceived from here, and how strongly?* The seam below exists so a second
channel — comms, magic, sight — is a class implementing `propagate`, not a second
place that knows how sound works.

Threshold semantics — **shockwave, deliberately.**
`engine.sound.propagate_sound` walks the graph as a pressure wave: it takes
every path and the loudness a listener perceives is set by the *least-damped*
route, not by whichever route a FIFO flood-fill happened to reach first (bug-30,
since fixed — it is a Dijkstra on cumulative barrier). So "audible above
threshold" here means "**some** route leaves enough penetration". A locked door
cuts a character out of attention only when no cheaper alternate route reaches
them, which is the physically honest outcome and the one this module is built on.
This does not depend on bug-30 *staying* fixed: the threshold is defined against
the returned amplitude, whatever walk produced it.
"""
from typing import Callable, Dict, Iterable, List, Optional, Sequence, Tuple

from engine import sound as _sound
from graph import Node, WorldGraph

# Tier order, highest first. A character is filed at its best tier, so an
# anchored character is never demoted by also being audible.
#
# Recency is deliberately *not* a tier. Nothing in the world makes an
# inaudible character attendable, so a recency tier could only ever restate
# co-presence at a lower rank — it is the within-tier sort key instead, which is
# also what the eviction order `(tier, recency, id)` says.
TIER_ANCHOR = 0
TIER_COPRESENT = 1
TIER_AWARE = 2
# A hook is the one reason to attend a character you cannot perceive: a mid-plan,
# a mid-quest, or a trigger whose scope they are inside of.
TIER_HOOK = 3

# Every channel reports strength in 0..1; this is the floor below which an area
# is merely "there" rather than something the origin can pick out.
DEFAULT_THRESHOLD = 0.05


class ChannelContext:
    """Per-pass scratch shared by the channels of one aware-set build.

    Building the `areas` map is O(graph); doing it once per channel per origin
    would multiply that by the number of anchors for no reason.
    """

    __slots__ = ("graph", "areas")

    def __init__(self, graph: WorldGraph):
        self.graph = graph
        self.areas: Optional[Dict[str, Node]] = None

    def all_areas(self) -> Dict[str, Node]:
        if self.areas is None:
            self.areas = {n.id: n for n in self.graph.nodes.values()
                          if n.type == "area"}
        return self.areas


class AwarenessChannel:
    """The channel seam. One method, one contract: area_id -> strength 0..1.

    `propagate` must include the origin area itself, so a caller can ask "is this
    area aware of itself" without a special case.
    """

    name = "channel"

    def __init__(self, threshold: float = DEFAULT_THRESHOLD):
        self.threshold = float(threshold)

    def propagate(self, graph: WorldGraph, origin_area_id: str,
                  context: Optional[ChannelContext] = None) -> Dict[str, float]:
        raise NotImplementedError


class SoundChannel(AwarenessChannel):
    """Sound as an awareness channel.

    `penetration` is the engine's own sound scale (0-3: whisper..scream); the
    returned strengths are that scale normalised to 0..1, so a channel threshold
    is comparable across channels and a louder voice simply reaches further.
    """

    name = "sound"

    def __init__(self, penetration: Optional[int] = None, threshold: float = 0.0,
                 respect_ambient_noise: bool = True):
        # A shout by default: a character you are aware of is one you could
        # plausibly hear, and a whisper is the wrong bar for "who is around".
        super().__init__(threshold)
        self.penetration = (_sound.SPEECH_LEVELS["shout"]
                            if penetration is None else int(penetration))
        self.respect_ambient_noise = respect_ambient_noise

    def propagate(self, graph: WorldGraph, origin_area_id: str,
                  context: Optional[ChannelContext] = None) -> Dict[str, float]:
        ctx = context or ChannelContext(graph)
        areas = ctx.all_areas()
        if origin_area_id not in areas:
            return {}
        penetration = self.penetration
        if self.respect_ambient_noise:
            # A shout in a loud room carries no further than a shout in a quiet
            # one, so noise is subtracted per area exactly as sound.py does.
            origin_noise = _sound.get_area_noise_level(areas[origin_area_id], graph)
            penetration = _sound.get_effective_penetration(penetration, origin_noise)

        heard = _sound.propagate_sound(origin_area_id, penetration, graph, areas)
        scale = float(self.penetration) or 1.0
        out = {origin_area_id: 1.0}
        for area_id, (remaining, _direction) in (heard or {}).items():
            strength = remaining / scale
            if strength > 0:
                out[area_id] = strength
        return out


class AwarenessIndex:
    """Per-area aware sets, cached on graph **and** door-state revision.

    Two revisions, because a door is not a topology change: `way.properties
    ["current_state"] = "locked"` mutates the node in place and never bumps
    `graph.get_revision()`. Caching on the graph revision alone would keep a
    door's pre-lock awareness after the door was locked, which is exactly the
    barrier case the channel exists for. So the door fingerprint is part of the
    key: the shapes change, and comparing it short-circuits on the first door
    that actually moved.
    """

    def __init__(self, graph: WorldGraph,
                 channels: Optional[Sequence[AwarenessChannel]] = None):
        self.graph = graph
        self.channels: List[AwarenessChannel] = list(
            channels if channels is not None else [SoundChannel()])
        self._key: Optional[Tuple[int, tuple]] = None
        self._aware: Dict[str, Dict[str, float]] = {}

    # ── cache key ───────────────────────────────────────────────────────

    def _door_fingerprint(self) -> tuple:
        doors = []
        for node in self.graph.nodes.values():
            if node.type != "way":
                continue
            props = node.properties
            doors.append((node.id, props.get("current_state", "open"),
                          props.get("sound_barrier"),
                          bool(props.get("see_through", False))))
        return tuple(sorted(doors))

    def _current_key(self) -> Tuple[int, tuple]:
        return (self.graph.get_revision(), self._door_fingerprint())

    def invalidate(self) -> None:
        """Drop the cache. For a caller that mutates the world behind the graph."""
        self._key = None
        self._aware = {}

    def _fresh(self) -> None:
        key = self._current_key()
        if key != self._key:
            self._key = key
            self._aware = {}

    # ── queries ─────────────────────────────────────────────────────────

    def aware_from(self, area_id: str) -> Dict[str, float]:
        """area_id -> strongest strength over all channels, including the origin."""
        if not area_id:
            return {}
        self._fresh()
        cached = self._aware.get(area_id)
        if cached is not None:
            return cached
        ctx = ChannelContext(self.graph)
        merged: Dict[str, float] = {}
        for channel in self.channels:
            if not getattr(channel, "name", None):
                continue
            # `getattr` rather than attribute access: the seam is deliberately
            # duck-typed, so a channel that is not an AwarenessChannel subclass
            # but implements `propagate` is a valid channel, not a crash.
            threshold = getattr(channel, "threshold", 0.0)
            try:
                spread = channel.propagate(self.graph, area_id, ctx) or {}
            except Exception:  # a broken channel must not blind the others
                continue
            for other, strength in spread.items():
                if strength >= threshold and strength > merged.get(other, 0.0):
                    merged[other] = strength
        self._aware[area_id] = merged
        return merged

    def is_aware(self, origin_area_id: str, area_id: str) -> bool:
        """Is `area_id` perceptible at all from `origin_area_id`?"""
        return area_id in self.aware_from(origin_area_id)


# ── the attended set ─────────────────────────────────────────────────────


class Anchor:
    """One thing the attended set is built around.

    `kind` is `character` (a named character, attended by definition), `human`
    (a human player, attended by definition), or `item`/`location` (a pinned
    place — it contributes an area, not a person).
    """

    __slots__ = ("kind", "id")

    def __init__(self, kind: str, anchor_id: str):
        self.kind = kind
        self.id = anchor_id

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Anchor({self.kind!r}, {self.id!r})"

    @staticmethod
    def normalise(raw) -> Optional["Anchor"]:
        """Accept a dict, an Anchor, or a bare id, and refuse a blank one."""
        if raw is None:
            return None
        if isinstance(raw, Anchor):
            return raw
        if isinstance(raw, dict):
            kind = str(raw.get("kind") or "").strip()
            anchor_id = str(raw.get("id") or "").strip()
        else:
            kind, anchor_id = "character", str(raw).strip()
        if not anchor_id:
            return None
        return Anchor(kind or "character", anchor_id)


def normalise_anchors(raw: Iterable) -> List[Anchor]:
    """Drop blanks, de-duplicate by (kind, id), keep the caller's order.

    Order matters: it is the first key of the eviction sort, so a stable order
    here is what makes the attended set reproducible.
    """
    out: List[Anchor] = []
    seen = set()
    for entry in raw or ():
        anchor = Anchor.normalise(entry)
        if anchor is None:
            continue
        key = (anchor.kind, anchor.id)
        if key in seen:
            continue
        seen.add(key)
        out.append(anchor)
    return out


def select_attended(anchors: Sequence[Anchor],
                    anchor_areas: Dict[str, str],
                    aware: Dict[str, Dict[str, float]],
                    characters_by_area: Callable[[str], Sequence[str]],
                    cap: int,
                    recency: Optional[Dict[str, int]] = None,
                    hooks: Optional[Iterable[str]] = None) -> List[str]:
    """The attended set: who runs at full fidelity, highest tier first.

    Tiers: an anchor; someone in an anchor's own room; someone in a room the
    anchor can perceive; then a hook. Each character is filed at its *best*
    tier. Within a tier the order is most-recently-in-the-foreground first,
    then id — so the result is reproducible for a fixed state.

    `characters_by_area` is called once per area some channel found audible and
    never for an area nothing perceives, so the cost is bounded by how much of
    the world is audible from the anchors — not by the population. That is the
    whole point of retiring the hop radius: the scan follows awareness.

    `recency` maps a character to its last foreground tick; absent means least
    recent. Nothing here stores it. `hooks` are characters a mid-plan,
    mid-quest or in-scope trigger cares about — the only way someone inaudible
    gets in.

    Returns at most `cap` ids.
    """
    cap = max(0, int(cap))
    if cap == 0:
        return []

    anchors = normalise_anchors(anchors)
    if not anchors:
        return []
    recent = recency or {}
    hook_ids = set(hooks or ())

    co_present: Dict[str, str] = {}   # character -> the anchor's area they share
    audible: Dict[str, str] = {}      # character -> the anchor's area that hears them
    for anchor in anchors:
        area = anchor_areas.get(anchor.id)
        if not area:
            continue
        for who in (characters_by_area(area) or ()):
            co_present.setdefault(who, area)
        for other_area in (aware.get(area) or {}):
            if other_area == area:
                continue
            for who in (characters_by_area(other_area) or ()):
                audible.setdefault(who, area)

    best: Dict[str, int] = {}

    def offer(who: str, tier: int) -> None:
        if who not in best or tier < best[who]:
            best[who] = tier

    for anchor in anchors:
        if anchor.kind in ("character", "human"):
            # An anchor is attended even if they are nowhere near themselves —
            # the human's own character, the one being followed.
            offer(anchor.id, TIER_ANCHOR)
    for who in co_present:
        offer(who, TIER_COPRESENT)
    for who in audible:
        offer(who, TIER_AWARE)
    for who in hook_ids:
        offer(who, TIER_HOOK)

    # Negated recency so an ascending sort puts the most recent first.
    ranked = sorted(best.items(),
                    key=lambda kv: (kv[1], -recent.get(kv[0], -1), kv[0]))
    return [who for who, _tier in ranked[:cap]]
