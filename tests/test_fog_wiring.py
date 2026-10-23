"""The fog gate's writers (task-499) and the authored route bridge (task-467).

`engine/fog.py` shipped the reveal verbs and the `only_known` filter, but nothing
called them: walking, examining and reading a charted map left `player.known`
unchanged, so the gate had a key and no hand. These tests pin the call sites and
the one place authored `known` entries become route knowledge.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from area import Area
from graph import Edge, EDGE_IN, Node
from virtual_world_engine import VirtualWorld


def _two_rooms():
    """Hall and Kitchen, joined north <-> south, player standing in the Hall."""
    world = VirtualWorld()
    world.movement.add_area(Area("Hall", "A hall.", []))
    world.movement.add_area(Area("Kitchen", "A kitchen.", []))
    world.movement.connect_areas("Hall", "Kitchen", "north", "south", state="open")
    world.name_matcher._set_player_area(world.active_player, "Hall")
    return world


def _corridor():
    """Hall -> Corridor -> Study, all along the east/west line of sight."""
    world = VirtualWorld()
    world.movement.add_area(Area("Hall", "A hall.", []))
    world.movement.add_area(Area("Corridor", "A corridor.", []))
    world.movement.add_area(Area("Study", "A study.", []))
    world.movement.connect_areas("Hall", "Corridor", "east", "west", state="open")
    world.movement.connect_areas("Corridor", "Study", "east", "west", state="open")
    world.name_matcher._set_player_area(world.active_player, "Hall")
    return world


def _player(world):
    player = world.players[world.active_player]
    player.known = []
    return player


def _item(world, node, area_id="area_hall"):
    world.graph.add_node(node)
    world.graph.add_edge(Edge(source=node.id, target=area_id, type=EDGE_IN))


# ── walking ────────────────────────────────────────────────────────────────


def test_walking_into_an_area_teaches_it():
    world = _two_rooms()
    player = _player(world)

    world.movement.move_to_area("north")

    assert "Kitchen" in player.known, "arrival must teach the area name"
    assert "area_kitchen" in player.known, "and the id the perception gate matches"


def test_walking_teaches_both_spellings_only_once():
    world = _two_rooms()
    player = _player(world)

    world.movement.move_to_area("north")
    world.movement.move_to_area("south")
    world.movement.move_to_area("north")

    assert len(player.known) == len(set(player.known)), "reveal must not duplicate"


# ── examining ──────────────────────────────────────────────────────────────


def test_examining_a_room_teaches_it():
    world = _two_rooms()
    player = _player(world)

    world.get_item_desc("room")

    assert "Hall" in player.known


def test_examining_a_way_teaches_the_far_side():
    world = _two_rooms()
    player = _player(world)

    world.get_item_desc("north")

    assert "Kitchen" in player.known, "a way is described by where it goes"


def test_examining_an_item_teaches_the_item_and_the_room():
    world = _two_rooms()
    player = _player(world)
    crate = Node(id="item_crate", type="item", name="crate",
                 properties={"description": "A heavy crate.", "actions": ["examine"]})
    _item(world, crate)

    world.get_item_desc("crate")

    assert "Hall" in player.known
    assert "crate" in player.known


# ── sightlines ─────────────────────────────────────────────────────────────


def test_looking_down_a_corridor_teaches_the_far_rooms():
    world = _corridor()
    player = _player(world)

    world.get_area_description()

    assert "Corridor" in player.known, "the room behind the first door"
    assert "area_study" in player.known, (
        "looking down two open ways must teach the far room, not just the near one"
    )


def test_a_closed_door_stops_the_sightline():
    world = _corridor()
    player = _player(world)
    world.movement.connect_areas("Corridor", "Study", "east", "west", state="closed")

    world.get_area_description()

    assert "Corridor" in player.known
    assert "Study" not in player.known, "a shut door is not a sightline"


# ── a charted map teaches ──────────────────────────────────────────────────


def test_reading_a_charted_map_teaches_its_chart():
    world = _two_rooms()
    player = _player(world)
    chart = Node(id="item_estate_map", type="item", name="Estate Map",
                 properties={"description": "Rooms inked on linen.",
                             "actions": ["examine"],
                             "charted_areas": ["Kitchen"]})
    _item(world, chart)

    world.get_item_desc("Estate Map")

    assert "Kitchen" in player.known
    assert "area_kitchen" in player.known


def test_reading_an_uncharted_map_does_not_teach_the_world():
    world = _two_rooms()
    player = _player(world)
    prop = Node(id="item_blank_map", type="item", name="Blank Map",
                properties={"description": "A blank sheet.", "actions": ["examine"]})
    _item(world, prop)

    world.get_item_desc("Blank Map")

    assert "Hall" in player.known
    assert "Kitchen" not in player.known, (
        "an uncharted map is a prop; it must not call teach_from_map's "
        "no-chart fallback, which hands out every area"
    )


# ── authored knowledge becomes route knowledge ─────────────────────────────


def test_authored_known_area_feeds_the_route_block():
    world = _two_rooms()
    player = _player(world)
    player.known = ["area_kitchen"]

    from engine.spatial_memory import SpatialMemory, known_route_areas

    known = known_route_areas(player, world.graph)
    assert "Kitchen" in known

    block = SpatialMemory(world.graph).build_known_routes("Hall", known)
    assert "KNOWN ROUTES FROM HERE" in block
    assert "Kitchen" in block
    assert "north" in block


def test_a_known_way_is_not_a_destination():
    world = _two_rooms()
    player = _player(world)
    player.known = ["way_hall_north"]

    from engine.spatial_memory import known_route_areas

    known = known_route_areas(player, world.graph)
    assert "Kitchen" not in known, (
        "a known way gates visibility; it must not widen the route search as "
        "if it were a place"
    )


def test_authored_known_area_makes_a_path_findable():
    world = _two_rooms()
    player = _player(world)
    player.known = ["area_kitchen"]

    from engine.spatial_memory import SpatialMemory, known_route_areas

    route = SpatialMemory(world.graph).find_route(
        "Hall", "Kitchen", known_route_areas(player, world.graph))
    assert route, "authored knowledge must satisfy find_route's known gate"
    assert route[0]["direction"] == "north"
    assert route[0]["to"] == "Kitchen"


def test_walked_areas_still_feed_the_route_block():
    world = _two_rooms()
    player = _player(world)
    world.movement.move_to_area("north")

    from engine.spatial_memory import known_route_areas

    assert "Kitchen" in known_route_areas(player, world.graph)
