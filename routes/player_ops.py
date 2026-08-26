import logging
from flask import request, jsonify
from player import Player, PERIODIC_CONDITIONS, CONDITION_DEFINITIONS
from graph import Node, Edge, EDGE_CARRYING
from engine.equipment_bonuses import effective_temperature, aggregate_bonuses

logger = logging.getLogger(__name__)


def handle_get_players(app):
    return jsonify({
        "players": list(app.world.players.keys()),
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
    emotion = data.get("emotion")
    if emotion not in ("happy", "sad", "afraid", "angry", "envious",
                       "affectionate", "disgusted"):
        return jsonify({"error": f"unknown emotion '{emotion}'"}), 400
    try:
        delta = float(data.get("delta") or 0)
    except (TypeError, ValueError):
        return jsonify({"error": "delta must be numeric"}), 400
    player.spike_emotion(emotion, delta)
    return jsonify({"emotions": player.emotions_map()})


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
    player.stats = data.get('stats', player.stats)
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
        "players": list(app.world.players.keys()),
        "active": app.world.active_player
    })


def handle_kill_player(app, name):
    name = name.strip()
    if not name:
        return jsonify({"error": "Missing player name"}), 400
    if name not in app.world.players:
        return jsonify({"error": "No such player"}), 404

    player = app.world.players[name]
    player.vitals["HP"] = 0
    player.state = "dead"
    app.world._spawn_body_item(name, "killed by external force")
    app.world.add_log_entry(f"[System] {name} has been killed.")

    return jsonify({"status": "killed", "player": name})


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
        player.stats = data["stats"]
    if "skills" in data:
        player.skills = data["skills"]
    if "traits" in data:
        player.traits = data["traits"]
    if "tags" in data:
        player.tags = data["tags"]
        player.sync_vitals_with_tags()
    if "interest_tags" in data:
        player.interest_tags = data["interest_tags"]
    if "equipped" in data:
        player.equipped = data["equipped"]
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
                    held = grapple._grappling_targets(player.name)
                    for held_name in held:
                        grapple._remove_edge(player.name, held_name)
                    grappler = grapple._grappler_of(player.name)
                    if grappler:
                        grapple._remove_edge(grappler, player.name)
                except Exception:
                    pass
    if "relationships" in data:
        rels = data["relationships"]
        if isinstance(rels, dict):
            for k, v in rels.items():
                if v is None:
                    player.relationships.pop(k, None)
                else:
                    player.relationships[k] = v

    return jsonify({"status": "updated", "player": player.name})


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
        player.equipped = data.get('equipped', player.equipped)
    player.state = data.get('state', player.state) or 'awake'
    player.stats = data.get('stats', player.stats) or player.stats
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

    emotion = data.get('emotion') or {}
    if isinstance(emotion, dict):
        player.emotion = emotion.get('current', player.emotion)
        player.emotion_intensity = emotion.get('intensity', player.emotion_intensity)

    relationships = data.get('relationships') or {}
    for other_name, rel_data in relationships.items():
        if isinstance(rel_data, dict):
            player.relationships[other_name] = {
                "closeness": rel_data.get('closeness', 0),
                "last_interaction_tick": rel_data.get('last_interaction_tick', 0),
                "interaction_count": rel_data.get('interaction_count', 0)
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


def handle_get_vital(app, name, vital_name):
    if name not in app.world.players:
        return jsonify({"error": "Player not found"}), 404
    player = app.world.players[name]
    if vital_name not in player.vitals:
        return jsonify({"error": f"Vital '{vital_name}' not found"}), 404

    value = player.vitals[vital_name]
    max_val = player.vitals.get("Max_HP" if vital_name == "HP" else f"Max_{vital_name}", 100)
    if vital_name == "Temperature":
        max_val = 45
    elif vital_name == "HP":
        max_val = player.vitals.get("Max_HP", 100)

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
        if hasattr(app.world, 'graph') and app.world.graph:
            bonuses = aggregate_bonuses(player, app.world.graph)
        eff_temp = int(effective_temperature(float(room_temp), bonuses))

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
    elif vital_name == "HP":
        max_val = player.vitals.get("Max_HP", 100)
    else:
        max_val = 100

    if "value" in data:
        if vital_name == "Temperature":
            player.vitals[vital_name] = max(min_val, min(max_val, float(data["value"])))
        else:
            player.vitals[vital_name] = max(0, min(max_val, int(data["value"])))
    if "decay_rate" in data:
        player.decay_rates[vital_name] = float(data["decay_rate"])

    return jsonify({"status": "updated", "name": vital_name, "value": player.vitals[vital_name], "max": max_val, "decay_rate": player.decay_rates.get(vital_name, app.world.baseline_decay.get(vital_name, 0))})


def _temperature_drift_desc(direction, rate, eff_temp):
    if direction == "stable":
        if 15 <= eff_temp <= 30:
            return "Comfortable temperature — body is stable"
        return "Temperature is stable"
    if direction == "cooling":
        return f"Cooling at {rate}°C per turn — seek warmth"
    return f"Heating up at {rate}°C per turn — cool down needed"
