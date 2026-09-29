"""Regression tests for area-node resolution in the tick (task-399 / backsim).

`current_area` is a display name, but area node ids are sanitized differently
(apostrophes, generated coordinates). An id-only lookup silently returned None
and skipped the caller's whole per-area block — environment effects AND the
company-aware Social gain — for 5 of the 23 camp characters.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.node_ids import NodeIDHelper
from engine.tick_manager import TickManager
from graph import Node, WorldGraph


def _stub(graph):
    return SimpleNamespace(
        graph=graph,
        player_manager=SimpleNamespace(area_node_id=NodeIDHelper.area_node_id),
    )


def test_resolves_by_name_when_id_is_sanitized_differently():
    graph = WorldGraph()
    graph.add_node(Node(id="area_chiefs_pit", type="area", name="Chief's Pit",
                        properties={}))
    # id lookup produces area_chief's_pit, which does not exist
    assert NodeIDHelper.area_node_id("Chief's Pit") == "area_chief's_pit"
    node = TickManager._resolve_area_node(_stub(graph), "Chief's Pit")
    assert node is not None and node.id == "area_chiefs_pit"


def test_resolves_coordinate_style_generated_area():
    graph = WorldGraph()
    graph.add_node(Node(id="area_road_world_9_4", type="area",
                        name="Road (world 9,4)", properties={}))
    node = TickManager._resolve_area_node(_stub(graph), "Road (world 9,4)")
    assert node is not None and node.id == "area_road_world_9_4"


def test_resolves_plain_id_unchanged():
    graph = WorldGraph()
    graph.add_node(Node(id="area_cooking_area", type="area", name="Cooking Area",
                        properties={}))
    node = TickManager._resolve_area_node(_stub(graph), "Cooking Area")
    assert node is not None and node.id == "area_cooking_area"


def test_missing_area_returns_none():
    graph = WorldGraph()
    assert TickManager._resolve_area_node(_stub(graph), "Nowhere At All") is None
    assert TickManager._resolve_area_node(_stub(graph), None) is None


def test_every_camp_character_area_resolves(tmp_path):
    """The 5/23 regression: every player's current_area must resolve."""
    import json

    from app import create_app

    root = Path(__file__).parent.parent
    scenario = json.loads((root / "data/scenarios/kraktooth_goblin_camp.json")
                          .read_text(encoding="utf-8"))
    scenario.pop("persist", None)
    app = create_app({"TESTING": True, "DATA_DIR": str(tmp_path)})
    app.test_client().post("/api/load", json=scenario)

    world = app.world
    stub = SimpleNamespace(
        graph=world.graph,
        player_manager=SimpleNamespace(area_node_id=world.area_node_id),
    )
    unresolved = [p.name for p in world.players.values()
                  if p.current_area
                  and TickManager._resolve_area_node(stub, p.current_area) is None]
    assert unresolved == [], f"areas unresolved by the tick: {unresolved}"
