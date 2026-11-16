"""Unit tests for dark examine semantics (task-681)."""
import pytest
from unittest.mock import MagicMock
from engine.items.examine_actions import ExamineActionsMixin
from graph import WorldGraph, Node, Edge, EDGE_IN, EDGE_CONNECTION


class DummyActions(ExamineActionsMixin):
    def __init__(self, graph, equipment, trigger_system, matching):
        self.graph = graph
        self.equipment = equipment
        self.trigger_system = trigger_system
        self.matching = matching

    def _render_node_desc(self, node):
        return node.properties.get("description", "")

    def _register_item_discovery(self, player_manager, node):
        return False

    def _exec_triggers(self, node, trigger_type):
        return []


@pytest.fixture
def test_setup():
    graph = WorldGraph()

    # Create area
    area = Node(id="area_cellar", type="area", name="Dark Cellar", properties={
        "environment": {"light": 0, "noise": "quiet"}
    })
    graph.add_node(area)

    # Lighting mock
    lighting = MagicMock()
    lighting.can_see_in_dark.return_value = False
    lighting.get_ambient_light.return_value = 0

    # Player mock
    player = MagicMock()
    player.name = "Tester"
    player.state = "alive"
    player.known = []

    player_manager = MagicMock()
    player_manager.active_player = "Tester"
    player_manager.current_area = area
    player_manager._get_current_area_id.return_value = "area_cellar"
    player_manager._player_node_id.return_value = "player_Tester"
    player_manager.players = {"Tester": player}
    player_manager.lighting = lighting
    player_manager.get_active_player_obj.return_value = player

    # Matching mock
    matching = MagicMock()
    matching._match_character_name.return_value = (None, [])

    # Trigger system mock
    trigger_system = MagicMock()
    trigger_system._get_available_actions.return_value = []

    # Equipment mock
    equipment = MagicMock()
    equipment.get_equipment_narrative.return_value = ""

    examine = DummyActions(
        graph=graph,
        equipment=equipment,
        trigger_system=trigger_system,
        matching=matching,
    )

    return {
        "graph": graph,
        "area": area,
        "player_manager": player_manager,
        "lighting": lighting,
        "matching": matching,
        "examine": examine,
    }


def test_dark_examine_item_unnamed_tactile_impression(test_setup):
    graph = test_setup["graph"]
    pm = test_setup["player_manager"]
    matching = test_setup["matching"]
    examine = test_setup["examine"]

    # Object 1: Brass key
    key = Node(id="item_brass_key", type="item", name="brass_key", properties={
        "description": "a small brass key, cold to the touch with fine notches.",
        "material": "brass",
        "temperature": "cold",
        "size": "small",
    })
    graph.add_node(key)
    graph.add_edge(Edge(source="item_brass_key", target="area_cellar", type=EDGE_IN))

    matching._match_item_name.side_effect = lambda name: "brass_key" if "key" in name.lower() or name == "something" else None

    result = examine.get_item_desc(pm, "brass_key")

    # 1. Must NOT reveal the item name or ID
    assert "brass_key" not in result
    assert "item_brass_key" not in result
    assert "key" not in result

    # 2. Must describe tactile cues: brass, cold, small
    assert "cold to the touch" in result
    assert "brass" in result
    assert "small" in result

    # Object 2: Heavy wooden chest
    chest = Node(id="item_wood_chest", type="item", name="wooden_chest", properties={
        "description": "a massive chest of rough oak planks bound in iron.",
        "material": "wood",
        "texture": "rough",
        "shape": "rectangular",
        "size": "heavy",
    })
    graph.add_node(chest)
    graph.add_edge(Edge(source="item_wood_chest", target="area_cellar", type=EDGE_IN))

    matching._match_item_name.side_effect = lambda name: "wooden_chest" if "chest" in name.lower() else None

    result_chest = examine.get_item_desc(pm, "wooden_chest")

    # 1. Must NOT reveal the item name
    assert "wooden_chest" not in result_chest
    assert "chest" not in result_chest

    # 2. Must describe different tactile cues: rough, wood, rectangular
    assert "rough" in result_chest
    assert "wood" in result_chest
    assert "rectangular" in result_chest

    # 3. Both results must be distinct
    assert result != result_chest


def test_dark_examine_generic_target(test_setup):
    graph = test_setup["graph"]
    pm = test_setup["player_manager"]
    matching = test_setup["matching"]
    examine = test_setup["examine"]

    item = Node(id="item_goblet", type="item", name="silver_goblet", properties={
        "description": "a polished silver goblet, smooth and cold.",
        "material": "silver",
        "texture": "smooth",
    })
    graph.add_node(item)
    graph.add_edge(Edge(source="item_goblet", target="area_cellar", type=EDGE_IN))

    matching._match_item_name.return_value = None  # "something" does not match any literal item name

    # Examining "something" or "the shape" resolves to the item in the dark
    result = examine.get_item_desc(pm, "something")
    assert "silver_goblet" not in result
    assert "smooth" in result


def test_dark_examine_way(test_setup):
    graph = test_setup["graph"]
    pm = test_setup["player_manager"]
    matching = test_setup["matching"]
    examine = test_setup["examine"]

    way = Node(id="way_door", type="way", name="iron_door", properties={
        "current_state": "locked"
    })
    graph.add_node(way)
    conn = Edge(source="area_cellar", target="way_door", type=EDGE_CONNECTION, properties={"direction": "north"})
    graph.add_edge(conn)

    matching.resolve_exit.return_value = (conn, way, "north")
    matching._match_item_name.return_value = None

    result = examine.get_item_desc(pm, "north")
    assert "locked barrier" in result
    assert "rigid latch" in result


def test_lit_examine_reveals_normal_description(test_setup):
    graph = test_setup["graph"]
    pm = test_setup["player_manager"]
    matching = test_setup["matching"]
    lighting = test_setup["lighting"]
    examine = test_setup["examine"]

    key = Node(id="item_key", type="item", name="brass_key", properties={
        "description": "a small brass key with intricate engravings.",
    })
    graph.add_node(key)
    graph.add_edge(Edge(source="item_key", target="area_cellar", type=EDGE_IN))

    matching._match_item_name.return_value = "brass_key"

    # Turn the light on (ambient >= 20)
    lighting.get_ambient_light.return_value = 80

    result = examine.get_item_desc(pm, "brass_key")
    # Lit examine should return full description with name
    assert "small brass key with intricate engravings" in result
