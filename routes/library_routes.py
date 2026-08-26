"""Library routes — unified CRUD and import for all entity types.

Extends items_registry.py with generic routes for areas, conditions,
behaviours, and multi-type build/refresh operations.
"""

import logging
from flask import Flask, request, jsonify
from .library_ops import (
    REGISTRY_TYPES,
    RELATION_EDGE_TYPES,
    _library_type_count,
    _lookup_library_item,
    _content_ref_id,
    _content_relation,
    graph_add_relation_edge,
    graph_add_in_edge,
    _materialize_trigger_nodes,
    _spawn_library_item_node,
    _materialize_contained_items,
    _refresh_item,
    _refresh_way,
    _refresh_area,
    _refresh_character,
    _rebuild_triggers,
    handle_library_entities,
    handle_library_list,
    handle_library_all,
    handle_library_create_or_update,
    handle_library_delete,
    handle_library_rename,
    handle_library_place_item,
    handle_library_import_character,
    handle_library_import_area,
    handle_refresh_way_from_library,
    handle_library_refresh_to_world,
)

logger = logging.getLogger(__name__)


def register_library_routes(app):
    @app.route('/api/library/entities', methods=['GET'])
    def library_entities():
        return handle_library_entities(app)

    @app.route('/api/library/<registry_type>', methods=['GET'])
    def library_list(registry_type):
        return handle_library_list(app, registry_type)

    @app.route('/api/library/all', methods=['GET'])
    def library_all():
        return handle_library_all(app)

    @app.route('/api/library/<registry_type>', methods=['POST'])
    def library_create_or_update(registry_type):
        return handle_library_create_or_update(app, registry_type)

    @app.route('/api/library/<registry_type>/<entry_id>', methods=['DELETE'])
    def library_delete(registry_type, entry_id):
        return handle_library_delete(app, registry_type, entry_id)

    @app.route('/api/library/<registry_type>/<entry_id>/rename', methods=['POST'])
    def library_rename(registry_type, entry_id):
        return handle_library_rename(app, registry_type, entry_id)

    @app.route('/api/library/items/<item_id>/place', methods=['POST'])
    def library_place_item(item_id):
        return handle_library_place_item(app, item_id)

    @app.route('/api/library/import/character/<char_id>', methods=['POST'])
    def library_import_character(char_id):
        return handle_library_import_character(app, char_id)

    @app.route('/api/library/import/area/<area_id>', methods=['POST'])
    def library_import_area(area_id):
        return handle_library_import_area(app, area_id)

    @app.route('/api/ways/<node_id>/refresh-from-library', methods=['POST'])
    def refresh_way_from_library(node_id):
        return handle_refresh_way_from_library(app, node_id)

    @app.route('/api/library/refresh-to-world', methods=['POST'])
    def library_refresh_to_world():
        return handle_library_refresh_to_world(app)
