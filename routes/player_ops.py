import logging
from flask import request, jsonify
from player import Player, PERIODIC_CONDITIONS, CONDITION_DEFINITIONS
from graph import Node, Edge, EDGE_CARRYING, EDGE_CONNECTION
from engine.equipment_bonuses import effective_temperature, aggregate_bonuses
from engine.abilities import normalize_stat_block
from engine.vitals import ceiling, clamp_to_ceiling, polarity as vital_polarity

logger = logging.getLogger(__name__)


def handle_get_players(app):
    return jsonify({
        "players": [
            getattr(p, "name", k) for k, p in app.world.players.items()
        ],
        "active": app.world.active_player
    })


def handle_get_emotions(app, name):
    player = app.world.players.get(name)
    if not player:
        return jsonify({"error": "Player not found"}), 404
    return jsonify({
        "emotions": player.emotions_map(),
        "description": player.emotions_description(),
    })


def handle_spike_emotion(app, name):
    player = app.world.players.get(name)
    if not player:
        return jsonify({"error": "Player not found"}), 404
    data = request.get_json(force=True) or {}
    emotion = str(data.get("emotion") or "").strip().lower()
    # task-350: toward a specific person -> accept the wider recipient-decided
    # vocabulary (uneasy, grateful, etc.); otherwise the strict global list.
    # task-350 aliases: the LLM names someone by the handle it sees (the man / a
    # subjective alias). Resolve it to a real player name; if it does not resolve,
    # fall back to a global affect spike rather than create a bogus relationship.
    raw_other = str(data.get("toward") or "").strip()
    from engine import emotion as emotion_engine
    valid = tuple(emotion_engine.BASELINES.keys())
    other = ""
    if raw_other:
        resolved = _resolve_other(app, name, raw_other)
        if resolved and hasattr(player, "_FELT_TO_DIM"):
            other = resolved
            valid = tuple(player._FELT_TO_DIM.keys())
    # task-652: one normaliser for a declared feeling. This route used
    # `map_label`, which substring-matches, so an LLM saying "hangry" became
    # "angry" on a coincidence — the exact failure task-505 was filed to prevent,
    # and the reason `felt_from_llm` exists. Using it here means the authored
    # vocabulary is consulted too: "terrified", "furious" and "sadness" are
    # declared aliases in engine/emotion.py and were being dropped here.
    if emotion not in valid:
        resolved = emotion_engine.felt_from_llm(
            {"label": emotion, "intensity": data.get("intensity") or 5})
        if not resolved:
            return jsonify({"emotions": player.emotions_map(), "ignored": emotion})
        emotion = resolved[0]
    if emotion not in valid:
        return jsonify({"emotions": player.emotions_map(), "ignored": emotion})

    # Legacy global spike path (no target): nudge the affect map.
    if not other:
        try:
            delta = float(data.get("delta") or 0)
        except (TypeError, ValueError):
            return jsonify({"error": "delta must be numeric"}), 400
        player.spike_emotion(emotion, delta)
        return jsonify({"emotions": player.emotions_map()})

    # task-350: the feeling is TOWARD a person -> record it as an experience so
    # relationships/feelings can change toward that person (recipient decides).
    try:
        intensity = max(1.0, min(10.0, float(data.get("intensity") or data.get("delta") or 5)))
    except (TypeError, ValueError):
        intensity = 5.0
    if player.felt_toward(other, emotion, intensity, getattr(app.world, "time_ticks", 0)):
        return jsonify({
            "felt_toward": other,
            "emotions": player.emotions_map(),
            "relationships": [
                (v.get("name") or k) for k, v in (player.relationships or {}).items()
            ],
        })

    try:
        delta = float(data.get("delta") or 0)
    except (TypeError, ValueError):
        return jsonify({"error": "delta must be numeric"}), 400
    player.spike_emotion(emotion, delta)
    return jsonify({"emotions": player.emotions_map()})


def handle_map_player_emotions(app, name):
    """Map an emotion label onto the affect map + mental vitals (recall path).

    Accepts:
      {label, intensity, mapped?, vitals?, toward?}
        - label:   freeform emotion word (agent-invented or curated).
        - mapped:  optional client-side semantic {dimension: delta} if the
                   caller already resolved it via embedding.
        - vitals:  optional explicit {vital: delta} to apply verbatim.
        - toward:  optional speaker name — when it resolves to a known person,
                   the recalled memory also nudges the relationship toward them.
    Resolution order: supplied `mapped`, else server keyword ``map_label``.
    Unknown labels are a graceful no-op (no spike, no vital change).
    Mental-vital coupling is subtle and scaled so a single recalled memory
    only shifts Sanity/Entertainment/Social by a few points.
    """
    from engine import emotion as emotion_engine
    from engine.runtime_config import config as runtime_config
    player = app.world.players.get(name)
    if not player:
        return jsonify({"error": "Player not found"}), 404
    data = request.get_json(force=True) or {}

    # --- Resolve dimension deltas ---
    dim_deltas = {}
    mapped = data.get("mapped")
    if isinstance(mapped, dict):
        dim_deltas = {str(k): float(v) for k, v in mapped.items() if v}
    else:
        label = str(data.get("label") or "").strip().lower()
        try:
            intensity = float(data.get("intensity") or 5)
        except (TypeError, ValueError):
            intensity = 5.0
        intensity = max(0.0, min(10.0, intensity))
        # Subtle feel scale: a full-strength (10) emotion nudges ~+/-15-18 pts.
        spike_scale = float(runtime_config.get("emotion.spike_scale", 1.7))
        for dim, _w in emotion_engine.map_label(label):
            dim_deltas[dim] = dim_deltas.get(dim, 0.0) + intensity * spike_scale

    if not dim_deltas and not isinstance(data.get("vitals"), dict):
        return jsonify({"error": "unresolved emotion"}, 400)

    for dim, delta in dim_deltas.items():
        if dim in emotion_engine.BASELINES:
            player.spike_emotion(dim, delta)

    # --- Apply mental-vital coupling (subtle) ---
    vitals = {}
    if isinstance(data.get("vitals"), dict):
        vitals.update({str(k): float(v) for k, v in data["vitals"].items() if v})
    else:
        vital_scale = float(runtime_config.get("emotion.vital_scale", 0.25))
        for dim in dim_deltas:
            if dim not in emotion_engine.VITAL_EFFECTS:
                continue
            vital, factor = emotion_engine.VITAL_EFFECTS[dim]
            vitals[vital] = vitals.get(vital, 0.0) + factor * (dim_deltas[dim] / 1.7) * vital_scale

    for vital, delta in vitals.items():
        if vital not in player.vitals:
            continue
        cur = float(player.vitals[vital])
        new_val = max(0.0, min(100.0, cur + delta))
        # Round to match the storage convention: Temperature is a float with
        # 1 decimal; all other vitals are integers.  Without this the mental
        # vital coupling produces ugly long floats (e.g. Social 98.183823…).
        if vital == "Temperature":
            player.vitals[vital] = round(new_val, 1)
        else:
            player.vitals[vital] = round(new_val)

    # --- Relationship nudge toward the speaker (name-gated) ---
    # Only when the recalled memory is attributed to a real, resolvable speaker.
    # An anonymized voice label ("a woman's voice") resolves to None and is left
    # as a pure re-feel — we never invent a relationship with an unknown person.
    toward = str(data.get("toward") or "").strip()
    if toward and dim_deltas:
        speaker = _resolve_other(app, name, toward)
        if speaker:
            from engine.relationships import ensure_relationship
            rel, created = ensure_relationship(
                player, speaker, getattr(app.world, "time_ticks", 0))
            if created:
                rel["first_sighting"] = True
            drive_deltas = {}
            rel_scale = float(runtime_config.get("emotion.rel_scale", 0.25))
            for dim, delta in dim_deltas.items():
                if dim in emotion_engine.RELATIONSHIP_VALENCE:
                    d, f = emotion_engine.RELATIONSHIP_VALENCE[dim]
                    drive_deltas[d] = drive_deltas.get(d, 0.0) + f * delta * rel_scale
            if drive_deltas:
                tags = ["rel:" + speaker] + [f"{d}:{round(v, 3)}" for d, v in drive_deltas.items()]
                try:
                    # N6: the recall writer used to store a contentless placeholder
                    # ("I was reminded of something…"). The client now sends the
                    # triggering memory as `reason` — no reason, no memory: the
                    # affect spike already happened; a junk entry helps nobody.
                    reason = str(data.get("reason") or "").strip()
                    if not reason:
                        return jsonify({"emotions": player.emotions_map(), "vitals": player.vitals})
                    player.add_memory(
                        f'Remembered: "{reason}" — it made me feel this way toward {speaker}.',
                        tick=getattr(app.world, "time_ticks", 0),
                        importance=6,
                        memory_type="emotion",
                        tags=tags,
                        source="recall",
                    )
                except Exception:
                    pass

    return jsonify({"emotions": player.emotions_map(), "vitals": player.vitals})


def _resolve_other(app, char_name, handle):
    """Resolve an agent-facing handle to a real player name (task-350 aliases).

    The LLM refers to others by the handle it actually sees: an anonymized
    display label ("the man"), a subjective alias it assigned, or a description.
    This resolves that back to the real player name within char_name's own area,
    so felt_toward / learn_names never create a bogus record keyed by "the man".

    Tiers (mirrors engine.matching _match_character_name but scoped to
    char_name's area, independent of who is the active player):
      exact name -> word-boundary name-substring -> node alias -> description word.
    Returns the real player name, or None when unresolved/ambiguous.
    """
    import re
    from engine.matching import node_aliases, CHARACTER_DESCRIPTION_STOPWORDS
    if not handle:
        return None
    h = str(handle).strip().lower()
    # A clear NAME resolves anywhere (feelings about a known person shouldn't
    # require physical co-location). Only description/alias/name-substring tiers
    # need the actor to be in the same area.
    global_exact = [p for p in app.world.players if p != char_name and p.lower() == h]
    if len(global_exact) == 1:
        return global_exact[0]
    area = None
    char = app.world.players.get(char_name)
    if char:
        area = getattr(char, "current_area", None)
    # candidates: same area as char_name (or all players if area unknown), not self
    cands = []
    for pname, p in app.world.players.items():
        display = getattr(p, "name", pname)
        if pname == char_name or display == char_name:
            continue
        if area is not None and getattr(p, "current_area", None) != area:
            continue
        cands.append(display)
    if not cands:
        return None
    # 1 exact
    exact = [p for p in cands if p.lower() == h]
    if len(exact) == 1:
        return exact[0]
    # 2 word-boundary name substring
    name_m = []
    for p in cands:
        pl = p.lower()
        if re.search(r'(?<!\w)' + re.escape(h) + r'(?!\w)', pl) or            re.search(r'(?<!\w)' + re.escape(pl) + r'(?!\w)', h):
            name_m.append(p)
    if len(name_m) == 1:
        return name_m[0]
    # 3 alias
    alias_m = []
    get_node_id = getattr(app.world, "_player_node_id", None)
    for p in cands:
        node = None
        if callable(get_node_id):
            try:
                node = app.world.graph.get_node(get_node_id(p))
            except Exception:
                node = None
        for a in node_aliases(node):
            if a == h or re.search(r'(?<!\w)' + re.escape(h) + r'(?!\w)', a):
                alias_m.append(p)
                break
    if len(alias_m) == 1:
        return alias_m[0]
    # 4 description words
    significant = [w for w in re.findall(r"[a-z]+", h)
                   if len(w) >= 4 and w not in CHARACTER_DESCRIPTION_STOPWORDS]
    if significant:
        scored = []
        for p in cands:
            pl = app.world.players.get(p)
            text = ((getattr(pl, "description", "") or "") + " " +
                    (getattr(pl, "base_description", "") or "")).lower()
            count = sum(1 for w in set(significant)
                        if re.search(r'(?<!\w)' + re.escape(w) + r'(?!\w)', text))
            scored.append((count, p))
        best = max((c for c, _ in scored), default=0)
        top = [p for c, p in scored if c == best]
        # accept a single best match (>=2 is preferred; a lone distinctive word
        # like "tall" already narrows to one same-area candidate). Keep it
        # conservative: only when exactly one candidate matched at the top.
        if best >= 1 and len(top) == 1:
            return top[0]
    return None


def handle_get_relationship_profiles(app, name):
    """Derived per-person relationship reads (task-350).

    Returns {other: {summary, role, consent, dims...}} for every person this
    character has a relationship with. The prompt builder renders these instead
    of raw closeness.
    """
    from engine.derive import derive_person_profile
    player = app.world.players.get(name)
    if not player:
        return jsonify({"error": "Player not found"}), 404
    profiles = {}
    for other in (player.relationships or {}).keys():
        try:
            prof = derive_person_profile(player, other)
        except Exception:
            continue
        display = (player.relationships.get(other) or {}).get("name") or other
        profiles[display] = {
            "summary": prof.get("summary"),
            "role": prof.get("role"),
            "consent": round(prof.get("consent", 0.0), 3),
            "trust": round(prof.get("trust", 0.0), 1),
            "fear": round(prof.get("fear", 0.0), 1),
            "closeness": round(prof.get("closeness", 0.0), 1),
            "has_signal": bool(prof.get("_has_signal")),
        }
    return jsonify({"profiles": profiles})


def handle_learn_names(app, name):
    """Learn names this player has confirmed/deduced this turn (task-350).

    Body: {"names": ["Rex", ...]}. Only names of actual present players are
    accepted — the engine validates, so the agent cannot invent a name tag.
    Each valid name clears the player's name-unknown (stranger) flag via
    learn_name, exactly as if they had heard it.
    """
    player = app.world.players.get(name)
    if not player:
        return jsonify({"error": "Player not found"}), 404
    data = request.get_json(force=True) or {}
    names = data.get("names") or []
    tick = getattr(app.world, "time_ticks", 0)
    learned = []
    for raw in names:
        candidate = str(raw or "").strip()
        if not candidate:
            continue
        # task-350 aliases: the agent names this person by the handle it saw
        # (the man / a subjective alias / a deduction). Resolve to a real player
        # name so we clear the right stranger flag and never invent a record.
        resolved = _resolve_other(app, name, candidate)
        if not resolved:
            continue
        if player.learn_name(resolved, tick):
            learned.append(resolved)
    return jsonify({"learned": learned, "relationships": [
        (v.get("name") or k) for k, v in (player.relationships or {}).items()
    ]})


def handle_get_conditions(app):
    catalog = []
    for cid, definition in CONDITION_DEFINITIONS.items():
        catalog.append({
            "value": cid,
            "label": definition.get("name", cid),
            "description": definition.get("description", ""),
            "default_duration": definition.get("default_duration"),
            "blocks_actions": bool(definition.get("blocks_actions")),
            "blocks_movement": bool(definition.get("blocks_movement")),
            "blocks_speech": bool(definition.get("blocks_speech")),
            "known": definition.get("known", True),
        })
    catalog.sort(key=lambda c: (not c["blocks_actions"], c["label"]))
    return jsonify({"conditions": catalog})


def handle_create_player(app):
    data = request.get_json() or {}
    name = data.get('name')
    if not name:
        return jsonify({"error": "Missing player 'name'"}), 400

    player = Player(name)
    player.stats = normalize_stat_block(data.get('stats', player.stats))
    player.vitals = data.get('vitals', player.vitals)
    player.skills = data.get('skills', player.skills)
    player.traits = data.get('traits', player.traits)
    player.tags = data.get('tags', player.tags)
    player.interest_tags = data.get('interest_tags', player.interest_tags)
    player.sync_vitals_with_tags()
    app.world.add_player(player)
    return jsonify({"status": "success", "player": name})


def handle_set_active_player(app):
    data = request.get_json() or {}
    name = data.get('name')
    if not name:
        return jsonify({"error": "Missing 'name'"}), 400
    try:
        app.world.set_active_player(name)
        return jsonify({"status": "success", "active": app.world.active_player})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


def handle_delete_player(app, name):
    name = name.strip()
    if not name:
        return jsonify({"error": "Missing player name"}), 400
    if name not in app.world.players:
        return jsonify({"error": "No such player"}), 404
    if len(app.world.players) <= 1:
        return jsonify({"error": "Cannot delete the last remaining player"}), 400

    pnode_id = app.world._player_node_id(name)
    app.world.graph.remove_node(pnode_id)

    del app.world.players[name]
    if app.world.active_player == name:
        try:
            app.world.active_player = next(iter(app.world.players.keys()))
        except StopIteration:
            app.world.active_player = None

    return jsonify({
        "status": "deleted",
        "deleted": name,
        "players": [
            getattr(p, "name", k) for k, p in app.world.players.items()
        ],
        "active": app.world.active_player
    })


def handle_kill_player(app, name):
    name = name.strip()
    if not name:
        return jsonify({"error": "Missing player name"}), 400
    if name not in app.world.players:
        return jsonify({"error": "No such player"}), 404

    player = app.world.players[name]
    # task-538: the single death path, so a scripted kill is the same event a
    # killing blow is — body, dropped items, lived-log record and all.
    killed = app.world.kill_player(name, "killed by external force")
    app.world.add_log_entry(f"[System] {name} has been killed.")

    return jsonify({"status": "killed", "player": name, "newly_dead": killed})


def handle_move_player(app, name):
    name = name.strip()
    data = request.get_json() or {}
    area_name = data.get('area')
    if not area_name:
        return jsonify({"error": "Missing 'area'"}), 400
    if area_name not in app.world.areas:
        return jsonify({"error": f"Area '{area_name}' not found"}), 404
    if name not in app.world.players:
        return jsonify({"error": f"Player '{name}' not found"}), 404

    app.world._set_player_area(name, area_name)
    return jsonify({"status": "moved", "player": name, "area": area_name})


def handle_player_speak(app, name):
    name = name.strip()
    data = request.get_json() or {}
    text = data.get('text', '').strip()
    area_name = data.get('area')
    if not text:
        return jsonify({"error": "Missing 'text'"}), 400

    target_area = None
    if area_name and area_name in app.world.areas:
        target_area = app.world.areas[area_name]
    elif name in app.world.players:
        player = app.world.players[name]
        target_area = app.world.areas.get(player.current_area)
    elif app.world.current_area:
        target_area = app.world.current_area

    if not target_area:
        return jsonify({"error": "Could not determine target area"}), 400

    app.world.broadcast_speech(name, text, area_name=target_area.name)

    return jsonify({"status": "broadcast", "speaker": name, "text": text, "area": target_area.name})


def handle_update_player(app, name):
    name = name.strip()
    if not name or name not in app.world.players:
        return jsonify({"error": "No such player"}), 404

    data = request.get_json() or {}
    player = app.world.players[name]
    old_name = name

    if "new_name" in data and data["new_name"] and data["new_name"] != old_name:
        new_name = data["new_name"].strip()
        if not new_name or new_name in app.world.players:
            return jsonify({"error": "Invalid or duplicate name"}), 400

        app.world.players.pop(old_name)
        player.name = new_name
        app.world.players[new_name] = player

        old_node_id = app.world._player_node_id(old_name)
        new_node_id = app.world._player_node_id(new_name)
        node = app.world.graph.get_node(old_node_id)
        if node:
            node.name = new_name
            node.id = new_node_id
            for edge in app.world.graph.edges:
                if edge.source == old_node_id:
                    edge.source = new_node_id
                if edge.target == old_node_id:
                    edge.target = new_node_id
            app.world.graph.nodes[new_node_id] = node
            del app.world.graph.nodes[old_node_id]

        if app.world.active_player == old_name:
            app.world.active_player = new_name

        return jsonify({"status": "updated", "player": new_name, "renamed": True})

    if "state" in data:
        player.state = data["state"]
    if "current_area" in data:
        app.world._set_player_area(name, data["current_area"])
    if "emotion" in data:
        ed = data["emotion"]
        if isinstance(ed, dict):
            if "current" in ed:
                player.emotion = ed["current"]
            if "intensity" in ed:
                player.emotion_intensity = float(ed["intensity"])
        elif isinstance(ed, str):
            player.emotion = ed
    if "emotion_intensity" in data:
        player.emotion_intensity = float(data["emotion_intensity"])
    if "personality" in data:
        player.personality = data["personality"]
    if "description" in data:
        player.description = data["description"]
    if "base_description" in data:
        player.base_description = data["base_description"]
    if "stats" in data:
        player.stats = normalize_stat_block(data["stats"]) or player.stats
    if "skills" in data:
        player.skills = data["skills"]
    if "traits" in data:
        player.traits = data["traits"]
    # task-605: size is a property, not a trait. None means "not authored", which
    # is what lets the engine fall back to a size_* trait. An unrecognised value
    # is rejected rather than stored, so the six tiers stay the whole model.
    if "size" in data:
        raw_size = data["size"]
        if raw_size is None or str(raw_size).strip() == "":
            player.size = None
        else:
            from engine.size import SIZE_TIERS
            candidate = str(raw_size).strip().lower()
            if candidate not in SIZE_TIERS:
                return jsonify({"error": f"size must be one of {SIZE_TIERS}"}), 400
            player.size = candidate
    if "tags" in data:
        player.tags = data["tags"]
        player.sync_vitals_with_tags()
    # task-549: species is a free-text kind ("goblin", "forest goblin"), not a
    # closed enum — the whole point is that an author can name a species nobody
    # registered. It is normalised and stored, never validated away, because an
    # unknown species permits everything rather than nothing.
    if "species" in data:
        raw_species = data["species"]
        if isinstance(raw_species, (list, tuple)):
            raw_species = raw_species[0] if raw_species else None
        player.species = str(raw_species).strip().lower() or None if raw_species else None
    if "known" in data:
        player.known = [str(k) for k in (data["known"] or []) if str(k).strip()]
    if "interest_tags" in data:
        player.interest_tags = data["interest_tags"]
    if "fear_tags" in data:
        player.fear_tags = data["fear_tags"]
    # task-654: an `equipped` payload is written through the equipment system so
    # the graph edges are updated with the dict. Assigning `player.equipped`
    # directly left the item visible in the inspector and inert in combat, because
    # weapon selection and damage reduction read the edges.
    if "equipped" in data:
        app.world.equipment.set_equipped_payload(player, data["equipped"])
    if "behaviors" in data:
        player.behaviors = data["behaviors"]
    if "npc_state" in data:
        player.npc_state = data["npc_state"]
    if "npc_behavior" in data:
        player.npc_behavior = data["npc_behavior"]
    if "npc_action_interval" in data:
        player.npc_action_interval = int(data["npc_action_interval"])
    if "simple_npc" in data:
        player.simple_npc = bool(data["simple_npc"])
    if "autonomy" in data:
        player.autonomy = bool(data["autonomy"])
    if "conditions" in data:
        player.load_conditions(data["conditions"])
    if "add_condition" in data:
        payload = data["add_condition"]
        if isinstance(payload, dict):
            cid = payload.get("condition") or payload.get("id")
            if not (isinstance(cid, str) and cid):
                raise ValueError("add_condition object requires a 'condition' id")
            player.add_condition(
                cid,
                duration=payload.get("duration"),
                source=payload.get("source"),
                level=payload.get("level"),
                periodic=payload.get("periodic"),
                extra_conditions=payload.get("extra_conditions"),
                ends_on=payload.get("ends_on"),
                symptoms=payload.get("symptoms"),
                known=payload.get("known"),
                source_type=payload.get("source_type"),
                overrides=payload.get("overrides") or None,
            )
        elif isinstance(payload, str) and payload:
            player.add_condition(payload)
    if "remove_condition" in data:
        cid = data["remove_condition"]
        if isinstance(cid, str) and cid in player.conditions:
            player.remove_condition(cid)
            if cid == "grappled":
                try:
                    grapple = app.world.grapple
                    # task-449: grapple edges are keyed by identity, not name.
                    pkey = app.world.player_manager.relationship_key(player)
                    held = grapple._grappling_targets(pkey)
                    for held_key in held:
                        grapple._remove_edge(pkey, held_key)
                    grappler = grapple._grappler_of(pkey)
                    if grappler:
                        grapple._remove_edge(grappler, pkey)
                except Exception:
                    pass
    if "relationships" in data:
        rels = data["relationships"]
        if isinstance(rels, dict):
            for k, v in rels.items():
                key = player._rel_key(k) if hasattr(player, "_rel_key") else k
                if v is None:
                    player.relationships.pop(key, None)
                else:
                    if isinstance(v, dict) and not v.get("name"):
                        v = dict(v)
                        v["name"] = str(k)
                    player.relationships[key] = v

    response = {"status": "updated", "player": player.name}

    # task-606: a stat block that contradicts its own size is **reported, not
    # refused**. A leviathan at STR 9 is storable and always was; the point is
    # that the author who just typed it finds out, in the response, rather than
    # discovering it the next time something tries to move the thing.
    if {"stats", "size"} & set(data):
        from engine.abilities import scale_issues
        issues = scale_issues(entity=player)
        if issues:
            response["scale_warnings"] = issues

    return jsonify(response)


def handle_import_player(app):
    data = request.get_json() or {}
    name = data.get('name')
    if not name:
        return jsonify({"error": "Missing 'name'"}), 400

    player = app.world.players.get(name)
    if not player:
        player = Player(name)
    player.personality = data.get('personality', player.personality) or ''
    if 'description' in data:
        player.description = data.get('description', '')
    if 'base_description' in data:
        player.base_description = data.get('base_description', '')
    if 'equipped' in data:
        # task-654: edges too — see the update route above.
        app.world.equipment.set_equipped_payload(
            player, data.get('equipped', player.equipped))
    player.state = data.get('state', player.state) or 'awake'
    player.stats = normalize_stat_block(data.get('stats', player.stats)) or player.stats
    player.vitals = data.get('vitals', player.vitals) or player.vitals
    player.skills = data.get('skills', player.skills) or player.skills
    player.traits = data.get('traits', player.traits) or player.traits
    player.tags = data.get('tags', player.tags) or player.tags
    player.interest_tags = data.get('interest_tags', player.interest_tags) or player.interest_tags
    player.decay_rates = data.get('decay_rates', player.decay_rates) or player.decay_rates
    player.simple_npc = data.get('simple_npc', player.simple_npc) or False
    player.npc_behavior = data.get('npc_behavior', player.npc_behavior) or 'wander'
    player.npc_state = data.get('npc_state', player.npc_state) or 'idle'
    player.behaviors = data.get('behaviors', player.behaviors) or []
    player.state_timer = data.get('state_timer', player.state_timer) or 0
    player.sync_vitals_with_tags()

    emotion = data.get('emotion') or {}
    if isinstance(emotion, dict):
        player.emotion = emotion.get('current', player.emotion)
        player.emotion_intensity = emotion.get('intensity', player.emotion_intensity)

    relationships = data.get('relationships') or {}
    for other_name, rel_data in relationships.items():
        if isinstance(rel_data, dict):
            key = player._rel_key(other_name) if hasattr(player, "_rel_key") else other_name
            player.relationships[key] = {
                "closeness": rel_data.get('closeness', 0),
                "last_interaction_tick": rel_data.get('last_interaction_tick', 0),
                "interaction_count": rel_data.get('interaction_count', 0),
                "name": other_name,
            }

    area_name = data.get('current_area')
    if area_name:
        area_node_id = app.world._area_node_id(area_name)
        area_node = app.world.graph.get_node(area_node_id)
        if area_node:
            player.current_area = area_name
        else:
            first_area = next((n.name for n in app.world.graph.nodes.values() if n.type == 'area'), None)
            if first_area:
                player.current_area = first_area

    if name not in app.world.players:
        app.world.add_player(player)
    app.world.set_active_player(name)

    inventory = data.get('inventory') or []
    player_node_id = app.world._player_node_id(name)
    placed_items = []
    skipped_items = []
    for item_name in inventory:
        item_node_id = f"item_{item_name.replace(' ', '_')}"
        item_node = app.world.graph.get_node(item_node_id)
        if not item_node:
            item_node = Node(id=item_node_id, type='item', name=item_name, properties={
                "description": "",
                "actions": ["examine", "take", "drop"],
                "uses": -1,
                "weight": 0.5
            })
            app.world.graph.add_node(item_node)
        for e in list(app.world.graph.edges):
            if e.source == item_node_id and e.type in (EDGE_CARRYING, 'location', 'carried_by'):
                app.world.graph.remove_edge(e.source, e.target, e.type)
        app.world.graph.add_edge(Edge(source=item_node_id, target=player_node_id, type=EDGE_CARRYING))
        placed_items.append(item_name)

    player.sync_vitals_with_tags()
    return jsonify({"status": "imported", "player": name, "placed_items": placed_items})


def handle_generate_character_description(app, name):
    if name not in app.world.players:
        return jsonify({"error": "No such player"}), 404
    try:
        player = app.world.players[name]
        app.world._update_equipment_description(player)
        return jsonify({"description": player.description})
    except Exception as e:
        logger.exception("Error generating description")
        return jsonify({"error": str(e)}), 500


# ── structured appearance / personality (task-507) ───────────────────────


def _character_node(app, name):
    """The character's graph node, or None."""
    try:
        return app.world.graph.get_node(app.world._player_node_id(name))
    except Exception:
        return None


def handle_get_character_record(app, name):
    """Read a character's structured block, the schema, and the rendered prose."""
    from engine import character_appearance as ca
    if name not in app.world.players:
        return jsonify({"error": "No such player"}), 404
    node = _character_node(app, name)
    return jsonify({
        "structured": ca.is_structured(node),
        "record": ca.get_record(node),
        "appearance": ca.appearance(node),
        "personality": ca.personality(node),
        "prose": ca.render_prose(node),
        "schema": ca.schema_for_llm(),
    })


def handle_set_character_record(app, name):
    """Validate and store the structured block, then render prose once.

    ``{"record": {...}, "render": true}`` — ``render`` defaults to true because
    the task's flow is "set the fields, then generate the description ONCE", and
    a caller that has just filled a whole card almost always wants the prose with
    it. Pass ``false`` to fill fields in stages.
    """
    from engine import character_appearance as ca
    if name not in app.world.players:
        return jsonify({"error": "No such player"}), 404
    node = _character_node(app, name)
    if node is None:
        return jsonify({"error": "No character node"}), 404
    data = request.get_json(force=True) or {}
    try:
        stored = ca.set_record(node, data.get("record"))
    except ca.StructuredError as e:
        return jsonify({"error": str(e)}), 400

    body = {"record": stored, "structured": bool(stored)}
    if data.get("render", True) and stored:
        # Prose is the narrative layer and is written once, into
        # base_description, where the existing equipment/LLM description
        # pipeline picks it up. An authored base_description is not clobbered:
        # the structured block is the source of truth, but replacing a hand-
        # written paragraph with a generated one is not a decision this route
        # gets to make silently.
        player = app.world.players[name]
        prose = ca.render_prose(node)
        body["prose"] = prose
        if prose and not (player.base_description or "").strip():
            player.base_description = prose
            body["base_description"] = player.base_description
    return jsonify(body)


def handle_clear_character_record(app, name):
    """Drop the structured block, restoring prose-only authoring."""
    from engine import character_appearance as ca
    if name not in app.world.players:
        return jsonify({"error": "No such player"}), 404
    node = _character_node(app, name)
    if node is None:
        return jsonify({"error": "No character node"}), 404
    ca.clear_record(node)
    return jsonify({"record": {}, "structured": False})


def handle_character_affect(app, name):
    """Affect deltas for a stimulus id against this character's record.

    The read side of the task-507 mechanic: a trigger asks what a character
    thinks of a stimulus and applies the axes this returns. Returns ``{}`` for an
    unknown stimulus or a prose-only character, so a caller can apply
    unconditionally without needing to special-case the common case.
    """
    from engine import character_appearance as ca
    if name not in app.world.players:
        return jsonify({"error": "No such player"}), 404
    data = request.get_json(silent=True) or {}
    if request.method == "GET":
        stimulus = request.args.get("stimulus", "")
    else:
        stimulus = str(data.get("stimulus") or "")
    node = _character_node(app, name)
    return jsonify({
        "stimulus": stimulus,
        "affect": ca.affect_for_stimulus(node, stimulus),
    })


def handle_get_vital(app, name, vital_name):
    if name not in app.world.players:
        return jsonify({"error": "Player not found"}), 404
    player = app.world.players[name]
    if vital_name not in player.vitals:
        return jsonify({"error": f"Vital '{vital_name}' not found"}), 404

    value = player.vitals[vital_name]
    # task-538: the ceiling is the character's own. The old lookup was
    # `Max_HP if HP else Max_{vital}`, which is the resolver's first rule with
    # the fallback spelled out — and it spelled 100 out again for anything that
    # had not declared a maximum.
    max_val = ceiling(player.vitals, vital_name)
    if vital_name == "Temperature":
        max_val = 45
    elif max_val == float("inf"):
        max_val = None

    base_rate = app.world.baseline_decay.get(vital_name, 0)
    override_rate = player.decay_rates.get(vital_name)
    effective_rate = override_rate if override_rate is not None else base_rate

    time_to_empty = None
    if effective_rate > 0:
        time_to_empty = round(value / effective_rate, 1)

    conditions_affecting = []
    for cond, effects in PERIODIC_CONDITIONS.items():
        if cond in player.conditions and vital_name in effects:
            conditions_affecting.append({
                "condition": cond,
                "effect": effects[vital_name],
                "description": f"{cond}: {effects[vital_name]:+d} {vital_name}/turn"
            })

    result = {
        "name": vital_name,
        "value": value,
        "max": max_val,
        "percentage": round((value / max_val) * 100, 1) if max_val > 0 else 0,
        "decay_rate": effective_rate,
        "decay_rate_override": override_rate,
        "base_decay_rate": base_rate,
        "time_to_empty": time_to_empty,
        # task-635: 'resource' drains toward 0, 'drive' fills toward 100,
        # 'band' is a comfort window. The source of truth is engine/vitals.py;
        # the modal reads this to describe the direction it actually moves.
        "polarity": vital_polarity(vital_name),
        "conditions_affecting": conditions_affecting
    }

    if vital_name == "Temperature":
        min_val = 25
        room_temp = 21
        area_name = getattr(player, 'current_area', '')
        if area_name and hasattr(app.world, 'graph') and app.world.graph:
            needle = area_name.lower()
            for node in app.world.graph.nodes.values():
                if node.type == "area" and node.name.lower() == needle:
                    env = node.properties.get("environment", {})
                    room_temp = int(env.get("temperature", 21))
                    break

        bonuses = {}
        env = {}
        if hasattr(app.world, 'graph') and app.world.graph:
            bonuses = aggregate_bonuses(player, app.world.graph)
            if area_name:
                found = app.world.graph.get_node(app.world.area_node_id(area_name))
                if found:
                    env = found.properties.get("environment", {})
        eff_temp = int(effective_temperature(float(room_temp), bonuses,
                                             wind_level=env.get("wind", "none"),
                                             humidity=env.get("humidity", "dry")))

        equip_items = []
        ins = bonuses.get("insulation", 0)
        if ins != 0:
            sign = "+" if ins > 0 else ""
            equip_items = [{
                "insulation": ins,
                "description": f"Shifts effective temp by {sign}{ins}°C"
            }]

        drift_rate = 0.0
        drift_direction = "stable"
        if eff_temp < 15:
            drift_rate = round((15 - eff_temp) * 0.02, 4)
            drift_direction = "cooling"
        elif eff_temp > 30:
            drift_rate = round((eff_temp - 30) * 0.02, 4)
            drift_direction = "warming"
        else:
            if float(value) < 36.5:
                drift_rate = 0.1
                drift_direction = "warming"
            elif float(value) > 37.5:
                drift_rate = 0.1
                drift_direction = "cooling"
            else:
                drift_rate = 0.0
                drift_direction = "stable"

        time_est = {"to_hypothermia": None, "to_death_cold": None,
                    "to_heat_stroke": None, "to_death_heat": None,
                    "to_comfortable": None}
        if drift_direction == "cooling" and drift_rate > 0:
            time_est["to_hypothermia"] = max(0, round((float(value) - 33) / drift_rate, 1))
            time_est["to_death_cold"] = max(0, round((float(value) - 30) / drift_rate, 1))
            if float(value) <= 35:
                time_est["to_comfortable"] = 0
            else:
                time_est["to_comfortable"] = max(0, round((float(value) - 35) / drift_rate, 1))
        elif drift_direction == "warming" and drift_rate > 0:
            time_est["to_heat_stroke"] = max(0, round((40 - float(value)) / drift_rate, 1))
            time_est["to_death_heat"] = max(0, round((42 - float(value)) / drift_rate, 1))
            if float(value) >= 39:
                time_est["to_comfortable"] = 0
            else:
                time_est["to_comfortable"] = max(0, round((39 - float(value)) / drift_rate, 1))
        else:
            if float(value) < 35:
                time_est["to_comfortable"] = round((35 - float(value)) / 0.1, 1)
            elif float(value) > 39:
                time_est["to_comfortable"] = round((float(value) - 39) / 0.1, 1)
            else:
                time_est["to_comfortable"] = 0

        dmg = {"hp": 0, "energy": 0, "thirst": 0}
        if eff_temp > 30:
            dmg["thirst"] += 2
            if eff_temp > 40:
                dmg["hp"] += 1
        elif eff_temp < 10:
            dmg["energy"] += 1
            if eff_temp < 0:
                dmg["hp"] += 1
        if 35 <= float(value) < 37:
            dmg["energy"] += 1
        elif 33 <= float(value) < 35:
            dmg["energy"] += 2
            dmg["hp"] += 1
        elif float(value) < 33:
            dmg["hp"] += 3
        elif 37 < float(value) <= 38:
            dmg["thirst"] += 1
        elif 38 < float(value) <= 40:
            dmg["hp"] += 1
        elif float(value) > 40:
            dmg["hp"] += 3

        if 35 <= float(value) <= 39 and 15 <= eff_temp <= 30:
            comfort = "comfortable"
        elif float(value) < 33 or float(value) > 40:
            comfort = "dangerous"
        elif float(value) < 35 or float(value) > 38:
            comfort = "uncomfortable"
        else:
            comfort = "tolerable"

        result.update({
            "min": min_val,
            "room_temperature": room_temp,
            "effective_temperature": eff_temp,
            "equipment": {
                "insulation": bonuses.get("insulation", 0),
                "items": equip_items
            },
            "drift": {
                "direction": drift_direction,
                "rate_per_tick": drift_rate,
                "description": _temperature_drift_desc(drift_direction, drift_rate, eff_temp)
            },
            "time_estimates": time_est,
            "comfort_status": comfort,
            "damage_per_tick": dmg
        })

    return jsonify(result)


def handle_update_vital(app, name, vital_name):
    if name not in app.world.players:
        return jsonify({"error": "Player not found"}), 404
    player = app.world.players[name]
    if vital_name not in player.vitals:
        return jsonify({"error": f"Vital '{vital_name}' not found"}), 404

    data = request.get_json() or {}
    if vital_name == "Temperature":
        max_val = 45
        min_val = 25
    else:
        # task-538: read the character's own ceiling (see handle_get_vital).
        max_val = ceiling(player.vitals, vital_name)

    # task-538: writing a `Max_*` companion also re-clamps the vital it bounds.
    # Setting Max_HP to 8 while HP sits at 100 otherwise leaves the character at
    # 1250% of its maximum, which every later clamp would silently repair and
    # every reader would find surprising — the same reason
    # `modify_vital_max` brings the current value back under a lowered ceiling.
    paired = None
    if vital_name.startswith("Max_"):
        paired = vital_name[len("Max_"):]
        if paired not in player.vitals:
            paired = None

    if "value" in data:
        if vital_name == "Temperature":
            player.vitals[vital_name] = max(min_val, min(max_val, float(data["value"])))
        elif paired:
            # A `Max_*` write is not bounded by the old ceiling (that is the
            # point of it), but the value it bounds is re-clamped against the
            # new one.
            player.vitals[vital_name] = max(0, int(data["value"]))
            player.vitals[paired] = clamp_to_ceiling(
                player.vitals, paired, player.vitals.get(paired, 0))
            max_val = ceiling(player.vitals, paired)
        else:
            player.vitals[vital_name] = max(0, min(max_val, int(data["value"])))
    if "decay_rate" in data:
        player.decay_rates[vital_name] = float(data["decay_rate"])

    return jsonify({"status": "updated", "name": vital_name, "value": player.vitals[vital_name], "max": max_val, "decay_rate": player.decay_rates.get(vital_name, app.world.baseline_decay.get(vital_name, 0))})


# ── player map (task-677) ────────────────────────────────────────────────────
#
# Read-only. The cells a character has been in are not a new registry: an
# arrival writes an observation row for the area (``engine/movement.py`` ->
# ``engine/observation.py``) and refreshes it in place, and the item and
# character rows carry the area they were seen in as ``location``. So this
# handler reads the observation store and adds no state of its own.
#
# Way knowledge is decided HERE, not in the client, and by the same rule the
# turn panel uses (``engine/scene_snapshot.py``): a locked or blocked way reads
# as ``closed`` until the character has learned that aspect, and hidden ways
# stay out entirely. Emitting ``way_blocked`` as one server-computed boolean is
# deliberate — a client-side copy of that rule is how a panel ends up leaking
# what the composer withholds.


def _observed_by_location(player):
    """Areas this character has been in, and what was last seen in each.

    Areas are keyed by node id and carry their own name in ``location``; items
    and people are keyed by that same area *name*, because that is the field
    the observation rows share. Superseded rows are dropped — that is how a
    belief that stopped being true stops being reported.
    """
    areas, items, people = {}, {}, {}
    for m in getattr(player, "memories", []) or []:
        if not isinstance(m, dict) or m.get("superseded_by"):
            continue
        kind = m.get("kind")
        where = str(m.get("location") or "")
        ids = [str(e) for e in (m.get("entity_ids") or []) if e]
        if not ids:
            continue
        if kind == "area":
            areas[ids[0]] = {"id": ids[0], "name": where, "last_seen": m.get("tick")}
        elif where and kind in ("item", "character"):
            bucket = items if kind == "item" else people
            bucket.setdefault(where, {})[ids[0]] = ids[0]
    return areas, items, people


def _map_ways(world, player, area_id, area_name):
    """This area's ways, with the far end and whether the blockage is known."""
    from engine.barriers import SOLID_STATES
    from engine.room_perception import way_visible_to

    graph = world.graph
    player_manager = world.player_manager
    out = []
    seen = set()
    for edge in graph.get_edges_for_source(area_id, EDGE_CONNECTION):
        way_node = graph.get_node(edge.target)
        if not way_node or way_node.id in seen:
            continue
        seen.add(way_node.id)

        raw_direction = edge.properties.get("direction", "") or way_node.name
        if not way_visible_to(player, player_manager, player.name, way_node,
                              area_name, raw_direction):
            continue

        # The way's other end. Ways are nodes joined to both areas, so the far
        # side is whichever connection is not the one we came in by.
        to_area_id = None
        for conn in graph.get_edges_for_source(way_node.id, EDGE_CONNECTION):
            if conn.target != area_id:
                to_area_id = conn.target
                break

        try:
            handle = world.name_matcher.way_handle(
                way_node, raw_direction, area_name) or raw_direction
        except Exception:
            handle = raw_direction

        real_state = way_node.properties.get("current_state", "closed")
        known = {
            aspect: bool(player.knows_way_aspect(area_name, handle, aspect))
            for aspect in ("locked", "blocked", "needs_force")
        }
        reported = real_state
        if real_state in ("locked", "blocked") and not known.get(real_state):
            reported = "closed"

        out.append({
            "way_id": way_node.id,
            "direction": handle,
            # The raw edge direction ("north", "southeast", "up"). The handle is
            # a display string ("north passage") and cannot be stepped on, so an
            # unpainted world needs this to lay its areas out on a lattice at all.
            "compass": raw_direction,
            "to_area_id": to_area_id,
            "name": way_node.name,
            "state": reported,
            "real_state": real_state,
            "solid": real_state in SOLID_STATES,
            # A shut door needs no discovery to be seen shut. A locked or
            # blocked one only reads as itself once the character has hit it.
            "way_blocked": real_state not in ("locked", "blocked") or known.get(real_state, False),
            "known_locked": known["locked"],
            "known_blocked": known["blocked"],
            "visible_in_direction": edge.properties.get("visible_in_direction", "") or "",
        })
    return out


def handle_get_player_map(app, name):
    """The cells this character has been in, and what they last observed there.

    Areas with no painted ``cell`` come back with ``cell: null`` on purpose:
    the client draws those from the cardinal layout rather than dropping them,
    so an unpainted world still produces a usable map.
    """
    from engine.room_perception import resolve_area_node
    from engine import world_scopes as ws

    world = app.world
    player = (getattr(world, "players", {}) or {}).get(name)
    if player is None:
        return jsonify({"error": "No such player"}), 404

    graph = world.graph
    areas, items, people = _observed_by_location(player)
    current_area = getattr(player, "current_area", "")

    cells = []
    scope_counts = {}
    for entry in areas.values():
        node = resolve_area_node(graph, entry["name"])
        if node is None:
            continue
        props = node.properties or {}
        cell = props.get("cell")
        where = entry["name"]

        seen_items = []
        for sid in (items.get(where) or {}).values():
            inode = graph.get_node(sid)
            seen_items.append({"id": sid, "name": inode.name if inode else sid})

        seen_people = []
        for sid in (people.get(where) or {}).values():
            pnode = graph.get_node(sid)
            other = pnode.name if pnode else sid
            known = bool(player.knows_name(other)) if hasattr(player, "knows_name") else True
            seen_people.append({
                "id": sid,
                "name": other if known else None,
                "display": other if known else "someone you have met",
            })

        scope_id = str(props.get("world_scope_id") or "")
        if scope_id:
            scope_counts[scope_id] = scope_counts.get(scope_id, 0) + 1

        cells.append({
            "id": node.id,
            "name": where,
            "cell": ({"x": int(cell["x"]), "y": int(cell["y"])}
                     if isinstance(cell, dict) and "x" in cell and "y" in cell else None),
            "floor": int(props.get("floor", 0) or 0),
            "scope_id": scope_id,
            "biome": str(props.get("biome") or ""),
            "kind": str(props.get("kind") or ""),
            "last_seen": entry["last_seen"],
            "current": where == current_area,
            "items": seen_items,
            "people": seen_people,
            "ways": _map_ways(world, player, node.id, where),
        })

    manifest = ws.normalise_manifest(getattr(world, "world_scopes", {}) or {})
    scopes = []
    for scope_id, count in sorted(scope_counts.items()):
        rec = manifest.get(scope_id) or {}
        grid = rec.get("grid") or {}
        scopes.append({
            "id": scope_id,
            "name": rec.get("name") or scope_id,
            "visited_cells": count,
            "w": grid.get("w"),
            "h": grid.get("h"),
            "cell_scale": grid.get("cell_scale", 1),
        })

    return jsonify({
        "player": name,
        "current_area": current_area,
        "tick": getattr(world, "time_ticks", 0),
        "areas": cells,
        "scopes": scopes,
    })


def handle_mark_visited(app, name):
    """Seed a character's map with places they have been.

    Writes the *same* row an arrival writes — ``Player.record_observation``
    with ``kind="area"`` — rather than appending to a parallel registry, so the
    map, the memory store, recall and anything added later all read one fact.
    Also mirrors the name into ``visited_areas``, which is what the known-routes
    prose and the adventurous-traveller bonus still read; when task-430 retires
    that set in favour of these rows, this line goes with it.

    Accepts ``{"areas": [...]}`` or ``{"areas": "A, B"}``. An area that does
    not resolve is reported in ``unresolved`` rather than silently dropped: a
    typo in an author's list should be visible, not quietly shrink the map.
    """
    from engine.room_perception import resolve_area_node, visible_area_items

    world = app.world
    player = (getattr(world, "players", {}) or {}).get(name)
    if player is None:
        return jsonify({"error": "No such player"}), 404

    data = request.get_json(force=True) or {}
    raw = data.get("areas")
    if isinstance(raw, str):
        raw = [part.strip() for part in raw.split(",")]
    if not isinstance(raw, (list, tuple)):
        raw = []
    # Also record what was in each area, as an arrival would. Off by default:
    # "was here" and "saw these things" are different claims, and seeding the
    # second one for an area the character never entered asserts something the
    # author may not mean.
    observe = bool(data.get("observe"))

    graph = world.graph
    tick = data.get("tick")
    tick = int(tick) if isinstance(tick, (int, float)) else int(getattr(world, "time_ticks", 0) or 0)

    added, unresolved = [], []
    for entry in raw:
        label = str(entry or "").strip()
        if not label:
            continue
        node = resolve_area_node(graph, label)
        if node is None:
            unresolved.append(label)
            continue
        player.record_observation(
            node.id,
            "You have been to %s." % node.name,
            tick,
            kind="area",
            location=node.name,
        )
        visited = getattr(player, "visited_areas", None)
        if isinstance(visited, set):
            visited.add(node.name)

        seeded_items = []
        if observe:
            # Items go through the same perception an arrival uses, so a seeded
            # area's tooltip reads like a walked one. Characters deliberately do
            # NOT: engine/observation.py:96-105 excludes them because
            # arrival-stamping people saturated camp Entertainment at 87/100.
            # visible_area_items yields nodes, not ids.
            for inode in visible_area_items(graph, node.id, player=player) or []:
                player.record_observation(
                    inode.id,
                    "You have seen %s in %s." % (inode.name, node.name),
                    tick,
                    kind="item",
                    location=node.name,
                )
                seeded_items.append(inode.name)

        added.append({"id": node.id, "name": node.name, "items_seeded": seeded_items})

    return jsonify({
        "player": name,
        "tick": tick,
        "added": added,
        "unresolved": unresolved,
    })


def _temperature_drift_desc(direction, rate, eff_temp):
    if direction == "stable":
        if 15 <= eff_temp <= 30:
            return "Comfortable temperature — body is stable"
        return "Temperature is stable"
    if direction == "cooling":
        return f"Cooling at {rate}°C per turn — seek warmth"
    return f"Heating up at {rate}°C per turn — cool down needed"
