"""Tag routes -- search, validate, and stats endpoints."""
import os, json, logging
from flask import Blueprint, request, jsonify
from difflib import get_close_matches
logger = logging.getLogger(__name__)

def register_tag_routes(app):
    @app.route("/api/tags/search")
    def search_tags():
        q = request.args.get("q", "").strip().lower()
        tags_dir = os.path.join(app.root_path, "data", "library", "tags")
        results = []
        if not os.path.isdir(tags_dir):
            return jsonify(results)
        for fn in os.listdir(tags_dir):
            if not fn.endswith(".json"):
                continue
            try:
                with open(os.path.join(tags_dir, fn), "r", encoding="utf-8") as f:
                    tag = json.load(f)
            except:
                continue
            if q and q not in tag.get("name", "").lower() and q not in tag.get("id", fn[:-5]).lower():
                continue
            results.append({"id": tag.get("id", fn[:-5]), "name": tag.get("name", tag.get("id", fn[:-5])), "icon": tag.get("icon", "\U0001f397\ufe0f"), "color": tag.get("color", "#888888"), "category": tag.get("category", ""), "description": tag.get("description", "")})
        results.sort(key=lambda t: t["name"])
        return jsonify(results)

    @app.route("/api/tags/validate")
    def validate_tags():
        raw = request.args.get("tags", "")
        tag_list = [t.strip() for t in raw.split(",") if t.strip()]
        tags_dir = os.path.join(app.root_path, "data", "library", "tags")
        library = {}
        if os.path.isdir(tags_dir):
            for fn in os.listdir(tags_dir):
                if not fn.endswith(".json"):
                    continue
                try:
                    with open(os.path.join(tags_dir, fn), "r", encoding="utf-8") as f:
                        t = json.load(f)
                    library[t["id"]] = t["name"]
                except:
                    continue
        valid, unknown = [], []
        for tag in tag_list:
            if tag in library:
                valid.append(tag)
            else:
                suggestions = get_close_matches(tag, list(library.keys()), n=1, cutoff=0.6)
                unknown.append({"tag": tag, "suggestion": suggestions[0] if suggestions else None})
        return jsonify({"valid": valid, "unknown": unknown})

    @app.route("/api/tags/stats")
    def tag_stats():
        """Return usage count of each tag across items, characters, and areas."""
        tags_dir = os.path.join(app.root_path, "data", "library", "tags")
        library_tags = set()
        if os.path.isdir(tags_dir):
            for fn in os.listdir(tags_dir):
                if fn.endswith(".json"):
                    library_tags.add(fn.replace(".json", ""))
        counts = {t: {"items": 0, "characters": 0, "areas": 0} for t in library_tags}
        try:
            from virtual_world_engine import VirtualWorld
            world = VirtualWorld()
            for nid, node in (world.graph.nodes or {}).items():
                if not node.properties: continue
                node_tags = node.properties.get("tags", [])
                if isinstance(node_tags, str): node_tags = [t.strip() for t in node_tags.split(",")]
                if not isinstance(node_tags, list): continue
                for t in node_tags:
                    t = t.lower().strip()
                    if t in counts:
                        if node.type == "item": counts[t]["items"] += 1
                        elif node.type == "character": counts[t]["characters"] += 1
                        elif node.type == "area": counts[t]["areas"] += 1
        except Exception as e:
            logger.warning(f"Could not compute tag stats: {e}")
        return jsonify(counts)
