"""Handlers for tag-chain area population (task-9).

Thin registrar lives in ``routes/population.py``. These handlers read an area's
domain tags, plan furniture/items with ``engine.population``, and materialize
them through the public library materialization service.
"""

import logging
import random
from pathlib import Path

from flask import jsonify, request

from engine.population import LibraryIndex, apply_population, plan_population
from routes.library_ops import graph_add_relation_edge, materialize_library_item

logger = logging.getLogger(__name__)

# Edge types that mean "this item is located in/at the area itself".
_SPATIAL_TYPES = {"in", "on", "under", "behind", "beside", "at"}


def _library_items_dir(app):
    return Path(app.config["DATA_DIR"]) / "library" / "items"


def _tags_of(node):
    tags = node.properties.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    return [str(t).lower() for t in tags]


def _area_items(graph, area_id):
    """Top-level item nodes located in the area (not inside furniture)."""
    items = []
    for edge in graph.get_edges_for_target(area_id):
        if edge.type not in _SPATIAL_TYPES:
            continue
        node = graph.get_node(edge.source)
        if node is not None and getattr(node, "type", "") == "item":
            items.append(node)
    return items


def handle_populate_area(app, area_id):
    """POST /api/populate/area/<area_id> — furnish an area from its tags.

    Body (all optional): ``seed`` (int), ``furniture_max`` (int),
    ``items_per_area`` (int), ``preview`` (bool — plan without applying).
    Idempotent-ish: existing furniture suppresses furniture seeding, and the
    item target is reduced by what the area already contains.
    """
    graph = app.world.graph
    node = graph.get_node(area_id)
    if node is None or getattr(node, "type", "") != "area":
        return jsonify({"error": f"Area '{area_id}' not found"}), 404

    data = request.get_json(silent=True) or {}
    seed = data.get("seed", 1)
    furniture_max = int(data.get("furniture_max", 3))
    items_per_area = int(data.get("items_per_area", 6))
    preview = bool(data.get("preview"))

    tags = _tags_of(node)
    existing = _area_items(graph, area_id)
    existing_furniture = sum(1 for n in existing if "furniture" in _tags_of(n))

    # Re-run safe: a populated area is left alone rather than duplicated. Callers
    # who want a fresh pass should clear the area first (task-398 owns regenerate).
    if existing:
        return jsonify({
            "area_id": area_id,
            "status": "already_populated",
            "domains": tags,
            "furniture": [],
            "items": [],
            "unresolved_domains": [],
            "notes": ["area already contains items; skipping"],
            "existing_items": len(existing),
            "existing_furniture": existing_furniture,
            "placed_furniture": 0,
            "placed_items": 0,
        })

    index = LibraryIndex.from_directory(_library_items_dir(app))
    rng = random.Random(seed)
    plan = plan_population(tags, index, rng,
                           furniture_max=furniture_max,
                           items_per_area=items_per_area)

    payload = {
        "area_id": area_id,
        "domains": plan.domains,
        "furniture": [p.library_id for p in plan.furniture],
        "items": [p.library_id for p in plan.items],
        "unresolved_domains": plan.unresolved_domains,
        "notes": plan.notes,
        "existing_items": 0,
        "existing_furniture": 0,
    }

    if plan.is_empty:
        return jsonify({**payload, "status": "empty"})
    if preview:
        return jsonify({**payload, "status": "preview"})

    def spawn(library_id):
        return materialize_library_item(app, library_id)

    def relate(child, parent, relation):
        graph_add_relation_edge(graph, child, parent, relation)

    try:
        apply_population(plan, spawn, relate, area_id)
    except Exception:
        logger.exception("Population failed for area %s", area_id)
        return jsonify({"error": "population failed"}), 500

    return jsonify({**payload, "status": "populated",
                    "placed_furniture": len(plan.furniture),
                    "placed_items": len(plan.items)})
