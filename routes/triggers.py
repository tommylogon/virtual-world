"""Trigger routes — dry-run / live-run a trigger definition + world-wide validation."""
import time

from flask import jsonify, request


def register_triggers_routes(app):
    @app.route('/api/triggers/validate', methods=['GET'])
    def validate_triggers():
        """Scan every trigger in the world for broken references.

        Optional query param ``node_id`` filters to the triggers owned by a
        single node. Returns ``{"issues": [...], "count": n}`` where each
        issue is ``{severity, code, message, source_node_id, ...}``.
        """
        world = app.world
        node_id = request.args.get('node_id', '')
        issues = world.validate_triggers(node_id=node_id)
        return jsonify({
            "issues": issues,
            "count": len(issues),
        })

    @app.route('/api/triggers/ignore', methods=['POST'])
    def set_ignored_issue():
        """Dismiss / restore a validation code on a single node (task-393).

        Request JSON: {"node_id": "...", "code": "empty_trigger",
        "ignore": true|false}. Writes the code into the node's
        ``ignored_issues`` list (with ``_ignored_at`` = the node's updated
        timestamp at write time); the validator hides the code until the node
        is edited again. Returns the node's new ignored list.
        """
        data = request.get_json() or {}
        node_id = data.get('node_id') or ''
        code = str(data.get('code') or '').strip()
        if not node_id or not code:
            return jsonify({"error": "node_id and code are required"}), 400
        world = app.world
        node = world.graph.get_node(node_id)
        if node is None:
            return jsonify({"error": f"Node '{node_id}' not found"}), 404
        props = node.properties
        ignored = [c for c in (props.get('ignored_issues') or []) if c != code]
        if data.get('ignore', True):
            ignored.append(code)
        props['ignored_issues'] = sorted(set(ignored))
        node.updated = time.time()
        props['_ignored_at'] = node.updated
        world._edit_seq = getattr(world, '_edit_seq', 0) + 1
        return jsonify({"status": "success", "ignored_issues": props['ignored_issues']})
    @app.route('/api/triggers/test', methods=['POST'])
    def test_trigger():
        """Evaluate a trigger definition against the live world.

        Request JSON:
        {
            "trigger": {...trigger properties...},  # trigger_type, conditions, effects, conditions_logic
            "item_id": "item_xyz",                   # optional — context item
            "dry_run": true,                         # default true; false = execute effects
            "context": {...}                         # optional extra template context (e.g. speech, speaker)
        }

        Returns the TriggerSystem.test_trigger result: per-condition pass/fail,
        whether it's fireable, dry-run effect descriptions or live outputs, and
        side-effect warnings.
        """
        data = request.get_json() or {}
        trigger_def = data.get('trigger') or {}
        if not isinstance(trigger_def, dict) or not trigger_def:
            return jsonify({"error": "Missing 'trigger' definition"}), 400

        item_id = data.get('item_id') or ''
        dry_run = data.get('dry_run', True)
        context = data.get('context') or {}

        world = app.world
        item_node = None
        if item_id:
            item_node = world.graph.get_node(item_id)

        result = world.test_trigger(
            trigger_def, item_node=item_node, dry_run=bool(dry_run), context=context
        )
        return jsonify(result)

    @app.route('/api/triggers/validate-definition', methods=['POST'])
    def validate_trigger_definition():
        """Validate an unsaved trigger definition from the editor/graph."""
        data = request.get_json() or {}
        trigger_def = data.get('trigger') or {}
        if not isinstance(trigger_def, dict) or not trigger_def:
            return jsonify({"error": "Missing 'trigger' definition"}), 400

        source_node_id = data.get('source_node_id') or data.get('item_id') or ''
        world = app.world
        issues = world.validate_trigger_props(
            trigger_def, source_node_id=source_node_id
        )
        return jsonify({"issues": issues, "count": len(issues)})

    @app.route('/api/import/audit', methods=['POST'])
    def audit_import():
        """Run the full TriggerValidator against an UNLOADED world dict.

        Builds a throwaway VirtualWorld (no side effects on the live world,
        no autosave, no scenario writes) and returns grouped issue counts —
        the backend half of import preview / scenario auditing.
        """
        data = request.get_json() or {}
        if not isinstance(data, dict) or not data:
            return jsonify({"error": "No import data provided"}), 400
        try:
            from virtual_world_engine import VirtualWorld
            from engine.trigger_validator import TriggerValidator
            probe = VirtualWorld()
            probe.graph.clear()
            probe.player_manager.players = {}
            probe.load_from_dict(data)
            validator = TriggerValidator(probe.graph)
            issues = validator.validate()
        except Exception as exc:
            return jsonify({"error": f"Audit failed: {exc}"}), 400
        return jsonify({
            "issues": issues,
            "count": len(issues),
            "areas": len(probe.graph.nodes) and len([n for n in probe.graph.nodes.values() if n.type == "area"]),
            "items": len([n for n in probe.graph.nodes.values() if n.type == "item"]),
            "players": len(probe.player_manager.players),
            "severities": {
                sev: len([i for i in issues if i.get("severity") == sev])
                for sev in ("error", "warning", "info")
            },
        })
