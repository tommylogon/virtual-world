import logging
import time
import random
import difflib
import os
from flask import request, jsonify
from werkzeug.utils import secure_filename
from graph import Node, Edge, EDGE_IN, EDGE_CARRYING, EDGE_EQUIPPED, EDGE_ON, EDGE_UNDER, EDGE_BEHIND, EDGE_BESIDE, EDGE_AT, EDGE_TRIGGERS, EDGE_CONNECTION
from engine.item_actions import normalize_item_actions

logger = logging.getLogger(__name__)


def handle_get_graph_nodes(app):
    return jsonify(app.world.graph.to_dict()["nodes"])


def handle_get_graph_edges(app):
    return jsonify(app.world.graph.to_dict()["edges"])


def handle_get_area_sounds(app, area_id):
    """task-173: active sound sources in an area (read-only designer block)."""
    from engine.sound import get_sound_sources_in_area
    graph = app.world.graph
    area_node = graph.get_node(area_id)
    if area_node is None or area_node.type != "area":
        return jsonify({"error": "Area not found"}), 404
    sounds = []
    for node, level, pattern in get_sound_sources_in_area(area_id, graph):
        sounds.append({
            "name": node.name,
            "level": int(level or 1),
            "pattern": pattern or "a sound",
            "state": node.properties.get("current_state", ""),
        })
    return jsonify({"sounds": sounds})


def handle_create_node(app):
    data = request.get_json()
    node_type = data.get('type')
    node_name = data.get('name')
    if not node_type or not node_name:
        return jsonify({"error": "Missing 'type' or 'name'"}), 400

    node_id = (data.get('id') or f"{node_type}_{node_name.replace(' ', '_')}").lower()
    if app.world.graph.get_node(node_id):
        return jsonify({"error": f"Node with id '{node_id}' already exists"}), 409

    node = Node(
        id=node_id,
        type=node_type,
        name=node_name,
        properties=data.get('properties', {})
    )
    app.world.graph.add_node(node)
    return jsonify({"status": "success", "id": node_id})


# ─────────────────────────── Duplicate (task-377) ───────────────────────────

def _unique_node_id(graph, base):
    candidate = base
    n = 2
    while graph.get_node(candidate) is not None:
        candidate = f"{base}_{n}"
        n += 1
    return candidate


def _strip_copy_suffix(name):
    """'Bath Room (copy) (copy 3)' → 'Bath Room'; '(2)' → ''."""
    import re as _re
    return _re.sub(r' \((?:copy(?:\s\d+)?|\d+)\)$', '', str(name or ''))


def handle_duplicate_node(app):
    """Duplicate an area / item / way / character with its attached subtree.

    Semantics (matches the graph's edge direction convention):
      * children point TO the node  — ``salt --[on]--> table``, ``top --[equipped]--> char``
      * the node points to its parents — ``table --[in]--> kitchen``
    So a duplicate clones the node + nodes attached TO it (children), and keeps
    the node's own attachment edges pointing at the SAME parents (the kitchen is
    never duplicated, the character is never duplicated).
    Trigger nodes are never duplicated via the graph — they are cloned only as
    attachments of a duplicated node, each with a brand-new id + link.
    """
    data = request.get_json() or {}
    node_id = data.get("node_id") or data.get("id")
    include_children = bool(data.get("include_children", True))
    graph = app.world.graph
    node = graph.get_node(node_id) if node_id else None
    if node is None:
        return jsonify({"error": "Node not found"}), 404
    if node.type == "logic_trigger":
        return jsonify({
            "error": "Triggers are never duplicated from the graph — "
                     "create new triggers from the inspector editor instead."
        }), 400
    if node.type not in ("area", "item", "way", "character"):
        return jsonify({"error": f"Cannot duplicate nodes of type '{node.type}'"}), 400

    import copy as _copy
    # Snapshot BEFORE mutating so a runaway/aborted duplicate is undoable.
    from routes.saveload import _push_undo_snapshot
    _push_undo_snapshot(app, label=f"duplicate {node.name}")
    ts = int(time.time() * 1000)
    MAX_CLONED_NODES = 200
    state = {"count": 0}

    # PRE-INDEX the ORIGINAL graph once. Child relations are attach edges
    # (in/on/under/behind/beside/at/carrying/equipped) pointing TO the parent.
    # The recursion must never scan live edges (a parent edge clone→parent looks
    # like a child and would re-discover clones forever).
    CHILD_ATTACH_TYPES = {EDGE_IN, EDGE_ON, EDGE_UNDER, EDGE_BEHIND,
                          EDGE_BESIDE, EDGE_AT, EDGE_CARRYING, EDGE_EQUIPPED}
    children_of = {}   # parent_id -> [(child_id, edge_type, edge_props)]
    for _e in graph.edges:
        if _e.type not in CHILD_ATTACH_TYPES:
            continue
        _src = graph.get_node(_e.source)
        if _src is None or _src.type != "item":
            continue  # only items are cloned as children (never chars/ways/triggers)
        children_of.setdefault(_e.target, []).append(
            (_e.source, _e.type, dict(_e.properties or {})))

    def clone_node(src, nid, name):
        props = _copy.deepcopy(src.properties or {})
        clone = Node(id=nid, type=src.type, name=name, properties=props)
        graph.add_node(clone)
        state["count"] += 1
        return clone

    def clone_triggers_for(src_id, dst_id):
        for edge in [e for e in graph.edges[:] if e.source == src_id and e.type == EDGE_TRIGGERS]:
            tgt = graph.get_node(edge.target)
            if tgt is None:
                continue
            _tt = tgt.properties.get('trigger_type', 'x')
            if not isinstance(_tt, str):
                _tt = str(_tt)
            _safe = ''.join(c if c.isalnum() or c in '-_' else '_' for c in _tt)[:24] or 'x'
            tid = _unique_node_id(graph, f"trigger_{dst_id}_{ts}_{_safe}")
            graph.add_node(Node(id=tid, type=tgt.type, name=tgt.name,
                                properties=_copy.deepcopy(tgt.properties or {})))
            graph.add_edge(Edge(source=dst_id, target=tid, type=EDGE_TRIGGERS,
                                properties=_copy.deepcopy(edge.properties or {})))
            state["count"] += 1

    def clone_item_tree(item_id, parent_id, visited):
        """Clone one ORIGINAL item + its children-subtree; link to parent."""
        if item_id in visited or state["count"] >= MAX_CLONED_NODES:
            return None
        visited.add(item_id)
        src = graph.get_node(item_id)
        if src is None or src.type != "item":
            return None
        cid = _unique_node_id(graph, f"{item_id}_dup")
        cnode = clone_node(src, cid, f"{_strip_copy_suffix(src.name)} (copy)")
        clone_triggers_for(item_id, cid)
        for child_id, etype, eprops in children_of.get(item_id, []):
            if isinstance(child_id, str) and graph.get_node(child_id) is not None:
                child_clone = clone_item_tree(child_id, cid, visited)
                if child_clone is not None:
                    graph.add_edge(Edge(source=child_clone.id, target=cid,
                                        type=etype, properties=eprops))
        return cnode

    def attach_children(src_id, dst_id, visited):
        visited.add(src_id)
        for child_id, etype, eprops in children_of.get(src_id, []):
            if isinstance(child_id, str) and graph.get_node(child_id) is not None:
                child_clone = clone_item_tree(child_id, dst_id, visited)
                if child_clone is not None:
                    graph.add_edge(Edge(source=child_clone.id, target=dst_id,
                                        type=etype, properties=eprops))

    if node.type == "area":
        new_id = _unique_node_id(graph, f"{node.id}_dup")
        new_area = clone_node(node, new_id, f"{_strip_copy_suffix(node.name)} (2)")
        clone_triggers_for(node.id, new_id)
        if include_children:
            attach_children(node.id, new_id, set())
    elif node.type == "item":
        new_id = _unique_node_id(graph, f"{node.id}_dup")
        citem = clone_node(node, new_id, f"{_strip_copy_suffix(node.name)} (copy)")
        clone_triggers_for(node.id, new_id)
        if include_children:
            attach_children(node.id, new_id, set())
        # Re-link the copy to the SAME parents as the original (never clone a
        # parent, always share it): the copy stays in the same room/container.
        for _e in graph.edges[:]:
            if _e.source != node.id or _e.type not in CHILD_ATTACH_TYPES:
                continue
            if _e.type in (EDGE_CARRYING, EDGE_EQUIPPED):
                # Don't strap the copy onto the same holder — drop it into the
                # holder's area instead ("duplicate the top, not the char").
                holder_area = None
                for _h in graph.get_edges_for_source(_e.target, EDGE_IN):
                    _an = graph.get_node(_h.target)
                    if _an is not None and _an.type == "area":
                        holder_area = _h.target
                        break
                if holder_area:
                    graph.add_edge(Edge(source=new_id, target=holder_area, type=EDGE_IN))
            else:
                graph.add_edge(Edge(source=new_id, target=_e.target, type=_e.type,
                                    properties=_copy.deepcopy(_e.properties or {})))
    elif node.type == "way":
        new_id = _unique_node_id(graph, f"{node.id}_dup")
        cway = clone_node(node, new_id, f"{_strip_copy_suffix(node.name)} (copy)")
        clone_triggers_for(node.id, new_id)
        if include_children:
            attach_children(node.id, new_id, set())
        # Reconnect the copy to the SAME areas (both directions), never cloning.
        for _e in graph.edges[:]:
            if _e.type != EDGE_CONNECTION:
                continue
            if _e.source == node.id:
                graph.add_edge(Edge(source=new_id, target=_e.target, type=EDGE_CONNECTION,
                                    properties=_copy.deepcopy(_e.properties or {})))
            elif _e.target == node.id:
                graph.add_edge(Edge(source=_e.source, target=new_id, type=EDGE_CONNECTION,
                                    properties=_copy.deepcopy(_e.properties or {})))
    else:  # character
        from player import Player
        new_name_base = f"{_strip_copy_suffix(node.name)} (copy)"
        new_name = new_name_base
        _n = 2
        while (new_name in app.world.players or
               graph.get_node(f"player_{new_name}".replace(' ', '_')) is not None):
            new_name = f"{new_name_base} {_n}"
            _n += 1
        src_player = app.world.players.get(node.name)
        new_player = Player(new_name)
        if src_player is not None:
            for _f in ("stats", "skills", "vitals", "traits", "tags", "interest_tags",
                       "personality", "base_description", "description",
                       "simple_npc", "npc_behavior", "npc_action_interval"):
                setattr(new_player, _f, _copy.deepcopy(getattr(src_player, _f)))
            new_player.emotion = "neutral"
            new_player.emotion_intensity = 0.0
        # add_player() flips active_player to the new copy — restore afterwards.
        prev_active = app.world.active_player
        app.world.player_manager.add_player(new_player)
        new_pid = f"player_{new_name}".replace(' ', '_')
        clone_triggers_for(node.id, new_pid)
        # Spawn the copy in the SAME area as the original.
        for _e in graph.get_edges_for_source(node.id, EDGE_IN):
            _an = graph.get_node(_e.target)
            if _an is not None and _an.type == "area":
                # current_area is the area NAME in this engine (client + move API).
                new_player.current_area = _an.name
                graph.add_edge(Edge(source=new_pid, target=_an.id, type=EDGE_IN))
                break
        if include_children:
            attach_children(node.id, new_pid, set())
        app.world.active_player = prev_active
        new_id = new_pid

    if state["count"] >= MAX_CLONED_NODES:
        return jsonify({
            "error": f"Duplicate aborted after {state['count']} clones "
                     f"(subtree cycle or a huge container chain). Undo restores the world."
        }), 400

    return jsonify({"status": "success", "id": new_id,
                    "name": graph.get_node(new_id).name,
                    "cloned": state["count"]})


def handle_update_node(app, node_id):
    data = request.get_json()
    node = app.world.graph.get_node(node_id)
    if not node:
        return jsonify({"error": "Node not found"}), 404

    if 'properties' in data:
        props = data['properties']
        if isinstance(props.get('actions'), (list, str)):
            props['actions'] = normalize_item_actions(props['actions'])
        node.properties.update(props)
    if 'name' in data:
        node.name = data['name']
    node.updated = time.time()

    warnings = []
    if 'properties' in data and 'tags' in data['properties']:
        from routes.helpers import validate_tags_on_save
        warnings = validate_tags_on_save(data['properties']['tags'], app.config.get('DATA_DIR'))
    return jsonify({"status": "success", "tag_warnings": warnings})


def handle_upload_node_image(app, node_id):
    node = app.world.graph.get_node(node_id)
    if not node:
        return jsonify({"error": "Node not found"}), 404

    upload = request.files.get('file')
    if not upload or not upload.filename:
        return jsonify({"error": "No file provided (field 'file')"}), 400

    allowed = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp', 'ico'}
    ext = (upload.filename.rsplit('.', 1)[-1] if '.' in upload.filename else '').lower()
    if ext not in allowed:
        return jsonify({"error": f"Unsupported image type '{ext or 'unknown'}'. Allowed: {', '.join(sorted(allowed))}."}), 400

    try:
        images_dir = app.config.get('IMAGES_DIR') or os.path.join(
            app.root_path, 'static', 'images', 'nodes')
        os.makedirs(images_dir, exist_ok=True)
        safe_base = secure_filename(node_id) or 'node'
        filename = f"{safe_base}-{int(time.time() * 1000)}.{ext}"
        path = os.path.join(images_dir, filename)
        upload.save(path)
    except Exception as exc:
        logger.warning("Image upload save failed for %s: %s", node_id, exc)
        return jsonify({"error": "Could not save image on server."}), 500

    old_image = node.properties.get('image') or ''
    if old_image.startswith('/static/images/nodes/'):
        old_name = os.path.basename(old_image)
        old_path = os.path.join(images_dir, old_name)
        if old_name not in filename and os.path.isfile(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass

    url = f"/static/images/nodes/{filename}"
    node.properties['image'] = url
    node.updated = time.time()
    return jsonify({"status": "success", "image": url})


def handle_move_item_node(app, node_id):
    data = request.get_json()
    node = app.world.graph.get_node(node_id)
    if not node or node.type != 'item':
        dest_parts = []
        if data.get('area'):
            dest_parts.append(f"area '{data.get('area')}'")
        if data.get('container'):
            dest_parts.append(f"container '{data.get('container')}'")
        if data.get('character'):
            dest_parts.append(f"character '{data.get('character')}'")
        dest = ', '.join(dest_parts) or 'unknown'
        found = app.world.graph.get_node(node_id)
        extra = []
        if found:
            extra.append(f"node '{node_id}' exists but is type '{found.type}' (name '{found.name}')")
        else:
            item_ids = sorted(nid for nid, n in app.world.graph.nodes.items()
                              if n.type == 'item')
            close = difflib.get_close_matches(node_id.lower(), item_ids, n=3, cutoff=0.4)
            if close:
                extra.append(f"did you mean: {', '.join(close)}")
        where = "nowhere"
        if found:
            for e in app.world.graph.edges:
                if e.source.lower() == node_id.lower() and e.type in ('in', 'location', 'contains', 'carrying', 'carried_by', 'equipped'):
                    holder = app.world.graph.get_node(e.target)
                    holder_name = holder.name if holder else e.target
                    where = f"'{holder_name}' ({e.target}) via '{e.type}'"
                    break
        extra_txt = ('; ' + '; '.join(extra)) if extra else ''
        return jsonify({
            "error": f"Item node '{node_id}' not found — currently {where}, "
                     f"intended destination {dest}{extra_txt}"
        }), 404

    RELATION_EDGE_TYPES = {
        "in": EDGE_IN,
        "on": EDGE_ON,
        "under": EDGE_UNDER,
        "behind": EDGE_BEHIND,
        "beside": EDGE_BESIDE,
        "at": EDGE_AT,
        "carrying": EDGE_CARRYING,
    }
    target_type = data.get('target_type') or ('item' if data.get('container') else 'character' if data.get('character') else 'area' if data.get('area') else None)
    target_id = data.get('target_id') or data.get('container') or data.get('character') or data.get('area') or None
    relation = data.get('relation') or ('in' if target_type in ('item', 'area') else 'carrying' if target_type == 'character' else 'in')
    if target_type == 'character':
        relation = 'carrying'
    if not target_type or not target_id:
        return jsonify({"error": "Provide target_type and target_id, or legacy area/container/character"}), 400

    target_node = app.world.graph.get_node(target_id)
    if not target_node:
        # Legacy payloads may pass a display name rather than a node id (e.g.
        # {"area": "Elm Street"}). Resolve by name among nodes of the expected
        # type so the legacy area/container/character path still works.
        id_lower = str(target_id).lower()
        want = {
            'area': {'area'},
            'item': {'item'},
            'container': {'item'},
            'character': {'character', 'player'},
        }.get(target_type, set())
        for n in app.world.graph.nodes.values():
            if str(n.name).lower() == id_lower and n.type in want:
                target_node = n
                target_id = target_node.id
                break
    if not target_node:
        return jsonify({"error": f"Target '{target_id}' not found"}), 404
    if target_type == 'character' and target_node.type not in ('character', 'player'):
        return jsonify({"error": f"'{target_id}' is not a character node"}), 400

    edge_type = RELATION_EDGE_TYPES.get(relation, relation)
    for e in app.world.graph.edges[:]:
        if e.source.lower() == node_id.lower() and e.type in ('in', 'location', 'contains', 'carried_by', 'carrying', 'equipped', 'on', 'under', 'behind', 'beside', 'at'):
            app.world.graph.remove_edge(e.source, e.target, e.type)
    app.world.graph.add_edge(Edge(source=node_id, target=target_id, type=edge_type))
    return jsonify({"status": "success", "target_type": target_type, "target_id": target_id, "relation": relation})


def handle_rename_node(app, node_id):
    data = request.get_json()
    new_id = data.get('new_id', '').strip().lower().replace(' ', '_')
    if not new_id:
        return jsonify({"error": "new_id is required"}), 400
    if new_id == node_id:
        return jsonify({"status": "success", "id": new_id})
    if app.world.graph.get_node(new_id):
        return jsonify({"error": f"Node '{new_id}' already exists"}), 409

    node = app.world.graph.get_node(node_id)
    if not node:
        return jsonify({"error": "Node not found"}), 404

    new_node = Node(id=new_id, type=node.type, name=node.name, properties=dict(node.properties))
    app.world.graph.add_node(new_node)

    node_id_l = node_id.lower()
    for edge in app.world.graph.edges:
        if edge.source.lower() == node_id_l:
            edge.source = new_id
        if edge.target.lower() == node_id_l:
            edge.target = new_id

    new_id_l = new_id.lower()
    for trig_node in app.world.graph.nodes.values():
        if trig_node.type != "logic_trigger":
            continue
        actions = trig_node.properties.get("actions", [])
        changed = False
        for action in actions:
            for param_key in ("item_id", "node_id", "way_id"):
                if str(action.get(param_key) or "").lower() == node_id_l:
                    action[param_key] = new_id
                    changed = True
        if changed:
            trig_node.updated = time.time()

    app.world.graph.remove_node(node_id)
    return jsonify({"status": "success", "id": new_id})


def handle_delete_node(app, node_id):
    node = app.world.graph.get_node(node_id)
    if not node:
        return jsonify({"error": "Node not found"}), 404

    if node.type == 'area':
        for edge in app.world.graph.get_edges_for_target(node_id, EDGE_IN):
            if edge.source.startswith('player_'):
                return jsonify({"error": f"Cannot delete area '{node.name}' – player inside"}), 400
    if node.type == 'character':
        characters = [n for n in app.world.graph.nodes.values() if n.type == 'character']
        if len(characters) <= 1:
            return jsonify({"error": "Cannot delete the last character"}), 400

    # task-378: bulk deletes should be undo-safe too (snapshot per delete).
    from routes.saveload import _push_undo_snapshot
    _push_undo_snapshot(app, label=f"delete {node.name}")
    app.world.graph.remove_node(node_id)
    return jsonify({"status": "success"})


def handle_create_edge(app):
    data = request.get_json()
    source = data.get('source')
    target = data.get('target')
    edge_type = data.get('type')
    if not all([source, target, edge_type]):
        return jsonify({"error": "Missing source, target, or type"}), 400

    src_r = app.world.graph._resolve_id(source) or source
    tgt_r = app.world.graph._resolve_id(target) or target
    edge = Edge(source=src_r, target=tgt_r, type=edge_type, properties=data.get('properties', {}))
    app.world.graph.add_edge(edge)
    return jsonify({"status": "success"})


# ─────────────────────────── NL-Editor batch (task-387) ───────────────────────────

_BATCH_PHASE = {
    'create_node': 0, 'spawn_library_item': 0, 'connect_areas': 0,
    'update_node': 1, 'link_to_library': 1,
    'attach': 2, 'detach': 2,
    'delete_node': 3,
}


def _apply_batch_op(app, optype, p):
    """Replay ONE staged NL-editor op directly against the live graph.

    Deliberately does NOT push undo snapshots: the route-level after_request
    hook records exactly ONE snapshot for the whole /api/graph/batch call.
    """
    graph = app.world.graph

    if optype == 'create_node':
        node = p.get('node') or p
        node_type = node.get('type') or node.get('kind')
        name = node.get('name')
        if not node_type or not name:
            return {"error": "Missing 'type' or 'name'"}
        nid = (node.get('id') or f"{node_type}_{name.replace(' ', '_')}").lower()
        if graph.get_node(nid):
            return {"error": f"Node with id '{nid}' already exists"}
        graph.add_node(Node(id=nid, type=node_type, name=name,
                            properties=node.get('properties') or {}))
        return {"id": nid}

    if optype == 'spawn_library_item':
        from routes.library_ops import place_library_item
        parent_id = p.get('parent_id')
        parent = graph.get_node(parent_id) if parent_id else None
        container_id = character_id = area_name = None
        if parent is not None:
            if parent.type == 'area':
                area_name = parent.name
            elif parent.type == 'character':
                character_id = parent.id
            else:
                container_id = parent.id
        elif parent_id:
            area_name = parent_id  # parent_id may itself be an area name
        node_id, error, _code = place_library_item(
            app, p.get('library_id'),
            container_id=container_id, character_id=character_id,
            area_name=area_name or None,
            edge_relation=p.get('relation') or None,
        )
        if error:
            return {"error": error}
        if p.get('rename'):
            placed = graph.get_node(node_id)
            if placed:
                placed.name = str(p['rename'])
                placed.updated = time.time()
        return {"node_id": node_id}

    if optype == 'connect_areas':
        way_id = p.get('way_id')
        area_a = p.get('area_a_id')
        area_b = p.get('area_b_id')
        if not way_id or not area_a or not area_b:
            return {"error": "connect_areas needs way_id, area_a_id, area_b_id"}
        if graph.get_node(way_id):
            return {"error": f"Way '{way_id}' already exists"}
        graph.add_node(Node(id=way_id, type='way',
                            name=p.get('way_name') or 'Door',
                            properties=p.get('properties') or {}))
        dir_a = p.get('direction_a') or 'north'
        dir_b = p.get('direction_b') or 'south'
        # Canonical connection edge pattern (mirrors handle_build_connect_legacy):
        # area→way carries direction + visible_in_direction; way→area only direction.
        graph.add_edge(Edge(source=area_a, target=way_id, type=EDGE_CONNECTION,
                            properties={"direction": dir_a, "visible_in_direction": ""}))
        graph.add_edge(Edge(source=way_id, target=area_b, type=EDGE_CONNECTION,
                            properties={"direction": dir_b}))
        graph.add_edge(Edge(source=area_b, target=way_id, type=EDGE_CONNECTION,
                            properties={"direction": dir_b, "visible_in_direction": ""}))
        graph.add_edge(Edge(source=way_id, target=area_a, type=EDGE_CONNECTION,
                            properties={"direction": dir_a}))
        return {"way_id": str(way_id)}

    if optype == 'update_node':
        node = graph.get_node(p.get('node_id'))
        if not node:
            return {"error": f"Node '{p.get('node_id')}' not found"}
        patch = p.get('patch') or {}
        if 'name' in patch:
            node.name = patch['name']
        props = dict(patch.get('properties') or {})
        # NL-editor agents hand over a FLAT property map ({description: ...});
        # fold every non-reserved key into properties.
        for k, v in patch.items():
            if k in ('name', 'properties', 'id', 'type'):
                continue
            props[k] = v
        if isinstance(props.get('actions'), (list, str)):
            props['actions'] = normalize_item_actions(props['actions'])
        node.properties.update(props)
        node.updated = time.time()
        return {"status": "success"}

    if optype == 'link_to_library':
        node = graph.get_node(p.get('node_id'))
        if not node:
            return {"error": f"Node '{p.get('node_id')}' not found"}
        node.properties['template_id'] = p.get('library_id')
        node.updated = time.time()
        return {"status": "success"}

    if optype == 'attach':
        src = graph._resolve_id(p.get('from_id')) or p.get('from_id')
        tgt = graph._resolve_id(p.get('to_id')) or p.get('to_id')
        etype = p.get('relation') or 'in'
        if not graph.get_node(src):
            return {"error": f"Source '{src}' not found"}
        if not graph.get_node(tgt):
            return {"error": f"Target '{tgt}' not found"}
        graph.add_edge(Edge(source=src, target=tgt, type=etype,
                            properties=p.get('properties') or {}))
        return {"status": "success"}

    if optype == 'detach':
        src, tgt, etype = p.get('from_id'), p.get('to_id'), p.get('relation') or 'in'
        before = len(graph.edges)
        graph.remove_edge(src, tgt, etype)
        if len(graph.edges) == before:
            return {"error": f"No edge {src} -{etype}-> {tgt} to detach"}
        return {"status": "success"}

    if optype == 'delete_node':
        node = graph.get_node(p.get('node_id'))
        if not node:
            return {"error": f"Node '{p.get('node_id')}' not found"}
        if node.type == 'area':
            for edge in graph.get_edges_for_target(node.id, EDGE_IN):
                if edge.source.startswith('player_'):
                    return {"error": f"Cannot delete area '{node.name}' – player inside"}
        if node.type == 'character':
            characters = [n for n in graph.nodes.values() if n.type == 'character']
            if len(characters) <= 1:
                return {"error": "Cannot delete the last character"}
        graph.remove_node(node.id)
        return {"status": "success"}

    return {"error": f"Unknown op type '{optype}'"}


def handle_graph_batch(app):
    """Apply a staged NL-editor batch as ONE undo snapshot (task-387).

    Ops are replayed in topological order (creates → updates/links →
    edges → deletes). No per-op snapshot is pushed here; the global
    after_request hook records exactly one undo entry for the whole call,
    so a single Undo reverts an entire Apply. Per-op failures are reported
    with their index; the response status is 207 (partial) when any failed.
    """
    data = request.get_json() or {}
    ops = data.get('ops')
    if not isinstance(ops, list) or not ops:
        return jsonify({"error": "ops must be a non-empty array"}), 400

    # ONE pre-state snapshot for the whole batch (the after_request hook skips
    # this path), so a single Undo reverts the entire Apply.
    from routes.saveload import _push_undo_snapshot
    _push_undo_snapshot(app, label=f"NL editor batch ({len(ops)} op{'s' if len(ops) != 1 else ''})")

    ordered = sorted(
        enumerate(ops),
        key=lambda t: (_BATCH_PHASE.get((t[1] or {}).get('type'), 99), t[0]),
    )

    applied, errors = [], []
    for idx, op in ordered:
        if not isinstance(op, dict):
            errors.append({"index": idx, "error": "op must be an object"})
            continue
        optype = op.get('type')
        payload = op.get('payload') or {}
        try:
            result = _apply_batch_op(app, optype, payload)
        except Exception as exc:
            logger.warning("Batch op %s (%s) failed: %s", idx, optype, exc)
            result = {"error": str(exc)}
        if result.get('error'):
            errors.append({"index": idx, "type": optype, "error": result['error']})
        else:
            applied.append({"index": idx, "type": optype, **result})

    ok = not errors
    return jsonify({
        "status": "success" if ok else "partial",
        "applied": applied,
        "errors": errors,
    }), (200 if ok else 207)


def handle_build_area_legacy(app):
    data = request.get_json()
    area_name = data['name']
    node_id = f"area_{area_name.lower().replace(' ', '_')}"
    env = {
        "light": data.get('light', 80),
        "temperature": data.get('temperature', 21),
        "air": data.get('air', 'fresh'),
        "smell": data.get('smell', 'neutral'),
        "noise": data.get('noise', 'quiet')
    }
    props = {
        "description": data.get('description', ''),
        "environment": env,
        "tags": data.get('tags', [])
    }
    node = app.world.graph.get_node(node_id)
    if node:
        node.properties.update(props)
        if 'name' in data and data['name'] != node.name:
            node.name = data['name']
    else:
        node = Node(id=node_id, type='area', name=area_name, properties=props)
        app.world.graph.add_node(node)
    return jsonify({"status": "success"})


def handle_build_item_legacy(app):
    data = request.get_json()
    area_name = data.get('area')
    item_name = data['name']
    node_id = f"item_{item_name}".lower()
    for existing_id in app.world.graph.nodes:
        if existing_id.lower() == node_id:
            node_id = existing_id
            break
    RELATION_EDGE_TYPES = {
        "in": EDGE_IN,
        "on": EDGE_ON,
        "under": EDGE_UNDER,
        "behind": EDGE_BEHIND,
        "beside": EDGE_BESIDE,
        "at": EDGE_AT,
        "carrying": EDGE_CARRYING,
    }

    tags = data.get('tags', [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(',') if t.strip()]
    props = {
        "description": data.get('description', ''),
        "actions": normalize_item_actions(data.get('actions', '')),
        "uses": int(data.get('uses', -1)),
        "weight": float(data.get('weight', 0.1)),
        "effect_target": data.get('effect_target'),
        "effect_stat": data.get('effect_stat'),
        "effect_amount": data.get('effect_amount', 0),
        "action_costs": data.get('action_costs', {}),
        "current_state": "hidden" if data.get('hidden', False) else data.get('current_state', 'normal'),
        "skill_check": data.get('skill_check', {}),
        "equip_slots": data.get('equip_slots', []),
        "tags": tags,
        # Mechanical props the engine reads (lighting, heat, sound, equipment
        # bonuses). Defaults mirror _spawn_library_item_node in library_ops.
        "light_level": data.get('light_level', 'dim'),
        "target_temperature": data.get('target_temperature'),
        "heating_rate": data.get('heating_rate'),
        "sound_level": data.get('sound_level'),
        "sound_pattern": data.get('sound_pattern'),
        "defense": data.get('defense', 0),
        "damage": data.get('damage', 0),
        "insulation": data.get('insulation', 0),
        "resistances": data.get('resistances', {}),
    }
    for _prop in ("damage_skill", "damage_type", "stun_chance", "stun_duration", "image"):
        if data.get(_prop) is not None:
            props[_prop] = data[_prop]
    contents = data.get('contents', [])
    if isinstance(contents, list) and len(contents) > 0:
        props["contents"] = contents
    else:
        props["contents"] = []
    node = app.world.graph.get_node(node_id)
    if not node:
        node = Node(id=node_id, type='item', name=item_name, properties=props)
        app.world.graph.add_node(node)
    else:
        node.properties.update(props)

    if contents and isinstance(contents, list):
        for c in contents:
            if not isinstance(c, dict):
                continue
            child_id = c.get("id", "") or f"item_{c.get('name', 'content')}".lower()
            child_name = c.get("name", child_id)
            child_node = app.world.graph.get_node(child_id)
            if not child_node:
                child_node = Node(
                    id=child_id,
                    type="item",
                    name=child_name,
                    properties={
                        "description": c.get("description", ""),
                        "actions": normalize_item_actions(c.get("actions", "examine,take")),
                        "uses": int(c.get("uses", -1)),
                        "weight": float(c.get("weight", 0.1)),
                        "current_state": "hidden",
                    }
                )
                app.world.graph.add_node(child_node)
            child_id_l = str(child_id).lower()
            node_id_l = node_id.lower()
            for e in app.world.graph.edges[:]:
                if (e.source.lower() == child_id_l and e.target.lower() == node_id_l and e.type == EDGE_IN) or \
                   (e.source.lower() == node_id_l and e.target.lower() == child_id_l and e.type in ('contains', EDGE_IN)):
                    app.world.graph.remove_edge(e.source, e.target, e.type)
            content_edge_type = RELATION_EDGE_TYPES.get((c.get("relation", "") or "").strip().lower(), EDGE_IN)
            app.world.graph.add_edge(Edge(source=child_id, target=node_id, type=content_edge_type, properties={}))

    target_type = data.get('target_type') or ('item' if data.get('container') else 'character' if data.get('character') else 'area' if area_name else None)
    target_id = data.get('target_id') or data.get('container') or data.get('character') or None
    relation = data.get('relation') or 'in'
    if target_type == 'item' and relation == 'in':
        relation = 'in'
    if target_type == 'character':
        relation = 'carrying'
    if target_type == 'area':
        relation = 'in'

    item_triggers = data.get('triggers', [])
    for trigger_data in item_triggers:
        trigger_type = trigger_data.get('trigger_type', 'on_examine')
        effect_type = trigger_data.get('effect_type', 'message')
        effect_params = trigger_data.get('effect_params', {})
        target_name = trigger_data.get('target_name', '')
        condition = trigger_data.get('condition')
        conditions = trigger_data.get('conditions', [])
        effects = trigger_data.get('effects', [])

        trigger_id = f"trigger_{node_id}_{trigger_type}_{int(time.time()*1000)}_{random.randint(0,999)}"
        trig_props = {
            "trigger_type": trigger_type,
            "effect_type": effect_type,
            "effect_params": effect_params,
            "target_name": target_name
        }
        if condition:
            trig_props["condition"] = condition
        if conditions:
            trig_props["conditions"] = conditions
        if effects:
            trig_props["effects"] = effects
        trigger_node = Node(
            id=trigger_id,
            type="logic_trigger",
            name=f"{trigger_type} → {effect_type}",
            properties=trig_props
        )
        app.world.graph.add_node(trigger_node)
        app.world.graph.add_edge(Edge(
            source=node_id,
            target=trigger_id,
            type="triggers",
            properties=trig_props
        ))

    if target_type and target_id:
        target_node = app.world.graph.get_node(target_id)
        if not target_node:
            return jsonify({"error": f"Target '{target_id}' not found"}), 404
        if target_type == 'character' and target_node.type not in ('character', 'player'):
            return jsonify({"error": f"'{target_id}' is not a character node"}), 400
        edge_type = RELATION_EDGE_TYPES.get(relation, relation)
        for e in app.world.graph.edges[:]:
            if e.source.lower() == node_id.lower() and e.type in ('in', 'location', 'contains', 'carried_by', 'carrying', 'equipped', 'on', 'under', 'behind', 'beside', 'at'):
                app.world.graph.remove_edge(e.source, e.target, e.type)
        app.world.graph.add_edge(Edge(source=node_id, target=target_id, type=edge_type))

    return jsonify({"status": "success", "node_id": node_id, "target_type": target_type, "target_id": target_id, "relation": relation})


def handle_build_connect_legacy(app):
    data = request.get_json()
    room1 = data['room1']
    room2 = data['room2']
    dir1 = data['dir1']
    dir2 = data['dir2']
    state = data.get('state', 'open')
    desc = data.get('description', '')
    cost = data.get('cost', {})

    pass_message = data.get('pass_message', '')
    auto_close = data.get('auto_close', False)
    needs_open = data.get('needs_open', {})
    tags = data.get('tags', [])
    triggers_data = data.get('triggers', [])

    def _slugify_node_id(raw):
        return raw.strip().lower().replace(' ', '_')

    way_id = data.get('way_id', '') or ''
    way_id = _slugify_node_id(way_id)
    if not way_id:
        base_way_id = f"way_{_slugify_node_id(room1)}_{_slugify_node_id(dir1)}"
        way_id = base_way_id
        candidate = 2
        while app.world.graph.get_node(way_id):
            way_id = f"{base_way_id}_{candidate}"
            candidate += 1

    def _resolve_area_node_id(area_name):
        for n in app.world.graph.nodes.values():
            if n.type == "area" and n.name == area_name:
                return n.id
        return app.world._area_node_id(area_name)

    way_props = {
        "current_state": state,
        "description": desc,
        "cost": cost,
        "area_from": room1,
        "area_to": room2
    }
    if pass_message:
        way_props["pass_message"] = pass_message
    if auto_close:
        way_props["auto_close"] = True
    see_through = data.get('see_through', False)
    if see_through:
        way_props["see_through"] = True
    one_way = data.get('one_way', False)
    if one_way:
        way_props["one_way"] = True
    if needs_open.get('enabled'):
        way_props["needs_open"] = {
            "enabled": True,
            "skill": needs_open.get('skill', 'Athletics'),
            "dc": int(needs_open.get('dc', 15))
        }
    if tags:
        way_props["tags"] = tags
    way_node = Node(
        id=way_id,
        type='way',
        name=f"{room1}-{dir1}",
        properties=way_props
    )
    app.world.graph.add_node(way_node)
    way_id = way_node.id

    view_from_a = data.get('view_from_a', '')
    view_from_b = data.get('view_from_b', '')
    area_a_id = _resolve_area_node_id(room1)
    area_b_id = _resolve_area_node_id(room2)

    way_id_l = way_id.lower()
    stale = [e for e in app.world.graph.edges
             if (e.source.lower() == way_id_l or e.target.lower() == way_id_l)
             and e.type == 'connection']
    for e in stale:
        app.world.graph.remove_edge(e.source, e.target, e.type)

    app.world.graph.add_edge(Edge(source=area_a_id, target=way_id, type='connection', properties={"direction": dir1, "visible_in_direction": view_from_a}))
    app.world.graph.add_edge(Edge(source=way_id, target=area_b_id, type='connection', properties={"direction": dir2}))
    app.world.graph.add_edge(Edge(source=area_b_id, target=way_id, type='connection', properties={"direction": dir2, "visible_in_direction": view_from_b}))
    app.world.graph.add_edge(Edge(source=way_id, target=area_a_id, type='connection', properties={"direction": dir1}))

    if triggers_data:
        for i, tdata in enumerate(triggers_data):
            trigger_type = tdata.get('trigger_type', 'on_open')
            trigger_node_id = f"trigger_{way_id}_{trigger_type}_{i}"
            trigger_node = Node(
                id=trigger_node_id,
                type='logic_trigger',
                name=f"{way_id}:{trigger_type}",
                properties=tdata
            )
            app.world.graph.add_node(trigger_node)
            app.world.graph.add_edge(Edge(
                source=way_id, target=trigger_node_id,
                type='triggers',
                properties=tdata
            ))

    return jsonify({"status": "success"})


def handle_reconnect_way(app):
    data = request.get_json()
    way_id = data.get('way_id')
    new_area_a = data.get('area_a')
    new_area_b = data.get('area_b')

    if not all([way_id, new_area_a, new_area_b]):
        return jsonify({"error": "Missing way_id, area_a, or area_b"}), 400

    world = app.world

    way_id_l = way_id.lower()
    way_edges = [e for e in world.graph.edges
                  if (e.source.lower() == way_id_l or e.target.lower() == way_id_l)
                  and e.type == 'connection']

    if not way_edges:
        return jsonify({"error": "No connection edges found for this door"}), 404

    dir_a = data.get('dir_a') or 'out'
    dir_b = data.get('dir_b') or dir_a

    old_props_a = {}
    old_props_b = {}
    for e in way_edges:
        if e.source.lower() == new_area_a.lower() and e.target.lower() == way_id_l:
            old_props_a = dict(e.properties)
        if e.source.lower() == new_area_b.lower() and e.target.lower() == way_id_l:
            old_props_b = dict(e.properties)
    if new_area_a.lower() == new_area_b.lower():
        old_props_b = dict(old_props_a)

    for e in list(way_edges):
        world.graph.remove_edge(e.source, e.target, e.type)

    props_a = {"direction": dir_a}
    props_a.update({k: v for k, v in old_props_a.items() if k != 'direction'})
    props_b = {"direction": dir_b}
    props_b.update({k: v for k, v in old_props_b.items() if k != 'direction'})

    world.graph.add_edge(Edge(source=new_area_a, target=way_id, type='connection',
                              properties=props_a))
    world.graph.add_edge(Edge(source=way_id, target=new_area_b, type='connection',
                              properties=props_b))
    world.graph.add_edge(Edge(source=new_area_b, target=way_id, type='connection',
                              properties=props_b))
    world.graph.add_edge(Edge(source=way_id, target=new_area_a, type='connection',
                              properties=props_a))

    way_node = world.graph.get_node(way_id)
    if way_node:
        area_a_node = world.graph.get_node(new_area_a)
        area_b_node = world.graph.get_node(new_area_b)
        way_node.properties["area_from"] = area_a_node.name if area_a_node else new_area_a
        way_node.properties["area_to"] = area_b_node.name if area_b_node else new_area_b

    return jsonify({"status": "success", "dir_a": dir_a, "dir_b": dir_b})


def handle_update_edge(app):
    data = request.get_json()
    source = data.get('source')
    target = data.get('target')
    old_type = data.get('old_type')
    new_type = data.get('new_type')
    properties = data.get('properties', {})

    world = app.world
    edge = None
    for e in world.graph.edges:
        if (e.source.lower() == source.lower()
                and e.target.lower() == target.lower()
                and e.type == old_type):
            edge = e
            break
    if not edge:
        return jsonify({"error": "Edge not found"}), 404

    if new_type and new_type != old_type:
        world.graph.remove_edge(source, target, old_type)
        src_r = world.graph._resolve_id(source) or source
        tgt_r = world.graph._resolve_id(target) or target
        new_edge = Edge(source=src_r, target=tgt_r, type=new_type, properties=properties)
        world.graph.add_edge(new_edge)
    else:
        edge.properties.update(properties)

    return jsonify({"status": "success"})


def handle_flip_edge(app):
    data = request.get_json()
    source = data.get('source')
    target = data.get('target')
    edge_type = data.get('type')
    if not all([source, target, edge_type]):
        return jsonify({"error": "Missing source, target, or type"}), 400

    NON_FLIPPABLE = {'connection', 'triggers', 'requires'}
    if edge_type in NON_FLIPPABLE:
        return jsonify({"error": f"Cannot flip '{edge_type}' edges"}), 400

    world = app.world.graph
    edge = None
    for e in world.edges:
        if (e.source.lower() == source.lower()
                and e.target.lower() == target.lower()
                and e.type == edge_type):
            edge = e
            break
    if not edge:
        return jsonify({"error": "Edge not found"}), 404

    src_r = world._resolve_id(source) or source
    tgt_r = world._resolve_id(target) or target
    world.remove_edge(source, target, edge_type)
    flipped = Edge(source=tgt_r, target=src_r, type=edge_type, properties=dict(edge.properties))
    world.add_edge(flipped)
    return jsonify({"status": "success", "source": flipped.source, "target": flipped.target})


def handle_delete_edge(app):
    data = request.get_json()
    source = data.get('source')
    target = data.get('target')
    edge_type = data.get('type')
    if not all([source, target, edge_type]):
        return jsonify({"error": "Missing source, target, or type"}), 400

    app.world.graph.remove_edge(source, target, edge_type)
    return jsonify({"status": "success"})


def handle_append_draft(app):
    """Append mode (task-383): merge a template-format draft INTO the live world.

    The draft is the wizard's output (areas: {name: {description, environment,
    exits, items}}, characters, world_lore). Merge semantics:
      * Existing area names are skipped (no clobber) — return them as `skipped`.
      * New areas + their ways + items are added.
      * New characters are registered only if the name is free.
      * world_lore entries are appended (category+content dedupe).
    Undo snapshot pushed BEFORE the merge.
    """
    from routes.saveload import _push_undo_snapshot
    import copy as _copy
    data = request.get_json() or {}
    world = app.world
    graph = world.graph

    _push_undo_snapshot(app, label="scenario append (wizard)")

    areas = data.get('areas') or {}
    added = []
    skipped = []
    ways_created = 0
    items_created = 0

    # 1. areas (new ones only)
    for name, a in areas.items():
        existing = next((n for n in graph.nodes.values()
                         if n.type == 'area' and n.name.lower() == str(name).lower()), None)
        if existing:
            skipped.append(name)
            continue
        aid = f"area_{str(name).lower().replace(' ', '_')}"
        if graph.get_node(aid) is None:
            env = a.get('environment') or {}
            graph.add_node(Node(id=aid, type='area', name=str(name), properties={
                'description': a.get('description', ''),
                'environment': {
                    'light': env.get('light', 'normal'),
                    'temperature': env.get('temperature', 21),
                    'air': env.get('air', 'fresh'),
                    'smell': env.get('smell', 'neutral'),
                    'noise': env.get('noise', 'quiet'),
                },
            }))
            added.append(name)

    # 2. ways + items (only within the added/skipped set; ways spider across)
    for name, a in areas.items():
        aid = f"area_{str(name).lower().replace(' ', '_')}"
        if graph.get_node(aid) is None:
            continue
        for direction, exit_data in (a.get('exits') or {}).items():
            if not exit_data:
                continue
            target = exit_data.get('target') if isinstance(exit_data, dict) else exit_data
            if not target:
                continue
            tid = f"area_{str(target).lower().replace(' ', '_')}"
            if graph.get_node(tid) is None:
                continue
            wid = f"way_{str(name).lower().replace(' ', '_')}_{str(direction).lower().replace(' ', '_')}"
            if graph.get_node(wid) is not None:
                continue
            props = {}
            if isinstance(exit_data, dict):
                props = {
                    'current_state': 'hidden' if exit_data.get('hidden') else exit_data.get('state', 'open'),
                    'description': exit_data.get('description', f"A path to the {target}."),
                    'pass_message': exit_data.get('pass_message', ''),
                    'area_from': name,
                    'area_to': target,
                }
            else:
                props = {'current_state': 'open', 'description': f"A path to the {target}.", 'area_from': name, 'area_to': target}
            graph.add_node(Node(id=wid, type='way', name=f"{name}-{direction}", properties=props))
            graph.add_edge(Edge(source=aid, target=wid, type=EDGE_CONNECTION))
            graph.add_edge(Edge(source=wid, target=tid, type=EDGE_CONNECTION))
            ways_created += 1
        # items
        for item in (a.get('items') or []):
            if not isinstance(item, dict):
                continue
            iname = item.get('name') or 'Item'
            iid = f"item_{str(iname).lower().replace(' ', '_')}"
            if graph.get_node(iid) is not None:
                continue
            graph.add_node(Node(id=iid, type='item', name=str(iname), properties={
                'description': item.get('description', ''),
                **({k: v for k, v in item.items() if k not in ('name', 'description')}),
            }))
            graph.add_edge(Edge(source=iid, target=aid, type=EDGE_IN))
            items_created += 1

    # 3. characters (new names only)
    chars_added = []
    for c in (data.get('characters') or []):
        if not isinstance(c, dict) or not c.get('name'):
            continue
        cname = str(c['name'])
        if cname in world.player_manager.players:
            continue
        from player import Player
        p = Player(cname)
        p.personality = c.get('personality', '')
        p.description = c.get('description', '')
        p.base_description = c.get('base_description', '')
        world.player_manager.add_player(p)
        chars_added.append(cname)

    # 4. world_lore append (dedupe by category+content)
    lore_added = 0
    existing_lore = list(getattr(world, 'world_lore', None) or [])
    for entry in (data.get('world_lore') or []):
        if not isinstance(entry, dict):
            continue
        if any(
            isinstance(e, dict) and e.get('category') == entry.get('category') and
            e.get('content') == entry.get('content')
            for e in existing_lore
        ):
            continue
        existing_lore.append(dict(entry))
        lore_added += 1
    world.world_lore = existing_lore

    return jsonify({
        "status": "success",
        "added_areas": added,
        "skipped_areas": skipped,
        "characters_added": chars_added,
        "ways_created": ways_created,
        "items_created": items_created,
        "lore_added": lore_added,
    })
