"""Unit tests for unmade scope generate preview endpoint (task-580)."""
from pathlib import Path
from flask import Flask
import pytest

from engine.generation import UNMADE, MATERIALIZED
from engine.generation_recipes import RECIPES, apartment_v1
from graph import Node, WorldGraph
from routes.world_grid import register_world_grid_routes


@pytest.fixture
def app():
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["DATA_DIR"] = str(Path(__file__).parent.parent / "data")

    # Mock world
    class MockWorld:
        def __init__(self):
            self.graph = WorldGraph()
            self.turn_number = 0
            self.world_scopes = {
                "apartment_test": {
                    "id": "apartment_test",
                    "name": "Apartment Test",
                    "state": UNMADE,
                    "recipe": "apartment.v1",
                    "seed": "test-seed-123",
                },
                "already_made_scope": {
                    "id": "already_made_scope",
                    "name": "Made Scope",
                    "state": MATERIALIZED,
                    "recipe": "apartment.v1",
                    "seed": "test-seed-456",
                }
            }

    app.world = MockWorld()
    register_world_grid_routes(app)
    return app


def test_preview_returns_patch_details_without_modifying_graph(app):
    client = app.test_client()

    initial_nodes = len(app.world.graph.nodes)
    resp = client.post("/api/world/scopes/apartment_test/grid/generate/preview", json={})
    assert resp.status_code == 200
    data = resp.get_json()

    assert data["status"] == "ok"
    assert data["preview"] is True
    assert data["scope_id"] == "apartment_test"
    assert data["recipe_id"] == "apartment.v1"
    assert data["is_materialized"] is False
    assert len(data["areas"]) == 3, f"Expected 3 areas in apartment.v1, got {len(data['areas'])}"
    assert len(data["items"]) > 0
    assert len(data["ways"]) > 0

    # Assert dry-run: graph was NOT modified
    assert len(app.world.graph.nodes) == initial_nodes, "Preview must not write nodes to graph"


def test_preview_reports_already_materialized(app):
    client = app.test_client()
    resp = client.post("/api/world/scopes/already_made_scope/grid/generate/preview", json={})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["is_materialized"] is True


def test_preview_404_for_missing_scope(app):
    client = app.test_client()
    resp = client.post("/api/world/scopes/nonexistent_scope_xyz/grid/generate/preview", json={})
    assert resp.status_code == 404
