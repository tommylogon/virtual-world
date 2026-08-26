"""Trigger routes — dry-run / live-run a trigger definition + world-wide validation."""
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
