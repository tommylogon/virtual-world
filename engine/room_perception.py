"""Room perception invariants — ONE source of truth for what a character
can perceive in an area.

Two renderers present the same perception:

- the AGENT path: ``area_description.py`` → LLM prompt prose
- the PANEL path: ``scene_snapshot.py`` → ``/api/scene`` (turn composer)

The only allowed difference between them is PRESENTATION. Every time one
path re-implemented a shared rule, it drifted from the other (task-333
area-id crash, bug-23 hidden-way leak, bug-24 requires:"none" gate,
bug-26 empty panel). Renderers must call THESE functions instead of
re-implementing the rules.
"""

from typing import Optional

from graph import EDGE_IN


def normalize_name(value) -> str:
    """Comparison form for node/area names: lowercase, apostrophes dropped,
    underscores/hyphens read as spaces (project rule: id/name checks must
    lowercase everything so case never mismatches)."""
    return (str(value or "").lower()
            .replace("_", " ").replace("-", " ").replace("'", "").strip())


def resolve_area_node(graph, area_name: str) -> Optional[object]:
    """The area node for *area_name* — by NAME first (hand-authored ids
    strip punctuation: "Taco Bell Men's Restroom" lives at
    ``area_tacobell_mens_room``), then the canonical constructed id,
    validated against the graph. None when the area doesn't exist."""
    if graph is None or not area_name:
        return None
    wanted = normalize_name(area_name)
    for node in graph.nodes.values():
        if getattr(node, "type", "") == "area" and normalize_name(node.name) == wanted:
            return node
    from engine.node_ids import NodeIDHelper
    candidate = graph.get_node(NodeIDHelper.area_node_id(area_name))
    if candidate is not None and getattr(candidate, "type", "") == "area":
        return candidate
    return None


def normalize_requires(value) -> str:
    """Legacy data stores the literal "none" for walk-through ways;
    movement.py always special-cased it. none/nothing/no → ""."""
    req = str(value or "").strip().lower()
    if req in ("none", "nothing", "no"):
        return ""
    return str(value or "").strip()


def way_visible_to(player, player_manager, viewer_name: str,
                   way_node, area_name: str, direction: str) -> bool:
    """Hidden ways stay invisible until discovered: the slasher sees every
    hidden exit, anyone else needs the (area name, raw direction) key in
    ``discovered_exits`` — search/fumble discovery writes it (narration.py).
    Authored knowledge: a way, or its area, listed in the viewer's `known`
    registry is visible from the start (the butcher's passage, a scout's map).
    """
    if way_node.properties.get("current_state") != "hidden":
        return True
    try:
        known = set(getattr(player, "known", None) or [])
        area_id_guess = "area_" + str(area_name or "").lower().replace(" ", "_")
        if way_node.id in known or area_name in known or area_id_guess in known:
            return True
    except Exception:
        known = set()
    try:
        if viewer_name and player_manager.is_slasher(viewer_name):
            return True
    except Exception:
        pass
    discovered = getattr(player, "discovered_exits", None) or set()
    return (str(area_name), str(direction)) in discovered


def visible_area_items(graph, area_id, include_hidden: bool = False, player=None) -> list:
    """Non-hidden item nodes in the area (``get_edges_for_target`` already
    expands spatial edges, so surface items count). Items flagged in the
    viewer's authored ``known`` registry are visible even when hidden."""
    known = set()
    if player is not None:
        try:
            known = {str(k) for k in (getattr(player, "known", None) or [])}
        except Exception:
            known = set()
    items = []
    if graph is None or not area_id:
        return items
    for edge in graph.get_edges_for_target(area_id, EDGE_IN):
        node = graph.get_node(edge.source)
        if node and node.type == "item":
            if include_hidden or node.properties.get("current_state") != "hidden" or node.id in known:
                items.append(node)
    return items


#: Ceiling on a rendered pool. A generator that hands out a nonsense number
#: shouldn't put six digits in front of "berries".
MAX_ITEM_QUANTITY = 10000

#: Tokens an author can put in a description to do the counting themselves.
#: When one is present the description *is* the item's line and the label
#: carries no number of its own.
QUANTITY_TOKENS = ("{qty}", "{quantity}", "{name}")


def item_quantity(node) -> int:
    """How many of this kind an item node stands for (task-504).

    Absent means 1, so every existing item and every existing save reads
    exactly as it did before the property existed. Zero, negatives and junk
    read as 1 as well: a drained pool is removed from the world rather than
    rendered as "0 berries".
    """
    raw = (getattr(node, "properties", None) or {}).get("quantity", 1)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 1
    if value < 1:
        return 1
    return min(value, MAX_ITEM_QUANTITY)


def pluralise(name, count: int, plural: Optional[str] = None) -> str:
    """``berry`` at one, ``berries`` at three — but only if the item authored
    it. Irregulars come from the ``plural`` property; the naive ``+s`` is the
    fallback for everything else. The stored ``name`` always stays singular
    (matching deliberately does not pluralise, so a plural in ``name`` would
    stop ``take berries`` from resolving).
    """
    word = str(name or "").strip()
    if count == 1 or not word:
        return word
    authored = str(plural or "").strip()
    return authored or f"{word}s"


def describe_item_quantity(node) -> str:
    """``"40 berries"`` for a pooled node, ``"iron key"`` for a plain one.

    A count is shown only when the item AUTHORS one. Absent means "one of
    these" and renders exactly as it always did, which is what keeps every
    existing item and save unchanged; an authored ``quantity`` is shown even
    at 1, so "you see 1 giant tree" and "you see 40 berries" read alike.

    THE one place an item name picks up a count. Both perception paths call
    this — the AGENT path through ``area_description.get_area_items``, the
    PANEL path through ``scene_snapshot`` — so the two can never disagree
    about how much of something is standing there.
    """
    if node is None:
        return ""
    props = getattr(node, "properties", None) or {}
    name = str(getattr(node, "name", "") or "")
    if "quantity" not in props:
        return name
    count = item_quantity(node)
    return f"{count} {pluralise(name, count, props.get('plural'))}"


def describe_item(node, description: str = "") -> str:
    """``"40 berries, dark fruit on low branches."`` — label plus description.

    A description carrying a ``{qty}``/``{name}`` token *is* the line: the
    prose does the counting, so the label drops its own number. Otherwise the
    count is prefixed, which is why "you see 1 giant tree" still reads
    uniformly with "you see 40 berries".
    """
    if node is None:
        return ""
    count = item_quantity(node)
    props = getattr(node, "properties", None) or {}
    desc = " ".join(str(description or "").split())
    # task-514: one bounded provenance line, so the prompt can say where gear
    # came from without turning into a log dump.
    from engine.items.provenance import render_provenance
    provenance = render_provenance(props.get("provenance"))
    provenance_suffix = f" [{provenance}]" if provenance else ""
    if any(token in desc for token in QUANTITY_TOKENS):
        line = (desc.replace("{qty}", str(count))
                    .replace("{quantity}", str(count))
                    .replace("{name}", str(node.name or "")))
        return line + provenance_suffix
    label = describe_item_quantity(node)
    line = f"{label}, {desc}" if desc else label
    return line + provenance_suffix


def characters_in_area(graph, area_id, exclude_name: Optional[str] = None) -> list:
    """Character nodes present in the area (EDGE_IN), optionally excluding
    the viewer by name."""
    people = []
    if graph is None or not area_id:
        return people
    for edge in graph.get_edges_for_target(area_id, EDGE_IN):
        node = graph.get_node(edge.source)
        if node and node.type == "character":
            if exclude_name is not None and node.name == exclude_name:
                continue
            people.append(node)
    return people
