import logging
import math
import re
import time
import random
from flask import Flask, request, jsonify
from logger import setup_logger
from engine.spatial_memory import SpatialMemory
from engine.vector_store import VectorStore

logger = logging.getLogger(__name__)


def _normalize_tokens(text):
    """Lowercase, strip punctuation, return a token set for near-duplicate compare."""
    return set(re.findall(r"[a-z0-9']+", str(text or "").lower()))


def _is_near_duplicate(a_text, b_text, a_tick, b_tick,
                       tick_window=2, threshold=0.8):
    """True if two memory texts are near-verbatim within a small tick window.

    Used to collapse the same insight written by different writers in one tick
    (think-phase 💭 thought, observed 👁️ surfaced as a memory, react 📝 memory).
    Compares regardless of type. Jaccard >= threshold on normalized tokens.
    """
    try:
        if abs(int(a_tick or 0) - int(b_tick or 0)) > tick_window:
            return False
    except (TypeError, ValueError):
        return False
    a = _normalize_tokens(a_text)
    b = _normalize_tokens(b_text)
    if not a or not b:
        return False
    inter = len(a & b)
    union = len(a | b)
    if union == 0:
        return False
    return (inter / union) >= threshold


def register_memories_routes(app):
    """Register player-memory API routes (CRUD and clear)."""

    @app.route('/api/players/<name>/memories', methods=['GET'])
    def get_player_memories(name):
        player = app.world.players.get(name)
        if not player:
            return jsonify({"error": "Player not found"}), 404
        return jsonify({"memories": getattr(player, 'memories', [])})

    @app.route('/api/players/<name>/memories', methods=['PUT'])
    def set_player_memories(name):
        player = app.world.players.get(name)
        if not player:
            return jsonify({"error": "Player not found"}), 404
        data = request.get_json(force=True)
        memories = data.get("memories", [])
        if not isinstance(memories, list):
            return jsonify({"error": "memories must be a list"}), 400
        player.memories = memories
        return jsonify({"status": "success", "count": len(memories)})

    @app.route('/api/players/<name>/memories/entry', methods=['POST'])
    def add_player_memory(name):
        player = app.world.players.get(name)
        if not player:
            return jsonify({"error": "Player not found"}), 404
        data = request.get_json(force=True)
        emotions = data.get("emotions")
        tags = list(data.get("tags", []) or [])
        # task-350: a memory can carry a structured feelings block about a person
        # ({who, why, data:{dim:delta}}). Resolve the handle → real player name so
        # the derive reducer can match it, canonicalize `who`, and stamp a rel:
        # tag (which also registers the relationship). Guessing is blocked: an
        # unresolved/ambiguous handle simply is not attributed to anyone.
        if isinstance(emotions, dict):
            who = str(emotions.get("who") or "").strip()
            if who:
                resolved_who = None
                try:
                    from routes.player_ops import _resolve_other
                    resolved_who = _resolve_other(app, name, who)
                except Exception:
                    resolved_who = None
                if resolved_who:
                    emotions = dict(emotions)
                    emotions["who"] = resolved_who
                    reltag = "rel:" + resolved_who
                    if reltag not in tags:
                        tags.append(reltag)
        entry = {
            "id": data.get("id", f"mem_{int(time.time()*1000)}_{random.randint(0,999)}"),
            "text": data.get("text", ""),
            "tick": data.get("tick", app.world.time_ticks),
            "timestamp": data.get("timestamp", time.time()),
            "importance": data.get("importance", 5),
            "type": data.get("type", "observation"),
            "location": data.get("location", ""),
            "entity_ids": data.get("entity_ids", []),
            "embedding": data.get("embedding"),
            "tags": tags,
            "emotion": data.get("emotion"),
            "emotions": emotions,
            "memory_emotions": data.get("memory_emotions", []),
            "salience_override": data.get("salience_override", data.get("salience", 0)),
            "source": data.get("source", "auto")
        }

        # task-346: write-time dedup across writers (think / observation / react)
        # so the same insight isn't stored three times within one tick. On a
        # near-verbatim hit we merge the higher importance + union tags and do
        # NOT append a duplicate. Opt out with force: true (manual editor /
        # generator saves should never be silently collapsed).
        if not data.get("force"):
            for existing in player.memories:
                if _is_near_duplicate(existing.get("text", ""), entry["text"],
                                      existing.get("tick", 0), entry["tick"]):
                    if (entry.get("importance") or 0) > (existing.get("importance") or 0):
                        existing["importance"] = entry.get("importance", existing.get("importance", 5))
                    existing["tags"] = list(set(existing.get("tags", [])) | set(entry.get("tags", [])))
                    if len(entry["text"]) > len(existing.get("text", "")):
                        existing["text"] = entry["text"]
                    return jsonify({"status": "success", "entry": existing, "deduped": True}), 200

        player.memories.append(entry)
        return jsonify({"status": "success", "entry": entry}), 201

    @app.route('/api/players/<name>/memories/entry/<entry_id>', methods=['POST'])
    def update_player_memory(name, entry_id):
        player = app.world.players.get(name)
        if not player:
            return jsonify({"error": "Player not found"}), 404
        data = request.get_json(force=True)
        for entry in player.memories:
            if entry.get("id") == entry_id:
                for key in ["text", "type", "importance", "location", "tags",
                            "tick", "source", "entity_ids", "emotion", "emotions",
                            "memory_emotions", "salience_override", "timestamp"]:
                    if key in data:
                        entry[key] = data[key]
                return jsonify({"status": "success", "entry": entry})
        return jsonify({"error": "Entry not found"}), 404

    @app.route('/api/players/<name>/memories/entry/<entry_id>', methods=['DELETE'])
    def delete_player_memory(name, entry_id):
        player = app.world.players.get(name)
        if not player:
            return jsonify({"error": "Player not found"}), 404
        old_len = len(player.memories)
        player.memories = [m for m in player.memories if m.get("id") != entry_id]
        if len(player.memories) == old_len:
            return jsonify({"error": "Entry not found"}), 404
        return jsonify({"status": "success"})

    @app.route('/api/players/<name>/memories/clear', methods=['POST'])
    def clear_player_memories(name):
        player = app.world.players.get(name)
        if not player:
            return jsonify({"error": "Player not found"}), 404
        player.memories = []
        try:
            from engine.vector_store import VectorStore
            VectorStore(app.config['DATA_DIR']).remove_character(name)
        except OSError as e:
            logger.warning("vector store cleanup failed for %s: %s", name, e)
        return jsonify({"status": "success"})

    # --- Embedding vector store (task-91) ---------------------------------
    # The browser embeds memory text via its configured OpenAI-compatible
    # endpoint (keys never leave the browser) and POSTs finished vectors here.
    # Keys are "<Character>::<memory_id>".

    @app.route('/api/memory/embeddings', methods=['POST'])
    def upsert_memory_embeddings():
        data = request.get_json(force=True) or {}
        items = data.get("items")
        if not isinstance(items, list) or not items:
            return jsonify({"error": "items must be a non-empty list"}), 400
        store = VectorStore(app.config['DATA_DIR'])
        try:
            written = store.upsert(
                items, model=data.get("model") or "", dims=int(data.get("dims") or 0))
        except ValueError as e:
            return jsonify({"error": str(e)}), 409
        except (TypeError, AttributeError) as e:
            return jsonify({"error": f"bad payload: {e}"}), 400
        return jsonify({"status": "success", "written": written,
                        "stats": store.stats()})

    @app.route('/api/memory/embeddings/search', methods=['POST'])
    def search_memory_embeddings():
        data = request.get_json(force=True) or {}
        vector = data.get("vector")
        if not isinstance(vector, list) or not vector:
            return jsonify({"error": "vector must be a non-empty list"}), 400
        store = VectorStore(app.config['DATA_DIR'])
        results = store.search(
            vector, character=data.get("character") or None,
            k=int(data.get("k") or 5))
        return jsonify({"results": results, "stats": store.stats()})

    @app.route('/api/memory/embeddings/stats', methods=['GET'])
    def embeddings_stats():
        return jsonify(VectorStore(app.config['DATA_DIR']).stats())

    @app.route('/api/players/<name>/memories/retrieve', methods=['POST'])
    def retrieve_player_memories(name):
        """Score and return the most relevant memories for a query.

        Port of memory-store.js retrieve(): keyword overlap + recency +
        importance + entity boost scoring.
        """
        player = app.world.players.get(name)
        if not player:
            return jsonify({"error": "Player not found"}), 404
        data = request.get_json(force=True)
        query = data.get("query", "")
        max_results = data.get("max_results", 5)
        entity_boost = data.get("entity_boost", False)
        current_area_id = data.get("current_area_id", "")

        memories = getattr(player, 'memories', [])
        if not memories:
            return jsonify({"memories": []})

        query_lower = query.lower()
        query_words = set(query_lower.split()) if query_lower else set()

        def _score(m):
            text_lower = (m.get("text") or "").lower()
            # Keyword overlap
            word_overlap = sum(1 for w in query_words if w in text_lower)
            kw_score = word_overlap / len(query_words) if query_words else 0
            # Recency (decay over 500 ticks)
            tick = m.get("tick", 0)
            recency = max(0.0, 1.0 - tick / 500)
            # Importance
            importance = (m.get("importance") or 5) / 10
            # Entity boost
            eboost = 0.0
            if entity_boost and current_area_id:
                entity_ids = m.get("entity_ids") or []
                if current_area_id in entity_ids:
                    eboost = 2.0
            return (kw_score * 3) + (recency * 2) + (importance * 2) + eboost

        scored = [(_score(m), m) for m in memories]
        scored = [(s, m) for s, m in scored if s > 0.5]
        scored.sort(key=lambda x: x[0], reverse=True)

        result = [m for _, m in scored[:max_results]]
        return jsonify({"memories": result})

    @app.route('/api/players/<name>/memories/reflect', methods=['POST'])
    def reflect_player_memories(name):
        """Store reflection insights as high-importance memories.

        The frontend calls the LLM to summarize important memories, then
        POSTs the resulting insight strings here. This endpoint stores
        them as type=reflection, importance=8 memories.
        """
        player = app.world.players.get(name)
        if not player:
            return jsonify({"error": "Player not found"}), 404
        data = request.get_json(force=True)
        insights = data.get("insights", [])
        tick = data.get("tick", app.world.time_ticks)

        stored = 0
        for insight in insights:
            if isinstance(insight, str) and len(insight) > 10:
                entry = {
                    "id": f"mem_{int(time.time()*1000)}_{random.randint(0,999)}",
                    "text": insight,
                    "tick": tick,
                    "timestamp": time.time(),
                    "importance": 8,
                    "type": "reflection",
                    "location": "",
                    "entity_ids": [],
                    "embedding": None,
                    "tags": [],
                    "source": "auto"
                }
                player.memories.append(entry)
                stored += 1
        return jsonify({"status": "success", "stored": stored})

    @app.route('/api/players/<name>/memories/spatial', methods=['GET'])
    def get_spatial_routes(name):
        """Return KNOWN ROUTES FROM HERE block for a player.

        BFS from the player's current area through the real graph,
        filtered to visited_areas only.
        """
        player = app.world.players.get(name)
        if not player:
            return jsonify({"error": "Player not found"}), 404
        current_area = getattr(player, 'current_area', None)
        visited = getattr(player, 'visited_areas', set())
        sm = SpatialMemory(app.world.graph)
        block = sm.build_known_routes(current_area, visited)
        return jsonify({"spatial": block})

    @app.route('/api/players/<name>/memories/suppress', methods=['POST'])
    def suppress_player_memories(name):
        player = app.world.players.get(name)
        if not player:
            return jsonify({"error": "Player not found"}), 404
        data = request.get_json(force=True) or {}
        tags = data.get("tags", [])
        keywords = data.get("keywords", "")
        duration = int(data.get("duration", 1))
        scope = data.get("scope", "self")
        suppressed = player.suppress_memory(tags=tags, keywords=keywords, duration=duration, scope=scope)
        return jsonify({"status": "success", "suppressed": suppressed})

    @app.route('/api/players/<name>/memories/unblock', methods=['POST'])
    def unblock_player_memories(name):
        player = app.world.players.get(name)
        if not player:
            return jsonify({"error": "Player not found"}), 404
        data = request.get_json(force=True) or {}
        tags = data.get("tags", [])
        keywords = data.get("keywords", "")
        scope = data.get("scope", "self")
        unblocked = player.unblock_memory(tags=tags, keywords=keywords, scope=scope)
        return jsonify({"status": "success", "unblocked": unblocked})

    @app.route('/api/players/<name>/memories/clear-expired', methods=['POST'])
    def clear_expired_suppressions(name):
        player = app.world.players.get(name)
        if not player:
            return jsonify({"error": "Player not found"}), 404
        data = request.get_json(force=True) or {}
        current_tick = int(data.get("current_tick", app.world.time_ticks))
        player.clear_expired_suppressions(current_tick)
        return jsonify({"status": "success"})
