"""graph_image_ops: node and background image upload, removal, and persistence.

@module graph_image_ops
@contributes node expression images, background map uploads and multi-layer metadata
@docs docs/virtualWorld/World Building/Graph System.md
"""

import os
import time
import logging
from flask import request, jsonify
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

#: Expression-pack slots a character image can occupy (SillyTavern-style).
IMAGE_KINDS = ("profile", "full")


def _expression_slug(value, fallback="neutral"):
    """Normalise an expression key (emotion or action name) to a filename slug."""
    slug = secure_filename(str(value or "")).lower().replace("-", "_")
    return slug or fallback


def _delete_managed_image(images_dir, url):
    """Delete a previously uploaded node image if it lives in ``images_dir``."""
    if not url or not isinstance(url, str) or "/static/images/nodes/" not in url:
        return
    path = os.path.join(images_dir, os.path.basename(url))
    if os.path.isfile(path):
        try:
            os.remove(path)
        except OSError:
            pass


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

    kind = (request.form.get('kind') or 'full').strip().lower()
    if kind not in IMAGE_KINDS:
        return jsonify({"error": f"Unknown image kind '{kind}'. Use 'profile' or 'full'."}), 400
    expression = _expression_slug(request.form.get('expression') or 'neutral')

    try:
        images_dir = app.config.get('IMAGES_DIR') or os.path.join(
            app.root_path, 'static', 'images', 'nodes')
        os.makedirs(images_dir, exist_ok=True)
        safe_base = secure_filename(f"{node_id}-{kind}-{expression}") or 'node'
        filename = f"{safe_base}-{int(time.time() * 1000)}.{ext}"
        path = os.path.join(images_dir, filename)
        upload.save(path)
    except Exception as exc:
        logger.warning("Image upload save failed for %s: %s", node_id, exc)
        return jsonify({"error": "Could not save image on server."}), 500

    expressions = node.properties.get('expressions')
    if not isinstance(expressions, dict):
        expressions = {}
    slot = expressions.get(expression)
    if not isinstance(slot, dict):
        slot = {}

    _delete_managed_image(images_dir, slot.get(kind))

    url = f"/static/images/nodes/{filename}"
    slot[kind] = url
    expressions[expression] = slot
    node.properties['expressions'] = expressions
    # Back-compat defaults: the graph thumbnail and simple avatars read these.
    if expression == 'neutral':
        node.properties['image' if kind == 'full' else 'profile_image'] = url
    node.updated = time.time()
    return jsonify({
        "status": "success", "image": url, "kind": kind,
        "expression": expression, "expressions": expressions,
    })


def handle_remove_node_image(app, node_id):
    """Remove one expression image slot (kind + expression) and its file."""
    node = app.world.graph.get_node(node_id)
    if not node:
        return jsonify({"error": "Node not found"}), 404

    data = request.get_json(silent=True) or {}
    kind = (data.get('kind') or request.args.get('kind') or 'full').strip().lower()
    if kind not in IMAGE_KINDS:
        return jsonify({"error": f"Unknown image kind '{kind}'. Use 'profile' or 'full'."}), 400
    expression = _expression_slug(
        data.get('expression') or request.args.get('expression') or 'neutral')

    images_dir = app.config.get('IMAGES_DIR') or os.path.join(
        app.root_path, 'static', 'images', 'nodes')

    expressions = node.properties.get('expressions')
    removed = None
    if isinstance(expressions, dict):
        slot = expressions.get(expression)
        if isinstance(slot, dict):
            removed = slot.pop(kind, None)
            if not slot:
                expressions.pop(expression, None)
        if expressions:
            node.properties['expressions'] = expressions
        else:
            node.properties.pop('expressions', None)
    if removed:
        _delete_managed_image(images_dir, removed)
    if expression == 'neutral':
        node.properties.pop('image' if kind == 'full' else 'profile_image', None)
    node.updated = time.time()
    return jsonify({
        "status": "success", "kind": kind, "expression": expression,
        "expressions": node.properties.get('expressions', {}),
    })


def handle_upload_background_image(app):
    """Upload the graph's background map image.

    Saves a real FILE under ``static/images/backgrounds`` and returns its path -
    mirroring handle_upload_node_image. Deliberately NOT base64-in-the-scenario:
    a 2 MB map would add ~2.7 MB of text to the world file on every commit.
    """
    upload = request.files.get('file')
    if not upload or not upload.filename:
        return jsonify({"error": "No file provided (field 'file')"}), 400

    allowed = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp'}
    ext = (upload.filename.rsplit('.', 1)[-1] if '.' in upload.filename else '').lower()
    if ext not in allowed:
        return jsonify({
            "error": f"Unsupported image type '{ext or 'unknown'}'. Allowed: {', '.join(sorted(allowed))}.",
        }), 400

    try:
        images_dir = os.path.join(app.root_path, 'static', 'images', 'backgrounds')
        os.makedirs(images_dir, exist_ok=True)
        safe_base = secure_filename(os.path.splitext(upload.filename)[0]) or 'background'
        filename = f"{safe_base}-{int(time.time() * 1000)}.{ext}"
        upload.save(os.path.join(images_dir, filename))
    except Exception as exc:
        logger.warning("Background image save failed: %s", exc)
        return jsonify({"error": "Could not save image on server."}), 500

    url = f"/static/images/backgrounds/{filename}"
    return jsonify({"status": "success", "image": url})


def handle_save_background(app):
    """Persist the background map's path + transform on the world.

    Presentation-only state (like `world_lore`): it lives at the scenario's top
    level so a laid-out map travels with the file and can be committed.
    """
    data = request.get_json(silent=True) or {}

    # Multi-layer form (task-451): the client owns the whole block and replaces
    # it. A scenario always serializes this key, so an EMPTY layer list has to
    # persist as an empty list - that is what tells the client to clear, and
    # losing it is bug-39.
    if 'layers' in data:
        raw_layers = data.get('layers')
        layers = [l for l in raw_layers if isinstance(l, dict)] if isinstance(raw_layers, list) else []
        positions = data.get('positions')
        app.world.graph_background = {
            'layers': layers,
            'positions': positions if isinstance(positions, dict) else {},
            'layoutLocked': bool(data.get('layoutLocked')),
        }
        return jsonify({"status": "success", "graph_background": app.world.graph_background})

    # Legacy single-image form: partial merge, kept so an older client (or a
    # hand-rolled request) still works.
    background = dict(getattr(app.world, 'graph_background', None) or {})

    if 'image' in data:
        image = data.get('image')
        background['image'] = str(image) if image else None
    for key in ('rect', 'crop'):
        if key in data:
            value = data.get(key)
            background[key] = value if isinstance(value, dict) else None
    for key in ('rotation', 'opacity'):
        if key in data:
            try:
                background[key] = float(data[key])
            except (TypeError, ValueError):
                pass
    if 'locked' in data:
        background['locked'] = bool(data['locked'])

    app.world.graph_background = background
    return jsonify({"status": "success", "graph_background": background})
