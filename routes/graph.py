import logging
import time
import random
import difflib
import os
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from graph import Node, Edge, EDGE_IN, EDGE_CARRYING
from logger import setup_logger
from engine.item_actions import normalize_item_actions

logger = logging.getLogger(__name__)


def register_graph_routes(app):
    """Register graph node/edge CRUD routes and legacy build endpoints."""

    @app.route('/api/graph/nodes', methods=['GET'])
    def get_graph_nodes():
        return jsonify(app.world.graph.to_dict()["nodes"])

    @app.route('/api/graph/edges', methods=['GET'])
    def get_graph_edges():
        return jsonify(app.world.graph.to_dict()["edges"])

    @app.route('/api/graph/node', methods=['POST'])
    def create_node():
        """Create a new node. Required: type, name. Optional: id, properties."""
        data = request.get_json()
        node_type = data.get('type')
        node_name = data.get('name')
        if not node_type or not node_name:
            return jsonify({"error": "Missing 'type' or 'name'"}), 400

        # Auto-generate ID if not provided — ids are always lowercase
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

    @app.route('/api/graph/node/<node_id>', methods=['PATCH'])
    def update_node(node_id):
        """Update node properties and/or name."""
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
        # Note: type change not allowed (would break edges)
        node.updated = time.time()

        # Tag validation on save — warn (log + response), never block
        warnings = []
        if 'properties' in data and 'tags' in data['properties']:
            from .helpers import validate_tags_on_save
            warnings = validate_tags_on_save(data['properties']['tags'], app.config.get('DATA_DIR'))
        return jsonify({"status": "success", "tag_warnings": warnings})

    @app.route('/api/graph/node/<node_id>/image', methods=['POST'])
    def upload_node_image(node_id):
        """Store an image for a graph node and bind it via the `image` property.

        Accepts multipart/form-data with a `file` field. Best-effort: on failure
        to store or bind, returns an error JSON (the node is left unchanged).
        Images are bundled assets under ``static/images/nodes/`` (served at the
        same URL), so offline scenarios work without remote dependencies.
        """
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

        # Best-effort cleanup of a previously uploaded file for this node so we
        # don't strand orphans. Only remove files that live in the node-images dir.
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

    @app.route('/api/graph/item/<node_id>/move', methods=['POST'])
    def move_item_node(node_id):
        """Move an item node to a area, into a container item, or onto a character (carrying)."""
        data = request.get_json()
        node = app.world.graph.get_node(node_id)
        if not node or node.type != 'item':
            # Rich error: name + id of the requested item, its current area
            # (if any node matches), the intended destination, and close
            # matches so a stale/wrong id is easy to spot.
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
                # Offer closest item ids so a wrong-case/typo id is debuggable.
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

        area_name = data.get('area', '').strip()
        container_id = data.get('container', '').strip()
        character_id = data.get('character', '').strip()
        if not area_name and not container_id and not character_id:
            return jsonify({"error": "Provide 'area', 'container', or 'character'"}), 400

        # Remove existing placement edges (canonical 'in' + legacy location/contains
        # + inventory edges) so the item ends up with exactly one new location.
        for e in app.world.graph.edges[:]:
            node_id_l = node_id.lower()
            if e.source.lower() == node_id_l and e.type in ('in', 'location', 'contains', 'carrying', 'carried_by', 'equipped'):
                app.world.graph.remove_edge(e.source, e.target, e.type)

        if container_id:
            container_node = app.world.graph.get_node(container_id)
            if not container_node:
                return jsonify({"error": f"Container item '{container_id}' not found"}), 404
            max_cap = container_node.properties.get("max_weight_capacity")
            if max_cap is not None:
                current_weight = 0
                for e in app.world.graph.edges:
                    if e.type in ('in', 'contains') and e.target.lower() == container_id.lower():
                        content_node = app.world.graph.get_node(e.source)
                        if content_node:
                            current_weight += content_node.properties.get("weight", 0)
                item_node = app.world.graph.get_node(node_id)
                item_w = item_node.properties.get("weight", 0) if item_node else 0
                remaining = max_cap - current_weight
                if item_w > remaining:
                    cname = container_node.name or container_id
                    return jsonify({"error": f"The {cname} can't hold that — it's too heavy (capacity: {current_weight:.1f}/{max_cap} kg)."}), 400
            app.world.graph.add_edge(Edge(source=node_id, target=container_id, type='in'))
            return jsonify({"status": "success", "container": container_id})
        else:
            if character_id:
                character_node = app.world.graph.get_node(character_id)
                if not character_node:
                    return jsonify({"error": f"Character '{character_id}' not found"}), 404
                if character_node.type not in ('character', 'player'):
                    return jsonify({"error": f"'{character_id}' is not a character node"}), 400
                app.world.graph.add_edge(Edge(source=node_id, target=character_id, type='carrying'))
                return jsonify({"status": "success", "character": character_id})
            area_node_id = app.world._area_node_id(area_name)
            # Find actual area node ID from graph (handles non-standard IDs)
            for n in app.world.graph.nodes.values():
                if n.type == "area" and n.name == area_name:
                    area_node_id = n.id
                    break
            if not app.world.graph.get_node(area_node_id):
                return jsonify({"error": f"Area '{area_name}' not found"}), 404
            app.world.graph.add_edge(Edge(source=node_id, target=area_node_id, type='in'))
            return jsonify({"status": "success", "area": area_name})

    @app.route('/api/graph/node/<node_id>/rename', methods=['POST'])
    def rename_node(node_id):
        """Rename a node ID, updating all edges and references."""
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

        # Create new node with same properties
        new_node = Node(id=new_id, type=node.type, name=node.name, properties=dict(node.properties))
        app.world.graph.add_node(new_node)

        # Update all edges referencing the old ID (case-insensitive — stored
        # edges may carry a mixed-case form of the old id)
        node_id_l = node_id.lower()
        for edge in app.world.graph.edges:
            if edge.source.lower() == node_id_l:
                edge.source = new_id
            if edge.target.lower() == node_id_l:
                edge.target = new_id

        # Update trigger effect params referencing the old ID
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

    @app.route('/api/graph/node/<node_id>', methods=['DELETE'])
    def delete_node(node_id):
        """Delete a node and all its incident edges."""
        node = app.world.graph.get_node(node_id)
        if not node:
            return jsonify({"error": "Node not found"}), 404

        # Optional safety checks (you can remove these if you want full freedom)
        if node.type == 'area':
            # Prevent deleting a area that has players inside
            for edge in app.world.graph.get_edges_for_target(node_id, EDGE_IN):
                if edge.source.startswith('player_'):
                    return jsonify({"error": f"Cannot delete area '{node.name}' – player inside"}), 400
        if node.type == 'character':
            # Optionally prevent deleting last character
            characters = [n for n in app.world.graph.nodes.values() if n.type == 'character']
            if len(characters) <= 1:
                return jsonify({"error": "Cannot delete the last character"}), 400

        app.world.graph.remove_node(node_id)
        return jsonify({"status": "success"})

    # ========== GENERIC EDGE CRUD ==========
    @app.route('/api/graph/edge', methods=['POST'])
    def create_edge():
        data = request.get_json()
        source = data.get('source')
        target = data.get('target')
        edge_type = data.get('type')
        if not all([source, target, edge_type]):
            return jsonify({"error": "Missing source, target, or type"}), 400

        # Resolve to canonical stored ids so a mixed-case source/target never
        # creates phantom-edge ids (standby node-id lowercase convention).
        src_r = app.world.graph._resolve_id(source) or source
        tgt_r = app.world.graph._resolve_id(target) or target
        edge = Edge(source=src_r, target=tgt_r, type=edge_type, properties=data.get('properties', {}))
        app.world.graph.add_edge(edge)
        return jsonify({"status": "success"})

    # ========== LEGACY BUILD ENDPOINTS ==========
    @app.route('/api/build/area', methods=['POST'])
    def build_area_legacy():
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

    @app.route('/api/build/item', methods=['POST'])
    def build_item_legacy():
        data = request.get_json()
        area_name = data.get('area')
        item_name = data['name']
        node_id = f"item_{item_name}".lower()
        # Reuse an existing node whose id matches ignoring case (scenario/world
        # nodes may predate the lowercase-id convention) instead of duplicating.
        for existing_id in app.world.graph.nodes:
            if existing_id.lower() == node_id:
                node_id = existing_id
                break
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
            "equip_slots": data.get('equip_slots', [])
        }
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

        # Create contains edges for container contents
        if contents and isinstance(contents, list):
            for c in contents:
                child_id = c.get("id", "") if isinstance(c, dict) else str(c)
                child_name = c.get("name", child_id) if isinstance(c, dict) else child_id
                if child_id:
                    child_node = app.world.graph.get_node(child_id)
                    if not child_node:
                        child_node = Node(
                            id=child_id,
                            type="item",
                            name=child_name,
                            properties={"description": c.get("description", "") if isinstance(c, dict) else ""}
                        )
                        app.world.graph.add_node(child_node)
                    # Remove any existing contains/in edge and add new one
                    child_id_l = str(child_id).lower()
                    node_id_l = node_id.lower()
                    for e in app.world.graph.edges[:]:
                        if (e.source.lower() == child_id_l and e.target.lower() == node_id_l and e.type == EDGE_IN) or \
                           (e.source.lower() == node_id_l and e.target.lower() == child_id_l and e.type in ('contains', EDGE_IN)):
                            app.world.graph.remove_edge(e.source, e.target, e.type)
                    app.world.graph.add_edge(Edge(source=child_id, target=node_id, type=EDGE_IN, properties={}))

        if data.get('container'):
            container_id = data.get('container')
            if not app.world.graph.get_node(container_id):
                return jsonify({"error": f"Container item '{container_id}' not found"}), 404
            for e in app.world.graph.edges[:]:
                if e.source.lower() == node_id.lower() and e.type in ('in', 'location', 'contains', 'carried_by', 'carrying', 'equipped'):
                    app.world.graph.remove_edge(e.source, e.target, e.type)
            app.world.graph.add_edge(Edge(source=node_id, target=container_id, type=EDGE_IN))
        elif data.get('character'):
            character_id = data.get('character')
            if not app.world.graph.get_node(character_id):
                return jsonify({"error": f"Character '{character_id}' not found"}), 404
            for e in app.world.graph.edges[:]:
                if e.source.lower() == node_id.lower() and e.type in ('in', 'location', 'contains', 'carried_by', 'carrying', 'equipped'):
                    app.world.graph.remove_edge(e.source, e.target, e.type)
            app.world.graph.add_edge(Edge(source=node_id, target=character_id, type=EDGE_CARRYING))
        elif area_name:
            area_node_id = app.world._area_node_id(area_name)
            # Find actual area node ID from graph (handles non-standard IDs)
            for n in app.world.graph.nodes.values():
                if n.type == "area" and n.name == area_name:
                    area_node_id = n.id
                    break
            for e in app.world.graph.edges[:]:
                if e.source.lower() == node_id.lower() and e.type in ('in', 'location', 'contains', 'carried_by', 'carrying', 'equipped'):
                    app.world.graph.remove_edge(e.source, e.target, e.type)
            app.world.graph.add_edge(Edge(source=node_id, target=area_node_id, type='in'))

        # Create trigger edges from the triggers array
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

        return jsonify({"status": "success"})

    @app.route('/api/build/connect', methods=['POST'])
    def build_connect_legacy():
        data = request.get_json()
        room1 = data['room1']
        room2 = data['room2']
        dir1 = data['dir1']
        dir2 = data['dir2']
        state = data.get('state', 'open')
        desc = data.get('description', '')
        cost = data.get('cost', {})

        # New door behavior fields
        pass_message = data.get('pass_message', '')
        auto_close = data.get('auto_close', False)
        needs_open = data.get('needs_open', {})
        tags = data.get('tags', [])
        triggers_data = data.get('triggers', [])

        def _slugify_node_id(raw: str) -> str:
            return raw.strip().lower().replace(' ', '_')

        way_id = data.get('way_id', '') or ''
        way_id = _slugify_node_id(way_id)
        if not way_id:
            # No manual ID given — generate a unique one instead of clobbering
            # an existing node with a colliding deterministic id (bug-16).
            base_way_id = f"way_{_slugify_node_id(room1)}_{_slugify_node_id(dir1)}"
            way_id = base_way_id
            candidate = 2
            while app.world.graph.get_node(way_id):
                way_id = f"{base_way_id}_{candidate}"
                candidate += 1

        def _resolve_area_node_id(area_name: str) -> str:
            # Find the actual area node by name (ids can differ in case / chars)
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
        way_id = way_node.id  # Use actual ID after potential rename by add_node

        # Connection edges (bidirectional) — resolve actual area node ids by name
        # so case / character mismatches (e.g. "Task 3 - main area") never
        # produce orphaned edges to nonexistent lowercase ids.
        view_from_a = data.get('view_from_a', '')
        view_from_b = data.get('view_from_b', '')
        area_a_id = _resolve_area_node_id(room1)
        area_b_id = _resolve_area_node_id(room2)

        # Idempotent: connecting an already-wired way must not leave stale
        # edges behind (that produced ways connected to 3+ areas). Remove any
        # existing connection edges for this way first, then rebuild the 4.
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

        # Create trigger nodes and edges if provided
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

    @app.route('/api/graph/way/reconnect', methods=['POST'])
    def reconnect_way():
        """Change which two areas a way connects to."""
        data = request.get_json()
        way_id = data.get('way_id')
        new_area_a = data.get('area_a')
        new_area_b = data.get('area_b')

        if not all([way_id, new_area_a, new_area_b]):
            return jsonify({"error": "Missing way_id, area_a, or area_b"}), 400

        world = app.world

        # Find all connection edges for this door (case-insensitive — edges
        # created before the lowercase-id convention may use mixed-case ids)
        way_id_l = way_id.lower()
        way_edges = [e for e in world.graph.edges
                      if (e.source.lower() == way_id_l or e.target.lower() == way_id_l)
                      and e.type == 'connection']

        if not way_edges:
            return jsonify({"error": "No connection edges found for this door"}), 404

        dir_a = data.get('dir_a') or 'out'
        dir_b = data.get('dir_b') or dir_a

        # Preserve old edge properties (cardinal, visible_in_direction, etc.).
        # The canonical edge is area -> way: visible_in_direction, cardinal,
        # and direction live there (the reverse way -> area edges carry only a
        # stale copy of direction). Match that edge specifically — matching by
        # area alone would pick the last edge in iteration order, which for the
        # A side is the reverse edge, silently dropping view/cardinal on
        # reconnect.
        old_props_a = {}
        old_props_b = {}
        for e in way_edges:
            if e.source.lower() == new_area_a.lower() and e.target.lower() == way_id_l:
                old_props_a = dict(e.properties)
            if e.source.lower() == new_area_b.lower() and e.target.lower() == way_id_l:
                old_props_b = dict(e.properties)
        # If same room on both sides after reconnect, use props_a for both
        if new_area_a.lower() == new_area_b.lower():
            old_props_b = dict(old_props_a)

        # Remove old edges
        for e in list(way_edges):
            world.graph.remove_edge(e.source, e.target, e.type)

        # Add new edges with preserved properties merged with new direction
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

        # Update door node's area_from/area_to properties for info display
        way_node = world.graph.get_node(way_id)
        if way_node:
            # Resolve display names from node IDs
            area_a_node = world.graph.get_node(new_area_a)
            area_b_node = world.graph.get_node(new_area_b)
            way_node.properties["area_from"] = area_a_node.name if area_a_node else new_area_a
            way_node.properties["area_to"] = area_b_node.name if area_b_node else new_area_b

        return jsonify({"status": "success", "dir_a": dir_a, "dir_b": dir_b})

    @app.route('/api/graph/edge/update', methods=['POST'])
    def update_edge():
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
            # Resolve to canonical stored ids so a mixed-case request never
            # creates phantom-edge ids.
            src_r = world.graph._resolve_id(source) or source
            tgt_r = world.graph._resolve_id(target) or target
            new_edge = Edge(source=src_r, target=tgt_r, type=new_type, properties=properties)
            world.graph.add_edge(new_edge)
        else:
            edge.properties.update(properties)

        return jsonify({"status": "success"})

    @app.route('/api/graph/edge/flip', methods=['POST'])
    def flip_edge():
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

    @app.route('/api/graph/edge', methods=['DELETE'])
    def delete_edge():
        data = request.get_json()
        source = data.get('source')
        target = data.get('target')
        edge_type = data.get('type')
        if not all([source, target, edge_type]):
            return jsonify({"error": "Missing source, target, or type"}), 400

        app.world.graph.remove_edge(source, target, edge_type)
        return jsonify({"status": "success"})


