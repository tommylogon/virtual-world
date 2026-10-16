"""Character-focused runtime state projections.

@module runtime_snapshot_ops
@contributes the bounded character-scope runtime snapshot response
"""

from flask import jsonify, request

from engine import world_scopes


def handle_runtime_state(app):
    """Return the live scope union for the requested stable character ids."""
    world = app.world
    manager = world.player_manager
    graph = world.graph
    manifest = world_scopes.normalise_manifest(
        getattr(world, "world_scopes", {}) or {})
    character_ids = list(dict.fromkeys(
        value.strip() for value in request.args.getlist("character_id")
        if value and value.strip()))
    if not character_ids:
        return jsonify({"error": "At least one character_id is required"}), 400

    selected = []
    scope_ids = set()
    for character_id in character_ids:
        player = manager.get_by_id(character_id)
        if player is None:
            return jsonify({"error": f"Character '{character_id}' not found"}), 404
        player_key = manager.relationship_key(character_id)
        if player_key not in manager.players:
            return jsonify({"error": f"Character '{character_id}' is not registered"}), 404

        node_id = manager.get_player_node_id(player_key)
        area_id = graph.area_of(node_id)
        index = getattr(world, "world_index", None)
        if area_id is None and index is not None:
            area_id = index.character_location(node_id)
        if not area_id:
            return jsonify({
                "error": f"Character '{character_id}' has no authoritative area location"
            }), 409

        area_node = graph.get_node(area_id)
        scope_id = (
            (getattr(area_node, "properties", {}) or {}).get("world_scope_id")
            if area_node is not None else None
        )
        if not scope_id and index is not None:
            scope_id = index.scope_for_area(area_id)
        if not scope_id or str(scope_id) not in manifest:
            return jsonify({
                "error": f"Area '{area_id}' has no known owning world scope"
            }), 409

        scope_id = str(scope_id)
        if area_node is None and (
                index is None or not index.ensure_scope_loaded(scope_id, graph)):
            return jsonify({
                "error": f"Character scope '{scope_id}' is not loaded"
            }), 409
        selected.append((character_id, player_key, player))
        scope_ids.add(scope_id)

    nodes = {}
    for scope_id in sorted(scope_ids):
        projection = world_scopes.project_subgraph(
            manifest, graph, manager.players, scope_id, include_items=True)
        nodes.update(projection["nodes"])

        area_ids = {
            node_id for node_id in graph.nodes_owned_by(scope_id)
            if getattr(graph.get_node(node_id), "type", "") == "area"
        }
        for boundary in world_scopes.boundary_ways(graph, area_ids):
            way = graph.get_node(boundary["id"])
            if way is not None:
                nodes[way.id] = way.to_dict()

    edge_map = {}
    for node_id in nodes:
        for edge in graph.get_edges_for_source(node_id):
            if edge.target in nodes:
                edge_map[(edge.source, edge.target, edge.type)] = edge.to_dict()

    areas_by_id = {}
    areas_by_name = {}
    for node_id, node_data in nodes.items():
        if node_data.get("type") != "area":
            continue
        area = world.serializer._serialize_area(node_id)
        if area is not None:
            areas_by_id[node_id] = area
            areas_by_name[area["name"]] = area

    players = {
        player_key: world.serializer._serialize_player(player_key, player)
        for _character_id, player_key, player in selected
    }
    player_node_ids = {
        player_key: manager.get_player_node_id(player_key)
        for _character_id, player_key, _player in selected
    }
    scope_area_names = {
        node_data.get("name")
        for node_data in nodes.values()
        if node_data.get("type") == "area" and node_data.get("name")
    }
    selected_names = {player.name for _character_id, _key, player in selected}
    turn_events = [
        event for event in (getattr(world, "turn_events", []) or [])
        if event.get("actor") in selected_names
        or event.get("area") in scope_area_names
    ]
    scopes = {
        scope_id: {
            "id": scope_id,
            "name": manifest[scope_id].get("name", scope_id),
            "parent_id": manifest[scope_id].get("parent_id"),
        }
        for scope_id in sorted(scope_ids)
    }
    state = {
        "snapshot_type": "character_runtime",
        "revision": getattr(app, "_state_revision", 0),
        "character_ids": [character_id for character_id, _key, _player in selected],
        "scope_ids": sorted(scope_ids),
        "scopes": scopes,
        "players": players,
        "player_node_ids": player_node_ids,
        "turn_events": turn_events,
        "areas": areas_by_name,
        "areas_by_id": areas_by_id,
        "graph": {"nodes": nodes, "edges": list(edge_map.values())},
        "active_player": world.player_manager.active_player,
        "game_time": world.get_current_time(),
        "time_ticks": world.time_ticks,
        "time_per_tick_minutes": world.time_per_tick_minutes,
        "turn_number": world.turn_number,
        "game_day": world.game_day,
        "game_month": world.game_month,
        "game_year": world.game_year,
        "mature_content": getattr(world, "mature_content", False),
        "scenario_ended": getattr(world, "scenario_ended", False),
        "_restart_requested": getattr(world, "_restart_requested", False),
    }
    return jsonify(state)
