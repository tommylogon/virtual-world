import os
import re
import json
import logging
import random
import time
from flask import request, jsonify
from player import Player
from graph import Node, Edge, EDGE_CARRYING, EDGE_TRIGGERS, EDGE_IN, EDGE_ON, EDGE_UNDER, EDGE_BEHIND, EDGE_BESIDE, EDGE_AT
from engine.item_actions import normalize_item_actions
from routes.helpers import load_registry, save_registry, delete_registry_entry, _registry_subdir, validate_tags_on_save

logger = logging.getLogger(__name__)

REGISTRY_TYPES = ['items', 'characters', 'areas', 'ways', 'traits', 'conditions', 'behaviours', 'tags', 'triggers']

RELATION_EDGE_TYPES = {
    "in": EDGE_IN,
    "on": EDGE_ON,
    "under": EDGE_UNDER,
    "behind": EDGE_BEHIND,
    "beside": EDGE_BESIDE,
    "at": EDGE_AT,
}


def _library_type_count(data_dir, lib_type):
    try:
        subdir = os.path.join(data_dir, 'library', lib_type)
        if not os.path.isdir(subdir):
            return 0
        return len([f for f in os.listdir(subdir) if f.endswith('.json')])
    except Exception:
        return 0


def _lookup_library_item(app, item_id):
    items_reg = load_registry(app.config['DATA_DIR'], 'items.json')
    return items_reg.get(item_id)


def _content_ref_id(ref):
    if isinstance(ref, str):
        return ref.strip() or None
    if isinstance(ref, dict):
        return ref.get('id') or None
    return None


def _content_relation(ref, default="in"):
    if isinstance(ref, dict):
        rel = (ref.get('relation') or default).strip().lower()
        if rel in RELATION_EDGE_TYPES:
            return rel
    return default


def graph_add_relation_edge(graph, source, target, relation="in"):
    etype = RELATION_EDGE_TYPES.get(relation, EDGE_IN)
    for e in list(graph.edges):
        if e.source == source and e.target == target and e.type == etype:
            graph.remove_edge(e.source, e.target, e.type)
    graph.add_edge(Edge(source=source, target=target, type=etype))


def graph_add_in_edge(graph, source, target):
    graph_add_relation_edge(graph, source, target, "in")


def _materialize_trigger_nodes(graph, node_id, trigger_data):
    trigger_type = trigger_data.get('trigger_type', 'on_examine')
    effect_type = trigger_data.get('effect_type', 'message')
    effect_params = trigger_data.get('effect_params', {})
    target_name = trigger_data.get('target_name', '')
    condition = trigger_data.get('condition')
    conditions = trigger_data.get('conditions', [])
    effects = trigger_data.get('effects', [])
    target_tag = trigger_data.get('target_tag', '')

    trigger_id = f"trigger_{node_id}_{trigger_type}_{int(time.time()*1000)}_{random.randint(0,999)}"
    trig_props = {"trigger_type": trigger_type, "target_name": target_name}
    if target_tag:
        trig_props["target_tag"] = target_tag
    if effects:
        trig_props["effects"] = effects
    else:
        trig_props["effect_type"] = effect_type
        trig_props["effect_params"] = effect_params
    if condition:
        trig_props["condition"] = condition
    if conditions:
        trig_props["conditions"] = conditions
    first_effect_type = (effects[0].get('type') if effects else None) or effect_type
    trigger_node = Node(
        id=trigger_id,
        type="logic_trigger",
        name=f"{trigger_type} → {first_effect_type}",
        properties=trig_props
    )
    graph.add_node(trigger_node)
    graph.add_edge(Edge(
        source=node_id,
        target=trigger_id,
        type="triggers",
        properties=trig_props
    ))


def _spawn_library_item_node(app, item_id, lib_item, container_id=None):
    item_name = lib_item.get('name', item_id)
    node_id = f"item_{item_name}_{int(time.time()*1000)}_{random.randint(0, 999)}".lower()
    props = {
        "description": lib_item.get('description', ''),
        "actions": normalize_item_actions(lib_item.get('actions', 'examine,take,use')),
        "uses": int(lib_item.get('uses', -1)),
        "weight": float(lib_item.get('weight', 0.1)),
        "action_costs": lib_item.get('action_costs', {}),
        "skill_check": lib_item.get('skill_check', {}),
        "equip_slots": lib_item.get('equip_slots', []),
        "tags": lib_item.get('tags', []),
        "current_state": "hidden" if lib_item.get('hidden', False) else lib_item.get('current_state', 'normal'),
        "light_level": lib_item.get('light_level', 'dim'),
        "target_temperature": lib_item.get('target_temperature'),
        "heating_rate": lib_item.get('heating_rate'),
        "sound_level": lib_item.get('sound_level'),
        "sound_pattern": lib_item.get('sound_pattern'),
        "stun_chance": lib_item.get('stun_chance'),
        "stun_duration": lib_item.get('stun_duration'),
        "library_id": item_id,
        "defense": lib_item.get('defense', 0),
        "damage": lib_item.get('damage', 0),
        "insulation": lib_item.get('insulation', 0),
        "resistances": lib_item.get('resistances', {}),
        "image": lib_item.get('image') or None,
    }
    graph = app.world.graph
    node = Node(id=node_id, type='item', name=item_name, properties=props)
    graph.add_node(node)

    for child_ref in (lib_item.get('contents') or []):
        child_id = _content_ref_id(child_ref)
        if not child_id:
            continue
        child_entry = _lookup_library_item(app, child_id)
        if not child_entry:
            logger.warning("Item '%s' contents references missing library item '%s'", item_id, child_id)
            continue
        child_node_id = _spawn_library_item_node(app, child_id, child_entry)
        graph_add_relation_edge(graph, child_node_id, node_id, _content_relation(child_ref))

    if container_id:
        graph_add_in_edge(graph, node_id, container_id)

    for trigger_data in lib_item.get('triggers', []):
        _materialize_trigger_nodes(graph, node_id, trigger_data)

    return node_id


def _materialize_contained_items(app, parent_node_id, contents, logger_ctx=""):
    for child_ref in (contents or []):
        child_id = _content_ref_id(child_ref)
        if not child_id:
            continue
        child_entry = _lookup_library_item(app, child_id)
        if not child_entry:
            logger.warning("Item '%s' contents references missing library item '%s'", logger_ctx or parent_node_id, child_id)
            continue
        child_node_id = _spawn_library_item_node(app, child_id, child_entry)
        graph_add_relation_edge(app.world.graph, child_node_id, parent_node_id, _content_relation(child_ref))


def handle_library_entities(app):
    data_dir = app.config['DATA_DIR']
    result = {}
    for t in REGISTRY_TYPES:
        count = _library_type_count(data_dir, t)
        result[t] = {'count': count}
    return jsonify(result)


def handle_library_list(app, registry_type):
    if registry_type not in REGISTRY_TYPES:
        return jsonify({"error": f"Unknown registry type: {registry_type}"}), 400
    filename = f"{registry_type}.json"
    return jsonify(load_registry(app.config['DATA_DIR'], filename))


def handle_library_all(app):
    data_dir = app.config['DATA_DIR']
    raw = request.args.get('types')
    if raw:
        wanted = [t.strip() for t in raw.split(',') if t.strip() in REGISTRY_TYPES]
    else:
        wanted = list(REGISTRY_TYPES)
    result = {}
    for t in wanted:
        result[t] = load_registry(data_dir, f"{t}.json")
    return jsonify(result)


def handle_library_create_or_update(app, registry_type):
    if registry_type not in REGISTRY_TYPES:
        return jsonify({"error": f"Unknown registry type: {registry_type}"}), 400
    data = request.get_json()
    if not data or 'id' not in data:
        return jsonify({"error": "Missing 'id' in payload"}), 400
    filename = f"{registry_type}.json"
    registry = load_registry(app.config['DATA_DIR'], filename)
    if 'data' in data:
        registry[data['id']] = data['data']
    else:
        entry_data = {k: v for k, v in data.items() if k != 'id'}
        registry[data['id']] = entry_data
    save_registry(app.config['DATA_DIR'], filename, registry)

    warnings = []
    entry = registry.get(data['id'], {})
    raw_tags = entry.get('tags')
    if isinstance(raw_tags, str):
        raw_tags = [t.strip() for t in raw_tags.split(',') if t.strip()]
    if isinstance(raw_tags, (list, tuple)):
        try:
            warnings = validate_tags_on_save(list(raw_tags), app.config.get('DATA_DIR'))
        except Exception as e:
            warnings = [f"Tag validation error: {e}"]
    return jsonify({"status": "success", "warnings": warnings})


def handle_library_delete(app, registry_type, entry_id):
    if registry_type not in REGISTRY_TYPES:
        return jsonify({"error": f"Unknown registry type: {registry_type}"}), 400
    filename = f"{registry_type}.json"
    registry = load_registry(app.config['DATA_DIR'], filename)
    if entry_id not in registry:
        return jsonify({"error": "Entry not found"}), 404
    del registry[entry_id]
    delete_registry_entry(app.config['DATA_DIR'], filename, entry_id)
    return jsonify({"status": "deleted"})


def handle_library_rename(app, registry_type, entry_id):
    if registry_type not in REGISTRY_TYPES:
        return jsonify({"error": f"Unknown registry type: {registry_type}"}), 400
    data = request.get_json() or {}
    new_id = (data.get('new_id') or '').strip()
    if not new_id:
        return jsonify({"error": "Missing 'new_id'"}), 400
    filename = f"{registry_type}.json"
    registry = load_registry(app.config['DATA_DIR'], filename)
    if entry_id not in registry:
        return jsonify({"error": "Entry not found"}), 404
    if new_id == entry_id:
        return jsonify({"status": "renamed", "old": entry_id, "new": new_id})
    if new_id in registry:
        return jsonify({"error": f"An entry named '{new_id}' already exists"}), 409
    registry[new_id] = registry.pop(entry_id)
    save_registry(app.config['DATA_DIR'], filename, registry)
    delete_registry_entry(app.config['DATA_DIR'], filename, entry_id)
    return jsonify({"status": "renamed", "old": entry_id, "new": new_id})


def handle_library_place_item(app, item_id):
    data = request.get_json() or {}
    library = load_registry(app.config['DATA_DIR'], 'items.json')
    lib_item = library.get(item_id)
    if not lib_item:
        return jsonify({"error": f"Item '{item_id}' not found in library"}), 404

    item_name = lib_item.get('name', item_id)
    node_id = f"item_{item_name}_{int(time.time()*1000)}_{random.randint(0, 999)}".lower()
    tags = lib_item.get('tags', [])
    props = {
        "description": lib_item.get('description', ''),
        "actions": normalize_item_actions(lib_item.get('actions', 'examine,take,use')),
        "uses": int(lib_item.get('uses', -1)),
        "weight": float(lib_item.get('weight', 0.1)),
        "action_costs": lib_item.get('action_costs', {}),
        "skill_check": lib_item.get('skill_check', {}),
        "equip_slots": lib_item.get('equip_slots', []),
        "tags": tags,
        "current_state": "hidden" if lib_item.get('hidden', False) else lib_item.get('current_state', 'normal'),
        "light_level": lib_item.get('light_level', 'dim'),
        "target_temperature": lib_item.get('target_temperature'),
        "heating_rate": lib_item.get('heating_rate'),
        "sound_level": lib_item.get('sound_level'),
        "sound_pattern": lib_item.get('sound_pattern'),
        "stun_chance": lib_item.get('stun_chance'),
        "stun_duration": lib_item.get('stun_duration'),
        "library_id": item_id,
        "image": lib_item.get('image') or None
    }
    node = app.world.graph.get_node(node_id)
    if not node:
        node = Node(id=node_id, type='item', name=item_name, properties=props)
        app.world.graph.add_node(node)
    else:
        node.properties.update(props)

    for child_ref in (lib_item.get('contents') or []):
        child_id = _content_ref_id(child_ref)
        if not child_id:
            continue
        child_entry = _lookup_library_item(app, child_id)
        if not child_entry:
            logger.warning("Item '%s' contents references missing library item '%s'", item_id, child_id)
            continue
        child_node_id = _spawn_library_item_node(app, child_id, child_entry)
        graph_add_in_edge(app.world.graph, child_node_id, node_id)

    node_id_l = node_id.lower()
    for e in app.world.graph.edges[:]:
        if e.source.lower() == node_id_l and e.type in (EDGE_IN, EDGE_CARRYING):
            app.world.graph.remove_edge(e.source, e.target, e.type)

    container_id = data.get('container')
    character_id = data.get('character')
    area_name = data.get('area')
    if container_id:
        if app.world.graph.get_node(container_id):
            app.world.graph.add_edge(Edge(source=node_id, target=container_id, type=EDGE_IN))
        else:
            return jsonify({"error": f"Container '{container_id}' not found"}), 400
    elif character_id:
        if app.world.graph.get_node(character_id):
            app.world.graph.add_edge(Edge(source=node_id, target=character_id, type=EDGE_CARRYING))
        else:
            return jsonify({"error": f"Character '{character_id}' not found"}), 400
    elif area_name:
        area_node_id = app.world._area_node_id(area_name)
        for n in app.world.graph.nodes.values():
            if n.type == "area" and n.name == area_name:
                area_node_id = n.id
                break
        app.world.graph.add_edge(Edge(source=node_id, target=area_node_id, type=EDGE_IN))
    else:
        return jsonify({"error": "Missing target: 'area', 'container', or 'character'"}), 400

    for trigger_data in lib_item.get('triggers', []):
        _materialize_trigger_nodes(app.world.graph, node_id, trigger_data)

    return jsonify({"status": "success", "node_id": node_id})


def handle_library_import_character(app, char_id):
    data = request.get_json() or {}
    make_active = data.get('active', True)
    area_name = data.get('area') or data.get('current_area', '')

    chars = load_registry(app.config['DATA_DIR'], 'characters.json')
    if char_id not in chars:
        return jsonify({"error": f"Character '{char_id}' not found in library"}), 404

    cdata = chars[char_id]
    player_name = cdata.get('name', char_id)

    player = Player(player_name)
    player.stats = cdata.get('stats', player.stats)
    player.vitals = cdata.get('vitals', player.vitals)
    player.decay_rates = cdata.get('decay_rates', player.decay_rates)
    player.skills = cdata.get('skills', player.skills)
    player.traits = cdata.get('traits', player.traits)
    player.tags = cdata.get('tags', player.tags)
    player.interest_tags = cdata.get('interest_tags', player.interest_tags)
    player.personality = cdata.get('personality', '')
    player.description = cdata.get('description', '')
    player.base_description = cdata.get('base_description', '')
    player.unknown_name = cdata.get('unknown_name', '')
    player.emotion = cdata.get('emotion', {})
    player.memories = cdata.get('memories', [])
    player.behaviors = cdata.get('behaviors', [])
    player.npc_behavior = cdata.get('npc_behavior', 'wander')
    player.npc_action_interval = cdata.get('npc_action_interval', 3)
    player.simple_npc = cdata.get('simple_npc', False)
    player.relationships = cdata.get('relationships', {})
    conditions = cdata.get('conditions')
    if conditions:
        player.load_conditions(conditions)
    equipped = cdata.get('equipped')
    if equipped:
        player.equipped = dict(equipped)
    activity = cdata.get('activity')
    if activity:
        player.activity = activity
    app.world.add_player(player)

    target_area = area_name or cdata.get('current_area', '')
    if target_area:
        try:
            app.world.set_player_area(player_name, target_area)
        except Exception as e:
            logger.warning(f"Could not place '{player_name}' in area '{target_area}': {e}")

    inventory = cdata.get('inventory', [])
    if isinstance(inventory, list):
        lib_items = load_registry(app.config['DATA_DIR'], 'items.json')
        player_node_id = f"player_{player_name}".replace(' ', '_')
        for inv_entry in inventory:
            if isinstance(inv_entry, str):
                lib_id = inv_entry
                if lib_id in lib_items:
                    item_data = lib_items[lib_id].copy()
                    item_name = item_data.get('name', lib_id)
                    node_id = f"item_{player_name}_{item_name}"
                    props = {
                        "description": item_data.get('description', ''),
                        "actions": normalize_item_actions(item_data.get('actions', 'examine,take,use')),
                        "uses": int(item_data.get('uses', -1)),
                        "weight": float(item_data.get('weight', 0.1)),
                        "tags": item_data.get('tags', []),
                        "current_state": "hidden" if item_data.get('hidden', False) else item_data.get('current_state', 'normal'),
                        "library_id": lib_id,
                        "image": item_data.get('image') or None
                    }
                    node = Node(id=node_id, type='item', name=item_name, properties=props)
                    app.world.graph.add_node(node)
                    app.world.graph.add_edge(
                        Edge(source=node_id, target=player_node_id, type=EDGE_CARRYING)
                    )
            elif isinstance(inv_entry, dict):
                item_name = inv_entry.get('name', 'Item')
                lib_id = inv_entry.get('library_id') or ''
                node_id = inv_entry.get('node_id') or f"item_{player_name}_{item_name}_{random.randint(100,999)}"
                if app.world.graph.get_node(node_id):
                    node_id = f"item_{player_name}_{item_name}_{random.randint(100,999)}"
                props = dict(inv_entry.get('properties', {}))
                props.setdefault('library_id', lib_id)
                if not props.get('name'):
                    props['name'] = item_name
                node = Node(id=node_id, type='item', name=item_name, properties=props)
                app.world.graph.add_node(node)
                app.world.graph.add_edge(
                    Edge(source=node_id, target=player_node_id, type=EDGE_CARRYING)
                )
                if lib_id and lib_id not in lib_items:
                    entry_data = {k: v for k, v in props.items()}
                    lib_items[lib_id] = entry_data
                    save_registry(app.config['DATA_DIR'], 'items.json', lib_items)

    equipped = cdata.get('equipped') or {}
    if isinstance(equipped, dict):
        resolved = {}
        for slot, stack in equipped.items():
            if not isinstance(stack, list):
                continue
            resolved_slot = []
            for entry in stack:
                if not entry or str(entry).startswith('__'):
                    resolved_slot.append(entry)
                    continue
                name = entry.get('name', entry) if isinstance(entry, dict) else entry
                node_id = entry.get('node_id') if isinstance(entry, dict) else None
                if node_id and app.world.graph.get_node(node_id):
                    resolved_slot.append(node_id)
                    continue
                found = None
                for edge in app.world.graph.get_edges_for_target(player_node_id, EDGE_CARRYING):
                    n = app.world.graph.get_node(edge.source)
                    if n and n.name == name:
                        found = n.id
                        break
                if found:
                    resolved_slot.append(found)
                elif isinstance(entry, dict):
                    # Self-contained: if the embedded item def carries properties and
                    # the node isn't already in the world, materialize it from the
                    # embedded copy (so a character is portable without item files).
                    props = entry.get('properties') if isinstance(entry.get('properties'), dict) else None
                    node_id = entry.get('node_id')
                    if props and (not node_id or not app.world.graph.get_node(node_id)):
                        item_name = entry.get('name') or props.get('name') or 'Item'
                        node_id = entry.get('node_id') or f"item_{player_name}_{item_name}_{random.randint(100,999)}"
                        if app.world.graph.get_node(node_id):
                            node_id = f"item_{player_name}_{item_name}_{random.randint(100,999)}"
                        props2 = dict(props)
                        props2.setdefault('library_id', entry.get('library_id') or '')
                        if not props2.get('name'):
                            props2['name'] = item_name
                        newnode = Node(id=node_id, type='item', name=item_name, properties=props2)
                        app.world.graph.add_node(newnode)
                        app.world.graph.add_edge(Edge(source=node_id, target=player_node_id, type=EDGE_CARRYING))
                        resolved_slot.append(node_id)
                        continue
                    resolved_slot.append(entry.get('node_id') or f"item_{player_name}_{name}")
            resolved[slot] = resolved_slot
        player.equipped = resolved

    if make_active:
        app.world.set_active_player(player_name)

    return jsonify({"status": "imported", "player": player_name})


def handle_library_import_area(app, area_id):
    data = request.get_json() or {}
    rooms_reg = load_registry(app.config['DATA_DIR'], 'areas.json')
    if area_id not in rooms_reg:
        return jsonify({"error": f"Area '{area_id}' not found in library"}), 404

    area_data = rooms_reg[area_id]
    area_name = data.get('name', area_data.get('name', area_id))
    area_desc = area_data.get('description', '')
    area_tags = area_data.get('tags', [])

    from area import Area
    from graph import Edge

    area = Area(area_name, area_desc, area_tags)
    app.world.add_area(area)
    area_node_id = app.world._area_node_id(area_name)

    from graph import Node, EDGE_IN
    lib_items = load_registry(app.config['DATA_DIR'], 'items.json')
    area_items = area_data.get('items', [])
    for entry in area_items:
        if isinstance(entry, str):
            lib_id = entry
            if lib_id in lib_items:
                item_data = lib_items[lib_id].copy()
                item_name = item_data.get('name', lib_id)
                node_id = f"item_{area_name}_{item_name}"
                node = Node(id=node_id, type='item', name=item_name, properties={
                    "description": item_data.get('description', ''),
                    "actions": normalize_item_actions(item_data.get('actions', 'examine,take,use')),
                    "uses": int(item_data.get('uses', -1)),
                    "weight": float(item_data.get('weight', 0.1)),
                    "tags": item_data.get('tags', []),
                    "current_state": "hidden" if item_data.get('hidden', False) else item_data.get('current_state', 'normal'),
                    "library_id": lib_id,
                    "image": item_data.get('image') or None
                })
                app.world.graph.add_node(node)
                app.world.graph.add_edge(Edge(source=node_id, target=area_node_id, type=EDGE_IN))
                _materialize_contained_items(app, node_id, item_data.get('contents', []), item_name)
        elif isinstance(entry, dict):
            lib_id = entry.get('library_id', entry.get('id', ''))
            item_name = entry.get('name', 'Item')
            node_id = f"item_{area_name}_{item_name}_{random.randint(100,999)}"
            node = Node(id=node_id, type='item', name=item_name, properties=entry)
            app.world.graph.add_node(node)
            app.world.graph.add_edge(Edge(source=node_id, target=area_node_id, type=EDGE_IN))
            _materialize_contained_items(app, node_id, entry.get('contents', []), item_name)
            item_lib_id = lib_id or re.sub(r'[^a-z0-9_]+', '_', item_name.lower())
            items_reg = load_registry(app.config['DATA_DIR'], 'items.json')
            if item_lib_id not in items_reg:
                entry_data = {k: v for k, v in entry.items() if k not in ('id', 'library_id')}
                items_reg[item_lib_id] = entry_data
                save_registry(app.config['DATA_DIR'], 'items.json', items_reg)

    return jsonify({"status": "imported", "area": area_name, "area_node_id": area_node_id})


def handle_library_import_way(app, way_id):
    """Create a way node from the library def and connect it between two areas.

    Body: {area_from, area_to, dir_from, dir_to?} — dirs default to "out".
    Mirrors the area/character import pattern so a library way (e.g. the blind
    corner) can be dropped into the world and wired between two rooms.
    """
    from routes.helpers import load_registry
    import re
    data = request.get_json() or {}
    ways_reg = load_registry(app.config["DATA_DIR"], "ways.json")
    if way_id not in ways_reg:
        return jsonify({"error": f"Way '{way_id}' not found in library"}), 404
    w = ways_reg[way_id]
    area_from = data.get("area_from") or ""
    area_to = data.get("area_to") or ""
    if not area_from or not area_to:
        return jsonify({"error": "Need area_from and area_to"}), 400
    if area_from.lower() == area_to.lower():
        return jsonify({"error": "area_from and area_to must differ"}), 400
    dir_from = data.get("dir_from") or "out"
    dir_to = data.get("dir_to") or "out"

    world = app.world
    # way node id derived from library id (filename stem) -> way_<id>
    node_id = "way_" + re.sub(r"[^a-z0-9_]+", "_", way_id.lower())
    if world.graph.get_node(node_id):
        return jsonify({"error": f"Way node '{node_id}' already in world"}), 409

    name = w.get("name") or node_id
    props = {}
    for k in ("current_state", "description", "pass_message", "requires",
              "max_size", "auto_close", "see_through", "one_way", "prevent_close",
              "edge_length", "needs_open", "parameters", "cost", "tags"):
        if k in w:
            props[k] = w[k]
    props["area_from"] = area_from
    props["area_to"] = area_to
    node = Node(id=node_id, type="way", name=name, properties=props)
    world.graph.add_node(node)

    # bidirectional connection via the way node (mirrors movement.connect_areas)
    fa = world._area_node_id(area_from)
    ta = world._area_node_id(area_to)
    world.graph.add_edge(Edge(source=fa, target=node_id, type="connection",
                              properties={"direction": dir_from}))
    world.graph.add_edge(Edge(source=node_id, target=ta, type="connection",
                              properties={"direction": dir_to}))
    world.graph.add_edge(Edge(source=ta, target=node_id, type="connection",
                              properties={"direction": dir_to}))
    world.graph.add_edge(Edge(source=node_id, target=fa, type="connection",
                              properties={"direction": dir_from}))
    return jsonify({"status": "imported", "way": node_id, "way_node_id": node_id})


def handle_refresh_way_from_library(app, node_id):
    node = app.world.graph.get_node(node_id)
    if not node or node.type != 'way':
        return jsonify({"error": "Way node not found"}), 404
    data = request.get_json() or {}
    return _refresh_way(app, node, data.get('sections'))


def handle_library_refresh_to_world(app):
    data = request.get_json() or {}
    node_id = data.get('node_id')
    if not node_id:
        return jsonify({"error": "Missing 'node_id'"}), 400
    node = app.world.graph.get_node(node_id)
    if not node:
        return jsonify({"error": "Node not found"}), 404
    sections = data.get('sections')
    template_id = data.get('template_id') or data.get('library_id')
    if node.type == 'item':
        return _refresh_item(app, node, sections, template_id)
    if node.type == 'way':
        return _refresh_way(app, node, sections, template_id)
    if node.type == 'area':
        return _refresh_area(app, node, sections, template_id)
    if node.type == 'character':
        return _refresh_character(app, node, sections, template_id)
    return jsonify({"error": f"Type '{node.type}' does not support refresh-to-world"}), 400


def _refresh_item(app, node, sections, template_id=None):
    current_library_id = node.properties.get('library_id', '')
    library_id = template_id or current_library_id
    if not library_id:
        return jsonify({"error": "Item has no library template — cannot refresh"}), 400

    library = load_registry(app.config['DATA_DIR'], 'items.json')
    lib_item = library.get(library_id)
    if not lib_item:
        return jsonify({"error": f"Library item '{library_id}' not found"}), 404

    locked = set(node.properties.get('locked_fields', []))

    if sections:
        prop_map = {
            'name': 'name', 'description': 'description', 'actions': 'actions',
            'uses': 'uses', 'weight': 'weight', 'equip_slots': 'equip_slots',
            'current_state': 'current_state', 'light_level': 'light_level',
            'target_temperature': 'target_temperature', 'heating_rate': 'heating_rate',
            'sound_level': 'sound_level', 'sound_pattern': 'sound_pattern',
            'stun_chance': 'stun_chance', 'stun_duration': 'stun_duration',
            'defense': 'defense', 'damage': 'damage', 'insulation': 'insulation',
            'resistances': 'resistances', 'action_costs': 'action_costs',
            'skill_check': 'skill_check', 'contents': 'contents',
            'aliases': 'aliases', 'tags': 'tags', 'image': 'image',
        }
        if 'name' in sections and 'name' not in locked and lib_item.get('name'):
            node.name = lib_item['name']
        for section_key, prop_key in prop_map.items():
            if section_key in sections and prop_key not in locked:
                if lib_item.get(prop_key) is not None:
                    value = lib_item[prop_key]
                    if prop_key == 'actions':
                        value = normalize_item_actions(value)
                    node.properties[prop_key] = value
    else:
        lib_props = {
            "description": lib_item.get('description', ''),
            "actions": normalize_item_actions(lib_item.get('actions', 'examine,take,use')),
            "uses": int(lib_item.get('uses', -1)),
            "weight": float(lib_item.get('weight', 0.1)),
            "equip_slots": lib_item.get('equip_slots', []),
            "tags": lib_item.get('tags', []),
            "current_state": "hidden" if lib_item.get('hidden', False) else lib_item.get('current_state', 'normal'),
            "light_level": lib_item.get('light_level', 'dim'),
            "target_temperature": lib_item.get('target_temperature'),
            "heating_rate": lib_item.get('heating_rate'),
            "sound_level": lib_item.get('sound_level'),
            "sound_pattern": lib_item.get('sound_pattern'),
            "stun_chance": lib_item.get('stun_chance'),
            "stun_duration": lib_item.get('stun_duration'),
            "defense": lib_item.get('defense', 0),
            "damage": lib_item.get('damage', 0),
            "insulation": lib_item.get('insulation', 0),
            "resistances": lib_item.get('resistances', {}),
            "action_costs": lib_item.get('action_costs', {}),
            "skill_check": lib_item.get('skill_check', {}),
            "contents": lib_item.get('contents', []),
            "aliases": lib_item.get('aliases', []),
            "image": lib_item.get('image') or None,
        }
        if lib_item.get('name'):
            node.name = lib_item['name']
        for key, val in lib_props.items():
            if key not in locked:
                node.properties[key] = val

    rebuild_triggers = (not sections and 'triggers' not in locked) or (sections and 'triggers' in sections and 'triggers' not in locked)
    if rebuild_triggers:
        _rebuild_triggers(app, node, lib_item.get('triggers', []))

    if template_id and template_id != current_library_id:
        node.properties['library_id'] = template_id

    return jsonify({"status": "refreshed", "node_id": node.id, "applied": sections if sections else ["all"]})


def _refresh_way(app, node, sections, template_id=None):
    props = node.properties or {}
    way_id = template_id or props.get('library_id') or ''
    if not way_id:
        way_name = props.get('name', node.name or '')
        way_id = re.sub(r'[^a-z0-9_]+', '_', way_name.lower()) if way_name else node.id

    ways_reg = load_registry(app.config['DATA_DIR'], 'ways.json')
    lib_way = ways_reg.get(way_id)
    if not lib_way:
        return jsonify({"error": f"Way '{way_id}' not found in library"}), 404

    locked = set(props.get('locked_fields', []))

    if sections is None:
        lib_props = {
            'name': lib_way.get('name', node.name),
            'description': lib_way.get('description', ''),
            'current_state': lib_way.get('current_state', 'closed'),
            'pass_message': lib_way.get('pass_message', ''),
            'edge_length': lib_way.get('edge_length', ''),
            'needs_open': lib_way.get('needs_open', {}),
            'auto_close': bool(lib_way.get('auto_close', False)),
            'see_through': bool(lib_way.get('see_through', False)),
            'one_way': bool(lib_way.get('one_way', False)),
            'requires': lib_way.get('requires', ''),
            'max_size': lib_way.get('max_size', ''),
            'sound_barrier': lib_way.get('sound_barrier'),
            'prevent_close': bool(lib_way.get('prevent_close', False)),
            'tags': lib_way.get('tags', []),
            'parameters': lib_way.get('parameters', {}),
        }
        for key, val in lib_props.items():
            if key not in locked:
                props[key] = val
        node.properties = props
        rebuild_triggers = 'triggers' not in locked
        applied = ['all']
    else:
        if 'name' in sections and 'name' not in locked:
            node.name = lib_way.get('name', node.name)

        prop_map = {
            'description': 'description', 'current_state': 'current_state',
            'pass_message': 'pass_message', 'needs_open': 'needs_open',
            'auto_close': 'auto_close', 'see_through': 'see_through',
            'one_way': 'one_way', 'requires': 'requires', 'max_size': 'max_size',
            'prevent_close': 'prevent_close', 'edge_length': 'edge_length',
            'sound_barrier': 'sound_barrier',
            'tags': 'tags', 'parameters': 'parameters',
        }
        for section_key, prop_key in prop_map.items():
            if section_key in sections and prop_key not in locked:
                if lib_way.get(prop_key) is not None:
                    props[prop_key] = lib_way[prop_key]
        node.properties = props
        rebuild_triggers = 'triggers' in sections and 'triggers' not in locked
        applied = sections

    if rebuild_triggers:
        _rebuild_triggers(app, node, lib_way.get('triggers', []))

    if template_id and node.properties.get('library_id') != template_id:
        node.properties['library_id'] = template_id

    return jsonify({"status": "refreshed", "node_id": node.id, "applied": applied})


def _refresh_area(app, node, sections, template_id=None):
    props = node.properties or {}
    area_id = template_id or props.get('library_id') or ''
    if not area_id:
        node_id = node.id or ''
        area_id = re.sub(r'^area_', '', node_id)
        if not area_id or area_id == node_id:
            name = props.get('name', node.name or '')
            area_id = re.sub(r'[^a-z0-9_]+', '_', name.lower()) if name else node.id

    areas_reg = load_registry(app.config['DATA_DIR'], 'areas.json')
    lib_area = areas_reg.get(area_id)
    if not lib_area:
        return jsonify({"error": f"Area '{area_id}' not found in library"}), 404

    locked = set(props.get('locked_fields', []))

    if sections is None:
        if 'name' not in locked and lib_area.get('name'):
            node.name = lib_area['name']
        for key in ('description', 'tags', 'environment'):
            if key not in locked and lib_area.get(key) is not None:
                props[key] = lib_area[key]
        node.properties = props
        rebuild_triggers = 'triggers' not in locked
        applied = ['all']
    else:
        if 'name' in sections and 'name' not in locked and lib_area.get('name'):
            node.name = lib_area['name']
        for key in ('description', 'tags', 'environment'):
            if key in sections and key not in locked and lib_area.get(key) is not None:
                props[key] = lib_area[key]
        node.properties = props
        rebuild_triggers = 'triggers' in sections and 'triggers' not in locked
        applied = sections

    if rebuild_triggers:
        _rebuild_triggers(app, node, lib_area.get('triggers', []))

    if template_id and props.get('library_id') != template_id:
        props['library_id'] = template_id
        node.properties = props

    return jsonify({"status": "refreshed", "node_id": node.id, "applied": applied})


def _refresh_character(app, node, sections, template_id=None):
    props = node.properties or {}
    char_id = template_id or props.get('library_id') or node.name or ''
    char_reg = load_registry(app.config['DATA_DIR'], 'characters.json')
    lib_char = char_reg.get(char_id)
    if not lib_char:
        return jsonify({"error": f"Character '{char_id}' not found in library"}), 404

    player = app.world.player_manager.get_player(node.name) if hasattr(app.world, 'player_manager') else None
    if player is None:
        return jsonify({"error": f"Character '{node.name}' not found in world"}), 404

    editable_map = {
        'name': 'name',
        'description': 'description',
        'base_description': 'base_description',
        'unknown_name': 'unknown_name',
        'personality': 'personality',
        'stats': 'stats',
        'skills': 'skills',
        'traits': 'traits',
        'tags': ('tags', 'list'),
        'interest_tags': ('interest_tags', 'list'),
        'behaviors': 'behaviors',
        'npc_behavior': 'npc_behavior',
        'npc_action_interval': 'npc_action_interval',
        'npc_state': 'npc_state',
        'simple_npc': 'simple_npc',
        'memories': ('memories', 'list'),
        'relationships': ('relationships', 'dict'),
        'vitals': ('vitals', 'dict'),
        'decay_rates': ('decay_rates', 'dict'),
        'conditions': ('conditions', 'dict'),
        'equipped': ('equipped', 'dict'),
        'recent_hearing': ('recent_hearing', 'list'),
        'activity': ('activity', 'scalar'),
        'current_area': ('current_area', 'area'),
        'emotion': ('emotion', 'emotion'),
    }

    def assign(player_field, value, kind=None):
        if kind == 'list':
            setattr(player, player_field, list(value if isinstance(value, (list, tuple)) else []))
        elif kind == 'dict':
            setattr(player, player_field, dict(value) if isinstance(value, dict) else {})
        elif kind == 'area':
            # Standalone characters: only set current_area if that area actually
            # exists in THIS world. A library character may carry a current_area
            # from another scenario — don't error or strand them, just leave them
            # where they are.
            try:
                aid = app.world._area_node_id(value)
                if value and app.world.graph.get_node(aid) is None:
                    return
            except Exception:
                return
            setattr(player, player_field, value)
            try:
                if hasattr(app.world, 'name_matcher') and hasattr(app.world.name_matcher, '_set_player_area'):
                    app.world.name_matcher._set_player_area(node.name, value)
            except Exception:
                pass
        elif kind == 'emotion':
            if isinstance(value, dict):
                player.emotion = str(value.get('current') or 'neutral')
                try:
                    player.emotion_intensity = float(value.get('intensity') or 0)
                except (TypeError, ValueError):
                    player.emotion_intensity = 0.0
        else:
            setattr(player, player_field, value)

    if sections is None:
        for section_key, target in editable_map.items():
            if isinstance(target, tuple):
                player_field, kind = target
            else:
                player_field, kind = target, None
            if lib_char.get(section_key) is not None:
                assign(player_field, lib_char[section_key], kind)
        applied = ['all']
    else:
        for section_key in sections:
            if section_key not in editable_map:
                continue
            if lib_char.get(section_key) is None:
                continue
            target = editable_map[section_key]
            if isinstance(target, tuple):
                player_field, kind = target
            else:
                player_field, kind = target, None
            assign(player_field, lib_char[section_key], kind)
        applied = sections

    if template_id:
        props['library_id'] = template_id
        node.properties = props

    return jsonify({"status": "refreshed", "node_id": node.id, "applied": applied})


def _rebuild_triggers(app, node, lib_triggers):
    node_id = node.id
    old_trigger_ids = set()
    for edge in app.world.graph.edges[:]:
        if edge.source == node_id and edge.type == EDGE_TRIGGERS:
            old_trigger_ids.add(edge.target)
            app.world.graph.remove_edge(edge.source, edge.target, edge.type)
    for tid in old_trigger_ids:
        app.world.graph.remove_node(tid)

    for trigger_data in lib_triggers:
        trigger_type = trigger_data.get('trigger_type', 'on_examine')
        effect_type = trigger_data.get('effect_type', 'message')
        effect_params = trigger_data.get('effect_params', {})
        target_name = trigger_data.get('target_name', '')
        condition = trigger_data.get('condition')
        conditions = trigger_data.get('conditions', {})
        effects = trigger_data.get('effects', [])
        target_tag = trigger_data.get('target_tag', '')

        tid = f"trigger_{node_id}_{trigger_type}_{int(time.time()*1000)}_{random.randint(0,999)}"
        trig_props = {"trigger_type": trigger_type, "target_name": target_name}
        if target_tag:
            trig_props["target_tag"] = target_tag
        if effects:
            trig_props["effects"] = effects
        else:
            trig_props["effect_type"] = effect_type
            trig_props["effect_params"] = effect_params
        if condition:
            trig_props["condition"] = condition
        if conditions:
            trig_props["conditions"] = conditions

        first_eff = (effects[0].get('type') if effects else None) or effect_type
        trigger_node = Node(id=tid, type="logic_trigger", name=f"{trigger_type} → {first_eff}", properties=trig_props)
        app.world.graph.add_node(trigger_node)
        app.world.graph.add_edge(Edge(source=node_id, target=tid, type=EDGE_TRIGGERS, properties=trig_props))
