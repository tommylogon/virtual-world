"""Player map route — the cells a character has actually been in (task-677).

The point of these tests is that the map needs **no producer of its own**. Every
row they assert on is written by the real ``engine.observation.observe_area`` on
arrival, exactly as it is in play — so a test that passes here is evidence the
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

from routes.player_ops import handle_get_player_map

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
    # No painted cell at all — the map must still report it and let the client
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
    # The load-time observation pass every character gets — standing still.
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
    # People are stamped on *meeting*, not on arrival — observation.py:96-105
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
                       "grid": {"w": 20, "h": 10, "cell_scale": 1}}}

    body = call(g, cook, scopes=scopes)[0]

    assert len(body["scopes"]) == 1
    entry = body["scopes"][0]
    assert entry["id"] == "camp"
    assert entry["name"] == "Camp"
    assert entry["visited_cells"] == 1
    assert entry["w"] == 20 and entry["h"] == 10


def test_unknown_player_is_a_404():
    g = make_graph()
    world = _Stub(g, {})
    with _flask.app_context():
        assert handle_get_player_map(_App(world), "nobody")[1] == 404
