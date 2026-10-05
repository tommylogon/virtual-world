"""library_ops: the library registry API and item materialisation.

@module library_ops
@contributes the library registry API and item materialisation
@docs docs/virtualWorld/Library System/Library System Overview.md
"""

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
from engine import behaviors as behavior_library
from engine import sync
from engine.abilities import normalize_stat_block
from engine.library_nodes import RELATION_EDGE_TYPES, library_item_properties
from engine.serialization import canonical_vitals
from routes.helpers import load_registry, save_registry, delete_registry_entry, _registry_subdir, validate_tags_on_save

logger = logging.getLogger(__name__)

REGISTRY_TYPES = ['items', 'characters', 'areas', 'ways', 'traits', 'conditions', 'behaviours', 'tags', 'triggers', 'structures', 'pursuit_templates']

# task-398: RELATION_EDGE_TYPES now comes from engine/library_nodes.py, which is
# the one definition shared with the generation recipes. routes/graph_ops.py
# still keeps its own copy.


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


def _spawn_library_item_node(app, item_id, lib_item, container_id=None, node_id=None):
    item_name = lib_item.get('name', item_id)
    if not node_id:
        # Generated ids embed the display name (lowercased, spaces included) plus
        # a timestamp and random suffix, so they are neither stable nor
        # re-derivable. Authored placement (tools/add_renewable_sources.py)
        # passes its own deterministic id instead.
        #
        # task-398: a generation recipe needs the opposite — a stable, scoped id
        # and no clock — so it uses engine/library_nodes.py instead. What is
        # shared is the property mapping below, which is the part that defines
        # what a library item node *is*.
        node_id = f"item_{item_name}_{int(time.time()*1000)}_{random.randint(0, 999)}".lower()
    props = library_item_properties(lib_item, item_id)
    props['actions'] = normalize_item_actions(lib_item.get('actions', 'examine,take,use'))
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


def materialize_library_item(app, library_id):
    """Create a world node for a library item WITHOUT placing it.

    Public materialization service for engine/tool callers (task-9). The caller
    writes the spatial edge afterwards (see ``graph_add_relation_edge``), which
    keeps the population engine free of Flask/route-private helpers.

    Returns the new node id, or None when the library entry is missing.
    """
    lib_item = _lookup_library_item(app, library_id)
    if not lib_item:
        return None
    return _spawn_library_item_node(app, library_id, lib_item)


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


def _ensure_carrying_edge(graph, source_id, target_id):
    """Idempotently link a carried item node to its player."""
    for e in graph.edges:
        if e.source == source_id and e.target == target_id and e.type == EDGE_CARRYING:
            return
    graph.add_edge(Edge(source=source_id, target=target_id, type=EDGE_CARRYING))


def _materialize_character_inventory(app, player_name, player_node_id, inventory,
                                     register_missing=False):
    """Materialize a character's authored ``inventory`` onto the world graph.

    One implementation for both import and refresh-to-world (bug-516/task-519),
    so the two paths cannot disagree about what an inventory entry means:

    - a **string** entry is a library-id reference;
    - a **dict** entry may carry a stable ``node_id``, a ``library_id`` and
      per-instance ``properties`` overrides.

    Both go through :func:`engine.library_nodes.library_item_properties`, so
    ``equip_slots``, ``damage``/``damage_type``, ``defense``, ``insulation``,
    ``light_level``, ``triggers`` and ``contents`` survive the character path the
    same way they survive ``place_library_item``. Idempotent: an existing node id
    is reused, never duplicated.

    Returns ``[(node_id, library_id, name), ...]`` for everything the character
    carries -- including items that already existed -- so equipped references can
    be resolved against it.
    """
    graph = app.world.graph
    lib_items = load_registry(app.config['DATA_DIR'], 'items.json')
    carried = []

    for entry in inventory or []:
        lib_id = None
        node_id = None
        name = None
        overrides = {}
        if isinstance(entry, str):
            lib_id = entry.strip()
        elif isinstance(entry, dict):
            lib_id = str(entry.get('library_id') or '').strip()
            node_id = entry.get('node_id') or None
            name = entry.get('name') or None
            if isinstance(entry.get('properties'), dict):
                overrides = entry['properties']
        else:
            continue

        lib_item = lib_items.get(lib_id) if lib_id else None
        if lib_item is None and lib_id and overrides and register_missing:
            # Legacy import convenience: a self-contained dict entry whose
            # library_id is not yet a template registers its inline copy, so a
            # later refresh can resolve it. Refresh must not mutate the library,
            # so this only happens on import.
            entry_data = dict(overrides)
            entry_data.setdefault('name', name or lib_id)
            lib_items[lib_id] = entry_data
            save_registry(app.config['DATA_DIR'], 'items.json', lib_items)
            lib_item = entry_data
        if lib_item is None and not overrides:
            logger.warning("Character '%s' inventory references missing library item '%s'",
                           player_name, lib_id)
            continue

        if not node_id:
            base = (lib_item.get('name') if lib_item else None) or name or lib_id or 'item'
            node_id = f"item_{player_name}_{base}".lower()

        node = graph.get_node(node_id)
        if node is None:
            if lib_item is not None:
                node_id = _spawn_library_item_node(app, lib_id, lib_item, node_id=node_id)
                node = graph.get_node(node_id)
            else:
                props = dict(overrides)
                props.setdefault('library_id', lib_id or '')
                node = Node(id=node_id, type='item', name=name or 'Item', properties=props)
                graph.add_node(node)
        if node is not None and overrides:
            node.properties.update(overrides)
        if node is not None and name:
            node.name = name

        _ensure_carrying_edge(graph, node_id, player_node_id)
        node = graph.get_node(node_id)
        carried.append((
            node_id,
            (node.properties or {}).get('library_id') if node else lib_id,
            node.name if node else name,
        ))
    return carried


def _resolve_character_equipped(carried, raw_equipped):
    """Resolve authored equipped references to runtime node-id strings.

    ``carried`` is :func:`_materialize_character_inventory`'s output. A reference
    may be an existing node id, a carried inventory node's id, its library id, or
    its display name -- checked in that order. Anything that does not resolve is
    dropped, never written through: ``player.equipped[slot]`` must hold node-id
    strings everywhere it is read (bug-516; engine/equipment.py:205/:265,
    engine/body_parts.py:260).

    ``__...`` runtime markers (``__multi_slot_<id>``) pass through untouched.
    """
    by_node = {}
    by_lib = {}
    by_name = {}
    for node_id, lib_id, name in carried:
        by_node[str(node_id)] = node_id
        if lib_id:
            by_lib.setdefault(str(lib_id), node_id)
        if name:
            by_name.setdefault(str(name).strip().lower(), node_id)

    resolved = {}
    if not isinstance(raw_equipped, dict):
        return resolved
    for slot, stack in raw_equipped.items():
        if not isinstance(stack, list):
            logger.warning("Equipped slot '%s' is not a list -- ignored", slot)
            continue
        out = []
        for ref in stack:
            if not ref:
                continue
            if isinstance(ref, dict):
                key = ref.get('node_id') or ref.get('library_id') or ref.get('name')
            else:
                key = ref
            if key is None:
                continue
            if str(key).startswith('__'):
                out.append(key)
                continue
            match = (by_node.get(str(key))
                     or by_lib.get(str(key))
                     or by_name.get(str(key).strip().lower()))
            if match:
                out.append(match)
            else:
                logger.warning(
                    "Equipped slot '%s' references '%s', which is not in inventory -- dropped",
                    slot, key)
        resolved[slot] = out
    return resolved


def handle_library_entities(app):
    data_dir = app.config['DATA_DIR']
    result = {}
    for t in REGISTRY_TYPES:
        count = _library_type_count(data_dir, t)
        result[t] = {'count': count}
    return jsonify(result)


def _filter_mature_entries(app, registry_type, data):
    """task-213/462: hide adult traits/conditions from library listings/pickers
    unless the mature_content toggle is on. Definitions stay functional for
    characters that already carry them."""
    if registry_type not in ('traits', 'conditions'):
        return data
    if getattr(app.world, 'mature_content', False):
        return data
    if not isinstance(data, dict):
        return data
    return {
        key: value for key, value in data.items()
        if not (isinstance(value, dict) and value.get('mature'))
    }


def _reload_condition_catalog(app, registry_type):
    """task-462/task-590: engine runtime catalogs re-read the JSON library after a
    write so an edit takes effect without an app restart. Conditions and the
    reusable behaviour and pursuit-template libraries are reloaded here."""
    if registry_type == 'conditions':
        try:
            from engine.player_conditions import reload_condition_library
            reload_condition_library()
        except Exception as e:
            logger.warning(f"Condition catalog reload failed: {e}")
    elif registry_type == 'behaviours':
        try:
            behavior_library.reload(app.config.get('DATA_DIR'))
        except Exception as e:
            logger.warning(f"Behaviour library reload failed: {e}")
    elif registry_type == 'pursuit_templates':
        try:
            from engine import pursuit_templates
            pursuit_templates.reload(app.config.get('DATA_DIR'))
        except Exception as e:
            logger.warning(f"Pursuit-template catalog reload failed: {e}")


def handle_library_list(app, registry_type):
    if registry_type not in REGISTRY_TYPES:
        return jsonify({"error": f"Unknown registry type: {registry_type}"}), 400
    filename = f"{registry_type}.json"
    data = load_registry(app.config['DATA_DIR'], filename)
    return jsonify(_filter_mature_entries(app, registry_type, data))


def handle_library_all(app):
    data_dir = app.config['DATA_DIR']
    raw = request.args.get('types')
    if raw:
        wanted = [t.strip() for t in raw.split(',') if t.strip() in REGISTRY_TYPES]
    else:
        wanted = list(REGISTRY_TYPES)
    result = {}
    for t in wanted:
        data = load_registry(data_dir, f"{t}.json")
        result[t] = _filter_mature_entries(app, t, data)
    return jsonify(result)


#: Node properties that describe where a node sits on the CANVAS, not the thing
#: itself. They must never reach a library template, or every world laid out over
#: a map would leak its coordinates into the archetype.
PRESENTATION_ONLY_PROPERTIES = ('x', 'y')


def _strip_presentation_properties(entry):
    """Copy *entry* without its canvas-only properties (x/y)."""
    if not isinstance(entry, dict):
        return entry
    props = entry.get('properties')
    if not isinstance(props, dict):
        return entry
    cleaned = {k: v for k, v in props.items() if k not in PRESENTATION_ONLY_PROPERTIES}
    if len(cleaned) == len(props):
        return entry
    entry = dict(entry)
    entry['properties'] = cleaned
    return entry


def _docs_warnings(entry_data):
    """Warnings for an entry's optional ``docs`` link (task-577).

    A repo-relative path (the same form as a module ``@docs`` header). A path
    that does not exist is a warning, never a rejection: an author may be
    linking a page they are about to write, and task-578's resolver is what
    turns the link into something. A non-string is invalid, and that is raised
    by ``write_library_entry`` before this runs.
    """
    docs = entry_data.get('docs') if isinstance(entry_data, dict) else None
    if not docs:
        return []
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if not os.path.exists(os.path.join(repo_root, docs)):
        return [f"docs path does not exist yet: {docs}"]
    return []


def _entry_tag_warnings(app, entry):
    raw_tags = entry.get('tags') if isinstance(entry, dict) else None
    if isinstance(raw_tags, str):
        raw_tags = [t.strip() for t in raw_tags.split(',') if t.strip()]
    if isinstance(raw_tags, (list, tuple)):
        try:
            return validate_tags_on_save(list(raw_tags), app.config.get('DATA_DIR'))
        except Exception as e:
            return [f"Tag validation error: {e}"]
    return []


def write_library_entry(app, registry_type, entry_id, entry_data):
    """Write one registry entry, shared by the HTTP route and the NL-editor batch.

    Returns the tag warnings. Raises ``ValueError`` on invalid input so a batch
    op can report it per op. ``save_registry`` never deletes, so this is an
    upsert.
    """
    if registry_type not in REGISTRY_TYPES:
        raise ValueError(f"Unknown registry type: {registry_type}")
    if not entry_id or not str(entry_id).strip():
        raise ValueError("Missing entry id")
    if not isinstance(entry_data, dict):
        raise ValueError("Entry data must be an object")
    # task-577: `docs` is an optional repo-relative link, keyed by the entry id.
    # A non-string is a shape error; a missing path is only a warning.
    if 'docs' in entry_data and entry_data['docs'] is not None \
            and not isinstance(entry_data['docs'], str):
        raise ValueError(
            "docs must be a repo-relative string path "
            "(e.g. 'docs/virtualWorld/World Building/Doors & Connections.md')")
    filename = f"{registry_type}.json"
    registry = load_registry(app.config['DATA_DIR'], filename)
    registry[str(entry_id)] = _strip_presentation_properties(entry_data)
    save_registry(app.config['DATA_DIR'], filename, registry)
    _reload_condition_catalog(app, registry_type)
    stored = registry.get(str(entry_id), {})
    return _entry_tag_warnings(app, stored) + _docs_warnings(stored)


def delete_library_entry(app, registry_type, entry_id):
    """Delete one registry entry. Returns True when it existed."""
    if registry_type not in REGISTRY_TYPES:
        raise ValueError(f"Unknown registry type: {registry_type}")
    filename = f"{registry_type}.json"
    registry = load_registry(app.config['DATA_DIR'], filename)
    if str(entry_id) not in registry:
        return False
    delete_registry_entry(app.config['DATA_DIR'], filename, str(entry_id))
    _reload_condition_catalog(app, registry_type)
    return True


def handle_library_create_or_update(app, registry_type):
    if registry_type not in REGISTRY_TYPES:
        return jsonify({"error": f"Unknown registry type: {registry_type}"}), 400
    data = request.get_json()
    if not data or 'id' not in data:
        return jsonify({"error": "Missing 'id' in payload"}), 400
    entry_data = data['data'] if 'data' in data else {k: v for k, v in data.items() if k != 'id'}
    try:
        warnings = write_library_entry(app, registry_type, data['id'], entry_data)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
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
    _reload_condition_catalog(app, registry_type)
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
    _reload_condition_catalog(app, registry_type)
    return jsonify({"status": "renamed", "old": entry_id, "new": new_id})


def place_library_item(app, item_id, container_id=None, character_id=None,
                       area_name=None, edge_relation=None):
    """Core of handle_library_place_item — no request dependency.

    Shared by POST /api/library/items/<id>/place and the NL-editor batch
    endpoint (POST /api/graph/batch). Returns (node_id, error, status_code).
    """
    library = load_registry(app.config['DATA_DIR'], 'items.json')
    lib_item = library.get(item_id)
    if not lib_item:
        return None, f"Item '{item_id}' not found in library", 404

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
        "affinity": lib_item.get('affinity', []),
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
    from engine.items.provenance import normalize_provenance
    provenance = normalize_provenance(lib_item.get('provenance'))
    if provenance:
        props["provenance"] = provenance
    graph = app.world.graph
    node = graph.get_node(node_id)
    if not node:
        node = Node(id=node_id, type='item', name=item_name, properties=props)
        graph.add_node(node)
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
        graph_add_in_edge(graph, child_node_id, node_id)

    node_id_l = node_id.lower()
    for e in graph.edges[:]:
        if e.source.lower() == node_id_l and e.type in (EDGE_IN, EDGE_CARRYING):
            graph.remove_edge(e.source, e.target, e.type)

    target_ref = None
    edge_type = EDGE_IN
    if container_id:
        if not graph.get_node(container_id):
            return node_id, f"Container '{container_id}' not found", 400
        target_ref = container_id
    elif character_id:
        if not graph.get_node(character_id):
            return node_id, f"Character '{character_id}' not found", 400
        target_ref = character_id
        edge_type = EDGE_CARRYING
    elif area_name:
        area_node_id = app.world._area_node_id(area_name)
        for n in graph.nodes.values():
            if n.type == "area" and n.name == area_name:
                area_node_id = n.id
                break
        target_ref = area_node_id
    else:
        return node_id, "Missing target: 'area', 'container', or 'character'", 400

    if edge_relation and str(edge_relation).strip():
        edge_type = RELATION_EDGE_TYPES.get(str(edge_relation).strip().lower(), edge_type)
    graph.add_edge(Edge(source=node_id, target=target_ref, type=edge_type))

    for trigger_data in lib_item.get('triggers', []):
        _materialize_trigger_nodes(graph, node_id, trigger_data)

    return node_id, None, 200


def handle_library_place_item(app, item_id):
    data = request.get_json() or {}
    node_id, error, code = place_library_item(
        app, item_id,
        container_id=data.get('container'),
        character_id=data.get('character'),
        area_name=data.get('area'),
    )
    if error:
        return jsonify({"error": error}), code
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
    # task-606: fold either stat-key case (see engine/abilities.normalize_stat_block).
    player.stats = normalize_stat_block(cdata.get('stats', player.stats))
    # Lowercase vital duplicates in library files fold into the canonical keys
    player.vitals = {**player.vitals, **canonical_vitals(cdata.get('vitals', player.vitals))}
    player.decay_rates = cdata.get('decay_rates', player.decay_rates)
    player.skills = cdata.get('skills', player.skills)
    player.traits = cdata.get('traits', player.traits)
    player.tags = cdata.get('tags', player.tags)
    player.sync_vitals_with_tags()
    player.known = list(cdata.get('known', []) or [])
    player.interest_tags = cdata.get('interest_tags', player.interest_tags)
    player.personality = cdata.get('personality', '')
    player.description = cdata.get('description', '')
    player.base_description = cdata.get('base_description', '')
    player.unknown_name = cdata.get('unknown_name', '')
    player.emotion = cdata.get('emotion', {})
    player.memories = cdata.get('memories', [])
    player.behaviors = cdata.get('behaviors', [])
    # task-590: reusable behaviours live in data/library/behaviours/ and are
    # referenced by id. Resolve them into the inline list the evaluator already
    # reads; an unresolvable ref is reported in the response, never dropped.
    behavior_warnings = []
    behavior_refs = cdata.get('behavior_refs') or []
    if behavior_refs:
        player.behaviors, unresolved = behavior_library.merge_into(
            player.behaviors, behavior_refs, app.config.get('DATA_DIR'))
        warning = behavior_library.report_unresolved(
            f"Character '{player_name}' (library '{char_id}')", unresolved)
        if warning:
            behavior_warnings.append(warning)
            logger.warning(warning)
    player.npc_behavior = cdata.get('npc_behavior', 'wander')
    player.npc_action_interval = cdata.get('npc_action_interval', 3)
    player.simple_npc = cdata.get('simple_npc', False)
    player.relationships = cdata.get('relationships', {})
    conditions = cdata.get('conditions')
    if conditions:
        player.load_conditions(conditions)
    activity = cdata.get('activity')
    if activity:
        player.activity = activity
    app.world.add_player(player)

    # task-446: a duplicate display name is registered under a uniqued key
    # ("zombie" -> "zombie__c4d808") while player.name keeps the bare name.
    # Every placement below must target the key the world actually assigned,
    # or the area lands on the first holder of the name and the new spawn
    # comes in with current_area None.
    pm = getattr(app.world, "player_manager", None)
    if pm is not None and getattr(player, "id", None):
        player_name = pm._players_by_id.get(player.id, player_name)

    # Expression pack: carry the library character's art onto its node.
    try:
        node = app.world.graph.get_node(
            app.world.player_manager.get_player_node_id(player_name))
        if node is not None:
            for key in ("image", "profile_image", "expressions"):
                value = cdata.get(key)
                if value:
                    node.properties[key] = value
    except Exception:
        pass

    target_area = area_name or cdata.get('current_area', '')
    if target_area:
        try:
            app.world.set_player_area(player_name, target_area)
        except Exception as e:
            logger.warning(f"Could not place '{player_name}' in area '{target_area}': {e}")

# task-519/bug-516: materialize inventory first, then resolve equipped
    # against what was actually loaded. Both the string (library-id) and dict
    # forms go through one shared materializer, so nothing is dropped and the
    # resolved shape is node-id strings.
    player_node_id = app.world.player_manager.get_player_node_id(player_name) \
        if getattr(app.world, 'player_manager', None) is not None else Player.node_id_for(player_name)
    carried = _materialize_character_inventory(
        app, player_name, player_node_id, cdata.get('inventory', []),
        register_missing=True)
    resolved_equipped = _resolve_character_equipped(carried, cdata.get('equipped') or {})
    # task-654: the dict alone is the inert half. Every reader --
    # `combat._best_weapon_node` and `equipment_bonuses.get_equipment_nodes` --
    # walks EDGE_EQUIPPED, so assigning `player.equipped` directly left an
    # imported goblin reporting five equipped slots while contributing zero
    # defense, zero damage mitigation and no weapon in a fight. One writer for
    # both truths.
    result = app.world.equipment.set_equipped_payload(
        player, resolved_equipped, player_name=player_name)
    player.equipped = result.get("slots") or {}
    if result.get("unresolved"):
        logger.warning(
            "[library] character '%s': equipped references did not resolve to an "
            "item node: %s", player_name, ", ".join(result["unresolved"]))

    if make_active:
        app.world.set_active_player(player_name)

    return jsonify({"status": "imported", "player": player_name,
                    "behavior_warnings": behavior_warnings})


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
              "edge_length", "needs_open", "parameters", "cost", "tags",
              # Read by the engine but previously absent from this copy list, so a
              # library-spawned way silently lost them. See tools/way_properties.py,
              # which is the declaration this list is checked against.
              "insulation", "sound_barrier", "climb_dc", "jump_dc",
              "refusal_message", "blocked_description", "aliases"):
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


def handle_break_template_link(app):
    """POST /api/library/break-template-link — unbind a node from its template.

    The missing half of ``refresh-to-world`` (task-289/317): any of the four
    linkable types could be re-synced and none could be unlinked, so "this copy
    is mine now" had no way to be expressed and an author's hand-fix was one
    stray refresh away from being overwritten.

    Removes the link marker and nothing else — the node keeps every value the
    template last wrote, which is the entire point of breaking a link. See
    ``engine/sync.py`` for the contract and for why this deliberately does not
    auto-lock the node's fields.
    """
    data = request.get_json() or {}
    node_id = data.get('node_id')
    if not node_id:
        return jsonify({"error": "Missing 'node_id'"}), 400
    node = app.world.graph.get_node(node_id)
    if not node:
        return jsonify({"error": "Node not found"}), 404
    if sync.spec_for(node.type) is None:
        return jsonify({
            "error": f"Type '{node.type}' has no library templates to link to"
        }), 400

    report = sync.break_template_link(node)
    report["status"] = "unlinked" if report.get("changed") else "not_linked"
    return jsonify(report)


def handle_library_refresh_to_world(app):
    data = request.get_json() or {}
    node_id = data.get('node_id')
    if not node_id:
        return jsonify({"error": "Missing 'node_id'"}), 400
    node = app.world.graph.get_node(node_id)
    if not node:
        return jsonify({"error": "Node not found"}), 404
    sections = data.get('sections')
    entries = data.get('entries') or {}
    template_id = data.get('template_id') or data.get('library_id')
    if node.type == 'item':
        return _refresh_item(app, node, sections, template_id)
    if node.type == 'way':
        return _refresh_way(app, node, sections, template_id)
    if node.type == 'area':
        return _refresh_area(app, node, sections, template_id)
    if node.type == 'character':
        return _refresh_character(app, node, sections, template_id, entries)
    return jsonify({"error": f"Type '{node.type}' does not support refresh-to-world"}), 400


def _refresh_item(app, node, sections, template_id=None):
    current_library_id = node.properties.get('library_id', '')
    # engine/sync.py owns the resolution order (explicit -> link -> per-type
    # guess). An item's id is an opaque library key, so its guess is "none":
    # a name-derived guess would attach a placed copy to a template the author
    # never chose.
    library_id = sync.resolve_template_id(node, template_id)
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
            'defense': 'defense', 'damage': 'damage', 'damage_type': 'damage_type',
            'insulation': 'insulation',
            'resistances': 'resistances', 'action_costs': 'action_costs',
            'skill_check': 'skill_check', 'contents': 'contents',
            'aliases': 'aliases', 'tags': 'tags', 'affinity': 'affinity',
            'provenance': 'provenance',
            'image': 'image',
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
            "affinity": lib_item.get('affinity', []),
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
            "damage_type": lib_item.get('damage_type', ''),
            "insulation": lib_item.get('insulation', 0),
            "resistances": lib_item.get('resistances', {}),
            "action_costs": lib_item.get('action_costs', {}),
            "skill_check": lib_item.get('skill_check', {}),
            "contents": lib_item.get('contents', []),
            "aliases": lib_item.get('aliases', []),
            "image": lib_item.get('image') or None,
        }
        from engine.items.provenance import normalize_provenance
        provenance = normalize_provenance(lib_item.get('provenance'))
        if provenance:
            lib_props["provenance"] = provenance
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

    return jsonify({"status": "refreshed", "node_id": node.id, "applied": sections if sections else ["all"],
                    "template_id": library_id, "linked": sync.is_linked(node)})


def _refresh_way(app, node, sections, template_id=None):
    props = node.properties or {}
    way_id = sync.resolve_template_id(node, template_id)

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
            'insulation': 'insulation', 'climb_dc': 'climb_dc', 'jump_dc': 'jump_dc',
            'refusal_message': 'refusal_message',
            'blocked_description': 'blocked_description', 'cost': 'cost',
            'aliases': 'aliases',
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
    elif way_id and not sync.linked_template_id(node):
        # A way guesses its template from its slugified name; record the guess we
        # actually synced from, so the link is inspectable and breakable.
        sync.link(node, way_id)

    return jsonify({"status": "refreshed", "node_id": node.id, "applied": applied,
                    "template_id": way_id, "linked": sync.is_linked(node)})


def _refresh_area(app, node, sections, template_id=None):
    props = node.properties or {}
    area_id = sync.resolve_template_id(node, template_id)

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
    elif area_id and not sync.linked_template_id(node):
        # Record a template we guessed and really synced from, so the link is
        # inspectable and breakable instead of being re-derived each refresh.
        sync.link(node, area_id)
        props = node.properties or {}

    return jsonify({"status": "refreshed", "node_id": node.id, "applied": applied,
                    "template_id": area_id, "linked": sync.is_linked(node)})


def _apply_entry_selection(current, source, sel_keys):
    """Merge the selected entries from `source` onto `current`.

    `source` is the incoming list/dict (usually the library character), `current`
    the existing value (usually the live player's). Array entries match by
    `id` else `name`; dict entries match by key. Returns the merged value.
    """
    sel_set = set(str(k) for k in (sel_keys or []))
    if isinstance(source, list):
        def _key(x):
            if isinstance(x, dict):
                return str(x.get('id') or x.get('name') or '')
            return ''
        out = list(current) if isinstance(current, list) else []
        for entry in source:
            k = _key(entry)
            if k and k in sel_set:
                idx = next((i for i, x in enumerate(out) if _key(x) == k), -1)
                if idx >= 0:
                    out[idx] = entry
                else:
                    out.append(entry)
        return out
    if isinstance(source, dict):
        out = dict(current) if isinstance(current, dict) else {}
        for k in sel_set:
            if k in source:
                out[k] = source[k]
        return out
    return source


def _refresh_character(app, node, sections, template_id=None, entries=None):
    props = node.properties or {}
    char_id = sync.resolve_template_id(node, template_id)
    char_reg = load_registry(app.config['DATA_DIR'], 'characters.json')
    lib_char = char_reg.get(char_id)
    if not lib_char:
        return jsonify({"error": f"Character '{char_id}' not found in library"}), 404

    player = app.world.player_manager.get_player(node.name) if hasattr(app.world, 'player_manager') else None
    if player is None:
        return jsonify({"error": f"Character '{node.name}' not found in world"}), 404

    # Expression pack is node presentation state, refreshed straight from the
    # library entry (not a Player field).
    try:
        for key in ("image", "profile_image", "expressions"):
            value = lib_char.get(key)
            if value:
                node.properties[key] = value
    except Exception:
        pass

    editable_map = {
        'name': 'name',
        'description': 'description',
        'base_description': 'base_description',
        'unknown_name': 'unknown_name',
        'personality': 'personality',
        'stats': 'stats',
        'skills': 'skills',
        'traits': 'traits',
        # task-549: species is free text, so it is passed through as a plain
        # string rather than validated against an enum — an unknown species
        # permits everything, which is the safe direction to be wrong in.
        'species': 'species',
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

    # task-519/bug-516: refresh must never write the raw template `equipped`
    # shape through. Materialize the authored inventory first (idempotent), then
    # resolve equipped against it, so runtime equipment is node-id strings
    # exactly as import produces. Equipment is only touched when the refresh
    # actually covers it.
    resolved_equipped = {}
    touches_equipment = sections is None or 'equipped' in sections or 'inventory' in sections
    if touches_equipment:
        player_node_id = app.world.player_manager.get_player_node_id(player) \
            if getattr(app.world, 'player_manager', None) is not None else node.id
        carried = _materialize_character_inventory(
            app, node.name, player_node_id, lib_char.get('inventory') or [])
        resolved_equipped = _resolve_character_equipped(
            carried, lib_char.get('equipped') or {})

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
            if entries and section_key in entries and (entries[section_key] or []):
                # Per-entry apply: merge only the named library entries onto the
                # player, leaving all other runtime values untouched.
                sel_keys = entries[section_key]
                current_val = getattr(player, player_field, None)
                if current_val is None:
                    current_val = {} if kind == 'dict' else ([] if kind == 'list' else None)
                merged = _apply_entry_selection(current_val, lib_char[section_key], sel_keys)
                if merged is not None:
                    assign(player_field, merged, kind)
                continue
            assign(player_field, lib_char[section_key], kind)
        applied = sections

# task-590: resolve reusable behaviour refs into the inline list the
    # evaluator reads. `merge_into` is idempotent, so refreshing twice does not
    # double the tree; an unresolvable ref is logged rather than dropped.
    refs = lib_char.get('behavior_refs') or []
    if refs and (sections is None or 'behaviors' in sections or 'behavior_refs' in sections):
        player.behaviors, unresolved = behavior_library.merge_into(
            player.behaviors, refs, app.config.get('DATA_DIR'))
        warning = behavior_library.report_unresolved(
            f"Character '{node.name}' (library '{char_id}')", unresolved)
        if warning:
            logger.warning(warning)
    applies_equipped = sections is None or 'equipped' in sections
    if applies_equipped and lib_char.get('equipped') is not None:
        if entries and 'equipped' in entries and (entries['equipped'] or []):
            # Per-slot merge: only the named slots take the library's (already
            # resolved) values; every other runtime slot is left untouched.
            merged_equipped = _apply_entry_selection(
                player.equipped or {}, resolved_equipped, entries['equipped'])
        else:
            merged_equipped = resolved_equipped
        # task-654: refresh is a writer too, so it writes both truths.
        result = app.world.equipment.set_equipped_payload(
            player, merged_equipped, player_name=player.name)
        player.equipped = result.get("slots") or {}
        if result.get("unresolved"):
            logger.warning(
                "[library] refresh '%s': equipped references did not resolve to "
                "an item node: %s", player.name, ", ".join(result["unresolved"]))

    if template_id:
        props['library_id'] = template_id
        node.properties = props
    elif char_id and not sync.linked_template_id(node):
        # A character guesses its template from its own name (see
        # engine/sync.py), so a refresh with no explicit id really did sync from
        # `char_id`. Record that, or the node keeps reading as unlinked: the next
        # refresh re-guesses, and "Break Link" has nothing to break even though
        # the node plainly has a template.
        sync.link(node, char_id)
        props = node.properties or {}

    return jsonify({"status": "refreshed", "node_id": node.id, "applied": applied,
                    "template_id": char_id, "linked": sync.is_linked(node)})


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
