"""WorldPainter grid→graph compiler (task-496).

Turns a painted scope grid (``engine/world_grid.py``) into a
:class:`~engine.generation.GenerationPatch` of normal ``area`` and ``way``
nodes, so the engine is unchanged: the compiled world loads through the same
area/way conventions as hand-authored data.

Decisions recorded here (see the Progress note on task-496):

- **496 stays a separate grid recipe that emits through task-398's contract.**
  task-398 owns *how* a patch applies safely (provenance, once-only); this module
  owns the *mapping* cell → area and adjacency → way. Folding them would put grid
  painting inside the generic generation contract, which other recipes (an
  apartment, an item plan) do not share.
- **Per-zone paint policy is ``canonical`` by default, ``baked`` opt-in.** A
  canonical zone may be re-compiled (``apply_patch(allow_regenerate=True)``) but
  a re-run is still rejected by default, so a manual edit after baking is never
  silently overwritten. A ``baked`` zone is compiled once and treated as
  hand-authored thereafter (``paint_policy`` on the scope record).
- Cell identity is the stable ``world_grid.cell_id`` anchor, so a reference to a
  cell survives edits elsewhere on the grid.

The observer-view model (2026-09-26, locked with the author):

- **Every painted cell is a place, roads included.** A cell that carries only a
  road compiles like any other; the compile set is
  ``biome_of | road_of``, not ``biome_of``. A cell holding a *hand-placed* area
  (task-528) is still skipped, so Generate cannot mint a second place on top.
- **A road cell replaces its biome.** One place per cell, and the road is that
  place's *identity*: region merging groups by ``road:<value>`` when a road is
  painted and ``biome:<value>`` otherwise (``identity`` below), so a run of road
  merges into one road area while a road cell beside forest stays its own place.
  The biome underneath is kept as ``properties.biome`` plus description context.
  ``static/js/worldpainter/grid-model.js`` mirrors this, so the painter's area
  estimate matches what Generate mints.
- **A description composes the place's character**, via
  :func:`classify_company`, from the terrain class of its neighbours plus the
  storey step to its neighbours (``cliff_dirs``, outdoors only). A neighbour is
  named for what its place is, so a road neighbour is a road even when a biome
  sits under it.
- **Compass outdoors, narrative on feature entry.** Grid passages stay compass
  directions. A child-scope gateway carries a phrase from :func:`_entry_phrases`
  ("enter the inn", "climb down into the cave") plus ``aliases: ["in", "out"]``,
  so the pre-existing ``go in`` / ``go out`` keep resolving and the engine needs
  no change — movement resolves by the direction string.
- **A building is a place you go *into*, not a cell you step onto** (task-563). A
  cell painted with a building biome gets an ``in`` way from every side that
  already has a way, so standing on the street you type ``in`` instead of walking
  sideways onto the doorstep first. Where the building owns a child scope the way
  leads to that interior (one-way, so ``out`` inside stays unambiguous and means
  the doorstep); where it has no interior the way is *shut* and refuses with a
  line drawn from the building's category, so a knock or a key can open it later
  (see :func:`_enter_way` and ``refusal_message`` in ``engine/movement.py``).
- **A floor is a storey index, not a floor material.** ``properties.floor`` is the
  cell's storey: 0 is the ground plane, 1 one up, -1 one down, and it is
  unbounded (three stacked rooms, a lake bottom at -2, an 80-storey tower, -900
  in a hole to hell). It is rounded to a whole storey because the engine
  compares whole storeys, not heights. What you *stand on* — dirt, grass, stone,
  pine needles — is a different fact and lands on ``properties.surface``, read
  from the biome/road record (``engine.biomes.ground_surface``). An earlier
  revision of this compiler put the material on ``floor`` and painted heights on
  a separate ``elevation`` property; both were wrong and are gone.
- **Floors inform prose now, gate movement later.** The floor layer feeds the
  cliff phrasing; blocking or costing a climb on a storey step is task-525.

Determinism is absolute: no ``random``, no clock. The same manifest + scope +
options yield identical nodes/edges, choosing description fragments by a stable
hash of ``seed:cell``.
"""

from __future__ import annotations

from collections import Counter, deque
from typing import Dict, List, Optional, Set, Tuple

from graph import EDGE_CONNECTION, Edge, Node

from engine import biomes as biomes_mod
from engine import world_grid as wg
from engine.generation import GenerationPatch, GenerationReport, provenance

#: Grid recipe version. Bump when the mapping changes, so provenance records
#: which compiler produced a node. ``v2`` is the storey model: ``floor`` became
#: the cell's storey index and the ground material moved to ``surface``
#: (``v1`` put the material on ``floor``).
RECIPE_ID = "grid.v2"

#: Compass deltas. ``y`` increases downward, so north is ``(0, -1)``.
DIRECTIONS: Dict[str, Tuple[int, int]] = {
    "north": (0, -1),
    "south": (0, 1),
    "east": (1, 0),
    "west": (-1, 0),
    "northeast": (1, -1),
    "northwest": (-1, -1),
    "southeast": (1, 1),
    "southwest": (-1, 1),
}
OPPOSITE = {
    "north": "south", "south": "north", "east": "west", "west": "east",
    "northeast": "southwest", "southwest": "northeast",
    "northwest": "southeast", "southeast": "northwest",
}
#: Directions emitted when scanning for adjacencies, so each shared edge is
#: visited once. The four "south half" deltas cover every 8-neighbour pair
#: exactly once (a north neighbour is found from that cell's ``south``, etc.).
_SCAN_DIRECTIONS = ("east", "south", "southeast", "southwest")
#: The four cardinal steps. Used where a diagonal is *not* the same thing as a
#: neighbour: which room a window faces, and which two rooms a doorway joins
#: (task-562). A diagonal place is a corner of the room, not the other side of a
#: wall.
_CARDINAL_STEPS = frozenset({(0, 1), (1, 0), (0, -1), (-1, 0)})

#: Default area environment for a painted cell; a biome record may override it
#: with its own ``environment`` dict.
DEFAULT_ENVIRONMENT = {"light": 60, "temperature": 20}

PAINT_POLICY_CANONICAL = "canonical"
PAINT_POLICY_BAKED = "baked"

#: Child-scope gateway directions (task-496). A placement compiles to a link
#: between the parent's cell area and the child's entry area. Unlike a grid
#: passage the two directions are not opposites — you enter with ``in`` and
#: return with ``out`` — so the gateway builds its own four connection edges.
GATEWAY_IN = "in"
GATEWAY_OUT = "out"

#: Canvas units per painted cell for generated node positions. The graph view
#: reads ``properties.x``/``y`` directly, so with physics off (or graph mode) a
#: compiled scope lays out in the exact shape it was painted — the point of
#: painting over a reference map. This is layout only; travel time stays one
#: turn per cell (``cell_scale`` is not read by the compiler or movement).
CELL_CANVAS_UNITS = 40


# ───────────────────────────── description ────────────────────────────────


def _stable_index(text: str, n: int) -> int:
    """Deterministic 0..n-1 index for *text* (no ``random``/``hash``)."""
    if n <= 1:
        return 0
    acc = 0
    for i, ch in enumerate(text):
        acc += (i + 1) * ord(ch)
    return acc % n


def _fragment(record: Optional[dict], key: str, seed: str) -> str:
    frags = [str(d).strip() for d in ((record or {}).get("descriptions") or [])
             if str(d).strip()]
    if not frags:
        return ""
    return frags[_stable_index(f"{seed}:{key}", len(frags))]


def _join_dirs(directions: List[str]) -> str:
    directions = list(directions)
    if not directions:
        return ""
    if len(directions) == 1:
        return directions[0]
    return ", ".join(directions[:-1]) + " and " + directions[-1]


# ─────────────────────── place character (task-496) ────────────────────────
#
# The observer-view model: a place is not "a biome with some neighbours", it is
# a *character* read off the surrounding cells. "A road in the woods" and "a road
# along the forest line" are the same tile with different company, and only the
# company distinguishes them. That company is classified below, then composed
# into one deterministic sentence. No LLM, no randomness.

#: Terrain classes the classifier distinguishes. Keyed by a biome's ``terrain``
#: field, so a new biome joins a class by declaring its terrain rather than by
#: a code change here.
_TERRAIN_CLASSES = {
    "forest": "woods",
    "rock": "rock",
    "water": "water",
    "farm": "cultivated",
}
DEFAULT_TERRAIN_CLASS = "open"

#: Cardinal directions the classifier reads company from. Diagonals are
#: included: a rockface to the north-east still shapes the path.
_SENSE_DIRECTIONS = ("north", "south", "east", "west",
                     "northeast", "northwest", "southeast", "southwest")

#: A storey difference at or above this reads as a cliff rather than a slope.
#: Prose only — gating traversal on a large delta is task-525.
#:
#: The name is *floor* because the unit is storeys, not because the cell's ground
#: is a floor (that is ``surface``). An 80-storey tower steps by 1 and reads as
#: ordinary ground; only a multi-storey jump outdoors is a rockface.
CLIFF_FLOOR_DELTA = 2


def terrain_class(biome_id: Optional[str], road: Optional[str] = None) -> str:
    """The company a neighbouring cell provides to a place's character.

    A road cell reads as ``road`` (it is a thoroughfare, whatever lies under it);
    otherwise the biome's declared terrain decides. ``None``/unknown → ``open``.
    """
    if road:
        return "road"
    rec = biomes_mod.biome(biome_id) if biome_id else None
    return _TERRAIN_CLASSES.get(str((rec or {}).get("terrain") or ""),
                                DEFAULT_TERRAIN_CLASS)


def classify_company(company: Dict[str, str]) -> str:
    """Compose the place's character from what surrounds it (deterministic).

    The rules, in the order they are checked:

    - **rock on opposite sides** (including a cliff-sized floor step promoted to
      rock) → a narrow path with a rockface rising and ground dropping away.
    - **rock on one side** → a road cut along its foot.
    - **woods on both sides** → "a road in the woods"; on one side → "a road
      along the forest line", naming it.
    - **water on both sides** → a road carried over it; on one side → beside it.
    - **cultivated** → a road between fields.
    - otherwise → open country.

    "Both sides" means *opposite* sides — a place with a cliff north and open
    ground south is along the cliff, not between cliffs. Diagonals count as a
    side, since a rockface to the north-east still shapes the road.

    ``company`` maps direction → terrain class (see :func:`terrain_class`).
    Returns "" when there is nothing to say, so the caller keeps its default.
    """
    sides = {d: company.get(d) for d in _SENSE_DIRECTIONS}
    present = {c for c in sides.values() if c and c != "open"}
    opposite = {"north": "south", "south": "north", "east": "west", "west": "east",
                "northeast": "southwest", "southwest": "northeast",
                "northwest": "southeast", "southeast": "northwest"}

    def dirs_of(cls: str) -> List[str]:
        return [d for d in _SENSE_DIRECTIONS if sides.get(d) == cls]

    def straddles(cls: str) -> bool:
        """True when the place has this class on *opposite* sides of it.

        "Between" and "in" need two opposing walls; a single neighbour is
        "along"/"beside"/"at the foot of". Diagonals count as a side, since a
        rockface to the north-east still shapes the road.
        """
        found = dirs_of(cls)
        return any(opposite.get(d) in found for d in found)

    # Rock first: a cliff is the strongest thing about a place. Both sides means
    # a place genuinely *between* cliffs — the narrow-path case.
    if straddles("rock"):
        return "a narrow path, rockface rising on one side and dropping away on the other"
    rock = dirs_of("rock")
    if rock:
        side = rock[0]
        if "woods" in present:
            return "a road cut along the foot of the rockface, the trees closing the other side"
        if "water" in present:
            return f"a road cut along the base of the cliff above the water to the {side}"
        return f"a road cut along the foot of the rockface to the {side}"
    if "woods" in present:
        if straddles("woods"):
            return "a road in the woods"
        return f"a road along the forest line, the trees close on the {dirs_of('woods')[0]}"
    if "water" in present:
        if straddles("water"):
            return "a road carried over the water"
        return f"a road running beside the water to the {dirs_of('water')[0]}"
    if "cultivated" in present:
        return "a road running between cultivated fields"
    return "a road across open country"


def _cliff_company(company: Dict[str, str], cliffs: Set[str]) -> None:
    """Promote cliff-sized storey steps into ``rock`` so the classifier sees them.

    Kept out of :func:`classify_company` so that function stays a pure function
    of company (and therefore trivially testable); the floor read lives here,
    where the grid is in scope.

    A promoted direction *outranks* whatever terrain stood there: standing on a
    shelf two storeys above a drop reads as a rockface even with woods on the
    other side, so the class is overwritten rather than only filling gaps.
    """
    for direction in cliffs:
        company[direction] = "rock"


def _area_description(cell: Tuple[int, int], biome_id: Optional[str],
                      road: Optional[str], neighbours: Dict[str, str],
                      directions: List[str], child_scope_id: Optional[str],
                      seed: str, company: Optional[Dict[str, str]] = None) -> str:
    """Deterministic prose from the cell's own tile, exits and company.

    No LLM. The place's *character* — "a road along the forest line" — is
    classified from the surrounding cells by :func:`classify_company` rather than
    guessed, and a road cell is a place in its own right, not a path across a
    biome.
    """
    biome_rec = biomes_mod.biome(biome_id) if biome_id else None
    key = wg.cell_key(*cell)
    parts: List[str] = []
    road_rec = (biomes_mod.features() or {}).get(str(road)) or {} if road else {}

    if road:
        # A road cell leads with what the road IS, then what it is like here.
        frag = _fragment(road_rec, f"road:{key}", seed)
        if frag:
            parts.append(frag)
        character = classify_company(company or {})
        if character:
            parts.append(character.capitalize() + ".")
        if directions:
            parts.append(f"It runs {_join_dirs(sorted(directions))} from here.")
    else:
        own = _fragment(biome_rec, key, seed)
        if own:
            parts.append(own)
        # A biome cell beside a road still gets the road's company, so a forest
        # with a track through it reads as such.
        if company and "road" in set(company.values()):
            parts.append("A track runs through it.")
        if directions:
            parts.append("Paths lead " + _join_dirs(sorted(directions)) + ".")

    if child_scope_id:
        parts.append(f"{child_scope_id.replace('_', ' ').title()} stands here.")

    if not road:
        own_tags = set(biomes_mod.area_tags(biome_id) if biome_id else [])
        for direction in ("north", "south", "east", "west"):
            nb = neighbours.get(direction)
            if not nb or nb == biome_id:
                continue
            if set(biomes_mod.area_tags(nb)) & own_tags:
                continue  # same family — not worth calling out
            # A road neighbour is already covered by the "track runs through it"
            # line above, and reading it as a biome would print "Road lies to
            # the south". Phrased without a verb so plural names agree.
            if nb in (biomes_mod.features() or {}):
                continue
            nb_rec = biomes_mod.biome(nb) or {}
            nb_name = (nb_rec.get("name") or nb).replace("_", " ")
            parts.append(f"{nb_name.capitalize()} to the {direction}.")

    text = " ".join(p.strip() for p in parts if p and p.strip())
    return text if text.endswith(".") else text + "."


# ─────────────────────────────── compile ──────────────────────────────────


def _area_id(scope_id: str, cell: Tuple[int, int]) -> str:
    return f"area_{scope_id}_{cell[0]}_{cell[1]}"


def _place_label(cell: Tuple[int, int], biome_of: Dict[Tuple[int, int], str],
                 road_of: Dict[Tuple[int, int], str]) -> str:
    """The display name fragment for a cell's place (task-496).

    A road cell is named for the road — it *is* a road, not forest-with-a-path —
    and falls back to the biome underneath so a road painted without a biome
    still reads sensibly.
    """
    road = road_of.get(cell)
    if road:
        rec = (biomes_mod.features() or {}).get(str(road)) or {}
        name = rec.get("name")
        if name and str(name).lower() != "road":
            return str(name)
        return "Road"
    return _biome_label(biome_of.get(cell))


def _biome_label(biome_id: Optional[str]) -> str:
    rec = biomes_mod.biome(biome_id) if biome_id else None
    return str((rec or {}).get("name") or str(biome_id or "Open ground").replace("_", " ").title())


def _place_name(scope_label: str, cell: Tuple[int, int],
                biome_of: Dict[Tuple[int, int], str],
                road_of: Dict[Tuple[int, int], str],
                authored: Optional[str] = None,
                taken: Optional[Set[str]] = None) -> str:
    """A display name unique to its scope (task-496, task-560).

    An author-set name wins when there is one — that is the whole point of naming
    cells, and it is what makes a painted town addressable ("The Stag Inn") rather
    than a column of coordinates. The generated form ``<label> (<scope> x,y)`` is
    the fallback, and it stays the fallback for an author name *repeated inside the
    same scope*, so no single area ever offers two exits with the same name — which
    is all ``go <name>`` needs (``NameMatching.resolve_exit`` collects the current
    area's exits first).

    Two scopes may still reuse a name, exactly as two hand-authored areas may: ids
    are the authoritative key, and names are user-facing labels resolved to them.
    `taken` is the set already handed out in this scope, so the scope is settled in
    one pass.
    """
    label = _place_label(cell, biome_of, road_of)
    generated = f"{label} ({scope_label} {cell[0]},{cell[1]})"
    name = str(authored or "").strip()
    if not name:
        return generated
    if taken is not None and name in taken:
        return generated
    if taken is not None:
        taken.add(name)
    return name


def _region_authored_name(cells: List[Tuple[int, int]],
                          names: Dict[str, str]) -> Optional[str]:
    """The author name for a whole region (task-560), or None.

    A merged region is one place, and its name should not depend on the author
    knowing that the *anchor* cell is the top-left-most one — naming the middle of
    a High Street is the natural thing to do. So the first named cell in region
    order speaks for the region, exactly as the anchor does for biome and road. Two
    different names in one region is an authoring slip, and the first wins rather
    than the region being left unnamed.
    """
    for cell in cells:
        value = str((names or {}).get(wg.cell_key(*cell), "") or "").strip()
        if value:
            return value
    return None


def _way_id(scope_id: str, area_a: str, area_b: str) -> str:
    a, b = sorted((area_a, area_b))
    return f"way_{scope_id}_{a}_{b}"


def _direction_between(a: Tuple[int, int], b: Tuple[int, int]) -> str:
    for name, (dx, dy) in DIRECTIONS.items():
        if (a[0] + dx, a[1] + dy) == b:
            return name
    return "across"


#: 8-wind compass keyed by the sign of (dx, dy).
_COMPASS_BY_SIGN: Dict[Tuple[int, int], str] = {
    (0, -1): "north", (0, 1): "south", (1, 0): "east", (-1, 0): "west",
    (1, -1): "northeast", (-1, -1): "northwest",
    (1, 1): "southeast", (-1, 1): "southwest",
}


def _compass_direction(dx: int, dy: int) -> str:
    """The compass name for an arbitrary delta, for long auto-link ways.

    ``_direction_between`` only names single-cell steps; an island link can span
    many cells, so the sign of the delta picks the 8-wind direction instead.
    """
    sx = (dx > 0) - (dx < 0)
    sy = (dy > 0) - (dy < 0)
    return _COMPASS_BY_SIGN.get((sx, sy), "across")


def _way_edges(area_from: str, area_to: str, way_id: str,
               direction: str) -> List[Edge]:
    """The four connection edges a bidirectional way needs (movement.py).

    Each edge carries ``cardinal`` as well as ``direction``: the way inspector's
    "cardinal for map layout" compass and the cardinal map fallback read
    ``edge.properties.cardinal`` (``area_description.build_exits_for_area``), so a
    generated way without it showed an empty compass. It is the same 8-wind name
    the painter's cell delta produced.
    """
    back = OPPOSITE.get(direction, direction)
    return [
        Edge(source=area_from, target=way_id, type=EDGE_CONNECTION,
             properties={"direction": direction, "cardinal": direction}),
        Edge(source=way_id, target=area_to, type=EDGE_CONNECTION,
             properties={"direction": back, "cardinal": back}),
        Edge(source=area_to, target=way_id, type=EDGE_CONNECTION,
             properties={"direction": back, "cardinal": back}),
        Edge(source=way_id, target=area_from, type=EDGE_CONNECTION,
             properties={"direction": direction, "cardinal": direction}),
    ]


def _entry_phrases(child_name: str, feature: Optional[str],
                   delta: Optional[float]) -> Tuple[str, str, List[str]]:
    """The narrative direction pair for entering a placed feature (task-496).

    Outdoors a cell-to-cell move is a compass word (``north``/``south``/…),
    which stays. Entering a *feature* is not a compass move — you go **in** — so
    the pair is narrative and sourced from what the placement actually is: the
    feature painted on the parent cell, and the floor step between the two
    places. A cave mouth in a cliff says "climb down into the cave", a plain
    cell says "enter".

    Returns ``(in_phrase, out_phrase, aliases)``. ``aliases`` are the short
    words kept working as exit handles (``go in``, ``go out``) — the matcher's
    alias tier reads them, so widening the vocabulary never takes a command away.
    """
    feature_name = str((biomes_mod.features() or {}).get(str(feature or ""), {})
                       .get("name") or "").lower()
    # Lower-cased, and without a leading article, so the phrase reads
    # "enter the mine" rather than "enter The Mine" — it is a handle a player
    # types and an agent reads mid-sentence, not a proper noun.
    subject = child_name.replace("_", " ").strip().lower()
    if subject.startswith("the "):
        subject = subject[4:]

    climb = delta is not None and delta >= CLIFF_FLOOR_DELTA
    drop = delta is not None and delta <= -CLIFF_FLOOR_DELTA

    if feature_name in ("tunnel", "cave") or "mine" in feature_name:
        return ("climb down into the tunnel" if climb else "enter the tunnel",
                "climb back out of the tunnel", ["in", "out", "tunnel"])
    if feature_name == "ford":
        return ("wade across the ford", "wade back across", ["in", "out", "ford"])
    if feature_name == "bridge":
        return ("cross the bridge", "cross back over", ["in", "out", "bridge"])
    if feature_name == "gate":
        return ("pass through the gate", "pass back through", ["in", "out", "gate"])
    if climb:
        return (f"climb up into {subject}", f"climb back down out of {subject}",
                ["in", "out"])
    if drop:
        return (f"climb down into {subject}", f"climb back up out of {subject}",
                ["in", "out"])
    if subject:
        return (f"enter {subject}", "leave", ["in", "out"])
    return (GATEWAY_IN, GATEWAY_OUT, [])


def _floor_value(layer: Dict[str, object],
                 cell: Tuple[int, int]) -> Optional[int]:
    """A cell's **storey index** from a floor layer, or None when unpainted.

    Whole storeys only: see :func:`world_grid.floor_paint_at`, which this mirrors
    so the compiler and the editor agree on what a painted number means.
    """
    value = (layer or {}).get(wg.cell_key(*cell))
    if value in (None, ""):
        return None
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return None


def _gateway_id(parent_id: str, child_id: str) -> str:
    return f"way_gateway_{parent_id}_{child_id}"


def _gateway(parent_id: str, child_id: str, parent_area: str, parent_name: str,
             entry_area: str, entry_name: str, child_name: str,
             recipe_id: str, seed: str, tick: int,
             cell: Optional[Tuple[int, int]] = None,
             enter: str = GATEWAY_IN, leave: str = GATEWAY_OUT,
             aliases: Optional[List[str]] = None) -> Tuple[Node, List[Edge]]:
    """The way from a parent's placed cell into a child scope's entry area.

    Deterministic and self-contained: it depends only on ids/names both sides
    already record, so whichever scope compiles second emits identical content.

    ``enter``/``leave`` are the narrative direction pair (see
    :func:`_entry_phrases`); ``aliases`` keep the short handles working.
    """
    way_id = _gateway_id(parent_id, child_id)
    props = {
        "area_from": parent_name,
        "area_to": entry_name,
        "area_from_id": parent_area,
        "area_to_id": entry_area,
        "direction": enter,
        "return_direction": leave,
        "current_state": "open",
        # You cannot see through into a whole child scope from outside it.
        "see_through": False,
        "pass_message": f"You pass between {parent_name} and {entry_name}.",
        "world_scope_id": parent_id,
        "child_scope_id": child_id,
        "generated": provenance(parent_id, recipe_id, seed, tick)["generated"],
    }
    if aliases:
        # The matcher reads aliases as exit handles (its alias tier), so "go in"
        # keeps resolving even though the direction is now a phrase.
        props["aliases"] = list(aliases)
    if cell is not None:
        # Sit on the parent cell it opens from, so the entrance appears in place.
        props["x"] = cell[0] * CELL_CANVAS_UNITS
        props["y"] = cell[1] * CELL_CANVAS_UNITS
    node = Node(id=way_id, type="way",
                name=f"Entrance to {child_name}", properties=props)
    edges = [
        Edge(source=parent_area, target=way_id, type=EDGE_CONNECTION,
             properties={"direction": enter}),
        Edge(source=way_id, target=entry_area, type=EDGE_CONNECTION,
             properties={"direction": enter}),
        Edge(source=entry_area, target=way_id, type=EDGE_CONNECTION,
             properties={"direction": leave}),
        Edge(source=way_id, target=parent_area, type=EDGE_CONNECTION,
             properties={"direction": leave}),
    ]
    return node, edges


#: How a building's door reads when there is nothing to go into (task-563).
#:
#: The refusal is a *tail* because it is composed onto the building's own name —
#: "The inn's door is shut" — so the sentence names the thing the character is
#: standing at. Keyed by the category tags task-561 gave the 31 building types
#: (commercial, military, religious, …); every tail is a noun phrase that reads
#: after an apostrophe-s, because the phrase is spliced in, not a whole sentence.
#: Two tails per category so two buildings of one category do not read as
#: clones; the pick is by :func:`_stable_index` on the biome id, so it is
#: deterministic like everything else in this file.
BUILDING_DOOR_TAILS = {
    "commercial": ("door is shut", "door is shut and the sign is turned"),
    "craft": ("door is shut", "door is shut and the bench is cold"),
    "industrial": ("door is locked", "door is bolted with a padlock"),
    "medical": ("door is locked", "door is locked to visitors"),
    "military": ("door is locked", "door is locked and barred"),
    "religious": ("door is shut", "door is barred for the night"),
    "residential": ("door is shut", "door stays shut"),
    "rural": ("door is shut", "door is bolted against the weather"),
    "transport": ("gate is shut", "gate is barred"),
}
BUILDING_DOOR_TAILS_DEFAULT = ("door is shut", "door is bolted")

#: The category tags consulted above, most specific first. A building may carry
#: several ("commercial" *and* "trade"), so the order decides which one speaks.
_BUILDING_CATEGORY_ORDER = (
    "military", "medical", "religious", "worship", "industrial", "craft",
    "commercial", "transport", "rural", "residential",
)


def building_subject(biome_id: Optional[str]) -> str:
    """A building's name as a thing you can be inside of: "inn", "ferry landing".

    Lower-cased and de-articled so the caller can put its own article in front
    and the possessive reads right. The *biome* name is used rather than the
    compiled area's name on purpose: the door belongs to the building type, and
    an author may have named the plot something else entirely (task-560).
    """
    rec = biomes_mod.biome(biome_id) or {}
    name = str(rec.get("name") or str(biome_id or "")).replace("_", " ").strip().lower()
    if name.startswith("the "):
        name = name[4:]
    return name


def building_refusal(biome_id: Optional[str]) -> str:
    """The line a building with no interior gives when someone tries to go in.

    Drawn from the building's category (see :data:`BUILDING_DOOR_TAILS`) so a
    smithy bars and a barn is merely shut. Deterministic per biome id, and the
    same function backs the editor's cell inspector, so what the painter shows
    and what the world says are one string rather than two implementations.
    """
    subject = building_subject(biome_id) or "door"
    tags = biomes_mod.area_tags(biome_id)
    tails = BUILDING_DOOR_TAILS_DEFAULT
    for tag in _BUILDING_CATEGORY_ORDER:
        if tag in tags:
            tails = BUILDING_DOOR_TAILS[tag]
            break
    tail = tails[_stable_index(f"door:{biome_id}", len(tails))]
    return f"The {subject}'s {tail}."


def _enter_way_id(scope_id: str, from_area: str, to_area: str) -> str:
    """Id of a building's ``in`` way (task-563).

    Keyed by the two areas it joins, like :func:`_way_id`, so both compile
    orders (parent-then-child, child-then-parent) mint the same id and a
    regenerate replaces rather than duplicates.
    """
    a, b = sorted((from_area, to_area))
    return f"way_enter_{scope_id}_{a}_{b}"


def _enter_way(scope_id: str, child_id: Optional[str], from_area: str,
               from_name: str, to_area: str, to_name: str, biome_id: str,
               recipe_id: str, seed: str, tick: int,
               cell: Tuple[int, int], *, refuse: bool
               ) -> Tuple[Node, List[Edge]]:
    """The way you go **into** a building from the place beside it (task-563).

    ``refuse`` is the whole of the difference between the two cases:

    - ``False`` — the building owns a child scope, so this leads to its interior
      entry. The way is **one-way** on purpose: inside, ``out`` must keep meaning
      one thing (the doorstep the child gateway points at), and a second ``out``
      to the street would make the word ambiguous. You come out onto the doorstep
      and walk off it, which is also what makes an adjacent building one turn.
    - ``True`` — the building has no interior, so the way leads to the building's
      own area and starts ``closed`` with a ``refusal_message`` drawn from the
      building's category. ``engine/movement.py`` raises that message instead of
      walking through, until the state becomes ``open`` — which is what a knock,
      a key or an author painting the interior actually does. ``aliases: ["in"]``
      keeps ``go in`` resolving.

    **One-way in both cases**, and that is the whole reason this is not
    ``_way_edges``. The place beside a building already has a compass way onto
    the plot, so a way back would be a *second* connection for the same pair — and
    two ways both answering to ``out`` on the plot means a bare "out" picks one at
    random, which is how you end up shut out of the smithy by the alley door you
    did not use. One way in, and the plot's own exits stay compass.

    The direction is a phrase rather than a compass word (``enter the inn``, with
    ``aliases: ["in"]`` keeping "go in" resolving), and no ``cardinal`` is
    recorded because nothing here points at a compass bearing.
    """
    subject = building_subject(biome_id) or "building"
    enter = f"enter the {subject}"
    way_id = _enter_way_id(scope_id, from_area, to_area)
    props: Dict[str, object] = {
        "area_from": from_name,
        "area_to": to_name,
        "area_from_id": from_area,
        "area_to_id": to_area,
        "direction": enter,
        "current_state": "closed" if refuse else "open",
        # A front door is not a window: you cannot see the interior from the
        # street, and the town map should not draw a line through the wall.
        "see_through": False,
        # `entrance`, not `door`: a painted `door` *cell* is structure the author
        # drew between two places (task-562), while this is a building's front
        # door, which exists because the cell is a building and has not been drawn
        # at all. Keeping the two apart means "how many doorways did I paint" and
        # "how many buildings are on this street" stay answerable from the graph.
        "kind": "entrance",
        "aliases": ["in"],
        "building": biome_id,
        "pass_message": (f"You step inside the {subject}." if refuse
                         else f"You go in through the door of the {subject}."),
        "world_scope_id": scope_id,
        "x": cell[0] * CELL_CANVAS_UNITS,
        "y": cell[1] * CELL_CANVAS_UNITS,
        "cell": {"x": cell[0], "y": cell[1]},
        "generated": provenance(scope_id, recipe_id, seed, tick)["generated"],
    }
    if refuse:
        props["refusal_message"] = building_refusal(biome_id)
    else:
        # Cleanup ownership: `ungenerate_scope` removes any way naming this child
        # even though the provenance says the parent (the gateway's rule), so
        # regenerating an interior cannot leave a way pointing into nothing.
        props["child_scope_id"] = child_id
    node = Node(id=way_id, type="way", name=f"{from_name} - {subject} door",
                properties=props)
    # Only the two edges that let you in — see the docstring on why there is no
    # way back. `move_to_area` finds "the other side" by scanning the way's
    # connection edges for a target that is not where it started, which is the
    # interior or the plot either way.
    return node, [
        Edge(source=from_area, target=way_id, type=EDGE_CONNECTION,
             properties={"direction": enter}),
        Edge(source=way_id, target=to_area, type=EDGE_CONNECTION,
             properties={"direction": enter}),
    ]


def _regions(cells: List[Tuple[int, int]], identity):
    """Flood-fill 8-neighbour cells of the same *identity* into ordered regions.

    ``identity`` maps a cell to what kind of place it is — the road if one is
    painted, else the biome (task-496). Passing the identity function rather
    than a biome map is what lets a run of road cells merge into one road area
    while staying distinct from the forest beside it.
    """
    remaining = set(cells)
    regions: List[List[Tuple[int, int]]] = []
    for start in sorted(cells, key=lambda c: (c[1], c[0])):
        if start not in remaining:
            continue
        kind = identity(start)
        stack = [start]
        remaining.discard(start)
        comp = []
        while stack:
            cell = stack.pop()
            comp.append(cell)
            for dx, dy in DIRECTIONS.values():
                nb = (cell[0] + dx, cell[1] + dy)
                if nb in remaining and identity(nb) == kind:
                    remaining.discard(nb)
                    stack.append(nb)
        regions.append(sorted(comp, key=lambda c: (c[1], c[0])))
    return regions


def _nearest_cells(cells_a: Set[Tuple[int, int]], cells_b: Set[Tuple[int, int]],
                   width: int, height: int
                   ) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
    """The closest (cell in A, cell in B) pair, by 8-neighbour BFS step count.

    ``cells_b`` may be a set of cells from several regions; the first B cell
    reached is the nearest. Used to join a disconnected island to the main
    landmass at one way rather than walling it off.
    """
    if not cells_a or not cells_b:
        return None
    start = sorted(cells_a, key=lambda c: (c[1], c[0]))
    seen: Set[Tuple[int, int]] = set(cells_a)
    # Carry the painted origin so the returned A cell is always a real region
    # cell, not an empty transit cell the BFS wandered through.
    queue: deque = deque((cell, cell) for cell in start)
    while queue:
        cell, origin = queue.popleft()
        for dx, dy in DIRECTIONS.values():
            nb = (cell[0] + dx, cell[1] + dy)
            if nb in cells_b:
                return origin, nb
            if nb in seen or not (0 <= nb[0] < width and 0 <= nb[1] < height):
                continue
            seen.add(nb)
            queue.append((nb, origin))
    return None


def _region_components(n_regions: int,
                       pairs: Set[Tuple[int, int]]) -> List[List[int]]:
    """Union-find of regions joined by ``pairs`` → one list of members each."""
    parent = list(range(n_regions))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for a, b in pairs:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    grouped: Dict[int, List[int]] = {}
    for i in range(n_regions):
        grouped.setdefault(find(i), []).append(i)
    return list(grouped.values())


def compile_grid(manifest: Dict[str, dict], scope_id: str, *,
                 region_merge: bool = False, link_islands: bool = True,
                 recipe_id: str = RECIPE_ID,
                 seed: Optional[str] = None, tick: int = 0) -> GenerationPatch:
    """Compile one scope's painted grid into an area/way ``GenerationPatch``.

    ``link_islands`` joins each disconnected component to the main landmass with
    a single way between the closest pair of cells, so a lone painted cell or a
    far island is reachable instead of compiling to a dead end.

    Raises ``ValueError`` when the scope is missing, has no grid, paints no
    cells, or its ``paint_policy`` is ``baked`` and it is already materialized.
    """
    record = manifest.get(scope_id)
    if record is None:
        raise ValueError(f"no such scope {scope_id!r}")
    if not wg.has_grid(record):
        raise ValueError(f"scope {scope_id!r} has no grid")
    if (record.get("paint_policy") == PAINT_POLICY_BAKED
            and record.get("state") == "materialized"):
        raise ValueError(
            f"scope {scope_id!r} is baked; compile it once then author by hand")

    if seed is None:
        seed = f"{scope_id}:{recipe_id}"
    # Display-name qualifier for generated areas, so two scopes never compile
    # to the same name (see ``_area_name``).
    scope_label = str(record.get("name") or scope_id)
    # Only a *world* scope has cliffs. A town or interior scope is built space
    # (rooms, decks, a storey of a skyscraper, the airlock of a spaceship), where
    # a storey step is a staircase rather than a rockface.
    outdoor = str(record.get("mode") or "world") == "world"

    width, height = wg.grid_size(record)
    layers = record.get("layers") or {}
    biome_layer = layers.get("biome") or {}
    road_layer = layers.get("road") or {}
    floor_layer = wg.layer_cells(record, "floor")

    biome_of: Dict[Tuple[int, int], str] = {}
    for y in range(height):
        for x in range(width):
            value = biome_layer.get(wg.cell_key(x, y))
            if value not in (None, ""):
                biome_of[(x, y)] = str(value)

    road_of: Dict[Tuple[int, int], str] = {}
    for y in range(height):
        for x in range(width):
            value = road_layer.get(wg.cell_key(x, y))
            if value not in (None, ""):
                road_of[(x, y)] = str(value)

    # **Every painted cell is a place** (task-496, observer-view model). A
    # road-only cell is no longer dropped: it compiles to an area whose terrain
    # IS the road. A road cell *replaces* its biome rather than adding a second
    # node on the same cell — one place per cell, and the biome underneath is
    # context for the description, not an extra area.
    cells = sorted(set(biome_of) | set(road_of), key=lambda c: (c[1], c[0]))

    def cell_road(cell: Tuple[int, int]) -> Optional[str]:
        return road_of.get(cell)

    def cell_biome(cell: Tuple[int, int]) -> Optional[str]:
        return biome_of.get(cell)

    def is_structure(cell: Tuple[int, int]) -> bool:
        """A cell that is structure rather than a place (task-562).

        A wall, a void, a window and a door occupy a cell and say how it connects,
        but they never become areas. A room with a wall between it and the corridor
        is a room with a wall; before this, that wall cell became an area and the
        gap between the two rooms read as a door. The vocabulary decides, through
        `cell_kind`, so a modder can add a `hedge` without touching this.

        A *road* painted over a structure biome is still a road — the road layer
        replaces the biome, exactly as it does everywhere else.
        """
        if cell_road(cell):
            return False
        return biomes_mod.cell_kind(cell_biome(cell)) != "place"

    structure = {c for c in cells if is_structure(c)}
    if structure:
        cells = [c for c in cells if c not in structure]

    # Unknown biome ids, reported rather than swallowed (task-562). An id the
    # taxonomy does not know compiles to a place — deleting the author's cell would
    # be worse than an area that reads thin — but a typo is invisible in the node
    # counts, so it is named here.
    unknown_ids = sorted({str(cell_biome(c)) for c in cells
                          if cell_biome(c) and not biomes_mod.biome(cell_biome(c))})

    # A cell holding a hand-placed area belongs to that area, not to the paint
    # (task-528). Drop it from the compile set *before* regions are formed, so a
    # merged region cannot swallow the cell either: the author gets one area on
    # that cell whether or not a biome is painted under it, and Generate can
    # never create a second one on top. The paint itself stays on the record, so
    # the WorldPainter still shows the cell.
    placed = wg.area_placements(record)
    if placed:
        occupied = {wg.cell_key(x, y)
                    for x, y in ((pos["x"], pos["y"]) for pos in placed.values())}
        cells = [c for c in cells if wg.cell_key(*c) not in occupied]
        if not cells:
            raise ValueError(
                f"scope {scope_id!r} paints no cells left to compile: every painted "
                f"cell holds a hand-placed area ({len(placed)} placed)")

    if not cells:
        raise ValueError(f"scope {scope_id!r} paints no cells")

    def identity(cell: Tuple[int, int]) -> str:
        """What *kind* of place this cell is: the road if painted, else the biome.

        Region merging groups by this, so a run of road cells merges into one
        road area while a road cell beside forest stays its own place — the road
        is a character of the cell, not a coat of paint over a shared biome.

        The **storey is part of the identity** (task-562). Merging is 8-neighbour,
        so a classroom on the floor above a classroom of the same kind touches it
        diagonally and used to merge into a single place that spanned two storeys —
        one area with a staircase inside it. A region is one storey's worth of one
        thing, which is what "a place" means at any scale.
        """
        road = road_of.get(cell)
        kind = f"road:{road}" if road else f"biome:{biome_of.get(cell)}"
        return f"{kind}|floor:{wg.floor_at(record, *cell)}"

    def floor_at(cell: Tuple[int, int]) -> Optional[int]:
        value = floor_layer.get(wg.cell_key(*cell))
        if value in (None, ""):
            return None
        try:
            return int(round(float(value)))
        except (TypeError, ValueError):
            return None

    def cliff_dirs(cell: Tuple[int, int]) -> Set[str]:
        """Directions whose neighbour stands a cliff-height above/below.

        Read only for *prose* (task-496): a multi-storey step makes an *outdoor*
        place read as a narrow path with a rockface. Gating traversal on the same
        delta is task-525's decision, deliberately not taken here.

        A storey step **inside** a building is not a cliff — it is a staircase,
        or simply the next deck of a spaceship — so ``town``/``interior`` scopes
        never promote a step to rock (see ``outdoor`` below). Outdoors, an
        unpainted floor counts as ground (0) rather than "unknown": the painter
        only asks for a number where the ground actually steps, and an author
        marking a cliff at cell A should not also have to number every plain cell
        around it. A cell that *is* painted still compares against its
        neighbours' painted values.
        """
        if not outdoor:
            return set()
        painted_here = floor_at(cell)
        here = 0 if painted_here is None else painted_here
        out: Set[str] = set()
        for direction, (dx, dy) in DIRECTIONS.items():
            nb = (cell[0] + dx, cell[1] + dy)
            # Any in-bounds cell counts, not just a painted one: a cliff face is
            # terrain whether or not it became a place, and an author who marks a
            # step up should not also have to paint a biome there.
            if not (0 <= nb[0] < width and 0 <= nb[1] < height):
                continue
            other = floor_at(nb)
            if other is None:
                continue
            if abs(other - here) >= CLIFF_FLOOR_DELTA:
                out.add(direction)
        return out

    region_lists = _regions(cells, identity) if region_merge else [[c] for c in cells]
    regions: List[List[Tuple[int, int]]] = region_lists
    cell_region: Dict[Tuple[int, int], int] = {}
    for index, region in enumerate(regions):
        for cell in region:
            cell_region[cell] = index
    region_anchor = {i: region[0] for i, region in enumerate(regions)}
    area_id_of_region = {i: _area_id(scope_id, region_anchor[i])
                         for i in range(len(regions))}

    # ── structure: the cells that are not places, and what they connect ──
    # Walked before the areas are built, because a place needs to know it has a
    # window (task-562), and before the ways, because a door's route has to be
    # emitted with them. This only *decides*; nothing is minted here.
    #
    # A threshold is a threshold between **exactly two** places, so the facing
    # places are counted before anything is decided. Four neighbours only: a
    # diagonal place is a corner of the room, not the other side of a wall, and
    # treating it as one is how a window in an outside wall ends up "facing" the
    # room across the corridor.
    windows: Dict[int, List[Dict[str, object]]] = {}
    door_pairs: List[Tuple[int, int, Tuple[int, int], Tuple[int, int], Tuple[int, int]]] = []
    dead_doors: List[Tuple[int, int]] = []
    for cell in sorted(structure, key=lambda c: (c[1], c[0])):
        kind_here = biomes_mod.cell_kind(cell_biome(cell))
        facing = [d for d, (dx, dy) in DIRECTIONS.items()
                  if (dx, dy) in _CARDINAL_STEPS
                  and (cell[0] + dx, cell[1] + dy) in cell_region]
        if kind_here == "see_through":
            # A window is not a route, so there is no way to mint — but the place it
            # belongs to should know it has one, so the description can say there is
            # a window in that wall. Only when it is unambiguous: a window with a
            # place on two sides is a passage in disguise (that is a door), and one
            # with none is a window onto nothing, which is still a window.
            if len(facing) == 1:
                dx, dy = DIRECTIONS[facing[0]]
                windows.setdefault(cell_region[(cell[0] + dx, cell[1] + dy)],
                                   []).append({"x": cell[0], "y": cell[1],
                                               "facing": facing[0]})
            continue
        if kind_here != "passable":
            continue
        # A passable cell joins the places on *opposite* sides of it — a doorway
        # crosses a wall, so the route it stands for is between the two cells
        # beyond, not between its own neighbours. The opposite pair is what
        # decides, and it is always the right reading: with four cardinal
        # neighbours, any three of them contain an opposite pair, so a door with
        # places all round it is a door in a wall with rooms either side of it.
        opposite = None
        for dx, dy in ((0, 1), (1, 0)):          # vertical pair, then horizontal
            before = (cell[0] - dx, cell[1] - dy)
            after = (cell[0] + dx, cell[1] + dy)
            if before in cell_region and after in cell_region:
                if cell_region[before] != cell_region[after]:
                    opposite = (before, after)
                break
        if opposite is not None:
            before, after = opposite
            door_pairs.append((cell_region[before], cell_region[after],
                               before, after, cell))
        elif facing:
            # No pair of places across it: a door onto a wall, or into the outside.
            # Worth saying out loud, because a door that leads nowhere is usually a
            # mis-painted one and is invisible in the node counts.
            dead_doors.append(cell)


    # Author-set cell names (task-560). A merged region is one place, so the first
    # named cell in the run speaks for all of it.
    cell_names = dict((record.get("names") or {}))
    _used_names: Set[str] = set()
    region_area_name = {
        i: _place_name(scope_label, region_anchor[i], biome_of, road_of,
                       _region_authored_name(regions[i], cell_names), _used_names)
        for i in range(len(regions))}
    # A scope's own entry area is its first region (regions are ordered by
    # (y, x), so region 0 is the top-left-most). A placed child links here.
    entry_area_id = area_id_of_region[0]
    entry_area_name = region_area_name[0]
    entry_anchor = region_anchor[0]

    nodes: List[Node] = []
    area_scope_assignments: Dict[str, str] = {}
    gateway_ids: set = set()
    gateways = 0
    #: (region index, building biome id) for every building cell, filled by the
    #: area loop below and consumed by the ``in``-way emitter (task-563).
    building_regions: List[Tuple[int, str]] = []
    #: Ids of the ``in`` ways already emitted, so a building whose region touches
    #: the same neighbour on two sides does not mint the way twice (task-563).
    enter_way_ids: Set[str] = set()

    for index, region in enumerate(regions):
        anchor = region_anchor[index]
        biome_id = cell_biome(anchor)
        road = cell_road(anchor)
        area_id = area_id_of_region[index]
        area_scope_assignments[area_id] = scope_id

        # Neighbours are anything adjacent to a *region* cell but outside the
        # region; a direction counts as an exit when such a neighbour exists.
        # A road cell beside unpainted ground has no neighbour there and no exit.
        neighbours: Dict[str, str] = {}
        company: Dict[str, str] = {}
        directions: List[str] = []
        for cell in region:
            for direction, (dx, dy) in DIRECTIONS.items():
                nb = (cell[0] + dx, cell[1] + dy)
                if nb not in cells or cell_region[nb] == index:
                    continue
                # A neighbour is named for what its place *is*, and a road cell's
                # place is a road — so the road label wins over the biome under
                # it. Otherwise a forest cell would report a road neighbour as
                # "sparse forest to the south" when the place next door is a road.
                neighbours.setdefault(direction, cell_road(nb) or cell_biome(nb) or "")
                company.setdefault(direction, terrain_class(cell_biome(nb), cell_road(nb)))
                if direction not in directions:
                    directions.append(direction)

        # Elevation is a description input now (task-496): a cliff-sized step
        # makes the place read as a narrow path with a rockface.
        _cliff_company(company, cliff_dirs(anchor))

        child_scope_id = wg.occupant_at(record, *anchor)

        # A road cell's tags and ground material come from the *road*; the biome
        # under it is context. Without a road the biome decides, as before.
        biome_rec = biomes_mod.biome(biome_id) or {}
        road_rec = (biomes_mod.features() or {}).get(str(road)) or {} if road else {}
        tags = list(road_rec.get("tags") or []) if road else []
        if not road:
            tags = list(biomes_mod.area_tags(biome_id))
        elif biome_id:
            # Keep the terrain's tags too, so a road through forest still forages
            # as forest and reads as a road *in* woods rather than bare tarmac.
            for tag in biomes_mod.area_tags(biome_id):
                if tag not in tags:
                    tags.append(str(tag))
        if child_scope_id and "feature" not in tags:
            tags.append("feature")

        props = {
            "world_scope_id": scope_id,
            "tags": tags,
            # The cell's **storey index** — 0 ground, 1 up, -1 down, unbounded.
            # Unpainted is ground, so every area carries a real storey.
            "floor": wg.floor_at(record, *anchor),
            # What you stand on, which is a different fact from which storey you
            # are on. A road's own material wins; otherwise the biome under it.
            "surface": biomes_mod.ground_surface(
                road_rec if road else None, biome_rec),
            "environment": dict(biome_rec.get("environment") or DEFAULT_ENVIRONMENT),
            "description": _area_description(
                anchor, biome_id, road, neighbours, directions,
                child_scope_id, seed, company=company),
            # Canvas position from the painted cell (task-496). The graph view
            # reads ``properties.x``/``y`` directly, so with physics off a
            # generated scope lays out in the shape it was painted instead of a
            # physics blob. Not a distance: travel stays one turn per cell.
            "x": anchor[0] * CELL_CANVAS_UNITS,
            "y": anchor[1] * CELL_CANVAS_UNITS,
            "cell": {"x": anchor[0], "y": anchor[1]},
        }
        if road:
            props["road"] = road
        if biome_id:
            # Kept even on a road cell: the biome underneath is the context the
            # description and the tags read ("a road in the woods").
            props["biome"] = biome_id
        if child_scope_id:
            props["child_scope_id"] = child_scope_id
        # A building cell is a place you go *into* rather than a cell you step
        # onto (task-563). Recorded on the area so the map, the description and
        # the editor can all read the fact from one field, and so the ``in``
        # ways below can be explained in the generate report.
        if biome_id and not road and biomes_mod.is_building(biome_id):
            props["building"] = biome_id
            building_regions.append((index, biome_id))
        # Windows in this place's walls (task-562). Not a route and not a place —
        # recorded so the description can mention one and so the map has something
        # to draw when windows become visible edges.
        if windows.get(index):
            props["windows"] = windows[index]
        props.update(provenance(scope_id, recipe_id, seed, tick))

        nodes.append(Node(
            id=area_id, type="area",
            name=region_area_name[index], properties=props))

    edges: List[Edge] = []
    emitted_pairs: Set[Tuple[int, int]] = set()

    def emit_passage(region_a: int, region_b: int,
                     cell: Tuple[int, int], nb: Tuple[int, int],
                     direction: str, floor_biome: str,
                     kind: str = "open") -> None:
        from_area = area_id_of_region[region_a]
        to_area = area_id_of_region[region_b]
        from_name = region_area_name[region_a]
        to_name = region_area_name[region_b]
        way_id = _way_id(scope_id, from_area, to_area)
        road_id = cell_road(cell)
        storey_delta = abs(wg.floor_at(record, *cell) - wg.floor_at(record, *nb))
        way_props = {
            "area_from": from_name,
            "area_to": to_name,
            "area_from_id": from_area,
            "area_to_id": to_area,
            "direction": direction,
            "current_state": "open",
            "see_through": True,
            # What kind of connection this is (task-562): `open` (you walk it),
            # `door` (a threshold you go through), `stairs` (a storey step you
            # climb). Read by prose now and by movement in task-525/task-563, which
            # is why it is data rather than a phrase in the pass message.
            "kind": kind,
            # The storey step the edge actually crosses, signed from `cell`. A big
            # jump is the gate task-525 will decide on; recording it here means the
            # decision has a number to read rather than to re-derive.
            "floor_step": storey_delta,
            # A way's **storey** is the lower of the two it joins: a corridor sits
            # on the storey both its ends are on, and a way that climbs is on the
            # one it leaves. `min` rather than "the emitting cell's storey" so the
            # value does not depend on which side of the adjacency emitted first.
            "floor": min(wg.floor_at(record, *cell), wg.floor_at(record, *nb)),
            # What you walk on: a road cell's way walks on the road, a biome
            # cell's on its ground. A road-only cell has no biome, so it falls
            # back to the default material.
            "surface": biomes_mod.ground_surface(
                (biomes_mod.features() or {}).get(str(road_id or "")),
                biomes_mod.biome(floor_biome)),
            "pass_message": f"You follow the path {direction} toward {to_name}.",
            "world_scope_id": scope_id,
            # Midpoint of the two cells, so a way sits between its areas
            # when the graph is laid out from painted positions.
            "x": ((cell[0] + nb[0]) / 2) * CELL_CANVAS_UNITS,
            "y": ((cell[1] + nb[1]) / 2) * CELL_CANVAS_UNITS,
            # A way is *painted* exactly like an area: those x/y are engine
            # units (cell * 40) that the map layout scales by the map pitch and
            # translates by the scope's `map_offset`. `cell` is the marker that
            # says so, and it is the ONLY thing distinguishing engine units from
            # the canvas pixels a hand-dragged node stores in the same field
            # (see `GraphLayoutEngine.hasPaintedCoords`). Without it a way is
            # indistinguishable from a dragged node, so saving a layout writes
            # canvas pixels over its engine units and the next layout re-adds the
            # scope offset on top — the way walks further out every save. The
            # midpoint of two cells is a half-integer cell; that is honest, and
            # the marker is a flag, not a cell index.
            "cell": {"x": (cell[0] + nb[0]) / 2, "y": (cell[1] + nb[1]) / 2},
            "generated": provenance(scope_id, recipe_id, seed, tick)["generated"],
        }
        # A pass message that says what the edge *is* (task-562), because that is
        # the difference the author painted and the character should feel it.
        if kind == "stairs":
            way_props["pass_message"] = (
                f"You climb {storey_delta} storey"
                f"{'s' if storey_delta != 1 else ''} to {to_name}.")
        elif kind == "door":
            way_props["pass_message"] = f"You go through the door into {to_name}."
        if kind == "door":
            # A door is named rather than steered: `way_handle` prefers a
            # non-empty direction, so an *empty* one is what makes "go through the
            # door" resolve (see engine/matching.py). The direction stays set for
            # the command the author expects ("go east"), and the way's name is what
            # a *name-based* exit matches on.
            way_props["handle"] = "door"
            way_props["aliases"] = ["door", "through", "in", "out"]
        nodes.append(Node(id=way_id, type="way",
                          name=f"{from_name} - door" if kind == "door"
                               else f"{from_name} to {to_name}",
                          properties=way_props))
        edges.extend(_way_edges(from_area, to_area, way_id, direction))

    for cell in cells:
        for direction in _SCAN_DIRECTIONS:
            dx, dy = DIRECTIONS[direction]
            nb = (cell[0] + dx, cell[1] + dy)
            if nb not in cell_region:
                continue
            region_a = cell_region[cell]
            region_b = cell_region[nb]
            if region_a == region_b:
                continue  # same merged area — no internal passage
            pair = (region_a, region_b) if region_a < region_b else (region_b, region_a)
            if pair in emitted_pairs:
                continue  # one passage per region boundary pair
            emitted_pairs.add(pair)
            # A storey step is a climb, not a stride (task-562). The threshold for
            # *blocking* a big one is task-525's decision; recording the kind is
            # what lets it be made later without re-deriving it.
            step = abs(wg.floor_at(record, *cell) - wg.floor_at(record, *nb))
            emit_passage(region_a, region_b, cell, nb,
                         _direction_between(cell, nb), cell_biome(cell) or "",
                         "stairs" if step >= 1 else "open")

    # ── doors: emit the routes a passable structure cell stands for ──
    # A wall stops a route because it occupies the cell between two places, so the
    # two are no longer adjacent and no way is minted. A *door* occupies the same
    # cell but is passable, so the route it stands for is built explicitly here —
    # otherwise painting a door would be indistinguishable from painting a wall.
    doorways: List[Dict[str, object]] = []
    for region_a, region_b, before, after, cell in door_pairs:
        pair = (region_a, region_b) if region_a < region_b else (region_b, region_a)
        if pair in emitted_pairs:
            continue                          # already connected some other way
        emitted_pairs.add(pair)
        # A passable cell between two *different* storeys is a stairwell, whatever
        # it was painted as: the storey is the stronger signal about what you do
        # crossing it, and a "door" that quietly climbs a floor would be a lie in
        # the pass message.
        climbs = wg.floor_at(record, *before) != wg.floor_at(record, *after)
        emit_passage(region_a, region_b, before, after,
                     _direction_between(before, after), cell_biome(before) or "",
                     "stairs" if climbs else "door")
        doorways.append({
            "x": cell[0], "y": cell[1],
            "from": area_id_of_region[region_a],
            "to": area_id_of_region[region_b],
            "kind": "stairwell" if climbs else "door",
        })

    # ── buildings: you go in, you do not walk on (task-563) ──
    # A building cell is entered with `in` from every side that already has a
    # way, so standing in the street you type `in` instead of stepping sideways
    # onto the doorstep. Cardinal sides only: a door is on a wall, not on a
    # corner, and a diagonal neighbour is a corner of the plot.
    #
    # Which side "has a way" is read from `emitted_pairs` rather than guessed
    # from adjacency, so a side walled off (task-562 removed the wall cell, so
    # the pair was never connected) gets no door, and a side reached through a
    # painted doorway does — the doorway minted the pair.
    sides_by_cell: Dict[Tuple[int, int], List[Dict[str, object]]] = {}
    entered = 0
    shut = 0
    for region_index, biome_id in building_regions:
        sides: List[Dict[str, object]] = []
        seen_sides: Set[Tuple[str, str]] = set()
        for cell in regions[region_index]:
            for direction, (dx, dy) in DIRECTIONS.items():
                if (dx, dy) not in _CARDINAL_STEPS:
                    continue
                neighbour = cell_region.get((cell[0] + dx, cell[1] + dy))
                if neighbour is None or neighbour == region_index:
                    continue
                pair = ((region_index, neighbour) if region_index < neighbour
                        else (neighbour, region_index))
                if pair not in emitted_pairs:
                    continue            # no way that way: no door to knock on
                key = (direction, area_id_of_region[neighbour])
                if key in seen_sides:
                    continue
                seen_sides.add(key)
                sides.append({"direction": direction,
                              "area_id": area_id_of_region[neighbour],
                              "area_name": region_area_name[neighbour]})
        sides.sort(key=lambda s: (str(s["direction"]), str(s["area_id"])))
        for cell in regions[region_index]:
            sides_by_cell[cell] = sides
        if not sides:
            continue
        anchor = region_anchor[region_index]
        plot_area = area_id_of_region[region_index]
        plot_name = region_area_name[region_index]
        child_id = wg.occupant_at(record, *anchor)
        child = manifest.get(str(child_id)) if child_id else None
        if child_id and not (child or {}).get("area_ids"):
            # A child scope is placed here but not generated yet. Emitting the
            # shut door now would be a lie (there IS an interior, we have just
            # not seen it), and emitting the `in` way needs an entry area id we do
            # not have — so the child emits its own when it compiles (see the
            # parent-first branch of the gateway block below).
            continue
        interior = str(child_id) if child_id else ""
        target_area = (str((child or {}).get("entry_area_id")
                           or sorted((child or {})["area_ids"])[0])
                       if interior else plot_area)
        target_name = (str((child or {}).get("entry_area_name") or target_area)
                       if interior else plot_name)
        for side in sides:
            node, enter_edges = _enter_way(
                scope_id, interior or None, str(side["area_id"]),
                str(side["area_name"]), target_area, target_name, biome_id,
                recipe_id, seed, tick, anchor, refuse=not interior)
            if node.id in enter_way_ids:
                continue
            enter_way_ids.add(node.id)
            nodes.append(node)
            edges.extend(enter_edges)
            entered += 1
            if not interior:
                shut += 1

    # ── link disconnected islands ──
    # An island (a cell/cluster with no painted 8-neighbour) would compile to an
    # unreachable dead end. Instead each disconnected component is joined to the
    # main landmass by a *single* way between its closest pair of cells, so a
    # lone outpost can be painted anywhere and still be walked to. One link per
    # component — not one to each of the 8 nearest neighbours.
    linked = 0
    if link_islands and len(regions) > 1:
        components = _region_components(len(regions), emitted_pairs)
        if len(components) > 1:
            main = max(components, key=lambda c: (len(c), -min(c)))
            connected: Set[int] = set(main)
            for comp in sorted((c for c in components if c is not main),
                               key=lambda c: min(c)):
                a_cells = {cell for i in comp for cell in regions[i]}
                b_cells = {cell for i in connected for cell in regions[i]}
                hit = _nearest_cells(a_cells, b_cells, width, height)
                if hit is not None:
                    ca, cb = hit
                    region_a, region_b = cell_region[ca], cell_region[cb]
                    pair = ((region_a, region_b) if region_a < region_b
                            else (region_b, region_a))
                    if region_a != region_b and pair not in emitted_pairs:
                        emitted_pairs.add(pair)
                        linked += 1
                        emit_passage(
                            region_a, region_b, ca, cb,
                            _compass_direction(cb[0] - ca[0], cb[1] - ca[1]),
                            # `cell_biome(... ) or ""`, not `biome_of[ca]`.
                            # A cell is a place if it has a biome **or a road**
                            # (`cells = set(biome_of) | set(road_of)`), so a
                            # road-only cell is a perfectly valid island member
                            # with no entry in `biome_of` — and a bare subscript
                            # there raises KeyError. The sibling call above (the
                            # region-boundary emitter) has always used the safe
                            # accessor, and the other `biome_of` reads in this file
                            # all use `.get`. This was the lone exception.
                            cell_biome(ca) or "")
                connected.update(comp)

    def _entry_delta(parent_rec: dict, child_id: str,
                     cell: Optional[Tuple[int, int]]) -> Optional[int]:
        """Storey step from a placement's parent cell down into the child.

        Both sides come off the records — the parent cell from this scope's
        floor layer, the child from the ``entry_floor`` it recorded when *it*
        compiled. So whichever scope compiles second derives the same phrase. An
        unpainted side reads as ground.
        """
        parent_floor = 0 if cell is None else (floor_at(cell) or 0)
        child = manifest.get(child_id) or {}
        if "entry_floor" not in child:
            return None            # child not compiled with a floor yet
        try:
            return int(round(float(child["entry_floor"]))) - parent_floor
        except (TypeError, ValueError):
            return None

    def _parent_cell_layer(manifest_: Dict[str, dict], child_id: str,
                           cell: Optional[Tuple[int, int]],
                           layer: str) -> Optional[str]:
        """A paint layer's value on the parent cell this child sits on."""
        if cell is None:
            return None
        for parent in manifest_.values():
            if child_id in (parent.get("placements") or {}):
                values = (parent.get("layers") or {}).get(layer) or {}
                value = values.get(wg.cell_key(*cell))
                return str(value) if value not in (None, "") else None
        return None

    def _parent_cell_feature(manifest_: Dict[str, dict], child_id: str,
                             cell: Optional[Tuple[int, int]]) -> Optional[str]:
        """The road feature painted on the parent cell this child sits on."""
        return _parent_cell_layer(manifest_, child_id, cell, "road")

    def _reverse_entry_delta(manifest_: Dict[str, dict], parent_id: str,
                             child_id: str) -> Optional[int]:
        """The same storey step, read from this scope's side (child-compiles-second).

        Mirrors :func:`_entry_delta` so both emission paths produce the same
        direction pair, whichever scope happened to compile second.
        """
        child = manifest_.get(child_id) or {}
        if "entry_floor" not in child:
            return None
        parent = manifest_.get(parent_id) or {}
        pos = (parent.get("placements") or {}).get(child_id) or {}
        parent_floor = 0
        try:
            parent_floor = wg.floor_at(parent, int(pos.get("x")), int(pos.get("y")))
        except (TypeError, ValueError):
            parent_floor = 0
        try:
            return int(round(float(child["entry_floor"]))) - parent_floor
        except (TypeError, ValueError):
            return None

    # ── child-scope gateways (task-496) ──
    # Every placement's compiled area is persisted on the parent, so a child
    # generated *after* this parent can still find its way in. The gateway
    # itself is emitted by whichever scope compiles second: the parent here if
    # the child is already materialized, otherwise the child when it compiles.
    placement_updates: Dict[str, dict] = {}
    for child_id, pos in sorted((record.get("placements") or {}).items()):
        if not isinstance(pos, dict):
            continue
        try:
            cell = (int(pos.get("x")), int(pos.get("y")))
        except (TypeError, ValueError):
            continue
        clean: Dict = {"x": cell[0], "y": cell[1]}
        region_index = cell_region.get(cell)
        if region_index is not None:
            clean["area_id"] = area_id_of_region[region_index]
            clean["area_name"] = region_area_name[region_index]
        # The door sides of a building cell (task-563), persisted so a child
        # scope compiled *later* can mint the `in` ways itself — the parent has
        # the compiled neighbour areas and their names, and recomputing them from
        # the child's side would mean re-deriving this scope's whole region
        # naming for the sake of one string.
        if cell in sides_by_cell:
            clean["sides"] = sides_by_cell[cell]
        placement_updates[str(child_id)] = clean

        child = manifest.get(child_id) or {}
        if region_index is None or not child.get("area_ids"):
            continue  # unpainted parent cell, or the child is not materialized
        child_entry = str(child.get("entry_area_id")
                          or sorted(child["area_ids"])[0])
        # The entry phrase is sourced from the placement: the road feature on the
        # parent cell, and the floor step between the two places.
        enter, leave, handles = _entry_phrases(
            str(child.get("name") or child_id), cell_road(cell),
            _entry_delta(record, child_id, cell))
        node, gw_edges = _gateway(
            scope_id, str(child_id), clean["area_id"], clean["area_name"],
            child_entry, str(child.get("entry_area_name") or child_entry),
            str(child.get("name") or child_id), recipe_id, seed, tick,
            cell=cell, enter=enter, leave=leave, aliases=handles)
        if node.id not in gateway_ids:
            gateway_ids.add(node.id)
            nodes.append(node)
            edges.extend(gw_edges)
            gateways += 1

    # If *this* scope is placed on an already-generated parent, emit the same
    # gateway now (the parent-first ordering).
    for parent_id in sorted(manifest):
        parent_rec = manifest[parent_id] or {}
        pos = (parent_rec.get("placements") or {}).get(scope_id)
        if not isinstance(pos, dict) or not pos.get("area_id"):
            continue
        pos_cell = None
        try:
            pos_cell = (int(pos.get("x")), int(pos.get("y")))
        except (TypeError, ValueError):
            pos_cell = None
        enter, leave, handles = _entry_phrases(
            str(record.get("name") or scope_id), _parent_cell_feature(manifest, scope_id, pos_cell),
            _reverse_entry_delta(manifest, parent_id, scope_id))
        node, gw_edges = _gateway(
            str(parent_id), scope_id,
            str(pos["area_id"]), str(pos.get("area_name") or pos["area_id"]),
            entry_area_id, entry_area_name, str(record.get("name") or scope_id),
            recipe_id, seed, tick, cell=pos_cell,
            enter=enter, leave=leave, aliases=handles)
        if node.id not in gateway_ids:
            gateway_ids.add(node.id)
            nodes.append(node)
            edges.extend(gw_edges)
            gateways += 1

        # The same parent-first ordering for the building's `in` ways (task-563).
        # The parent could not mint them — this scope had no entry area yet — so it
        # reads back the door sides it recorded on the placement and builds them
        # from here. Without this the common flow (generate the town, then draw
        # the interior) would leave the street with no `in` at all.
        building_id = _parent_cell_layer(manifest, scope_id, pos_cell, "biome")
        if building_id and biomes_mod.is_building(building_id):
            for side in (pos.get("sides") or []):
                if not isinstance(side, dict) or not side.get("area_id"):
                    continue
                node, enter_edges = _enter_way(
                    str(parent_id), scope_id, str(side["area_id"]),
                    str(side.get("area_name") or side["area_id"]),
                    entry_area_id, entry_area_name, building_id,
                    recipe_id, seed, tick, pos_cell or (0, 0), refuse=False)
                if node.id in enter_way_ids:
                    continue
                enter_way_ids.add(node.id)
                nodes.append(node)
                edges.extend(enter_edges)
                entered += 1
        break

    # An island is now auto-linked above, so this only counts a region left with
    # no exits at all (a single painted cell, or ``link_islands=False``).
    pair_degree: Dict[int, int] = {}
    for region_a, region_b in emitted_pairs:
        pair_degree[region_a] = pair_degree.get(region_a, 0) + 1
        pair_degree[region_b] = pair_degree.get(region_b, 0) + 1
    isolated = sum(1 for i in range(len(regions)) if not pair_degree.get(i))

    notes = [f"{len(regions)} area(s), {len(emitted_pairs)} passage(s)"
             + (" (region-merged)" if region_merge else "")]
    if structure:
        # Structure is invisible in the node count, so say it: a scope that lost 40
        # cells to walls is not a scope that compiled 40 fewer places by accident.
        notes.append(f"{len(structure)} structure cell(s) (not places: wall, "
                     f"void, window, door)")
    if doorways:
        kinds = Counter(w["kind"] for w in doorways)
        notes.append(f"{len(doorways)} threshold(s) joined the places either side: "
                     + ", ".join(f"{n} {k}" for k, n in sorted(kinds.items())))
    if windows:
        notes.append(f"{len(windows)} window(s) recorded on the places they face")
    if entered:
        # Say the split, not just the total: "4 in-ways, 2 of them shut" tells the
        # author which buildings still owe an interior, and the refusal strings
        # are in the vocabulary payload if they want to read one.
        notes.append(f"{entered} building door(s) entered with 'in'"
                     + (f" ({shut} shut, with no interior yet)" if shut else ""))
    if dead_doors:
        notes.append(f"{len(dead_doors)} door(s) with a place on only one side "
                     f"(they lead nowhere)")
    if unknown_ids:
        notes.append(f"WARNING: {len(unknown_ids)} painted id(s) are not in the "
                     f"taxonomy and compiled as bare places: "
                     f"{', '.join(unknown_ids[:6])}"
                     f"{' …' if len(unknown_ids) > 6 else ''}")
    if gateways:
        notes.append(f"{gateways} child gateway(s)")
    if linked:
        notes.append(f"{linked} island(s) linked to the nearest region")
    if isolated:
        notes.append(f"{isolated} area(s) have no exits (nothing else painted "
                     f"to link to)")
    report = GenerationReport(
        scope_id=scope_id, recipe_id=recipe_id, seed=str(seed),
        area_ids=sorted(area_scope_assignments),
        notes=notes,
    )
    updates: Dict = {"state": "materialized",
                     "entry_area_id": entry_area_id,
                     "entry_area_name": entry_area_name,
                     # The entry *cell*, so a parent compiling later can read the
                     # floor step between its cell and this scope's inside and
                     # phrase the gateway ("climb down into the cave") from
                     # something both sides of the compile agree on.
                      "entry_cell": {"x": entry_anchor[0], "y": entry_anchor[1]},
                      # The entry cell's **storey index**, so a parent compiling
                      # later can read the step between its cell and this scope's
                      # inside and phrase the gateway ("climb down into the cave")
                      # from something both sides of the compile agree on.
                      "entry_floor": _floor_value(floor_layer, entry_anchor)}
    if placement_updates:
        updates["placements"] = placement_updates
    return GenerationPatch(
        nodes=nodes, edges=edges,
        area_scope_assignments=area_scope_assignments,
        generated_manifest_updates=updates,
        report=report,
    )
