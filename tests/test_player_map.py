"""Player map route - the cells a character has actually been in (task-677).

The point of these tests is that the map needs **no producer of its own**. Every
row they assert on is written by the real ``engine.observation.observe_area`` on
arrival, exactly as it is in play - so a test that passes here is evidence the
map is wired, not just that a payload can be shaped.

The negative cases matter as much as the positive ones. The map must not report
a whole scope to a character who has not walked it, must not leak a hidden way,
and must not reveal that a door is *locked* to a character who has only found it
shut.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph import WorldGraph, Node, Edge, EDGE_IN, EDGE_CONNECTION
from flask import Flask
from player import Player
from engine.observation import observe_area

from routes.player_ops import handle_get_player_map, handle_mark_visited

# A bare Flask app purely so ``jsonify`` has an application context; the world
# behind it is the real graph and the real Player, not a mock.
_flask = Flask(__name__)


class _Stub:
    """Just enough world for the handler: real graph, real player."""

    def __init__(self, graph, players, tick=412, scopes=None):
        self.graph = graph
        self.players = players
        self.time_ticks = tick
        self.world_scopes = scopes or {}
        self.area_description = None

        class _Lighting:
            def can_see_in_dark(self, pm, name):
                return False

            def get_ambient_light(self, area_id, env):
                return 60

        class _PM:
            lighting = _Lighting()
            time_ticks = tick

            def is_slasher(self, name):
                return False

        self.player_manager = _PM()

        class _Matcher:
            @staticmethod
            def way_handle(way, direction, area_name):
                return direction or way.name

        self.name_matcher = _Matcher()


class _App:
    def __init__(self, world):
        self.world = world


class _GS:
    def __init__(self, graph, tick=412):
        self.graph = graph
        self.time_ticks = tick
        self.player_manager = _Stub(graph, {}).player_manager


def make_graph():
    """Two painted areas stacked on one footprint, one unpainted, three ways."""
    g = WorldGraph()
    g.add_node(Node(id="area_pantry", type="area", name="Pantry", properties={
        "cell": {"x": 3, "y": 2}, "world_scope_id": "camp", "floor": 0,
        "biome": "temperate_forest",
    }))
    g.add_node(Node(id="area_cellar", type="area", name="Cellar", properties={
        "cell": {"x": 3, "y": 3}, "world_scope_id": "camp", "floor": -1,
    }))
    # No painted cell at all - the map must still report it and let the client
    # fall back to the cardinal layout.
    g.add_node(Node(id="area_yard", type="area", name="Yard", properties={
        "world_scope_id": "camp", "floor": 0,
    }))
    g.add_node(Node(id="item_bread", type="item", name="Bread",
                    properties={"tags": ["food"]}))
    g.add_node(Node(id="player_Scout", type="character", name="Scout"))
    g.add_edge(Edge(source="item_bread", target="area_pantry", type=EDGE_IN))
    g.add_edge(Edge(source="player_Scout", target="area_pantry", type=EDGE_IN))

    g.add_node(Node(id="way_pantry_cellar", type="way", name="cellar steps",
                    properties={"current_state": "blocked"}))
    g.add_edge(Edge(source="area_pantry", target="way_pantry_cellar",
                    type=EDGE_CONNECTION, properties={"direction": "down"}))
    g.add_edge(Edge(source="way_pantry_cellar", target="area_cellar",
                    type=EDGE_CONNECTION, properties={"direction": "up"}))

    # Open way, so an unmarked boundary is representable.
    g.add_node(Node(id="way_pantry_yard", type="way", name="yard gate",
                    properties={"current_state": "open"}))
    g.add_edge(Edge(source="area_pantry", target="way_pantry_yard",
                    type=EDGE_CONNECTION, properties={"direction": "east"}))
    g.add_edge(Edge(source="way_pantry_yard", target="area_yard",
                    type=EDGE_CONNECTION, properties={"direction": "west"}))

    # Hidden: must never reach a map, because the character has not found it.
    g.add_node(Node(id="way_pantry_secret", type="way", name="secret panel",
                    properties={"current_state": "hidden"}))
    g.add_edge(Edge(source="area_pantry", target="way_pantry_secret",
                    type=EDGE_CONNECTION, properties={"direction": "north"}))
    g.add_edge(Edge(source="way_pantry_secret", target="area_yard",
                    type=EDGE_CONNECTION, properties={"direction": "south"}))
    return g


def make_player(name="Cook", area="Pantry"):
    p = Player(name)
    p.current_area = area
    return p


def call(g, player, scopes=None):
    world = _Stub(g, {player.name: player}, scopes=scopes)
    with _flask.app_context():
        result = handle_get_player_map(_App(world), player.name)
    if isinstance(result, tuple):
        return result[0].get_json(), result[1]
    return result.get_json(), 200


def test_a_character_who_never_moved_gets_one_cell_not_the_scope():
    """The acceptance case: knowing where you are is not knowing the map."""
    g = make_graph()
    cook = make_player()
    # The load-time observation pass every character gets - standing still.
    observe_area(cook, _GS(g))

    body = call(g, cook)[0]

    assert [a["name"] for a in body["areas"]] == ["Pantry"]
    assert body["current_area"] == "Pantry"
    assert body["areas"][0]["current"] is True
    # The scope holds three areas; one of them must not appear.
    assert "Cellar" not in [a["name"] for a in body["areas"]]
    assert "Yard" not in [a["name"] for a in body["areas"]]


def test_walking_writes_the_cells_and_the_map_follows_the_real_producer():
    g = make_graph()
    cook = make_player()
    observe_area(cook, _GS(g))

    cook.current_area = "Cellar"
    observe_area(cook, _GS(g))
    cook.current_area = "Pantry"
    observe_area(cook, _GS(g))

    body = call(g, cook)[0]
    by_name = {a["name"]: a for a in body["areas"]}

    assert set(by_name) == {"Pantry", "Cellar"}
    assert by_name["Pantry"]["current"] is True
    assert by_name["Cellar"]["current"] is False
    assert by_name["Pantry"]["cell"] == {"x": 3, "y": 2}
    # Storey travels with the cell, so a minimap can section on it later.
    assert by_name["Pantry"]["floor"] == 0
    assert by_name["Cellar"]["floor"] == -1
    # Re-entering refreshes the row rather than adding one.
    assert len([a for a in body["areas"] if a["name"] == "Pantry"]) == 1


def test_unpainted_area_reports_a_null_cell_rather_than_being_dropped():
    g = make_graph()
    cook = make_player()
    observe_area(cook, _GS(g))
    cook.current_area = "Yard"
    observe_area(cook, _GS(g))

    body = call(g, cook)[0]
    yard = next(a for a in body["areas"] if a["name"] == "Yard")

    assert yard["cell"] is None


def test_last_seen_carries_the_contents_and_the_people():
    g = make_graph()
    cook = make_player()
    observe_area(cook, _GS(g))
    # People are stamped on *meeting*, not on arrival - observation.py:96-105
    # excludes characters deliberately (arrival-stamping them saturated camp
    # Entertainment at 87/100). So the map's who-was-there is populated by the
    # meeting, and a room containing someone you have never met stays empty
    # rather than leaking their presence retroactively.
    cook.register_first_meeting("Scout", 412)

    body = call(g, cook)[0]
    pantry = next(a for a in body["areas"] if a["name"] == "Pantry")

    assert [i["name"] for i in pantry["items"]] == ["Bread"]
    assert [p["id"] for p in pantry["people"]] == ["player_Scout"]
    assert pantry["last_seen"] == 412


def test_a_hidden_way_never_reaches_the_map():
    g = make_graph()
    cook = make_player()
    observe_area(cook, _GS(g))

    body = call(g, cook)[0]
    pantry = next(a for a in body["areas"] if a["name"] == "Pantry")

    assert "way_pantry_secret" not in [w["way_id"] for w in pantry["ways"]]


def test_an_unlearned_locked_way_is_not_marked_and_reads_as_closed():
    """The leak the turn panel avoids must not be reopened by the map."""
    g = make_graph()
    cook = make_player()
    observe_area(cook, _GS(g))

    body = call(g, cook)[0]
    pantry = next(a for a in body["areas"] if a["name"] == "Pantry")
    blocked = next(w for w in pantry["ways"] if w["way_id"] == "way_pantry_cellar")

    assert blocked["real_state"] == "blocked"
    assert blocked["solid"] is True
    # Nothing has been learned, so it reads shut and must not be marked.
    assert blocked["state"] == "closed"
    assert blocked["way_blocked"] is False


def test_having_learned_the_aspect_marks_it_and_names_the_state():
    g = make_graph()
    cook = make_player()
    observe_area(cook, _GS(g))
    cook.learn_way_aspect("Pantry", "down", "blocked")

    body = call(g, cook)[0]
    pantry = next(a for a in body["areas"] if a["name"] == "Pantry")
    blocked = next(w for w in pantry["ways"] if w["way_id"] == "way_pantry_cellar")

    assert blocked["state"] == "blocked"
    assert blocked["way_blocked"] is True
    assert blocked["known_blocked"] is True


def test_an_open_way_is_not_marked_and_carries_its_far_end():
    g = make_graph()
    cook = make_player()
    observe_area(cook, _GS(g))

    body = call(g, cook)[0]
    pantry = next(a for a in body["areas"] if a["name"] == "Pantry")
    gate = next(w for w in pantry["ways"] if w["way_id"] == "way_pantry_yard")

    assert gate["state"] == "open"
    assert gate["solid"] is False
    # The far end is what the client draws the boundary marker between.
    assert gate["to_area_id"] == "area_yard"


def test_scope_list_covers_only_scopes_with_visited_cells():
    g = make_graph()
    cook = make_player()
    observe_area(cook, _GS(g))
    scopes = {"camp": {"id": "camp", "kind": "scope", "name": "Camp",
                       "grid": {"w": 20, "h": 10}}}

    body = call(g, cook, scopes=scopes)[0]

    assert len(body["scopes"]) == 1
    entry = body["scopes"][0]
    assert entry["id"] == "camp"
    assert entry["name"] == "Camp"
    assert entry["visited_cells"] == 1
    assert entry["w"] == 20 and entry["h"] == 10


def mark(g, player, areas, scopes=None, tick=None, observe=False):
    world = _Stub(g, {player.name: player}, scopes=scopes)
    body = {"areas": areas, "observe": observe}
    if tick is not None:
        body["tick"] = tick
    with _flask.test_request_context("/api/players/%s/map/visited" % player.name,
                                      method="POST", json=body):
        result = handle_mark_visited(_App(world), player.name)
    if isinstance(result, tuple):
        return result[0].get_json(), result[1]
    return result.get_json(), 200


def test_marking_visited_writes_the_row_the_map_already_reads():
    """The seed path must produce what an arrival produces, not a parallel store."""
    g = make_graph()
    cook = make_player()
    mark(g, cook, ["Cellar"])

    body = call(g, cook)[0]
    assert [a["name"] for a in body["areas"]] == ["Cellar"]
    # Same row shape an arrival writes.
    row = cook.observation_memory("area_cellar")
    assert row["kind"] == "area"
    assert row["location"] == "Cellar"
    assert "Cellar" in row["text"]
    # And the set the known-routes prose still reads.
    assert "Cellar" in cook.visited_area_names()


def test_marking_visited_accepts_a_comma_string():
    g = make_graph()
    cook = make_player()
    _, status = mark(g, cook, "Cellar, Yard")

    assert status == 200
    assert set(cook.visited_area_names()) == {"Cellar", "Yard"}


def test_marking_visited_is_idempotent():
    g = make_graph()
    cook = make_player()
    mark(g, cook, ["Cellar"])
    mark(g, cook, ["Cellar"])

    rows = [m for m in cook.memories if m.get("kind") == "area"]
    assert len(rows) == 1
    assert len(call(g, cook)[0]["areas"]) == 1


def test_an_unresolvable_area_is_reported_not_dropped():
    g = make_graph()
    cook = make_player()
    body, status = mark(g, cook, ["Cellar", "Nowhere At All"])

    assert status == 200
    assert [a["name"] for a in body["added"]] == ["Cellar"]
    # A typo in an author's list should be visible, not quietly shrink the map.
    assert body["unresolved"] == ["Nowhere At All"]


def test_marking_visited_for_an_unknown_player_is_a_404():
    g = make_graph()
    world = _Stub(g, {})
    with _flask.test_request_context("/api/players/nobody/map/visited",
                                     method="POST", json={"areas": ["Cellar"]}):
        assert handle_mark_visited(_App(world), "nobody")[1] == 404


def test_seeding_alone_does_not_invent_what_was_there():
    """"Was here" is not "saw these things" - the two are separate claims."""
    g = make_graph()
    cook = make_player()
    mark(g, cook, ["Pantry"])

    pantry = next(a for a in call(g, cook)[0]["areas"] if a["name"] == "Pantry")
    assert pantry["items"] == []


def test_observe_seeds_the_areas_contents_through_real_perception():
    g = make_graph()
    cook = make_player()
    body, _ = mark(g, cook, ["Pantry"], observe=True)

    assert body["added"][0]["items_seeded"] == ["Bread"]
    pantry = next(a for a in call(g, cook)[0]["areas"] if a["name"] == "Pantry")
    assert [i["name"] for i in pantry["items"]] == ["Bread"]


def test_observe_does_not_stamp_people():
    """Arrival-stamping characters is what saturated camp Entertainment."""
    g = make_graph()
    cook = make_player()
    mark(g, cook, ["Pantry"], observe=True)

    pantry = next(a for a in call(g, cook)[0]["areas"] if a["name"] == "Pantry")
    assert pantry["people"] == []


def test_unknown_player_is_a_404():
    g = make_graph()
    world = _Stub(g, {})
    with _flask.app_context():
        assert handle_get_player_map(_App(world), "nobody")[1] == 404


def test_player_map_returns_visible_cells_and_scope_id():
    g = make_graph()
    cook = make_player()
    observe_area(cook, _GS(g))

    scopes = {
        "camp": {
            "id": "camp",
            "name": "Camp",
            "mode": "settlement",
            "grid": {
                "w": 10,
                "h": 10,
                "cells": {
                    "3,2": {"layers": {"ground": "grass", "floor": "0"}},
                    "3,3": {"layers": {"ground": "grass", "floor": "0"}},
                },
            },
        }
    }
    body, status = call(g, cook, scopes=scopes)
    assert status == 200
    assert body["visible_scope_id"] == "camp"
    assert isinstance(body["visible_cells"], list)
    assert len(body["visible_cells"]) > 0
    # The observer's own cell is always visible
    coords = [(c["x"], c["y"]) for c in body["visible_cells"]]
    assert (3, 2) in coords
    # Charted cells are also populated and returned
    assert isinstance(body["charted_cells"], list)
    assert (3, 2) in [(c["x"], c["y"]) for c in body["charted_cells"]]


def test_player_map_charted_cells_persist_across_los_changes():
    g = make_graph()
    cook = make_player()
    observe_area(cook, _GS(g))

    scopes = {
        "camp": {
            "id": "camp",
            "name": "Camp",
            "mode": "settlement",
            "grid": {
                "w": 10,
                "h": 10,
            },
        }
    }
    # First pass: facing east
    cook.facing = "east"
    body1, _ = call(g, cook, scopes=scopes)
    assert (7, 2) in [(c["x"], c["y"]) for c in body1["visible_cells"]]

    # Second pass: turned around facing west
    cook.facing = "west"
    body2, _ = call(g, cook, scopes=scopes)
    vis2 = [(c["x"], c["y"]) for c in body2["visible_cells"]]
    charted2 = [(c["x"], c["y"]) for c in body2["charted_cells"]]

    # Cell (7, 2) is now behind the character (west facing) and beyond peripheral range (3), so not in visible_cells...
    assert (7, 2) not in vis2
    # ...but remains charted in persistent memory!
    assert (7, 2) in charted2



def test_interior_scope_is_strictly_topological_and_never_reveals_empty_cells():
    """Fine interiors remain strictly topological (task-882, worldpainter-knowledge-and-fog.md).
    A character in an interior scope must NOT cast geometric rays over empty grid cells.
    Sight is 1-hop topological: current area + adjacent areas via open ways.
    """
    g = WorldGraph()
    g.add_node(Node(id="area_room_a", type="area", name="Room A", properties={
        "cell": {"x": 2, "y": 2}, "world_scope_id": "interior_keep", "floor": 0,
    }))
    g.add_node(Node(id="area_room_b", type="area", name="Room B", properties={
        "cell": {"x": 4, "y": 4}, "world_scope_id": "interior_keep", "floor": 0,
    }))
    g.add_node(Node(id="area_room_c", type="area", name="Room C", properties={
        "cell": {"x": 8, "y": 8}, "world_scope_id": "interior_keep", "floor": 0,
    }))
    # Open doorway between Room A and Room B
    g.add_node(Node(id="way_a_b", type="way", name="archway", properties={"current_state": "open"}))
    g.add_edge(Edge(source="area_room_a", target="way_a_b", type=EDGE_CONNECTION, properties={"direction": "east"}))
    g.add_edge(Edge(source="way_a_b", target="area_room_b", type=EDGE_CONNECTION, properties={"direction": "west"}))

    # Closed heavy door between Room A and Room C
    g.add_node(Node(id="way_a_c", type="way", name="iron door", properties={"current_state": "closed"}))
    g.add_edge(Edge(source="area_room_a", target="way_a_c", type=EDGE_CONNECTION, properties={"direction": "north"}))
    g.add_edge(Edge(source="way_a_c", target="area_room_c", type=EDGE_CONNECTION, properties={"direction": "south"}))

    hero = make_player("Hero", "Room A")
    observe_area(hero, _GS(g))

    scopes = {
        "interior_keep": {
            "id": "interior_keep",
            "name": "Keep Interior",
            "mode": "interior",
            "grid": {"w": 20, "h": 20},
        }
    }

    body, _ = call(g, hero, scopes=scopes)
    vis_coords = {(c["x"], c["y"]) for c in body["visible_cells"]}

    # Room A (current) is visible
    assert (2, 2) in vis_coords
    # Room B (connected via open archway) is visible
    assert (4, 4) in vis_coords
    # Room C (blocked by closed iron door) is NOT visible
    assert (8, 8) not in vis_coords
    # Empty unplaced cells across the 20x20 grid are NEVER visible
    assert (13, 3) not in vis_coords
    assert (0, 0) not in vis_coords
    assert len(vis_coords) == 2

    # Charted cells should only contain the 2 visible room coordinates, never empty cells
    charted_coords = {(c["x"], c["y"]) for c in body["charted_cells"]}
    assert charted_coords == {(2, 2), (4, 4)}
