"""
VirtualWorld Engine - Flask Application
Reworked with lessons from WorldGraph: modular, robust, and ready for expansion.
"""
from flask import Flask, request
from virtual_world_engine import VirtualWorld
from area import Area
import json
import os
import logging
from routes.helpers import save_autosave, load_autosave_if_exists

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app(config=None):
    """Application factory pattern – allows multiple instances and easier testing."""
    app = Flask(__name__)

    # Default configuration
    app.config.update({
        'DATA_DIR': os.path.join(os.path.dirname(__file__), 'data'),
    })

    # Override with any passed config
    if config:
        app.config.update(config)

    # Ensure data directory exists
    os.makedirs(app.config['DATA_DIR'], exist_ok=True)

    # Initialize the world instance (will be attached to app for route access)
    world = VirtualWorld()

    # Load world from template JSON instead of creating bare default area
    template_path = os.path.join(os.path.dirname(__file__), 'world_template.json')
    if os.path.exists(template_path):
        try:
            with open(template_path, 'r', encoding='utf-8-sig') as f:
                template_data = json.load(f)
            world.load_from_dict(template_data)
            logger.info(f"Loaded world template from {template_path}")
        except Exception as e:
            logger.warning(f"Could not load world template: {e}. Using fallback default area.")
            # Only create fallback if world has no areas
            if not world.areas:
                spawn = Area("Living Area", "A cozy starting area.", [])
                world.add_area(spawn)
                world.set_current_area("Living Area")
    else:
        logger.warning(f"world_template.json not found at {template_path}. Using default area.")
        spawn = Area("Living Area", "A cozy starting area.", [])
        world.add_area(spawn)
        world.set_current_area("Living Area")

    # Track the scenario source file for Save Scenario
    world._scenario_source = template_path if os.path.exists(template_path) else None

    # Seed the data-driven conditions/traits catalogs on first run (never
    # overwrites existing full-schema files). Runs before routes import the
    # engine modules so derived constants / lookups capture the loaded state.
    if not app.config.get('TESTING'):
        from player import seed_condition_library
        from engine.traits import seed_trait_library
        seed_condition_library()
        seed_trait_library()

    # Override template with autosave if present (so edits survive restart)
    # Skip autosave in TESTING mode — tests need deterministic template state.
    if app.config.get('TESTING'):
        logger.info("TESTING mode — skipping autosave load")
    elif not load_autosave_if_exists(world):
        logger.info("No autosave found — using template")

    # Attach world to app for easy access in routes
    app.world = world

    # In-session undo/redo stacks. Each entry is (state_dict, scenario_source).
    # Reset loads state is saved here so undo can restore deleted areas/connections.
    app._undo_stack = []
    app._redo_stack = []

    # Auto-save after every mutating API operation
    @app.after_request
    def autosave_after_mutation(response):
        method = request.method
        path = request.path
        if response.status_code and response.status_code < 400:
            if method in ('POST', 'PATCH', 'DELETE') and (
                '/api/graph/' in path or '/api/players/' in path
                or '/api/build/' in path or '/api/world/' in path
            ):
                # Per-edit undo snapshots (task-371): every graph/player/build
                # mutation becomes a labeled history entry so simple edits show
                # up in the 📜 undo dropdown. Load/reset/undo/redo push their
                # own entries and live outside the covered paths. (In-memory
                # only — safe to keep active in TESTING.)
                if not app.config.get('TESTING'):
                    app.world._edit_seq = getattr(app.world, '_edit_seq', 0) + 1
                try:
                    from routes.saveload import _push_undo_snapshot
                    if path == '/api/graph/batch':
                        # task-387: the NL-editor batch handler pushes its own
                        # single PRE-state snapshot; a post-state push here
                        # would make the first Undo a no-op.
                        label = None
                    elif path.startswith('/api/graph/node/') and not path.endswith(('/image', '/rename')):
                        label = f"edited node {path.rsplit('/', 1)[-1]}"
                    elif '/api/graph/' in path:
                        label = "graph edit"
                    elif '/api/players/' in path:
                        label = "character edit"
                    elif '/api/build/' in path:
                        label = "build edit"
                    else:
                        label = "world edit"
                    if label is not None:
                        _push_undo_snapshot(app, label=label)
                except Exception:
                    pass  # never let history bookkeeping break a mutation
                if not app.config.get('TESTING'):
                    save_autosave(app.world)
        # Broadcast a live world-change so the GUI (and any MCP / SSE client) can
        # refetch state in real time — including edits made by external agents
        # hitting the same API. The MCP server tags calls with X-WV-Editor so the
        # editor is attributed in the live stream.
        if method in ('POST', 'PATCH', 'DELETE', 'PUT') and path.startswith('/api/'):
            editor = request.headers.get('X-WV-Editor', 'app')
            from engine.world_events import hub
            hub.publish({
                'type': 'world_changed',
                'method': method,
                'path': path,
                'editor': editor,
            })
        return response

    # Register all route modules
    register_routes(app)

    return app

def register_routes(app):
    """Register all route modules onto the Flask app."""
    from routes.pages import register_pages_routes
    from routes.action import register_action_routes
    from routes.players import register_players_routes
    from routes.graph import register_graph_routes
    from routes.saveload import register_saveload_routes
    from routes.settings import register_settings_routes
    from routes.world_lore import register_world_lore_routes
    from routes.memories import register_memories_routes
    from routes.narration import register_narration_routes
    from routes.health import register_health_routes
    from routes.library_routes import register_library_routes
    from routes.tags import register_tag_routes
    from routes.triggers import register_triggers_routes
    from routes.scene import register_scene_routes
    from routes.search import register_search_routes
    from routes.events import register_events_routes

    register_health_routes(app)
    register_events_routes(app)
    register_pages_routes(app)
    register_action_routes(app)
    register_players_routes(app)
    register_graph_routes(app)
    register_saveload_routes(app)
    register_settings_routes(app)
    register_world_lore_routes(app)
    register_memories_routes(app)
    register_narration_routes(app)
    register_library_routes(app)
    register_tag_routes(app)
    register_triggers_routes(app)
    register_scene_routes(app)
    register_search_routes(app)

# For running directly (development)
if __name__ == '__main__':
    app = create_app()
    app.run(debug=os.environ.get('VW_DEBUG') == '1', port=4444)
