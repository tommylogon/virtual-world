"""Search routes — placement target picker and general entity search."""
from flask import Blueprint, request, jsonify
import logging

logger = logging.getLogger(__name__)

def register_search_routes(app):
    @app.route("/api/search/placement-targets")
    def search_placement_targets():
        q = (request.args.get("q") or "").strip().lower()
        results = []
        try:
            world = app.world
            if not world:
                return jsonify(results)

            if world.areas:
                for name in world.areas.keys():
                    if not q or q in name.lower():
                        results.append({
                            "id": name,
                            "name": name,
                            "type": "area",
                            "icon": "🏠",
                            "description": (world.areas[name].get("description") if isinstance(world.areas[name], dict) else getattr(world.areas[name], "description", "")) or "",
                        })

            graph_nodes = getattr(world, "graph", {}).nodes or {}
            for node_id, node in graph_nodes.items():
                node_type = getattr(node, "type", None)
                if node_type not in ("item", "character"):
                    continue
                name = getattr(node, "name", "") or node_id
                if not q or q in name.lower() or q in node_id.lower():
                    desc = ""
                    props = getattr(node, "properties", None) or {}
                    if isinstance(props, dict):
                        desc = props.get("description", "") or ""
                    results.append({
                        "id": node_id,
                        "name": name,
                        "type": node_type,
                        "icon": "🧍" if node_type == "character" else "📦",
                        "description": desc or "",
                    })
        except Exception as exc:
            logger.warning("placement-target search failed: %s", exc)

        results.sort(key=lambda r: (r["type"], r["name"]))
        return jsonify(results)
