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

from collections import deque
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
                road_of: Dict[Tuple[int, int], str]) -> str:
    """A display name unique to its scope (task-496).

    The cell coordinates alone are not unique across scopes: a zone painted over
    a parent's cell (or two zones at the same cell) would both compile to
    "Sparse Forest (0,0)", and name-based resolution (movement, exits) would
    then pick the wrong area. Qualifying by the scope's display name keeps names
    unique in practice; ids stay the authoritative key.
    """
    label = _place_label(cell, biome_of, road_of)
    return f"{label} ({scope_label} {cell[0]},{cell[1]})"


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

    def cell_road(cell: Tuple[int, int]) -> Optional[str]:
        return road_of.get(cell)

    def cell_biome(cell: Tuple[int, int]) -> Optional[str]:
        return biome_of.get(cell)

    def identity(cell: Tuple[int, int]) -> str:
        """What *kind* of place this cell is: the road if painted, else the biome.

        Region merging groups by this, so a run of road cells merges into one
        road area while a road cell beside forest stays its own place — the road
        is a character of the cell, not a coat of paint over a shared biome.
        """
        road = road_of.get(cell)
        if road:
            return f"road:{road}"
        return f"biome:{biome_of.get(cell)}"

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
    region_area_name = {i: _place_name(scope_label, region_anchor[i], biome_of, road_of)
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
        props.update(provenance(scope_id, recipe_id, seed, tick))

        nodes.append(Node(
            id=area_id, type="area",
            name=region_area_name[index], properties=props))

    edges: List[Edge] = []
    emitted_pairs: Set[Tuple[int, int]] = set()

    def emit_passage(region_a: int, region_b: int,
                     cell: Tuple[int, int], nb: Tuple[int, int],
                     direction: str, floor_biome: str) -> None:
        from_area = area_id_of_region[region_a]
        to_area = area_id_of_region[region_b]
        from_name = region_area_name[region_a]
        to_name = region_area_name[region_b]
        way_id = _way_id(scope_id, from_area, to_area)
        road_id = cell_road(cell)
        way_props = {
            "area_from": from_name,
            "area_to": to_name,
            "area_from_id": from_area,
            "area_to_id": to_area,
            "direction": direction,
            "current_state": "open",
            "see_through": True,
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
        nodes.append(Node(id=way_id, type="way",
                          name=f"{from_name} to {to_name}",
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
            emit_passage(region_a, region_b, cell, nb,
                         _direction_between(cell, nb), cell_biome(cell) or "")

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

    def _parent_cell_feature(manifest_: Dict[str, dict], child_id: str,
                             cell: Optional[Tuple[int, int]]) -> Optional[str]:
        """The road feature painted on the parent cell this child sits on."""
        if cell is None:
            return None
        for parent in manifest_.values():
            if child_id in (parent.get("placements") or {}):
                layer = (parent.get("layers") or {}).get("road") or {}
                value = layer.get(wg.cell_key(*cell))
                return str(value) if value not in (None, "") else None
        return None

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
