"""What an item lets a character do with it — the portability contract (task-493).

A part of a device is an ordinary item node that happens to be a **child** of a
parent, and the only thing that says so is its own ``actions`` list: a battery
declares ``examine,use`` and never ``take``. No new edge type, no new
``is_part`` flag, no device-type field.

That makes the item's declared actions the single authority on portability, and
it has to be the *single* authority — not just for ``take``. Before this,
``take`` was the only verb that read the list, so a part was untakeable but
would still have been droppable, stealable and puttable had anything ever
pointed a verb at it. Every verb that moves an item asks here.

The reachability half is different on purpose: a part is not portable *and*
must still be reachable and usable, which is what ``engine.item_reach`` is for.
Portable and reachable are not opposites.
"""

from typing import Optional


def item_actions(node) -> list:
    """The verbs *node* declares, normalised from either a list or a
    comma-separated string. Absent means "nothing declared"."""
    raw = (getattr(node, "properties", None) or {}).get("actions", [])
    if isinstance(raw, str):
        raw = [part.strip() for part in raw.split(",")]
    return [str(part).strip() for part in (raw or []) if str(part).strip()]


def item_allows(action: str, node) -> bool:
    """True when *node* declares *action*."""
    return str(action) in item_actions(node)


def is_portable(node) -> bool:
    """True when *node* may be picked up, moved, dropped, stolen or put away.

    ``take`` is the load-bearing verb: the item declares what may be done
    *with* it, and taking it away is the one that must be authorised first.
    Note ``normalize_item_actions`` auto-adds each action's inverse, so a part
    has to omit **both** ``take`` and ``drop`` — a lone ``drop`` would author
    ``take`` right back in.
    """
    return item_allows("take", node)


def is_part(node) -> bool:
    """True when *node* is a non-portable child item — a component of
    something larger, rather than a thing in its own right.

    Non-portable, not just untakeable. That is what keeps a battery in its
    phone and out of a pack."""
    return node is not None and not is_portable(node)


def parent_of(graph, node) -> Optional[object]:
    """The item node *node* is a child of, or None at the top level."""
    if graph is None or node is None:
        return None
    from graph import EDGE_IN

    for edge in graph.get_edges_for_source(node.id, EDGE_IN):
        parent = graph.get_node(edge.target)
        if parent is not None and getattr(parent, "type", "") == "item":
            return parent
    return None


def portable_refusal(graph, node, verb: str) -> str:
    """Why *verb* is refused on *node*, in the character's own terms.

    A part is not a loose thing you fumble with — it is a piece of something.
    Naming the device is more use to a player (and to an agent deciding what to
    try next) than a bare "you can't".
    """
    name = getattr(node, "name", "") or "that"
    parent = parent_of(graph, node)
    if parent is not None:
        return (f"The {name} is part of the {parent.name} — it doesn't come "
                f"loose to {verb}.")
    return f"The {name} is fixed in place — you can't {verb} it."
