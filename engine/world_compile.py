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
#: which compiler produced a node.
RECIPE_ID = "grid.v1"

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


def _area_description(cell: Tuple[int, int], biome_id: str, road: Optional[str],
                      neighbours: Dict[str, str], directions: List[str],
                      child_scope_id: Optional[str], seed: str) -> str:
    """Deterministic prose from the cell's own tile, exits and neighbours.

    No LLM: a fragment from the biome, the road feature if painted, the exits,
    and the notable neighbouring biomes. Example: "A worn track cut through the
    land. Paths lead east and west. Dense forest lies to the north."
    """
    biome_rec = biomes_mod.biome(biome_id)
    key = wg.cell_key(*cell)
    parts: List[str] = []

    own = _fragment(biome_rec, key, seed)
    if own:
        parts.append(own)
    if road:
        feature = (biomes_mod.features() or {}).get(str(road)) or {}
        frag = _fragment(feature, f"road:{key}", seed)
        if frag:
            parts.append(frag)
        label = "road" if str(road) == "road" else f"{road} road"
        if directions:
            parts.append(f"The {label} runs {_join_dirs(sorted(directions))}.")
        else:
            parts.append(f"The {label} crosses here.")
    if child_scope_id:
        parts.append(f"{child_scope_id.replace('_', ' ').title()} stands here.")
    if directions and not road:
        parts.append("Paths lead " + _join_dirs(sorted(directions)) + ".")

    own_tags = set(biomes_mod.area_tags(biome_id))
    for direction in ("north", "south", "east", "west"):
        nb = neighbours.get(direction)
        if not nb or nb == biome_id:
            continue
        if set(biomes_mod.area_tags(nb)) & own_tags:
            continue  # same family — not worth calling out
        nb_rec = biomes_mod.biome(nb) or {}
        nb_name = (nb_rec.get("name") or nb).replace("_", " ")
        parts.append(f"{nb_name.capitalize()} lies to the {direction}.")

    text = " ".join(p.strip() for p in parts if p and p.strip())
    return text if text.endswith(".") else text + "."


# ─────────────────────────────── compile ──────────────────────────────────


def _area_id(scope_id: str, cell: Tuple[int, int]) -> str:
    return f"area_{scope_id}_{cell[0]}_{cell[1]}"


def _area_name(scope_label: str, biome_id: str, anchor: Tuple[int, int]) -> str:
    """A display name unique to its scope (task-496).

    The cell coordinates alone are not unique across scopes: a zone painted over
    a parent's cell (or two zones at the same cell) would both compile to
    "Sparse Forest (0,0)", and name-based resolution (movement, exits) would
    then pick the wrong area. Qualifying by the scope's display name keeps names
    unique in practice; ids stay the authoritative key.
    """
    biome_rec = biomes_mod.biome(biome_id) or {}
    name = biome_rec.get("name") or str(biome_id).replace("_", " ").title()
    return f"{name} ({scope_label} {anchor[0]},{anchor[1]})"


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


def _gateway_id(parent_id: str, child_id: str) -> str:
    return f"way_gateway_{parent_id}_{child_id}"


def _gateway(parent_id: str, child_id: str, parent_area: str, parent_name: str,
             entry_area: str, entry_name: str, child_name: str,
             recipe_id: str, seed: str, tick: int,
             cell: Optional[Tuple[int, int]] = None) -> Tuple[Node, List[Edge]]:
    """The way from a parent's placed cell into a child scope's entry area.

    Deterministic and self-contained: it depends only on ids/names both sides
    already record, so whichever scope compiles second emits identical content.
    """
    way_id = _gateway_id(parent_id, child_id)
    props = {
        "area_from": parent_name,
        "area_to": entry_name,
        "area_from_id": parent_area,
        "area_to_id": entry_area,
        "direction": GATEWAY_IN,
        "return_direction": GATEWAY_OUT,
        "current_state": "open",
        # You cannot see through into a whole child scope from outside it.
        "see_through": False,
        "pass_message": f"You pass between {parent_name} and {entry_name}.",
        "world_scope_id": parent_id,
        "child_scope_id": child_id,
        "generated": provenance(parent_id, recipe_id, seed, tick)["generated"],
    }
    if cell is not None:
        # Sit on the parent cell it opens from, so the entrance appears in place.
        props["x"] = cell[0] * CELL_CANVAS_UNITS
        props["y"] = cell[1] * CELL_CANVAS_UNITS
    node = Node(id=way_id, type="way",
                name=f"Entrance to {child_name}", properties=props)
    edges = [
        Edge(source=parent_area, target=way_id, type=EDGE_CONNECTION,
             properties={"direction": GATEWAY_IN}),
        Edge(source=way_id, target=entry_area, type=EDGE_CONNECTION,
             properties={"direction": GATEWAY_IN}),
        Edge(source=entry_area, target=way_id, type=EDGE_CONNECTION,
             properties={"direction": GATEWAY_OUT}),
        Edge(source=way_id, target=parent_area, type=EDGE_CONNECTION,
             properties={"direction": GATEWAY_OUT}),
    ]
    return node, edges


def _regions(cells: List[Tuple[int, int]], biome_of: Dict[Tuple[int, int], str]):
    """Flood-fill 8-neighbour cells of the same biome into ordered regions."""
    remaining = set(cells)
    regions: List[List[Tuple[int, int]]] = []
    for start in sorted(cells, key=lambda c: (c[1], c[0])):
        if start not in remaining:
            continue
        biome = biome_of[start]
        stack = [start]
        remaining.discard(start)
        comp = []
        while stack:
            cell = stack.pop()
            comp.append(cell)
            for dx, dy in DIRECTIONS.values():
                nb = (cell[0] + dx, cell[1] + dy)
                if nb in remaining and biome_of.get(nb) == biome:
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

    width, height = wg.grid_size(record)
    layers = record.get("layers") or {}
    biome_layer = layers.get("biome") or {}
    road_layer = layers.get("road") or {}
    elevation_layer = layers.get("elevation") or {}

    biome_of: Dict[Tuple[int, int], str] = {}
    for y in range(height):
        for x in range(width):
            value = biome_layer.get(wg.cell_key(x, y))
            if value not in (None, ""):
                biome_of[(x, y)] = str(value)

    cells = sorted(biome_of, key=lambda c: (c[1], c[0]))
    if not cells:
        raise ValueError(f"scope {scope_id!r} paints no cells")

    regions = _regions(cells, biome_of) if region_merge else [[c] for c in cells]
    cell_region: Dict[Tuple[int, int], int] = {}
    for index, region in enumerate(regions):
        for cell in region:
            cell_region[cell] = index
    region_anchor = {i: region[0] for i, region in enumerate(regions)}
    area_id_of_region = {i: _area_id(scope_id, region_anchor[i])
                         for i in range(len(regions))}
    region_area_name = {i: _area_name(scope_label, biome_of[region_anchor[i]],
                                      region_anchor[i])
                        for i in range(len(regions))}
    # A scope's own entry area is its first region (regions are ordered by
    # (y, x), so region 0 is the top-left-most). A placed child links here.
    entry_area_id = area_id_of_region[0]
    entry_area_name = region_area_name[0]

    nodes: List[Node] = []
    area_scope_assignments: Dict[str, str] = {}
    gateway_ids: set = set()
    gateways = 0

    for index, region in enumerate(regions):
        anchor = region_anchor[index]
        biome_id = biome_of[anchor]
        area_id = area_id_of_region[index]
        area_scope_assignments[area_id] = scope_id

        # Neighbours are anything adjacent to a *region* cell but outside the
        # region; a direction counts as an exit when such a neighbour exists.
        neighbours: Dict[str, str] = {}
        directions: List[str] = []
        for cell in region:
            for direction, (dx, dy) in DIRECTIONS.items():
                nb = (cell[0] + dx, cell[1] + dy)
                if nb not in biome_of or cell_region[nb] == index:
                    continue
                neighbours.setdefault(direction, biome_of[nb])
                if direction not in directions:
                    directions.append(direction)

        road = road_layer.get(wg.cell_key(*anchor))
        child_scope_id = wg.occupant_at(record, *anchor)

        biome_rec = biomes_mod.biome(biome_id) or {}
        tags = list(biomes_mod.area_tags(biome_id))
        if road:
            for tag in (biomes_mod.features().get(str(road)) or {}).get("tags", []):
                if tag not in tags:
                    tags.append(str(tag))
        if child_scope_id:
            tags.append("feature")

        props = {
            "world_scope_id": scope_id,
            "tags": tags,
            "floor": biome_rec.get("floor", "dirt"),
            "environment": dict(biome_rec.get("environment") or DEFAULT_ENVIRONMENT),
            "description": _area_description(
                anchor, biome_id, road, neighbours, directions,
                child_scope_id, seed),
            # Canvas position from the painted cell (task-496). The graph view
            # reads ``properties.x``/``y`` directly, so with physics off a
            # generated scope lays out in the shape it was painted instead of a
            # physics blob. Not a distance: travel stays one turn per cell.
            "x": anchor[0] * CELL_CANVAS_UNITS,
            "y": anchor[1] * CELL_CANVAS_UNITS,
            "cell": {"x": anchor[0], "y": anchor[1]},
        }
        elevation = elevation_layer.get(wg.cell_key(*anchor))
        if elevation not in (None, ""):
            props["elevation"] = elevation
        if road:
            props["road"] = road
        if child_scope_id:
            props["child_scope_id"] = child_scope_id
        props.update(provenance(scope_id, recipe_id, seed, tick))

        nodes.append(Node(
            id=area_id, type="area",
            name=_area_name(scope_label, biome_id, anchor), properties=props))

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
        way_props = {
            "area_from": from_name,
            "area_to": to_name,
            "area_from_id": from_area,
            "area_to_id": to_area,
            "direction": direction,
            "current_state": "open",
            "see_through": True,
            "floor": (biomes_mod.biome(floor_biome) or {}).get("floor", "dirt"),
            "pass_message": f"You follow the path {direction} toward {to_name}.",
            "world_scope_id": scope_id,
            # Midpoint of the two cells, so a way sits between its areas
            # when the graph is laid out from painted positions.
            "x": ((cell[0] + nb[0]) / 2) * CELL_CANVAS_UNITS,
            "y": ((cell[1] + nb[1]) / 2) * CELL_CANVAS_UNITS,
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
            if nb not in biome_of:
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
                         _direction_between(cell, nb), biome_of[cell])

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
                            biome_of[ca])
                connected.update(comp)

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
        node, gw_edges = _gateway(
            scope_id, str(child_id), clean["area_id"], clean["area_name"],
            child_entry, str(child.get("entry_area_name") or child_entry),
            str(child.get("name") or child_id), recipe_id, seed, tick,
            cell=cell)
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
        node, gw_edges = _gateway(
            str(parent_id), scope_id,
            str(pos["area_id"]), str(pos.get("area_name") or pos["area_id"]),
            entry_area_id, entry_area_name, str(record.get("name") or scope_id),
            recipe_id, seed, tick, cell=pos_cell)
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
                     "entry_area_name": entry_area_name}
    if placement_updates:
        updates["placements"] = placement_updates
    return GenerationPatch(
        nodes=nodes, edges=edges,
        area_scope_assignments=area_scope_assignments,
        generated_manifest_updates=updates,
        report=report,
    )
