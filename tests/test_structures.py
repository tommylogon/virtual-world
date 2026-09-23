"""Structure templates (task-357): capture + materialize connected areas.

Covers the reframed contract: template capture is a raw graph subset with
residents as Player payloads; materialization is deterministic, add-only, remaps
ids only (never display names), lands boundary exits as dead stubs, and brings
residents up in background simulation mode.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from graph import Edge, Node, EDGE_CARRYING, EDGE_CONNECTION, EDGE_IN
from engine.structures import (
    collect_structure,
    materialize_structure,
    summarize_structure,
)


def _make_world():
    from virtual_world_engine import VirtualWorld
    from area import Area
    from player import Player

    world = VirtualWorld()
    world.add_area(Area("Hall", "A narrow hall.", []))
    world.add_area(Area("Kitchen", "A steamy kitchen.", []))
    world.connect_areas("Hall", "Kitchen", "north", "south")

    hall_id = world._area_node_id("Hall")

    # An item placed in the hall and a locked item in the kitchen.
    world.graph.add_node(Node(id="item_lamp", type="item", name="Lamp", properties={
        "actions": ["examine", "take"], "current_state": "normal", "last_relation": "stale",
    }))
    world.graph.add_edge(Edge(source="item_lamp", target=hall_id, type=EDGE_IN))
    world.graph.add_node(Node(id="item_knife", type="item", name="Knife", properties={
        "actions": ["examine", "take"], "current_state": "locked",
    }))
    world.graph.add_edge(Edge(source="item_knife", target=world._area_node_id("Kitchen"), type=EDGE_IN))
    # The resident carries the lamp.
    world.graph.add_edge(Edge(source="item_lamp", target="player_miki", type=EDGE_CARRYING))

    # A boundary way: connected to the hall, no far-side area.
    world.graph.add_node(Node(id="way_hall_out", type="way", name="Hall-Out", properties={
        "current_state": "open",
    }))
    world.graph.add_edge(Edge(source=hall_id, target="way_hall_out", type=EDGE_CONNECTION,
                              properties={"direction": "out"}))

    # A resident.
    miki = Player("miki")
    miki.current_area = "Hall"
    world.player_manager.add_player(miki)
    return world


@pytest.fixture
def world():
    return _make_world()


def _collect(world, **kwargs):
    kwargs.setdefault("include_items", True)
    kwargs.setdefault("include_characters", True)
    return collect_structure(world, world._area_node_id("Hall"), **kwargs)


class TestCollectStructure:
    def test_captures_connected_areas_and_ways(self, world):
        template = _collect(world, include_items=False, include_characters=False)
        assert template["captured"]["areas"] == 2
        assert template["captured"]["ways"] >= 1
        node_types = {n["type"] for n in template["nodes"].values()}
        assert "area" in node_types and "way" in node_types

    def test_cycle_safe(self, world):
        # Add a second connection closing the loop Hall↔Kitchen already; add
        # Kitchen→Hall as another way to force a cycle over connections.
        world.connect_areas("Kitchen", "Hall", "east", "west")
        template = _collect(world, include_items=False, include_characters=False)
        assert template["captured"]["areas"] == 2

    def test_items_included_and_runtime_props_stripped(self, world):
        template = _collect(world, include_items=True, include_characters=False)
        assert "item_lamp" in template["nodes"]
        assert "item_knife" in template["nodes"]
        assert template["nodes"]["item_lamp"]["properties"].get("last_relation") is None
        assert template["nodes"]["item_knife"]["properties"]["current_state"] == "locked"

    def test_characters_excluded_by_default(self, world):
        template = _collect(world, include_characters=False)
        assert template["residents"] == []

    def test_characters_captured_as_players_not_nodes(self, world):
        template = _collect(world, include_characters=True)
        names = [r["name"] for r in template["residents"]]
        assert names == ["miki"]
        resident = template["residents"][0]
        assert resident["player"]["name"] == "miki"
        assert resident["player"]["current_area"] == "Hall"
        # The anchor travels as the resident, never as a raw graph node.
        assert resident["anchor_id"] not in template["nodes"]

    def test_boundary_exit_marked_near_side_only(self, world):
        template = _collect(world, include_items=False, include_characters=False)
        boundary_ways = {b["way"] for b in template["boundary_exits"]}
        assert "way_hall_out" in boundary_ways
        # No edge in the template leaves the captured group.
        captured = set(template["nodes"])
        for edge in template["edges"]:
            assert edge["source"] in captured and edge["target"] in captured


class TestMaterializeStructure:
    def _clear(self, world):
        world.graph.clear()
        world.player_manager.players = {}
        world.player_manager.active_player = None

    def test_round_trip_restores_structure_and_resident(self, world):
        template = _collect(world)
        self._clear(world)

        report = materialize_structure(world, template, seed=1)

        assert report["materialized"]["areas"] == 2
        assert "miki" in world.player_manager.players
        assert world.player_manager.players["miki"].simulation_mode == "background"
        anchor = world.player_manager.get_player_node_id("miki")
        assert world.graph.get_node(anchor) is not None
        # resident lands in the hall (area ids are unchanged with no collision)
        targets = {e.target for e in world.graph.get_edges_for_source(anchor, EDGE_IN)}
        assert world._area_node_id("Hall") in targets
        assert world.graph.get_node("item_knife").properties["current_state"] == "locked"

    def test_collision_remaps_ids_but_keeps_names(self, world):
        template = _collect(world, include_items=False, include_characters=False)
        # Materialize into the SAME world (everything collides).
        report = materialize_structure(world, template, seed=7, include_characters=False)

        assert report["materialized"]["areas"] == 2
        renamed_ids = {r["new_id"] for r in report["renamed"]}
        assert len(renamed_ids) >= 2
        # Display names preserved; a second Hall/Kitchen now exists under new ids.
        names = [n.name for n in world.graph.nodes.values() if n.type == "area"]
        assert names.count("Hall") == 2
        assert names.count("Kitchen") == 2
        # The new ways reference the new area ids, not the originals.
        for new_id in renamed_ids:
            node = world.graph.get_node(new_id)
            if node and node.type == "area":
                for edge in world.graph.get_edges_for_source(new_id, EDGE_CONNECTION):
                    way = world.graph.get_node(edge.target)
                    assert way is not None

    def test_duplicate_resident_mints_unique_instance(self, world):
        """A name clash mints a new instance (miki → miki 2) instead of dropping
        the resident, so a stamp always delivers its population."""
        template = _collect(world)
        report = materialize_structure(world, template, seed=3)
        assert report["minted_residents"] == [{"from": "miki", "to": "miki 2"}]
        assert {"miki", "miki 2"} <= set(world.player_manager.players)
        # Both are live and in background.
        assert world.player_manager.players["miki 2"].simulation_mode == "background"
        assert world.graph.get_node("player_miki_2") is not None

    def test_deterministic_ids_across_identical_worlds(self):
        template = _collect(_make_world(), include_items=False, include_characters=False)
        reports = []
        for _ in range(2):
            target = _make_world()  # already has Hall/Kitchen → collisions
            reports.append(materialize_structure(target, template, seed=42, include_characters=False))
        assert reports[0]["renamed"] == reports[1]["renamed"]

    def test_boundary_stub_is_a_dead_exit(self, world):
        template = _collect(world, include_items=False, include_characters=False)
        self._clear(world)
        materialize_structure(world, template, seed=1, include_characters=False)

        stub = world.graph.get_node("way_hall_out")
        assert stub is not None and stub.type == "way"
        far_edges = [
            e for e in world.graph.get_edges_for_source("way_hall_out", EDGE_CONNECTION)
        ]
        assert far_edges == []  # near-side edge only

    def test_summary_fields(self, world):
        summary = summarize_structure(_collect(world))
        assert summary["areas"] == 2 and summary["residents"] == 1


class TestStructureRoutes:
    def test_preview_save_list_materialize(self, tmp_path):
        from app import create_app
        from area import Area

        app = create_app({'TESTING': True, 'DATA_DIR': str(tmp_path)})
        client = app.test_client()
        app.world.add_area(Area("Yard", "An open yard.", []))

        area_id = app.world._area_node_id("Yard")

        preview = client.post('/api/structures/preview', json={'area_id': area_id})
        assert preview.status_code == 200
        assert preview.get_json()["areas"] == 1

        saved = client.post('/api/structures/save', json={'area_id': area_id, 'name': 'Yard Pack'})
        assert saved.status_code == 200
        assert saved.get_json()["status"] == "saved"

        listing = client.get('/api/structures')
        assert listing.status_code == 200
        assert any(e["name"] == "Yard Pack" for e in listing.get_json())

        report = client.post('/api/structures/yard_pack/materialize', json={'seed': 5})
        assert report.status_code == 200
        # The yard already exists → the materialized copy gets remapped ids.
        assert report.get_json()["materialized"]["areas"] == 1

    def test_materialize_missing_structure_404(self, tmp_path):
        from app import create_app

        app = create_app({'TESTING': True, 'DATA_DIR': str(tmp_path)})
        client = app.test_client()
        resp = client.post('/api/structures/nope/materialize', json={})
        assert resp.status_code == 404
