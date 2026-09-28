"""Attention budget: who is attended, and the cap that bounds it (task-411).

The selector, and nothing else. It decides *who* runs the foreground policy and
who is backgrounded. It does not simulate anybody, does not advance time, and
does not keep a second copy of anyone's state — task-399/409 carries the
off-screen time, task-414 advances the clock.

**`radius_hops` and `hysteresis` are retired.** The task was amended twice over:
task-411's own amendment ("attendance now derives from awareness channels ...
treat `radius_hops` / `hysteresis` as retired"), then task-418, which is
authoritative for the selection and specifies the `AwarenessChannel` seam this
module implements. A hop radius in a text world is a spatial fiction whose only
real job is bounding cost, and this module bounds cost with an explicit `cap`
instead — the honest mechanism, and the one the amendment kept.

So the shape is **a candidate set from channels, then a budget**, which is why
the two halves are separable: 418 supplies the channels, this supplies the cap,
the ordering and the eviction. That is also why this module is not obsoleted by
418.

Three decisions worth stating, because they are the ones that bite:

**Eviction is total, not incremental.** A character is either attended or
backgrounded; there is no partial fidelity. The cap is a hard line, not a soft
budget to be averaged against, so a cap of 8 with 30 candidates means 22 are
genuinely not run. Anything wanting a "mostly-attended" middle has to ask for
that explicitly rather than get it by accident.

**Awareness is seeded from anchors, not from every area.** A channel answers
"from *this* origin area, what else can be perceived", and the origins that
matter are the areas the anchors and the already-attended characters stand in.
Probing every area in the world would be O(areas) graph walks to answer a question
about a handful of rooms, which is the cost this whole task exists to bound.

**Awareness orders, the cap decides — awareness does not filter.** This is the
one thing a reader is most likely to assume otherwise, so it is worth being
blunt about. A character behind a locked door is not *excluded* by the door; they
are ranked below everybody the door cannot separate them from. They end up
backgrounded when the cap is full, which is the realistic case — a budget exists
because there are more characters than budget — and not before. Setting this the
other way (dropping unaware candidates outright) would make attention shrink and
grow with the world's topology rather than with the cap, and would make a quiet
afternoon attended by nobody at all.

**Ties break on id, and recency is a frozen input, not a clock.** The ordering is
``(tier, recency, id)`` with recency read from the caller's state, so two runs of
the same state produce byte-identical sets. A ``time.time()`` anywhere in here
would make the set unreproducible, and an unreproducible attention set cannot be
regression-tested at all — which is the acceptance criterion.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

#: Candidates are ranked by this tuple, highest first. Named rather than inlined
#: so a channel, a report or a test can talk about tiers without magic numbers.
TIER_ANCHOR = 0
TIER_HUMAN = 1
TIER_PINNED = 2
TIER_COPRESENT = 3
TIER_AWARE = 4
TIER_RECENT = 5
TIER_NONE = 6

TIER_NAMES = {
    TIER_ANCHOR: "anchor",
    TIER_HUMAN: "human",
    TIER_PINNED: "pinned",
    TIER_COPRESENT: "co-present",
    TIER_AWARE: "aware",
    TIER_RECENT: "recent",
    TIER_NONE: "far",
}

#: The default budget. Deliberately small: a cap is a promise about cost, and the
#: task's own worked example is 23 goblins, so 8 is a real cut and not a no-op.
DEFAULT_CAP = 8

#: A channel strength at or above this counts as "aware". This is the
#: *hysteresis threshold* the amendment moved off a hop count and onto a channel
#: value: a character demotes when their strength falls below it, which is a
#: physical statement (the door closed) rather than an arbitrary radius.
#:
#: 0.55 is where the door states separate, and the separation is the point. With
#: the `1/(1+cost)` strength curve (:class:`SoundChannel`):
#:
#: | route | cumulative cost | strength | aware? |
#: |---|---|---|---|
#: | the same room | 0 | 1.0 | yes |
#: | one open door | 0.5 | 0.67 | yes |
#: | one window | 0.75 | 0.57 | yes — faintly, but yes |
#: | one closed or locked door | 1.0 | 0.50 | **no** |
#: | one hidden panel | 2.0 | 0.33 | no |
#: | two open doors | 1.0 | 0.50 | no |
#:
#: The last two rows are the same number, and that is not a defect: two open
#: doors really do attenuate exactly as much as one closed one. A cost-based
#: channel cannot tell them apart, and pretending otherwise would mean the
#: threshold was not measuring what it says.
DEFAULT_AWARE_THRESHOLD = 0.55

#: Entering needs strictly more strength than staying, so a character balanced on
#: the threshold does not flap. A door swinging in the draught should not
#: repeatedly promote and demote somebody. Small on purpose: a wide margin would
#: keep characters in the set that the threshold just excluded them from, which
#: defeats the point of having a threshold.
ENTER_MARGIN = 0.05

#: Strength of an area a character is standing in. Defined here rather than
#: inferred from a channel, because co-presence is not a perception result — it
#: is a fact about where somebody is, and it holds through a locked door.
COPRESENT_STRENGTH = 1.0


class AwarenessChannel:
    """One way of perceiving beyond the room you stand in (task-418's seam).

    A channel answers one question — *from this origin area, what else can be
    perceived, and how strongly?* — and knows nothing about caps, priorities or
    characters. That separation is the point: task-418 defines the channel set
    (``sound`` now, ``comms``/``magic``/``sight`` later) and this module consumes
    any of them without knowing which are present.
    """

    #: Stable id, used in serialised state and in the report. A channel's name is
    #: part of the observable output, so it must not be the class name.
    name = "channel"

    def propagate(self, graph, origin_area_id: str) -> Dict[str, float]:
        """``area_id -> strength in 0..1``, including the origin at 1.0."""
        raise NotImplementedError

    def signature(self, graph=None) -> str:
        """A cheap fingerprint of the world inputs that change this channel.

        Part of the cache key. A channel whose answer depends on something the
        graph revision does not cover — a door's state, say — has to say so here,
        or the cache serves a stale awareness set. That is exactly the bug
        task-421 found in ``engine/lighting.py``.

        *graph* is passed in rather than remembered, so a channel holds no
        reference to the world it was last asked about.
        """
        return ""


class SoundChannel(AwarenessChannel):
    """Awareness by audibility, over the per-way barriers in ``engine.barriers``.

    Sound is the one cross-area channel the world already has, and it is the
    sober form of "one hop away": a locked door demotes somebody for a physical
    reason rather than because they are three rooms away.

    **The semantics are the shockwave one, chosen deliberately** as task-418
    asked: strength comes from the *strongest* (least-damped) route, because a
    sound is a pressure wave that takes every path. This does depend on bug-30
    being fixed, and it was (2026-09-22 — ``propagate_sound`` is a least-cost
    Dijkstra walk), so the dependence is real and satisfied rather than assumed.
    A first-touch FIFO walk would have let a loud detour *beat* a quiet one,
    which is not how a threshold should read.

    The consequence worth stating: a locked door only cuts a character out of
    attention when **no** quiet alternate route reaches them. Two rooms joined by
    a locked door and also by a long open corridor are still aware of each other,
    and that is correct — you can hear them through the corridor.
    """

    name = "sound"

    def __init__(self, threshold: float = DEFAULT_AWARE_THRESHOLD,
                 penetration: int = 2):
        self.threshold = float(threshold)
        #: How far a shout carries, in barrier units. It bounds the *walk*, not
        #: the strength: `propagate_sound` drops an area once the cumulative
        #: barrier reaches this, so a large value explores more of the graph
        #: without changing what any particular route scores.
        self.penetration = int(penetration)

    def propagate(self, graph, origin_area_id: str) -> Dict[str, float]:
        from engine.sound import propagate_sound

        areas = {n.id: n for n in graph.nodes.values() if n.type == "area"}
        if origin_area_id not in areas:
            return {}
        heard = propagate_sound(origin_area_id, self.penetration, graph, areas)
        # `propagate_sound` reports REMAINING penetration, so the cumulative
        # barrier of the best route is `penetration - remaining`. Strength is
        # `1/(1+cost)` rather than `remaining/penetration` because the latter
        # puts the threshold at a different place for every penetration value,
        # which makes the threshold a tuning knob that silently changes meaning
        # when somebody raises it.
        strengths = {
            area_id: 1.0 / (1.0 + max(0.0, self.penetration - float(remaining)))
            for area_id, (remaining, _direction) in heard.items()
        }
        strengths[origin_area_id] = 1.0
        return strengths

    def signature(self, graph=None) -> str:
        from engine.barriers import signature as way_signature

        if graph is None:
            return f"penetration:{self.penetration}"
        return f"penetration:{self.penetration}:" + way_signature(
            n for n in graph.nodes.values() if n.type == "way"
        )


class AttentionBudget:
    """The cap, the ordering, the eviction, and the state that survives a save.

    Not a singleton and not a component: construct one, ask it, read the result.
    The only state kept between calls is what the caller hands back in (the
    previous attended set), because hysteresis is exactly "compare against what
    was attended last time".
    """

    def __init__(self, *, cap: int = DEFAULT_CAP,
                 aware_threshold: float = DEFAULT_AWARE_THRESHOLD,
                 channels: Optional[Sequence[AwarenessChannel]] = None,
                 enter_margin: float = ENTER_MARGIN):
        self.cap = max(0, int(cap))
        self.aware_threshold = float(aware_threshold)
        self.enter_margin = float(enter_margin)
        self.channels: List[AwarenessChannel] = list(channels) if channels is not None \
            else [SoundChannel()]
        self._cache: Dict[str, Dict[str, float]] = {}
        self._cache_key: Optional[tuple] = None
        self._cache_graph = None
        #: How many channel walks the last `select` performed. Exposed so a test
        #: can assert the cache actually holds rather than inferring it from
        #: timing, which is how a cache regression hides.
        self.channel_walks = 0

    # ── the cache ────────────────────────────────────────────────────────
    #
    # Sound propagation is a graph walk. Recomputing it per character, per tick is
    # what makes a long-horizon run unaffordable, so the aware set is computed
    # once per (graph revision, door states) and reused. Both components are
    # needed: a door closing changes awareness without changing the graph, which
    # is the same trap `engine/lighting.py` fell into until task-421.

    def aware_from(self, graph, origins: Iterable[str]) -> Dict[str, float]:
        """Strongest awareness any of *origins* has, merged into one map.

        Cached on ``(graph identity, graph revision, channel signatures)``.
        """
        key = (id(graph), graph.get_revision(), self._channel_signature(graph))
        if self._cache_key != key:
            self._cache = {}
            self._cache_key = key
            self._cache_graph = graph
        missing = [o for o in dict.fromkeys(origins) if o and o not in self._cache]
        for origin in missing:
            self.channel_walks += 1
            for channel in self.channels:
                for area_id, strength in channel.propagate(graph, origin).items():
                    if strength > self._cache.get(area_id, -1.0):
                        self._cache[area_id] = strength
        return self._cache

    def _channel_signature(self, graph) -> str:
        # The graph HAS to be passed through. A channel that reports only
        # "penetration:2" here would leave the cache keyed on the graph revision
        # alone, and a door closing would serve a stale aware set — the exact bug
        # task-421 found in `engine/lighting.py`, reproduced in a second place
        # because the same mistake is easy to make twice.
        return "|".join(
            f"{channel.name}:{channel.signature(graph) or 'stateless'}"
            for channel in self.channels
        )

    def invalidate(self) -> None:
        """Drop the awareness cache. For a caller that mutates the graph itself."""
        self._cache = {}
        self._cache_key = None
        self._cache_graph = None

    # ── the selection ────────────────────────────────────────────────────

    def select(self, graph, *, anchors: Optional[Iterable[Mapping[str, Any]]] = None,
               humans: Optional[Iterable[str]] = None,
               pinned: Optional[Iterable[str]] = None,
               characters: Optional[Mapping[str, Mapping[str, Any]]] = None,
               previously_attended: Optional[Iterable[str]] = None,
               zones_in_play: Optional[Iterable[str]] = None) -> Dict[str, Any]:
        """Pick the attended set from a fixed world state. Mutates nothing.

        *characters* maps ``character id -> {"area_id", "recency",
        "world_scope_id"}``. It is the caller's view of the world, read from a
        mapping rather than a global, so the selection stays a pure function of
        its arguments and is testable without a running engine.

        *zones_in_play*, when given, turns on the zone-keyed fidelity of
        task-500: a character's zone is read off its ``world_scope_id`` and
        compared with the zones in play plus the anchors' own, so a character in
        a zone nobody is attending ranks below everything. Off by default, because
        a world with no zones should not pay for the key.
        """
        roster = {str(cid): dict(info) for cid, info in (characters or {}).items()}
        humans = {str(h) for h in (humans or ())}
        pinned = {str(p) for p in (pinned or ())}
        # Deliberately NOT unioned with `humans`: the task ranks anchor above
        # human above pinned, and a human who is also an anchor is an anchor
        # while a human who merely is one is a human. Collapsing the two would
        # make TIER_HUMAN unreachable and lose a real distinction.
        anchor_ids = {str(a.get("id")) for a in (anchors or ()) if a.get("id")}
        previous = {str(p) for p in (previously_attended or ())}

        # A human is a seed even when not an anchor: a human standing alone at
        # the far end of the map still defines where attention should reach.
        seed_ids = anchor_ids | humans
        anchor_areas = {
            str(roster[cid].get("area_id")) for cid in seed_ids if cid in roster
        }
        # Seeds: where the anchors are, plus wherever the currently-attended
        # already are, so an attended character stays aware of its own room
        # without a walk per character.
        seeds = [a for a in sorted(anchor_areas) if a]
        seeds += sorted({
            str(roster[cid].get("area_id")) for cid in previous
            if cid in roster and str(roster[cid].get("area_id")) not in anchor_areas
        })
        aware = self.aware_from(graph, [a for a in seeds if a])

        awareness = {
            cid: self._strength(cid, roster, aware, anchor_areas)
            for cid in roster
        }

        zone_tiers = self._zone_tiers(roster, seed_ids, zones_in_play)

        ranked = sorted(
            roster,
            key=lambda cid: self._rank_key(cid, roster, anchor_ids, humans,
                                           pinned, awareness, previous, zone_tiers),
        )
        attended = ranked[:self.cap]
        return {
            "attended": sorted(attended),
            "cap": self.cap,
            "tiers": {cid: TIER_NAMES[self._tier(cid, roster, anchor_ids, humans,
                                                  pinned, awareness, previous,
                                                  zone_tiers)]
                      for cid in attended},
            "awareness": {cid: round(awareness[cid], 4) for cid in attended},
            "promoted": sorted(cid for cid in attended if cid not in previous),
            "demoted": sorted(cid for cid in ranked[self.cap:] if cid in previous),
            "oversubscribed": max(0, len(ranked) - self.cap),
            "channel_walks": self.channel_walks,
        }

    @staticmethod
    def _zone_tiers(roster, seed_ids, zones_in_play) -> Dict[str, int]:
        """Zone distance for the roster: 0 in a zone in play, else 1.

        The **zone** (task-500's key) rather than the room. A zone is the
        materialisation boundary — task-500 releases a whole zone and rebuilds it
        on approach — so a character whose zone is distant is expensive in a way
        a character two rooms away is not, and lumping them into the same
        awareness tier hides that. Coarse on purpose: the zone is the unit that
        gets loaded and unloaded, so it is the unit the cost is in.

        A zone counts as in play when the caller named it *or* when an anchor or
        a human is standing in it. A caller that names a zone and no anchors is
        still expressing a fact about the world, and ignoring it would make the
        key inert in exactly the case that motivated it.
        """
        named = {str(z) for z in (zones_in_play or ()) if str(z)}
        if not named and not seed_ids:
            return {}
        seed_zones = set(named)
        for cid in seed_ids:
            zone = (roster.get(cid) or {}).get("world_scope_id")
            if zone:
                seed_zones.add(str(zone))
        if not seed_zones:
            return {}
        out = {}
        for cid, info in roster.items():
            zone = str(info.get("world_scope_id") or "")
            # An unplaced character is nobody's neighbour: no zone means no claim
            # that they are near, and guessing "near" would let a loose character
            # hold the budget over a placed one.
            out[cid] = 0 if zone and zone in seed_zones else 1
        return out

    def _strength(self, cid, roster, aware, anchor_areas) -> float:
        """How strongly *cid* perceives, co-presence first.

        Co-presence is a fact about where somebody is, not a perception result,
        so it holds at 1.0 through a locked door. A channel result can only beat
        it by being closer to 1.0, which nothing is.
        """
        area_id = str(roster[cid].get("area_id"))
        if area_id in anchor_areas:
            return COPRESENT_STRENGTH
        return float(aware.get(area_id, 0.0))

    def _tier(self, cid, roster, anchor_ids, humans, pinned, awareness,
              previous, zone_tiers=None) -> int:
        if cid in anchor_ids:
            return TIER_ANCHOR
        if cid in humans:
            return TIER_HUMAN
        if cid in pinned:
            return TIER_PINNED
        if zone_tiers and zone_tiers.get(cid, 1) == 1:
            # A character in a zone nothing is attending. Below every other tier
            # including "recent": their recency is a fact about a zone the world
            # is not paying attention to, and ranking them on it is how a whole
            # distant zone quietly holds the budget.
            return TIER_NONE
        strength = awareness.get(cid, 0.0)
        if strength >= self.aware_threshold:
            return TIER_COPRESENT if strength >= COPRESENT_STRENGTH else TIER_AWARE
        if cid in previous and strength >= self.enter_floor():
            # Was attended and is still above the *enter* floor: staying is the
            # cheap, stable answer. Hysteresis as a channel threshold, which is
            # what the amendment asked for.
            return TIER_AWARE
        if strength > 0.0:
            return TIER_RECENT
        if zone_tiers and zone_tiers.get(cid, 1) == 0:
            # In a zone the world IS attending, but no channel reaches them. Not
            # aware, and not far either — recency is the only signal left, so
            # they rank on it rather than falling to the bottom. This is what
            # gives the zone key teeth: without it, a zone in play and a zone
            # nobody is in both bottom out and the key is inert.
            return TIER_RECENT
        return TIER_NONE

    def enter_floor(self) -> float:
        """Strength needed to *enter* the set, below the threshold to *stay*.

        The asymmetry is the whole of the hysteresis. Without it a character
        whose strength sits exactly on the threshold is promoted and demoted by
        any fluctuation, and the set churns.
        """
        return max(0.0, self.aware_threshold - self.enter_margin)

    def _rank_key(self, cid, roster, anchor_ids, humans, pinned, awareness,
                  previous, zone_tiers=None):
        return (
            self._tier(cid, roster, anchor_ids, humans, pinned, awareness,
                       previous, zone_tiers),
            -int(roster[cid].get("recency") or 0),
            str(cid),
        )

    # ── the state that survives a save ───────────────────────────────────

    #: Keys that are *derived* from the graph and must never be serialised: a
    #: saved awareness snapshot is stale the moment a door moves, and a save that
    #: looks resumable while quietly disagreeing with its world is worse than one
    #: that clearly re-derives.
    DERIVED_KEYS = ("awareness", "aware_by_area", "channel_walks")

    def to_state(self, *, anchors: Optional[Iterable[Mapping[str, Any]]] = None,
                 humans: Optional[Iterable[str]] = None,
                 pinned: Optional[Iterable[str]] = None,
                 attended: Optional[Iterable[str]] = None) -> Dict[str, Any]:
        """The serialisable form: budget, anchors, and the current attended set."""
        return {
            "cap": self.cap,
            "aware_threshold": self.aware_threshold,
            "enter_margin": self.enter_margin,
            "channels": [c.name for c in self.channels],
            "anchors": [dict(a) for a in (anchors or ())],
            "humans": sorted({str(h) for h in (humans or ())}),
            "pinned": sorted({str(p) for p in (pinned or ())}),
            "attended": sorted({str(a) for a in (attended or ())}),
        }

    def from_state(self, state: Mapping[str, Any]) -> Dict[str, Any]:
        """Read :meth:`to_state` back into the argument shape :meth:`select` wants.

        Returns the inputs rather than mutating the budget, so two budgets with
        different caps can read the same saved state — a save is a fact about a
        world, not about the reader's settings.
        """
        return {
            "cap": int(state.get("cap", self.cap)),
            "aware_threshold": float(
                state.get("aware_threshold", self.aware_threshold)),
            "enter_margin": float(state.get("enter_margin", self.enter_margin)),
            "channels": list(state.get("channels") or []),
            "anchors": [dict(a) for a in (state.get("anchors") or ())],
            "humans": [str(h) for h in (state.get("humans") or ())],
            "pinned": [str(p) for p in (state.get("pinned") or ())],
            "attended": [str(a) for a in (state.get("attended") or ())],
        }
