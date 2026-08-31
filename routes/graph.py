import logging
from flask import Flask, request, jsonify
from .graph_ops import (
    handle_get_graph_nodes,
    handle_get_graph_edges,
    handle_create_node,
    handle_duplicate_node,
    handle_update_node,
    handle_upload_node_image,
    handle_move_item_node,
    handle_rename_node,
    handle_delete_node,
    handle_get_area_sounds,
    handle_create_edge,
    handle_build_area_legacy,
    handle_build_item_legacy,
    handle_build_connect_legacy,
    handle_reconnect_way,
    handle_update_edge,
    handle_flip_edge,
    handle_delete_edge,
    handle_append_draft,
    handle_graph_batch,
)

logger = logging.getLogger(__name__)


def register_graph_routes(app):
    @app.route('/api/graph/nodes', methods=['GET'])
    def get_graph_nodes():
        return handle_get_graph_nodes(app)

    @app.route('/api/graph/edges', methods=['GET'])
    def get_graph_edges():
        return handle_get_graph_edges(app)

    @app.route('/api/graph/node', methods=['POST'])
    def create_node():
        return handle_create_node(app)

    @app.route('/api/graph/node/<node_id>', methods=['PATCH'])
    def update_node(node_id):
        return handle_update_node(app, node_id)

    @app.route('/api/graph/node/<node_id>/image', methods=['POST'])
    def upload_node_image(node_id):
        return handle_upload_node_image(app, node_id)

    @app.route('/api/graph/item/<node_id>/move', methods=['POST'])
    def move_item_node(node_id):
        return handle_move_item_node(app, node_id)

    @app.route('/api/graph/node/<node_id>/rename', methods=['POST'])
    def rename_node(node_id):
        return handle_rename_node(app, node_id)

    @app.route('/api/areas/<area_id>/sounds', methods=['GET'])
    def area_sounds(area_id):
        return handle_get_area_sounds(app, area_id)

    @app.route('/api/graph/duplicate', methods=['POST'])
    def duplicate_node():
        return handle_duplicate_node(app)

    @app.route('/api/graph/node/<node_id>', methods=['DELETE'])
    def delete_node(node_id):
        return handle_delete_node(app, node_id)

    @app.route('/api/graph/edge', methods=['POST'])
    def create_edge():
        return handle_create_edge(app)

    @app.route('/api/build/area', methods=['POST'])
    def build_area_legacy():
        return handle_build_area_legacy(app)

    @app.route('/api/build/item', methods=['POST'])
    def build_item_legacy():
        return handle_build_item_legacy(app)

    @app.route('/api/build/connect', methods=['POST'])
    def build_connect_legacy():
        return handle_build_connect_legacy(app)

    @app.route('/api/graph/way/reconnect', methods=['POST'])
    def reconnect_way():
        return handle_reconnect_way(app)

    @app.route('/api/graph/edge/update', methods=['POST'])
    def update_edge():
        return handle_update_edge(app)

    @app.route('/api/graph/edge/flip', methods=['POST'])
    def flip_edge():
        return handle_flip_edge(app)

    @app.route('/api/graph/edge', methods=['DELETE'])
    def delete_edge():
        return handle_delete_edge(app)

    @app.route('/api/scenario/append', methods=['POST'])
    def append_draft():
        return handle_append_draft(app)

    @app.route('/api/graph/batch', methods=['POST'])
    def graph_batch():
        return handle_graph_batch(app)
