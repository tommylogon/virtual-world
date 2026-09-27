"""Venues: a character that needs something walks to the place that has it (task-566).

A painted town is a service directory. The Stag Inn has beds, the Crooked Mug has
drink, the smithy has a forge, and a bathhouse has hot water — and before this
module **nothing in the simulation asked where any of that was**. There was no
venue concept at all: a tired traveller walked the streets, because the only
lookup the background sim had was by *item* tag, and a bed is not an item.

So the lookup is by **place tag**, and it needs no new vocabulary. Task-561's
building types already carry the tags this module reads — `sleeps` on an inn and
a cottage, `food` and `drink` on a tavern, `craft` on a smithy, `worship` on a
temple — and task-568's rooms carry `sleeps`, `washroom`'s own tag, and so on. A
venue is therefore *a set of tags plus a preference order*, and a building type
becomes a venue for free by being tagged.

Choosing among several is the part worth being explicit about
(:func:`choose_venue`), because "a character walks to the inn" is a decision with
at least four inputs and a wrong answer in each direction:

1. **Reachable, first.** An unreachable bed is not a bed. Every candidate is
   ranked by hops along the engine's own exits, so the first hop returned is one
   ``movement.move_to_area`` will actually accept.
2. **Familiarity.** A place this character has been before beats an equally
   distant place it has not. This is what makes a town feel inhabited rather than
   shuffled: a regular goes back to *their* inn, and a newcomer goes to the
   nearest. It is one counter per venue on the character, and it needs no plan.
3. **Preference tier.** At equal hops and equal familiarity, the nicer kind wins:
   an inn before a barn, a smithy before a kitchen. Declared per venue, ordered.
4. **Node id, last.** A tie-break, so the same world gives the same choice on
   every turn. A simulation that re-picks its destination each turn is a
   character that never arrives, and a soak that reads as a bug.

Nearest-first is the *default* and familiarity only breaks ties, which is
deliberate: a character with a bed in the next room is not going to the best inn
in the city because it is better. The tiers are a preference among equals, not a
shopping list.

The reachability walk is the one the rest of the sim already uses
(``build_exits_for_area``), so a venue step is a step the engine can take — a
venue is never somewhere a character can be routed that the player could not.
"""

from __future__ import annotations

from collections import deque
from typing import Dict, List, Optional, Tuple

#: A venue: what tags a place may carry to serve it, which kinds are *nicer*,
#: the verb the character uses there, and the word for the log line.
#:
#: ``prefers`` is ordered best-first and holds either tags or building/room ids
#: (whatever a generated area records in ``properties.building`` / ``biome``).
#: It is a **preference among equals**, never a filter: an inn that is the only
#: bed in reach is still the right answer.
VENUES: Dict[str, dict] = {
    "rest": {
        "tags": ("sleeps", "bed"),
        "prefers": ("inn", "guest_room", "bedroom", "cottage", "bunkroom",
                    "infirmary", "stable"),
        "verb": "sleeping",
        "why": "is looking for a bed",
    },
    "meal": {
        "tags": ("food", "eats"),
        "prefers": ("dining_hall", "taproom", "mess_hall", "inn", "tavern",
                    "fast_food", "market", "kitchen"),
        "verb": "eating",
        "why": "is looking for somewhere to eat",
    },
    "drink": {
        "tags": ("drink", "water"),
        "prefers": ("taproom", "tavern", "inn", "washroom", "bathroom"),
        "verb": "drinking",
        "why": "is looking for a drink",
    },
    "bath": {
        "tags": ("washroom", "bath", "hygiene"),
        "prefers": ("bathroom", "washroom", "bathhouse", "laundry"),
        "verb": "washing",
        "why": "is looking for hot water",
    },
    "work": {
        "tags": ("craft", "forge", "trade", "workshop"),
        "prefers": ("smithy", "forge", "workshop", "mill", "bank", "shop",
                    "market", "library"),
        "verb": "working",
        "why": "is looking for somewhere to work",
    },
    "worship": {
        "tags": ("worship", "religious"),
        "prefers": ("temple", "shrine", "chapel", "oratory", "nave"),
        "verb": "at worship",
        "why": "is going to worship",
    },
    "care": {
        "tags": ("medical", "care", "infirmary"),
        "prefers": ("infirmary", "ward", "washroom", "cellar"),
        "verb": "being tended",
        "why": "is looking for a healer",
    },
}


def venue(name: str) -> Optional[dict]:
    """The venue definition, or ``None`` for a name nothing serves."""
    return VENUES.get(str(name or "").strip().lower())


def node_ids(node) -> Tuple[str, ...]:
    """The ways this node can be *named* when matching a preference.

    A generated area records its source in three places, and a venue has to match
    whichever one the area happens to carry: ``building`` for a building cell
    (task-563), ``biome`` for an ordinary painted cell, and the node's own id
    for a hand-authored one. All three, in that order, so `inn` matches an inn
    whether it was compiled or written by hand.
    """
    props = (getattr(node, "properties", {}) or {})
    out = []
    for key in ("building", "biome", "road"):
        value = str(props.get(key) or "").strip().lower()
        if value and value not in out:
            out.append(value)
    node_id = str(getattr(node, "id", "") or "").lower()
    if node_id and node_id not in out:
        out.append(node_id)
    return tuple(out)


def _area_tags(node) -> set:
    return {str(t).lower() for t in ((getattr(node, "properties", {}) or {})
                                    .get("tags") or [])}


def serves(node, spec: dict) -> bool:
    """Whether this area can serve a venue at all.

    **Tags *or* name.** Task-568's rooms mostly carry a *purpose* tag
    (``service``, ``sleeping``) and express what they are through their id
    (``bathroom``, ``guest_room``), so a tag-only match would not find a bathroom:
    the word is in the name, not the tags. Both are read, and a building is a
    service directory whether it was compiled from paint or written by hand.

    ``current_state`` is deliberately **not** consulted: a shut door is a routing
    problem (and the traversal layer already refuses it), not a reason to decide
    the character does not want a bed there. A locked building that everyone has
    the key to is still the building.
    """
    wanted = {str(t).lower() for t in spec["tags"]}
    if _area_tags(node) & wanted:
        return True
    names = set(node_ids(node))
    return any(want in names or any(want in name for name in names)
               for want in wanted)


def find_venues(gs, p, name: str) -> List[Tuple[str, int, int]]:
    """Every reachable venue area, as ``(area_name, hops, preference_rank)``.

    Ranked the way :func:`choose_venue` wants to read it: hops first, then
    preference. Reachable means "there is a path along the engine's own exits
    from where the character stands", found by the same BFS the rest of the sim
    uses — including hidden authoring-only passages, so a venue behind a
    GM-only door is still found by a character who can get there.
    """
    spec = venue(name)
    if not spec or not p.current_area:
        return []
    prefers = [str(t).lower() for t in spec.get("prefers") or ()]
    graph = gs.graph
    player_id = gs._player_node_id(p.name)
    start_area_id = gs.area_node_id(p.current_area) if p.current_area else None
    found: Dict[str, Tuple[int, int]] = {}
    seen = set()
    queue = deque([(p.current_area, 0)])
    while queue:
        area_name, hops = queue.popleft()
        if area_name in seen:
            continue
        seen.add(area_name)
        node = graph.get_node(gs.area_node_id(area_name)) if area_name else None
        if node is not None and area_name != p.current_area and serves(node, spec):
            ids = node_ids(node)
            rank = next((i for i, want in enumerate(prefers) if want in ids),
                        len(prefers))
            found[area_name] = (hops, rank)
        for label, exit_data in gs.build_exits_for_area(
                area_name, include_hidden=True).items():
            target = (exit_data or {}).get("target")
            if not target or target in seen:
                continue
            # A character standing in another character is not a doorway.
            if target == player_id:
                continue
            queue.append((target, hops + 1))
    return sorted((area, hops, rank) for area, (hops, rank) in found.items())


def _visits(p) -> Dict[str, int]:
    """The character's venue memory, created on first use.

    A plain counter per area name, kept on the character rather than in a module,
    so it travels with a save and a character who has never been anywhere has
    nothing to be loyal to.
    """
    memory = getattr(p, "venue_visits", None)
    if not isinstance(memory, dict):
        memory = {}
        try:
            p.venue_visits = memory
        except Exception:
            return {}
    return memory


def remember_venue(p, area_name: str) -> None:
    """Note that a character used a place, so they may prefer it next time."""
    if not area_name:
        return
    memory = _visits(p)
    if area_name in memory:
        memory[area_name] = int(memory[area_name]) + 1


def choose_venue(gs, p, name: str) -> Optional[str]:
    """The venue this character should go to, or ``None`` when there is none.

    The four tiers, in order, and why each is where it is:

    1. **fewest hops** — a character with a bed next door does not cross town for
       a better one;
    2. **familiarity** — among equally near places, one this character has used
       before, and more-used first. This is what makes a regular go back to their
       inn and a stranger go to the nearest;
    3. **preference tier** — among those still equal, the nicer kind (an inn
       before a barn), as declared by the venue;
    4. **node name** — a total order, so the same world picks the same place
       twice. Without this a tie is resolved by dictionary order and a character
       re-picks its destination every turn, which reads as a bug in a soak.

    Returns the area **name**, because that is what the rest of the sim's travel
    helpers speak.
    """
    candidates = find_venues(gs, p, name)
    if not candidates:
        return None
    visits = _visits(p)
    return min(candidates, key=lambda row: (
        row[1],                                             # hops
        -int(visits.get(row[0], 0)),                       # familiar, and often
        row[2],                                             # nicer kind
        str(row[0]).lower(),                                # stable
    ))[0]


def describe(gs, p, name: str) -> str:
    """A one-line reason for the log, naming where it is going and why.

    "Ari walks to The Stag Inn — is looking for a bed" is a line a player reads
    and understands. The alternative, a silent hop, is the difference between a
    living town and a character teleporting for unexplained reasons.
    """
    spec = venue(name)
    target = choose_venue(gs, p, name)
    if not spec or not target:
        return ""
    return f"{p.name} walks to {target} — {spec['why']}"
