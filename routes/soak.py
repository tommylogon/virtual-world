"""URL registration for the soak-run API (logic lives in routes/soak_ops.py)."""
from routes import soak_ops


def register_soak_routes(app):
    app.add_url_rule('/api/soak/meta', 'soak_meta', soak_ops.meta, methods=['GET'])
    app.add_url_rule('/api/soak/runs', 'soak_list_runs', soak_ops.list_runs, methods=['GET'])
    app.add_url_rule('/api/soak/runs', 'soak_start_run', soak_ops.start, methods=['POST'])
    app.add_url_rule('/api/soak/runs/<run_id>', 'soak_get_run', soak_ops.get_run, methods=['GET'])
    app.add_url_rule('/api/soak/runs/<run_id>/stop', 'soak_stop_run', soak_ops.stop, methods=['POST'])
    app.add_url_rule('/api/soak/runs/<run_id>', 'soak_delete_run', soak_ops.delete, methods=['DELETE'])
    app.add_url_rule('/api/soak/runs/<run_id>/report', 'soak_report', soak_ops.report, methods=['GET'])
    app.add_url_rule('/api/soak/runs/<run_id>/export', 'soak_export', soak_ops.export, methods=['GET'])
    app.add_url_rule('/api/soak/runs/<run_id>/characters', 'soak_characters',
                     soak_ops.characters, methods=['GET'])
    app.add_url_rule('/api/soak/runs/<run_id>/characters/<path:name>/series',
                     'soak_character_series', soak_ops.character_series, methods=['GET'])
    app.add_url_rule('/api/soak/runs/<run_id>/events', 'soak_events', soak_ops.events, methods=['GET'])
    app.add_url_rule('/api/soak/runs/<run_id>/samples', 'soak_samples', soak_ops.samples, methods=['GET'])
