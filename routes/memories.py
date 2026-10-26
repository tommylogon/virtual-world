import logging
import math
import re
import time
import random
from flask import Flask, g, request, jsonify
from logger import setup_logger
from engine.spatial_memory import SpatialMemory, known_route_areas
from engine.vector_store import VectorStore
from engine import memory_dynamics

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


def _is_reencounter(a, b, threshold=0.75):
    """True if ``b`` re-encounters ``a``: near-verbatim at ANY tick distance,
    about the same subject (task-686). A re-encounter reinforces the original
    instead of appending a duplicate episode."""
    a_entities = {str(e) for e in (a.get("entity_ids") or []) if e}
    b_entities = {str(e) for e in (b.get("entity_ids") or []) if e}
    if a_entities and b_entities and not (a_entities & b_entities):
        return False
    a = _normalize_tokens(a.get("text", ""))
    b = _normalize_tokens(b.get("text", ""))
    if not a or not b:
        return False
    inter = len(a & b)
    union = len(a | b)
    if union == 0:
        return False
    return (inter / union) >= threshold


def _resolve_entity_ids(world, names):
    """Graph node ids for display names (exact, case-insensitive). Names that
    resolve to nothing are dropped  -  an unresolved name never becomes a key."""
    graph = getattr(world, "graph", None)
    nodes = getattr(graph, "nodes", None) or {}
    by_name = {}
    for node_id, node in nodes.items():
        node_name = str(getattr(node, "name", "") or "").strip().lower()
        if node_name:
            by_name.setdefault(node_name, node_id)
    players = getattr(world, "players", None) or {}
    for pname in players:
        key = str(pname or "").strip().lower()
        if key and key not in by_name:
            try:
                pid = world._player_node_id(pname)
            except Exception:
                pid = "player_" + re.sub(r"\s+", "_", key)
            by_name[key] = pid
    out = []
    for name in (names or []):
        want = str(name or "").strip().lower()
        if not want:
            continue
        node_id = by_name.get(want) or (want if want in nodes else None)
        if node_id and node_id not in out:
            out.append(node_id)
    return out


def _resolve_person_name(app, actor_name, who):
    """Resolve a person handle or name to a canonical player name, or None."""
    raw = str(who or "").strip()
    if not raw:
        return None
    resolved = None
    try:
        from routes.player_ops import _resolve_other
        resolved = _resolve_other(app, actor_name, raw)
    except Exception:
        resolved = None
    if resolved:
        return resolved
    players = getattr(getattr(app, "world", None), "players", None) or {}
    raw_lower = raw.lower()
    for pname in players:
        if pname != actor_name and str(pname).strip().lower() == raw_lower:
            return pname
    return None


def _apply_relationship_deltas(app, player, actor_name, entry, raw_deltas, raw_emotions, tick, ensure_rel=True):
    """Normalize and apply interpersonal feeling deltas onto a memory entry.

    Supports both `relationship_deltas: [{who, why, data: {dim: delta}}]` and
    legacy `emotions: {who, why, data: {dim: delta}}`. Resolves each `who` to a
    canonical player name, ensures the relationship exists on `player` when
    `ensure_rel` is True, adds `rel:<Name>` to `entry["tags"]`, and links the
    person's entity ID in `entry["entity_ids"]`.
    """
    candidates = []
    if isinstance(raw_deltas, list):
        for item in raw_deltas:
            if isinstance(item, dict) and item.get("who"):
                candidates.append(item)
    if not candidates and isinstance(raw_emotions, dict) and raw_emotions.get("who"):
        candidates.append(raw_emotions)

    tags = list(entry.get("tags") or [])
    entity_ids = list(entry.get("entity_ids") or [])
    cleaned = []
    for item in candidates:
        resolved_who = _resolve_person_name(app, actor_name, item.get("who"))
        if not resolved_who or resolved_who == actor_name:
            continue
        raw_data = item.get("data") if isinstance(item.get("data"), dict) else {}
        clean_data = {}
        for k, v in raw_data.items():
            try:
                num = float(v)
            except (TypeError, ValueError):
                continue
            if abs(num) > 1e-6:
                clean_data[str(k).strip().lower()] = num
        block = {
            "who": resolved_who,
            "why": str(item.get("why") or "").strip(),
            "data": clean_data,
        }
        cleaned.append(block)
        reltag = "rel:" + resolved_who
        if not any(str(t).lower() == reltag.lower() for t in tags):
            tags.append(reltag)
        for pid in _resolve_entity_ids(app.world, [resolved_who]):
            if pid not in entity_ids:
                entity_ids.append(pid)
        if ensure_rel and player is not None:
            try:
                from engine.relationships import ensure_relationship
                ensure_relationship(player, resolved_who, tick=int(tick or 0))
            except Exception:
                pass

    entry["tags"] = tags
    entry["entity_ids"] = entity_ids
    if cleaned:
        entry["relationship_deltas"] = cleaned
        entry["emotions"] = dict(cleaned[0])
    elif isinstance(raw_emotions, dict):
        entry["emotions"] = raw_emotions
    return cleaned


def _profile_summary_dict(profile):
    return {
        "trust": round(float(profile.get("trust", 0) or 0), 2),
        "fear": round(float(profile.get("fear", 0) or 0), 2),
        "attraction": round(float(profile.get("attraction", 0) or 0), 2),
        "disgust": round(float(profile.get("disgust", 0) or 0), 2),
        "respect": round(float(profile.get("respect", 0) or 0), 2),
        "familiarity": round(float(profile.get("familiarity", 0) or 0), 2),
        "closeness": round(float(profile.get("closeness", 0) or 0), 2),
        "consent": round(float(profile.get("consent", 0) or 0), 3),
        "role": profile.get("role", "stranger"),
        "summary": profile.get("summary", ""),
        "has_signal": bool(profile.get("_has_signal")),
    }


def _preview_contradictions(player, candidate_entry):
    """Run contradiction detection against shallow-copied pool memories without mutating player."""
    text = str(candidate_entry.get("text") or "").strip()
    if not text:
        return []
    cand = dict(candidate_entry)
    cand["id"] = str(cand.get("id") or "_preview_candidate")
    cand["contradicts"] = list(cand.get("contradicts") or [])
    cand["entity_ids"] = list(cand.get("entity_ids") or [])
    pool_copy = []
    for m in (getattr(player, "memories", None) or []):
        if not isinstance(m, dict):
            continue
        mc = dict(m)
        mc["contradicts"] = list(m.get("contradicts") or [])
        mc["entity_ids"] = list(m.get("entity_ids") or [])
        pool_copy.append(mc)
    try:
        linked = memory_dynamics.detect_contradiction(cand, pool_copy)
    except Exception:
        linked = []
    return [
        {
            "id": m.get("id"),
            "text": m.get("text", ""),
            "tick": m.get("tick", 0),
            "confidence": m.get("confidence", 0.7),
        }
        for m in linked
    ]


def _preview_relationships(player, candidate_entry):
    """Compute before/after derived relationship profiles for a candidate memory without mutating player."""
    from engine.derive import derive_person_profile

    deltas = candidate_entry.get("relationship_deltas") or []
    if not deltas and isinstance(candidate_entry.get("emotions"), dict):
        deltas = [candidate_entry["emotions"]]
    seen = set()
    targets = []
    for d in deltas:
        if not isinstance(d, dict):
            continue
        who = str(d.get("who") or "").strip()
        if who and who.lower() not in seen:
            seen.add(who.lower())
            targets.append(who)
    if not targets:
        return []

    class _PlayerProxy:
        def __init__(self, real_player, extra_memory):
            self.name = getattr(real_player, "name", "")
            self.relationships = getattr(real_player, "relationships", {}) or {}
            self.player_manager = getattr(real_player, "player_manager", None)
            self.memories = list(getattr(real_player, "memories", []) or []) + [extra_memory]
            self._real = real_player

        def emotions_map(self):
            if hasattr(self._real, "emotions_map"):
                return self._real.emotions_map()
            return {}

    proxy = _PlayerProxy(player, candidate_entry)
    out = []
    for who in targets:
        before = derive_person_profile(player, who)
        after = derive_person_profile(proxy, who)
        out.append({
            "who": who,
            "before": _profile_summary_dict(before),
            "after": _profile_summary_dict(after),
        })
    return out


def _character_birth_bounds(app, player, name):
    """Resolve the character's birth_tick, dd.mm.yyyy birthday, and age."""
    birth_tick = None
    birthday = None
    age = None
    try:
        from engine import character_appearance as ca
        from engine import lifecycle as _lifecycle
        node = app.world.graph.get_node(app.world._player_node_id(name))
        ident = (ca.identity(node) if node is not None else {}) or {}
        birthday = ident.get("birthday")
        age = ident.get("age")
        birth_tick = _lifecycle.ensure_birth_tick(player, app.world, node)
    except Exception:
        birth_tick = getattr(player, "birth_tick", None)
    return {
        "birth_tick": int(birth_tick) if birth_tick is not None else None,
        "birthday": birthday,
        "age": age,
    }


def _format_birth_gate_error(name, requested_tick, bounds):
    b_tick = bounds.get("birth_tick")
    bday = bounds.get("birthday")
    age = bounds.get("age")
    parts = [f"tick {b_tick}"]
    if bday:
        parts.append(f"birthday {bday}")
    if age is not None:
        try:
            parts.append(f"age {float(age):g}")
        except (TypeError, ValueError):
            pass
    detail = ", ".join(parts)
    return f"Cannot place memory at tick {requested_tick}: {name} was not born until {detail}."


def _build_persona_summary(app, player, name):
    """Assemble the character's persona summary from node record and Player fields."""
    bounds = _character_birth_bounds(app, player, name)
    summary = {
        "base_description": str(getattr(player, "base_description", "") or getattr(player, "description", "") or "").strip(),
        "personality": str(getattr(player, "personality", "") or "").strip(),
        "birthday": bounds["birthday"],
        "age": bounds["age"],
        "birth_tick": bounds["birth_tick"],
        "values": [],
        "fears": list(getattr(player, "fear_tags", []) or []),
        "likes": list(getattr(player, "interest_tags", []) or []),
        "dislikes": [],
        "biography": "",
        "goals": [
            str(g.get("what") or "").strip()
            for g in (getattr(player, "goals", []) or [])
            if isinstance(g, dict) and g.get("what")
        ],
    }
    try:
        from engine import character_appearance as ca
        node = app.world.graph.get_node(app.world._player_node_id(name))
        if node is not None:
            props = getattr(node, "properties", None) or {}
            if props.get("base_description"):
                summary["base_description"] = str(props["base_description"]).strip()
            if props.get("personality"):
                summary["personality"] = str(props["personality"]).strip()
            pers = ca.personality(node) or {}
            narr = ca.narrative(node) or {}
            if isinstance(pers.get("values"), list) and pers["values"]:
                summary["values"] = [str(x) for x in pers["values"] if x]
            if isinstance(pers.get("fears"), list) and pers["fears"]:
                summary["fears"] = list(dict.fromkeys(summary["fears"] + [str(x) for x in pers["fears"] if x]))
            if isinstance(pers.get("likes"), list) and pers["likes"]:
                summary["likes"] = list(dict.fromkeys(summary["likes"] + [str(x) for x in pers["likes"] if x]))
            if isinstance(pers.get("dislikes"), list) and pers["dislikes"]:
                summary["dislikes"] = [str(x) for x in pers["dislikes"] if x]
            if narr.get("backstory"):
                summary["biography"] = str(narr["backstory"]).strip()
    except Exception:
        pass
    return summary


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
        entity_ids = list(data.get("entity_ids", []) or [])
        if isinstance(data.get("entities"), list) and data["entities"]:
            for eid in _resolve_entity_ids(app.world, data["entities"]):
                if eid not in entity_ids:
                    entity_ids.append(eid)
        entry = {
            "id": data.get("id", f"mem_{int(time.time()*1000)}_{random.randint(0,999)}"),
            "text": data.get("text", ""),
            "tick": int(data.get("tick", app.world.time_ticks)),
            "timestamp": data.get("timestamp", time.time()),
            "importance": data.get("importance", 5),
            "type": data.get("type", "observation"),
            "location": data.get("location", ""),
            "entity_ids": entity_ids,
            "embedding": data.get("embedding"),
            "tags": tags,
            "emotion": data.get("emotion"),
            "emotions": emotions,
            "memory_emotions": data.get("memory_emotions", []),
            "salience_override": data.get("salience_override", data.get("salience", 0)),
            "source": data.get("source", "auto")
        }
        bounds = _character_birth_bounds(app, player, name)
        if bounds["birth_tick"] is not None and entry["tick"] < bounds["birth_tick"]:
            return jsonify({
                "error": _format_birth_gate_error(name, entry["tick"], bounds),
                "birth_tick": bounds["birth_tick"],
                "birthday": bounds["birthday"],
            }), 400
        # task-350 / task-730: a memory can carry structured feelings about one
        # or more people (`relationship_deltas` or `emotions`). Resolve each
        # handle to the canonical player name, stamp `rel:<Name>`, and link the
        # entity id. Guessing is blocked: unresolved handles are dropped.
        _apply_relationship_deltas(
            app, player, name, entry,
            data.get("relationship_deltas"), emotions, entry["tick"],
            ensure_rel=True,
        )
        # task-685: optional dynamics fields  -  client-provided values win,
        # ensure_dynamics fills only what is missing (old clients unaffected).
        for key in ("category", "confidence", "activation", "reflection_depth",
                    "source_memory_ids", "contradicts", "last_recalled_tick"):
            if data.get(key) is not None:
                entry[key] = data[key]
        memory_dynamics.ensure_dynamics(entry)
        # task-730: optional natural age-decay simulation for backdated memories.
        if data.get("simulate_age_decay") and data.get("activation") is None:
            current_tick = int(getattr(app.world, "time_ticks", 0) or 0)
            elapsed = max(0, current_tick - int(entry.get("tick", 0) or 0))
            if elapsed > 0 and str(entry.get("source", "")) not in memory_dynamics.NON_DECAYING_SOURCES:
                try:
                    from engine.runtime_config import config as runtime_config
                    rate = float(runtime_config.get(memory_dynamics.DECAY_RATE_KEY, 0.002) or 0.002)
                except Exception:
                    rate = 0.002
                mult = 0.5 if str(entry.get("source", "")) in memory_dynamics.HALF_DECAY_SOURCES else 1.0
                step = elapsed * rate * mult * memory_dynamics.decay_resistance(entry)
                entry["activation"] = round(max(0.15, 1.0 - step), 4)
        # task-689: structural contradiction marking runs on the HTTP write
        # path too, not only Player.add_memory. Guarded: a write must never
        # fail because detection did.
        try:
            memory_dynamics.detect_contradiction(entry, player.memories)
        except Exception:
            pass

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

            # task-686: re-encounter reinforcement  -  the same thing happening
            # again days later strengthens the original memory instead of
            # piling up near-identical episodes.
            for existing in player.memories:
                if _is_reencounter(existing, entry):
                    memory_dynamics.reinforce(existing, tick=entry.get("tick"))
                    if (entry.get("importance") or 0) > (existing.get("importance") or 0):
                        existing["importance"] = entry.get("importance", existing.get("importance", 5))
                    existing["tags"] = list(set(existing.get("tags", [])) | set(entry.get("tags", [])))
                    return jsonify({"status": "success", "entry": existing,
                                    "deduped": True, "reinforced": True}), 200

        player.memories.append(entry)
        derived_entry = None
        derived_text = str(data.get("derived_expectation") or "").strip()
        if len(derived_text) > 5:
            derived_entry = {
                "id": f"{entry['id']}_exp",
                "text": derived_text,
                "tick": entry["tick"],
                "timestamp": entry["timestamp"],
                "importance": max(4, min(10, int(entry.get("importance", 5) or 5) - 1)),
                "type": "expectation",
                "category": "procedural",
                "location": entry.get("location", ""),
                "entity_ids": list(entry.get("entity_ids") or []),
                "embedding": None,
                "tags": ["expectation"],
                "source": entry.get("source", "manual"),
                "confidence": entry.get("confidence", 0.9),
                "reflection_depth": 1,
                "source_memory_ids": [entry["id"]],
                "contradicts": [],
            }
            memory_dynamics.ensure_dynamics(derived_entry)
            player.memories.append(derived_entry)
        resp = {"status": "success", "entry": entry}
        if derived_entry is not None:
            resp["derived_entry"] = derived_entry
        return jsonify(resp), 201

    @app.route('/api/players/<name>/memories/entry/<entry_id>', methods=['POST'])
    def update_player_memory(name, entry_id):
        player = app.world.players.get(name)
        if not player:
            return jsonify({"error": "Player not found"}), 404
        data = request.get_json(force=True)
        if "tick" in data and data["tick"] is not None:
            bounds = _character_birth_bounds(app, player, name)
            req_tick = int(data["tick"])
            if bounds["birth_tick"] is not None and req_tick < bounds["birth_tick"]:
                return jsonify({
                    "error": _format_birth_gate_error(name, req_tick, bounds),
                    "birth_tick": bounds["birth_tick"],
                    "birthday": bounds["birthday"],
                }), 400
        for entry in player.memories:
            if entry.get("id") == entry_id:
                previous_contra = list(entry.get("contradicts") or [])
                for key in ["text", "type", "importance", "location", "tags",
                            "tick", "source", "entity_ids", "emotion", "emotions",
                            "relationship_deltas", "memory_emotions",
                            "salience_override", "timestamp",
                            "category", "confidence", "activation",
                            "reflection_depth", "source_memory_ids", "contradicts"]:
                    if key in data:
                        entry[key] = data[key]
                if "relationship_deltas" in data or "emotions" in data:
                    _apply_relationship_deltas(
                        app, player, name, entry,
                        data.get("relationship_deltas"), data.get("emotions"),
                        entry.get("tick", getattr(app.world, "time_ticks", 0)),
                        ensure_rel=True,
                    )
                memory_dynamics.ensure_dynamics(entry)
                # task-691: a contradicts link is a mutual relation  -  the
                # editor edits one side, so sync the other side here (idempotent).
                if "contradicts" in data:
                    by_id = {m.get("id"): m for m in player.memories}
                    for other_id in entry.get("contradicts") or []:
                        other = by_id.get(other_id)
                        if other is not None:
                            memory_dynamics.link(entry, other)
                    for other_id in previous_contra:
                        if other_id not in (entry.get("contradicts") or []):
                            other = by_id.get(other_id)
                            if other is not None and isinstance(other.get("contradicts"), list):
                                other["contradicts"] = [i for i in other["contradicts"] if i != entry_id]
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
        """Score and return the memories relevant to the current situation.

        Retrieval 2.0 (task-690): one multi-signal scorer  -  keyword overlap,
        entity-graph match, exponential recency, effective importance
        (task-685: availability × confidence modulate the base), and emotion
        match  -  with suppressed/superseded entries excluded (parity with
        ``Player.get_relevant_memories``). When ``structured`` is set, the
        same memories are also grouped as events / beliefs / social /
        expectations so the prompt can present a character model, not event
        soup. Belief/semantic memories matching the query entities get
        guaranteed seat time in the top slots.

        Recalled memories are reinforced (task-686) unless ``reinforce`` is
        false  -  Agent Lens previews must not mutate the character.
        """
        player = app.world.players.get(name)
        if not player:
            return jsonify({"error": "Player not found"}), 404
        data = request.get_json(force=True) or {}
        query = str(data.get("query", "") or "")
        max_results = int(data.get("max_results", 5) or 5)
        entity_boost = data.get("entity_boost", False)
        current_area_id = data.get("current_area_id", "")
        structured = bool(data.get("structured"))
        do_reinforce = data.get("reinforce", True)
        tick = int(data.get("tick", getattr(app.world, "time_ticks", 0) or 0) or 0)
        half_life = float(data.get("recency_half_life", 300) or 300)

        memories = getattr(player, 'memories', [])
        if not memories:
            return jsonify({"memories": [], **({"groups": {}} if structured else {})})

        query_lower = query.lower()
        query_words = set(query_lower.split()) if query_lower else set()

        # Query-side entities: explicit list first, else entities named in the
        # query resolve against the graph so relationship history beats noise.
        query_entities = {str(e) for e in (data.get("entities") or []) if e}
        if not query_entities:
            query_entities = {e.lower() for e in _resolve_entity_ids(
                app.world, list(query_words))}

        query_emotions = {str(e).lower() for e in (data.get("emotions") or [])}

        def _active(m):
            if m.get("superseded_by"):
                return False
            for s in (m.get("suppressions") or []):
                until = s.get("until_tick")
                if until is None or int(until or 0) > tick:
                    return False
            return True

        def _emotion_labels(m):
            labels = []
            for e in (m.get("memory_emotions") or []):
                if isinstance(e, dict) and e.get("label"):
                    labels.append(str(e["label"]).lower())
            if isinstance(m.get("emotion"), dict) and m["emotion"].get("label"):
                labels.append(str(m["emotion"]["label"]).lower())
            return labels

        def _score(m):
            text_lower = (m.get("text") or "").lower()
            # Keyword overlap
            word_overlap = sum(1 for w in query_words if w in text_lower)
            kw_score = word_overlap / len(query_words) if query_words else 0
            # Recency: exponential with a half-life, never negative
            # (the old linear 1 - tick/500 went negative past tick 500).
            age = max(0, tick - int(m.get("tick", 0) or 0))
            recency = 0.5 ** (age / half_life) if half_life > 0 else 0.0
            # Effective importance: availability × confidence modulate base.
            weight = memory_dynamics.effective_importance(m) / 10
            # Entity boosts: current area (legacy behavior) + query entities.
            eboost = 0.0
            entity_ids = m.get("entity_ids") or []
            if entity_boost and current_area_id and current_area_id in entity_ids:
                eboost += 2.0
            if query_entities and {str(e).lower() for e in entity_ids} & query_entities:
                eboost += 2.5
            # Emotion match: a feeling named in the query lifts memories
            # encoded with that feeling.
            emobooth = 0.0
            if query_emotions and set(_emotion_labels(m)) & query_emotions:
                emobooth += 1.5
            return (kw_score * 3) + (recency * 2) + (weight * 2) + eboost + emobooth

        candidates = [m for m in memories if (m.get("text") or "").strip() and _active(m)]
        scored = [( _score(m), m) for m in candidates]
        scored = [(s, m) for s, m in scored if s > 0.3]
        scored.sort(key=lambda x: x[0], reverse=True)

        result = []
        for s, m in scored[:max_results]:
            entry = dict(m)  # shallow copy so we don't mutate stored data
            entry["score"] = round(s, 3)
            result.append(entry)

        # Seat-time guarantee: conclusions the character already holds get a
        # place even when fresh episodic matches outscore them.
        if query_entities:
            picked = {m.get("id") for m in result}
            model = [(s, m) for s, m in scored
                     if m.get("id") not in picked
                     and m.get("category", memory_dynamics.category_for(m)) in
                     (memory_dynamics.BELIEF, memory_dynamics.SEMANTIC,
                      memory_dynamics.SOCIAL)
                     and {str(e).lower() for e in (m.get("entity_ids") or [])} & query_entities]
            for s, m in model[:2]:
                entry = dict(m)
                entry["score"] = round(s, 3)
                result.append(entry)

        if do_reinforce:
            for m in result:
                stored = next((c for c in memories if c.get("id") == m.get("id")), None)
                if stored is not None:
                    memory_dynamics.reinforce(stored, tick=tick)

        if structured:
            groups = {"events": [], "beliefs": [], "social": [], "expectations": []}
            for m in result:
                category = m.get("category") or memory_dynamics.category_for(m)
                if category == memory_dynamics.SOCIAL:
                    groups["social"].append(m)
                elif category in (memory_dynamics.BELIEF, memory_dynamics.SEMANTIC):
                    groups["beliefs"].append(m)
                elif category == memory_dynamics.PROCEDURAL:
                    groups["expectations"].append(m)
                else:
                    groups["events"].append(m)
            return jsonify({"memories": result, "groups": groups})
        return jsonify({"memories": result})

    @app.route('/api/players/<name>/memories/reinforce', methods=['POST'])
    def reinforce_player_memories(name):
        """Stamp recall reinforcement on specific memories (task-686).

        The client's semantic (vector) recall merges results outside the
        scoring endpoint, so it POSTs the hit ids here to keep the
        reinforcement loop honest. Fire-and-forget from the caller's side.
        """
        player = app.world.players.get(name)
        if not player:
            return jsonify({"error": "Player not found"}), 404
        data = request.get_json(force=True) or {}
        ids = {str(i) for i in (data.get("ids") or []) if i}
        tick = int(data.get("tick", getattr(app.world, "time_ticks", 0) or 0) or 0)
        reinforced = 0
        for m in getattr(player, "memories", []):
            if m.get("id") in ids:
                memory_dynamics.reinforce(m, tick=tick)
                reinforced += 1
        return jsonify({"status": "success", "reinforced": reinforced})

    @app.route('/api/players/<name>/memories/reflect', methods=['POST'])
    def reflect_player_memories(name):
        """Store reflection insights as derived memories (task-688).

        Two payload shapes are accepted:

        Legacy  -  ``{"insights": ["some sentence", ...]}``: stored as
        type=reflection, importance=8 memories exactly as before.

        Structured  -  ``{"insights": [{belief, about[], confidence, emotional,
        behavior, relationship{who, dim, delta}}], "source_memory_ids": [...],
        "force": bool}``: each belief is stored as a category=belief memory
        stamped ``reflection_depth: 1`` and the ids it was derived from; a
        ``behavior`` field becomes a category=procedural expectation memory;
        a ``relationship`` becomes ``rel:<name>`` + ``<dim>:<delta>`` tags,
        which is exactly what ``engine/derive.py`` folds into the per-person
        profile  -  one writer, no second store.

        Depth guard: when every source memory already carries
        ``reflection_depth >= 1``, the insight is rejected with 409 unless
        ``force``  -  reflections of reflections is how an LLM ends up
        summarizing its own summaries.
        """
        player = app.world.players.get(name)
        if not player:
            return jsonify({"error": "Player not found"}), 404
        data = request.get_json(force=True)
        insights = data.get("insights", [])
        tick = data.get("tick", app.world.time_ticks)
        force = bool(data.get("force"))
        source_ids = [str(s) for s in (data.get("source_memory_ids") or []) if s]

        stored = 0

        def _append(entry):
            memory_dynamics.ensure_dynamics(entry)
            player.memories.append(entry)
            return entry

        for insight in insights:
            if isinstance(insight, str):
                if len(insight) > 10:
                    player.memories.append({
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
                    })
                    stored += 1
                continue
            if not isinstance(insight, dict):
                continue
            belief = str(insight.get("belief", "") or "").strip()
            if len(belief) <= 10:
                continue
            sources = [m for m in player.memories if m.get("id") in source_ids]
            if source_ids and sources and not force and all(
                    int(m.get("reflection_depth", 0) or 0) >= 1 for m in sources):
                return jsonify({"error": "reflection depth guard: insights may only "
                                        "be derived from raw experience (pass force "
                                        "to override)"}), 409

            tags = ["reflection", "belief"]
            entity_ids = _resolve_entity_ids(app.world, insight.get("about") or [])
            confidence = insight.get("confidence")
            try:
                confidence = max(0.05, min(1.0, float(confidence))) if confidence is not None else 0.7
            except (TypeError, ValueError):
                confidence = 0.7
            emotional = insight.get("emotional") if isinstance(insight.get("emotional"), dict) else None

            base_id = f"mem_{int(time.time()*1000)}_{random.randint(0,999)}"
            _append({
                "id": base_id,
                "text": belief,
                "tick": tick,
                "timestamp": time.time(),
                "importance": 8,
                "type": "reflection",
                "category": "belief",
                "location": "",
                "entity_ids": entity_ids,
                "embedding": None,
                "tags": tags,
                "memory_emotions": ([{"label": str(emotional.get("label", ""))[:40],
                                      "intensity": max(1, min(10, int(emotional.get("intensity", 5) or 5)))}]
                                    if emotional and emotional.get("label") else []),
                "source": "auto",
                "confidence": confidence,
                "reflection_depth": 1,
                "source_memory_ids": list(source_ids),
                "contradicts": [],
            })
            stored += 1

            # The expectation of changed behaviour is its own memory kind.
            behavior = str(insight.get("behavior", "") or "").strip()
            if len(behavior) > 10:
                _append({
                    "id": f"{base_id}_b",
                    "text": behavior,
                    "tick": tick,
                    "timestamp": time.time(),
                    "importance": 7,
                    "type": "expectation",
                    "category": "procedural",
                    "location": "",
                    "entity_ids": list(entity_ids),
                    "embedding": None,
                    "tags": ["expectation"],
                    "source": "auto",
                    "confidence": confidence,
                    "reflection_depth": 1,
                    "source_memory_ids": list(source_ids),
                    "contradicts": [],
                })

            # A relationship conclusion moves the derived per-person profile by
            # writing rel:<name> + <dim>:<delta> tags  -  the exact convention
            # engine/derive.py reduces (task-350). Unresolved handles are
            # dropped, never guessed.
            relationship = insight.get("relationship")
            if isinstance(relationship, dict) and relationship.get("who"):
                who = str(relationship.get("who")).strip()
                dim = str(relationship.get("dim", "")).strip().lower()
                try:
                    delta = float(relationship.get("delta", 0) or 0)
                except (TypeError, ValueError):
                    delta = 0.0
                from engine.derive import DIMS, EMOTION_DELTA_MAX
                if dim in DIMS and delta:
                    delta = max(-EMOTION_DELTA_MAX, min(EMOTION_DELTA_MAX, delta))
                    reltag = "rel:" + who
                    dimtag = f"{dim}:{int(delta) if float(delta).is_integer() else round(delta, 2)}"
                    _append({
                        "id": f"{base_id}_r",
                        "text": belief,
                        "tick": tick,
                        "timestamp": time.time(),
                        "importance": 7,
                        "type": "reflection",
                        "category": "social",
                        "location": "",
                        "entity_ids": _resolve_entity_ids(app.world, [who]),
                        "embedding": None,
                        "tags": ["reflection", reltag, dimtag],
                        "source": "auto",
                        "confidence": confidence,
                        "reflection_depth": 1,
                        "source_memory_ids": list(source_ids),
                        "contradicts": [],
                    })
        return jsonify({"status": "success", "stored": stored})

    @app.route('/api/players/<name>/memories/people', methods=['GET'])
    def get_memory_people(name):
        """Derived per-person profiles (task-691 stage 3).

        For everyone this character holds a ``rel:<name>`` memory about, run
        engine/derive.py  -  the SAME reducer the prompt's relationship block
        uses  -  and return the resulting dimensions. No new state: the numbers
        are computed from memories + the relationship seed on every read.
        """
        player = app.world.players.get(name)
        if not player:
            return jsonify({"error": "Player not found"}), 404
        from engine.derive import derive_person_profile
        seen = set()
        people = []
        for memory in getattr(player, 'memories', []):
            for tag in (memory.get('tags') or []):
                tag = str(tag)
                if not tag.lower().startswith('rel:'):
                    continue
                who = tag[4:].strip()
                key = who.lower()
                if not who or key in seen:
                    continue
                seen.add(key)
                profile = derive_person_profile(player, who)
                count = sum(
                    1 for m in getattr(player, 'memories', [])
                    for t in (m.get('tags') or [])
                    if str(t).lower() == 'rel:' + key)
                people.append({
                    "name": who,
                    "memory_count": count,
                    "profile": {
                        "trust": profile.get("trust", 0),
                        "fear": profile.get("fear", 0),
                        "attraction": profile.get("attraction", 0),
                        "disgust": profile.get("disgust", 0),
                        "respect": profile.get("respect", 0),
                        "familiarity": profile.get("familiarity", 0),
                        "consent": profile.get("consent", 0),
                        "role": profile.get("role", "stranger"),
                        "summary": profile.get("summary", ""),
                        "has_signal": bool(profile.get("_has_signal")),
                    },
                })
        people.sort(key=lambda p: (-p["memory_count"], p["name"]))
        return jsonify({"people": people})

    @app.route('/api/players/<name>/memories/context', methods=['POST'])
    def get_memory_context(name):
        """Grounding and dry-run preview bundle for the Memory Weaver & Editor (task-730).

        Read-only (`g.no_broadcast = True`): returns the character's persona
        summary, current mood, relevant recalled memories (`reinforce=False`),
        derived per-person profiles, world entities, and non-mutating previews
        of contradiction links and relationship profile shifts for an optional
        `candidate` memory draft.
        """
        g.no_broadcast = True
        player = app.world.players.get(name)
        if not player:
            return jsonify({"error": "Player not found"}), 404
        data = request.get_json(silent=True) or {}
        query = str(data.get("query", "") or "").strip()
        candidate_raw = data.get("candidate") if isinstance(data.get("candidate"), dict) else {}
        current_tick = int(getattr(app.world, "time_ticks", 0) or 0)
        tm = getattr(app.world, "tick_manager", None)
        mpt_attr = getattr(tm, "minutes_per_tick", 1)
        try:
            minutes_per_tick = int((mpt_attr() if callable(mpt_attr) else mpt_attr) or 1)
        except Exception:
            minutes_per_tick = 1

        from engine.derive import derive_person_profile

        # 1. Persona summary & mood
        persona_summary = _build_persona_summary(app, player, name)
        current_emotion = getattr(player, "emotion", None) or {"current": "neutral", "intensity": 0}

        # 2. People profiles (anyone in relationships, rel: tags, or other world players)
        seen_people = set()
        people_profiles = []
        candidate_names = list((getattr(player, "relationships", None) or {}).keys())
        for m in (getattr(player, "memories", None) or []):
            for t in (m.get("tags") or []):
                ts = str(t)
                if ts.lower().startswith("rel:"):
                    who = ts[4:].strip()
                    if who:
                        candidate_names.append(who)
        for pname in (getattr(app.world, "players", None) or {}):
            if pname != name:
                candidate_names.append(pname)
        for who in candidate_names:
            key = str(who or "").strip().lower()
            if not key or key == name.lower() or key in seen_people:
                continue
            seen_people.add(key)
            prof = derive_person_profile(player, who)
            mem_count = sum(
                1 for m in (getattr(player, "memories", None) or [])
                for t in (m.get("tags") or [])
                if str(t).lower() == "rel:" + key
            )
            people_profiles.append({
                "name": who,
                "memory_count": mem_count,
                "profile": _profile_summary_dict(prof),
            })
        people_profiles.sort(key=lambda p: (-p["memory_count"], p["name"]))

        # 3. World entities (characters, areas, notable items)
        chars = [p for p in (getattr(app.world, "players", None) or {}).keys() if p != name]
        areas = []
        items = []
        graph = getattr(app.world, "graph", None)
        for node in ((getattr(graph, "nodes", None) or {}).values()):
            ntype = getattr(node, "type", "")
            nname = str(getattr(node, "name", "") or "").strip()
            if not nname:
                continue
            if ntype == "area" and nname not in areas:
                areas.append(nname)
            elif ntype == "item" and nname not in items:
                items.append(nname)
        world_entities = {
            "characters": sorted(chars),
            "areas": sorted(areas)[:60],
            "items": sorted(items)[:60],
        }

        # 4. Candidate normalization + previews (non-mutating)
        bounds = _character_birth_bounds(app, player, name)
        contradictions_preview = []
        relationship_preview = []
        birth_gate_error = None
        requested_target_tick = data.get("target_tick")
        if requested_target_tick is not None and bounds["birth_tick"] is not None:
            if int(requested_target_tick) < bounds["birth_tick"]:
                birth_gate_error = _format_birth_gate_error(name, int(requested_target_tick), bounds)
        cand_entities = set()
        if candidate_raw:
            cand_tick = int(candidate_raw.get("tick") if candidate_raw.get("tick") is not None else current_tick)
            if bounds["birth_tick"] is not None and cand_tick < bounds["birth_tick"]:
                birth_gate_error = _format_birth_gate_error(name, cand_tick, bounds)
            cand_entry = {
                "id": str(candidate_raw.get("id") or "_preview_candidate"),
                "text": str(candidate_raw.get("text") or "").strip(),
                "tick": cand_tick,
                "importance": int(candidate_raw.get("importance", 5) or 5),
                "type": str(candidate_raw.get("type") or "memory"),
                "category": candidate_raw.get("category"),
                "location": str(candidate_raw.get("location") or ""),
                "entity_ids": list(candidate_raw.get("entity_ids") or []),
                "tags": list(candidate_raw.get("tags") or []),
                "emotions": candidate_raw.get("emotions"),
                "memory_emotions": list(candidate_raw.get("memory_emotions") or []),
                "salience_override": int(candidate_raw.get("salience_override", 0) or 0),
                "source": str(candidate_raw.get("source") or "manual"),
            }
            if isinstance(candidate_raw.get("entities"), list) and candidate_raw["entities"]:
                for eid in _resolve_entity_ids(app.world, candidate_raw["entities"]):
                    if eid not in cand_entry["entity_ids"]:
                        cand_entry["entity_ids"].append(eid)
            _apply_relationship_deltas(
                app, player, name, cand_entry,
                candidate_raw.get("relationship_deltas"),
                candidate_raw.get("emotions"),
                cand_entry["tick"],
                ensure_rel=False,
            )
            # Also resolve entity names mentioned in candidate text so contradiction preview works before manual entity linking
            if cand_entry["text"]:
                words = re.findall(r"[a-zA-Z0-9_']+", cand_entry["text"])
                for eid in _resolve_entity_ids(app.world, words):
                    if eid not in cand_entry["entity_ids"]:
                        cand_entry["entity_ids"].append(eid)
            cand_entities = {str(e).lower() for e in (cand_entry.get("entity_ids") or []) if e}
            contradictions_preview = _preview_contradictions(player, cand_entry)
            relationship_preview = _preview_relationships(player, cand_entry)

        # 5. Recalled memories (non-mutating, reinforce=False)
        search_text = (query + " " + str(candidate_raw.get("text") or "")).strip().lower()
        q_words = {w for w in re.findall(r"[a-z0-9']+", search_text) if len(w) > 2}
        q_entities = set(cand_entities)
        if q_words:
            q_entities |= {e.lower() for e in _resolve_entity_ids(app.world, list(q_words))}

        memories = getattr(player, "memories", []) or []
        scored = []
        for m in memories:
            mtext = str(m.get("text") or "").strip()
            if not mtext or m.get("superseded_by"):
                continue
            m_lower = mtext.lower()
            overlap = sum(1 for w in q_words if w in m_lower)
            kw_score = (overlap / len(q_words)) if q_words else 0.0
            age = max(0, current_tick - int(m.get("tick", 0) or 0))
            recency = 0.5 ** (age / 300.0)
            weight = memory_dynamics.effective_importance(m) / 10.0
            eboost = 2.5 if (q_entities and {str(e).lower() for e in (m.get("entity_ids") or [])} & q_entities) else 0.0
            score = (kw_score * 3.0) + (recency * 1.5) + (weight * 2.0) + eboost
            if score > 0.25 or not q_words:
                copy_m = dict(m)
                copy_m["score"] = round(score, 3)
                scored.append((score, copy_m))
        scored.sort(key=lambda x: x[0], reverse=True)
        recalled_memories = [m for _, m in scored[:8]]

        return jsonify({
            "character": name,
            "current_tick": current_tick,
            "time_per_tick_minutes": minutes_per_tick,
            "birth_tick": bounds["birth_tick"],
            "birthday": bounds["birthday"],
            "age": bounds["age"],
            "birth_gate_error": birth_gate_error,
            "persona_summary": persona_summary,
            "current_emotion": current_emotion,
            "recalled_memories": recalled_memories,
            "people_profiles": people_profiles,
            "world_entities": world_entities,
            "contradictions_preview": contradictions_preview,
            "relationship_preview": relationship_preview,
        })

    @app.route('/api/players/<name>/memories/spatial', methods=['GET'])
    def get_spatial_routes(name):
        """Return KNOWN ROUTES FROM HERE block for a player.

        BFS from the player's current area through the real graph,
        filtered to known areas only.
        """
        player = app.world.players.get(name)
        if not player:
            return jsonify({"error": "Player not found"}), 404
        current_area = getattr(player, 'current_area', None)
        # task-467: authored/known areas are route knowledge too, not only the
        # areas the character has walked. One union, one route surface.
        known = known_route_areas(player, app.world.graph)
        sm = SpatialMemory(app.world.graph)
        block = sm.build_known_routes(current_area, known)
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
