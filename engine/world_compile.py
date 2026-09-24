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

from typing import Dict, List, Optional, Tuple

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
}
OPPOSITE = {"north": "south", "south": "north", "east": "west", "west": "east"}
#: Directions emitted when scanning for adjacencies, so each shared edge is
#: visited once (east + south cover every 4-neighbour pair).
_SCAN_DIRECTIONS = ("east", "south")

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


def _way_edges(area_from: str, area_to: str, way_id: str,
               direction: str) -> List[Edge]:
    """The four connection edges a bidirectional way needs (movement.py)."""
    back = OPPOSITE.get(direction, direction)
    return [
        Edge(source=area_from, target=way_id, type=EDGE_CONNECTION,
             properties={"direction": direction}),
        Edge(source=way_id, target=area_to, type=EDGE_CONNECTION,
             properties={"direction": back}),
        Edge(source=area_to, target=way_id, type=EDGE_CONNECTION,
             properties={"direction": back}),
        Edge(source=way_id, target=area_from, type=EDGE_CONNECTION,
             properties={"direction": direction}),
    ]


def _gateway_id(parent_id: str, child_id: str) -> str:
    return f"way_gateway_{parent_id}_{child_id}"


def _gateway(parent_id: str, child_id: str, parent_area: str, parent_name: str,
             entry_area: str, entry_name: str, child_name: str,
             recipe_id: str, seed: str, tick: int) -> Tuple[Node, List[Edge]]:
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
    """Flood-fill 4-neighbour cells of the same biome into ordered regions."""
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


def compile_grid(manifest: Dict[str, dict], scope_id: str, *,
                 region_merge: bool = False, recipe_id: str = RECIPE_ID,
                 seed: Optional[str] = None, tick: int = 0) -> GenerationPatch:
    """Compile one scope's painted grid into an area/way ``GenerationPatch``.

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
    emitted_pairs = set()
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

            from_area = area_id_of_region[region_a]
            to_area = area_id_of_region[region_b]
            from_name = region_area_name[region_a]
            to_name = region_area_name[region_b]
            way_id = _way_id(scope_id, from_area, to_area)
            way_dir = _direction_between(cell, nb)
            way_props = {
                "area_from": from_name,
                "area_to": to_name,
                "area_from_id": from_area,
                "area_to_id": to_area,
                "direction": way_dir,
                "current_state": "open",
                "see_through": True,
                "floor": (biomes_mod.biome(biome_of[cell]) or {}).get("floor", "dirt"),
                "pass_message": f"You follow the path {way_dir} toward {to_name}.",
                "world_scope_id": scope_id,
                "generated": provenance(scope_id, recipe_id, seed, tick)["generated"],
            }
            nodes.append(Node(id=way_id, type="way",
                              name=f"{from_name} to {to_name}",
                              properties=way_props))
            edges.extend(_way_edges(from_area, to_area, way_id, way_dir))

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
            str(child.get("name") or child_id), recipe_id, seed, tick)
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
        node, gw_edges = _gateway(
            str(parent_id), scope_id,
            str(pos["area_id"]), str(pos.get("area_name") or pos["area_id"]),
            entry_area_id, entry_area_name, str(record.get("name") or scope_id),
            recipe_id, seed, tick)
        if node.id not in gateway_ids:
            gateway_ids.add(node.id)
            nodes.append(node)
            edges.extend(gw_edges)
            gateways += 1
        break

    notes = [f"{len(regions)} area(s), {len(emitted_pairs)} passage(s)"
             + (" (region-merged)" if region_merge else "")]
    if gateways:
        notes.append(f"{gateways} child gateway(s)")
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
