"""Bladder relief: permitted anywhere, comfortable only in private (task-551).

The design is deliberately asymmetric, and getting that asymmetry wrong is what
created a 45,844-tick traffic jam in the one `Waste Disposal` room of the
Kraktooth camp:

* **Permission** — *any* character may relieve themselves in *any* area. A
  world that happens to contain no latrine is not a world where nobody can go;
  the `RELIEF_TAGS` tag marks a *proper place*, not the only legal one. Nothing
  in this module may ever be used to refuse relief.
* **Preference** — a character who can choose would rather not do it in front of
  people, and prefers a room built for it. That is a *ranking* of candidates,
  never a gate.

Both tiers read this module, so a background goblin and a human at the keyboard
are subject to exactly the same rules — including the dignity cost, which used to
exist only in the foreground handler and was hardcoded there.

The occupancy count is the load-bearing part of the score. An author's `private`
tag is a claim about a room; the number of people actually standing in one is
what produced the hub, and no amount of tagging describes it. See `score_privacy`
for the weights and why they are what they are.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

#: A proper place to relieve oneself: an area tag (a latrine room) or a fixture
#: standing in one. This is the *comfort* vocabulary, never a permission one.
RELIEF_TAGS = ("latrine", "toilet", "privy", "restroom", "bathroom")

#: Author-facing privacy vocabulary. `isolated` is here because a watchtower or a
#: ravine is secluded by geometry and has no more tag budget than a nest does.
PRIVATE_TAGS = ("private", "secluded", "isolated")

#: Tags marking a place that is emphatically *not* private, so an author can
#: overrule a default without having to think about scoring.
PUBLIC_TAGS = ("public", "communal")

#: What an improvised relief costs the one doing it. Internal embarrassment is
#: always paid; the social hit only lands when somebody actually saw, because
#: being alone keeps it between you and the puddle.
DIGNITY_SANITY_COST = 2
DIGNITY_SOCIAL_COST = 3

#: Score weights. Lower total is a better place to relieve oneself.
#:
#: `witness` is 1.0 because it is the term that actually caused the hub and it is
#: the only one a character can do anything about at run time. `private` is 1.5,
#: i.e. worth rather more than a single onlooker, so a character will cross one
#: room to reach a spot the author called secluded — but not an unbounded
#: distance, which is what `PRIVACY_SEARCH_HOPS` bounds instead of the weight.
#: `fixture` is 1.0: a latrine is worth exactly one person's presence, so a busy
#: latrine loses to an empty one but a quiet one still wins.
PRIVACY_WEIGHTS = {
    "witness": 1.0,
    "private": 1.5,
    "public": 3.0,
    "fixture": 1.0,
}

#: How far a character will walk for privacy, in ways. Two is "the next room or
#: the one after", which is what makes the latrine stop being a destination: the
#: crowded hall you are standing in is never the best room in the building.
PRIVACY_SEARCH_HOPS = 2


def _tags(node) -> set:
    props = (getattr(node, "properties", None) or {}) if node is not None else {}
    return {str(t).lower() for t in (props.get("tags") or [])}


def has_tag(node, tags) -> bool:
    """True when *node* carries any of *tags*, case-insensitively."""
    return bool(_tags(node) & {str(t).lower() for t in (tags or ())})


def is_private(node) -> bool:
    """True when the author has claimed this area as secluded.

    An explicit `public`/`communal` tag overrules it: a great hall can be tagged
    `public` even if something in it also says `private`, and the author who
    bothered to say so meant it.
    """
    tags = _tags(node)
    if tags & set(PUBLIC_TAGS):
        return False
    return bool(tags & set(PRIVATE_TAGS))


def witnesses(graph, area_id, players=None, exclude_name=None) -> int:
    """How many other living characters are in *area_id*.

    Counts the live `Player` roster (which is what actually moves) and falls back
    to graph `in` edges from character nodes, so a soak span that only has graph
    residents still scores. The dead do not watch anyone, and neither does the
    character asking.
    """
    if not area_id:
        return 0
    seen = set()
    for name, p in (players or {}).items():
        # The registry key and `Player.name` are the same string in practice, but
        # `player_manager` can park a player under a distinct key, and excluding
        # the wrong self would count the character asking as its own onlooker.
        if exclude_name is not None and name in (exclude_name, getattr(p, "name", None)):
            continue
        if getattr(p, "state", "") == "dead":
            continue
        if _area_id_of(p, graph) == area_id:
            seen.add(name)
    if graph is not None:
        for edge in graph.get_edges_for_target(area_id, "in"):
            node = graph.get_node(edge.source)
            if node is None or getattr(node, "type", None) != "character":
                continue
            if exclude_name is not None and node.name == exclude_name:
                continue
            seen.add(node.id)
    return len(seen)


def _area_id_of(player, graph) -> str:
    """Resolve a player's `current_area` to an area node id.

    `current_area` is a display name; the convention here is that lookups key on
    the node id and names resolve through the graph, never the other way round.
    """
    name = getattr(player, "current_area", None)
    if not name:
        return ""
    if graph is not None:
        for candidate_id in (name, f"area_{name}"):
            try:
                if graph.get_node(candidate_id) is not None:
                    return candidate_id
            except Exception:
                continue
    return str(name)


def has_fixture(graph, area_id, spatial_items=None) -> bool:
    """True when *area_id* is itself a relief place or holds a fixture that is.

    `spatial_items` lets a caller pass its own reachability walk
    (`BackgroundSimulation._spatial_items`) so this agrees with what the rest of
    the background tier can actually reach rather than second-guessing it.
    """
    if not graph or not area_id:
        return False
    try:
        node = graph.get_node(area_id)
    except Exception:
        node = None
    if node is not None and getattr(node, "type", None) == "area" and has_tag(node, RELIEF_TAGS):
        return True
    items = spatial_items(area_id) if spatial_items else ()
    return any(has_tag(item, RELIEF_TAGS) for item in items)


def score_privacy(graph, area_id, *, players=None, exclude_name=None,
                  spatial_items=None, weights=None) -> float:
    """How decent *area_id* is as a place to relieve oneself. Lower is better.

    The sum is over four terms, all of which can be negative, so a genuinely
    secluded empty room scores well below an unremarkable one and the comparison
    is total rather than a ranked list of "kinds of place". Exported weights let
    task-549 vary this per species or faction without touching this function.
    """
    w = dict(PRIVACY_WEIGHTS if weights is None else weights)
    return (
        w["witness"] * witnesses(graph, area_id, players, exclude_name)
        - w["private"] * _private_bonus(graph, area_id)
        - w["fixture"] * (1.0 if has_fixture(graph, area_id, spatial_items) else 0.0)
    )


def _private_bonus(graph, area_id) -> float:
    try:
        return 1.0 if is_private(graph.get_node(area_id)) else 0.0
    except Exception:
        return 0.0


def apply_dignity_cost(player, witnessed: bool) -> dict:
    """The cost of relieving somewhere that is not a proper place.

    Returns the vitals actually changed, so the caller can narrate the difference
    between "nobody saw" and "somebody did". Deliberately small and never
    lethal: this is embarrassment, not a punishment, and a character in a world
    with no latrine at all should be uncomfortable rather than ground down.
    """
    changed = {}
    sanity = player.vitals.get("Sanity")
    if sanity is not None:
        player.vitals["Sanity"] = max(0, min(100, sanity - DIGNITY_SANITY_COST))
        changed["Sanity"] = DIGNITY_SANITY_COST
    if witnessed:
        social = player.vitals.get("Social")
        if social is not None:
            player.vitals["Social"] = max(0, min(100, social - DIGNITY_SOCIAL_COST))
            changed["Social"] = DIGNITY_SOCIAL_COST
    return changed


def mark_smell(graph, area_id, note="urine") -> bool:
    """Leave the mark on the area's environment. Best effort, never fatal.

    This is the cheap, self-contained half of what the foreground handler does: it
    costs one property and no graph node, so a hundred improvised reliefs do not
    turn into a hundred `puddle` items that every later traversal has to look
    past. The foreground still spawns the item, because a human at the keyboard
    gets the full staging.
    """
    try:
        node = graph.get_node(area_id)
        if node is None:
            return False
        env = node.properties.setdefault("environment", {})
        if not isinstance(env, dict):
            return False
        existing = env.get("smell", "")
        env["smell"] = f"{existing}; {note}" if existing else note
        return True
    except Exception as e:
        logger.debug("relief: could not mark %s: %s", area_id, e)
        return False
