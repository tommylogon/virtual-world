"""Structure-template operations: list / preview / save / materialize.

Backend for task-357 (structure templates). The route registration lives in
``routes/structures.py``; the work lives here, matching the
``library_routes`` → ``library_ops`` split.
"""

from __future__ import annotations

import logging
import re

from flask import jsonify, request

from engine.structures import (
    collect_structure,
    materialize_structure,
    summarize_structure,
)
from .helpers import delete_registry_entry, load_registry, save_registry

logger = logging.getLogger(__name__)

STRUCTURES_REGISTRY = "structures.json"


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9_]+", "_", str(value or "").lower()).strip("_") or "structure"


def _body() -> dict:
    return request.get_json(silent=True) or {}


def handle_structures_list(app):
    registry = load_registry(app.config["DATA_DIR"], STRUCTURES_REGISTRY)
    out = []
    for key, template in registry.items():
        entry = summarize_structure(template)
        entry["id"] = template.get("template_id") or key
        out.append(entry)
    out.sort(key=lambda e: str(e.get("name", "")).lower())
    return jsonify(out)


def handle_structures_preview(app):
    body = _body()
    area_id = body.get("area_id")
    if not area_id:
        return jsonify({"error": "Missing 'area_id'"}), 400
    try:
        template = collect_structure(
            app.world,
            area_id,
            include_items=bool(body.get("include_items", True)),
            include_characters=bool(body.get("include_characters", False)),
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    summary = summarize_structure(template)
    root_node = app.world.graph.get_node(template["root_area"])
    summary["root_area_name"] = root_node.name if root_node else ""
    summary["boundary_exits"] = template.get("boundary_exits") or []
    return jsonify(summary)


def handle_structures_save(app):
    body = _body()
    area_id = body.get("area_id")
    if not area_id:
        return jsonify({"error": "Missing 'area_id'"}), 400
    name = str(body.get("name") or "").strip()
    try:
        template = collect_structure(
            app.world,
            area_id,
            include_items=bool(body.get("include_items", True)),
            include_characters=bool(body.get("include_characters", False)),
            name=name or None,
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    structure_id = _slug(body.get("id") or name or template.get("name") or area_id)
    template["template_id"] = structure_id
    save_registry(app.config["DATA_DIR"], STRUCTURES_REGISTRY, {structure_id: template})
    summary = summarize_structure(template)
    summary["status"] = "saved"
    return jsonify(summary)


def handle_structures_materialize(app, structure_id):
    registry = load_registry(app.config["DATA_DIR"], STRUCTURES_REGISTRY)
    template = registry.get(structure_id)
    if not template:
        return jsonify({"error": f"Structure '{structure_id}' not found"}), 404
    body = _body()
    try:
        report = materialize_structure(
            app.world,
            template,
            seed=body.get("seed"),
            include_items=bool(body.get("include_items", True)),
            include_characters=bool(body.get("include_characters", True)),
        )
    except Exception as exc:  # materialization must never half-apply silently
        logger.exception("Structure materialization failed: %s", structure_id)
        return jsonify({"error": str(exc)}), 500
    return jsonify(report)


def handle_structures_delete(app, structure_id):
    removed = delete_registry_entry(app.config["DATA_DIR"], STRUCTURES_REGISTRY, structure_id)
    if not removed:
        return jsonify({"error": f"Structure '{structure_id}' not found"}), 404
    return jsonify({"status": "deleted"})
