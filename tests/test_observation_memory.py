"""Observation memories — one live observation per subject (task-403).

What a character has seen is stored as a memory per *subject* (area, item,
character), refreshed in place rather than appended per visit, with the subject
id in ``entity_ids`` and a ``memory_index`` that maps a subject to its memory.

This is the foundation task-425 needs: novelty reads the observation tick rather
than the binary ``visited_areas`` / ``discovered_items`` sets.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph import WorldGraph, Node, Edge, EDGE_IN
from player import Player
from engine.observation import observe_area, can_perceive, AREA, ITEM, CHARACTER


class Lighting:
    """Minimal lighting stub: ambient per area, darkvision per character."""

    def __init__(self, ambient=50, darkvision=()):
        self.ambient = ambient
        self.darkvision = set(darkvision)

    def can_see_in_dark(self, player_manager, name):
        return name in self.darkvision

    def get_ambient_light(self, area_id, env):
        return self.ambient


class PlayerManager:
    def __init__(self, lighting=None):
        self.lighting = lighting


class GameState:
    def __init__(self, graph, tick=0, lighting=None):
        self.graph = graph
        self.time_ticks = tick
        self.player_manager = PlayerManager(lighting)


def make_graph():
    """Pantry (area) holds Bread (item) and a hidden Ledger; Scout stands there."""
    g = WorldGraph()
    g.add_node(Node(id="area_pantry", type="area", name="Pantry"))
    g.add_node(Node(id="item_bread", type="item", name="Bread",
                    properties={"tags": ["food"]}))
    g.add_node(Node(id="item_ledger", type="item", name="Ledger",
                    properties={"current_state": "hidden"}))
    g.add_node(Node(id="character_scout", type="character", name="Scout"))
    g.add_edge(Edge(source="item_bread", target="area_pantry", type=EDGE_IN))
    g.add_edge(Edge(source="item_ledger", target="area_pantry", type=EDGE_IN))
    g.add_edge(Edge(source="character_scout", target="area_pantry", type=EDGE_IN))
    return g


def make_player(name="Cook", area="Pantry"):
    p = Player(name)
    p.current_area = area
    return p


def test_observe_area_records_the_area_and_its_contents():
    g = make_graph()
    gs = GameState(g)
    cook = make_player()

    result = observe_area(cook, gs)

    assert result["seen"] == 2  # area + bread; the ledger is hidden
    assert cook.has_seen("area_pantry")
    assert cook.has_seen("item_bread")
    assert not cook.has_seen("item_ledger")  # hidden until discovered
    assert result["novel"] == ["area_pantry", "item_bread"]


def test_observe_area_ignores_people_so_meetings_are_the_only_payer():
    """People are claimed by register_first_meeting, not by sight (task-434).

    If arrival stamped them too, the meeting grant would read a tick this had just
    refreshed and pay nothing — and paying on sight saturates Entertainment,
    because a crowded camp re-observes everyone on every arrival.
    """
    g = make_graph()
    gs = GameState(g)
    cook = make_player()
    cook.vitals = {"Entertainment": 50}

    result = observe_area(cook, gs)

    assert "character_scout" not in result["freshness"]
    assert not cook.has_seen("character_scout")


def test_observation_carries_entity_id_place_and_kind():
    g = make_graph()
    gs = GameState(g, tick=42)
    cook = make_player()
    observe_area(cook, gs)

    bread = cook.observation_memory("item_bread")
    assert bread["entity_ids"] == ["item_bread"]
    assert bread["location"] == "Pantry"
    assert bread["tick"] == 42
    assert bread["kind"] == ITEM
    assert bread["type"] == "observation"
    # The observed thing's own tags ride along, so the bread is recallable as food.
    assert "food" in bread["tags"]


def test_reseeing_refreshes_in_place_instead_of_appending():
    """Volume is bounded by subjects, not by visits — the whole point."""
    g = make_graph()
    gs = GameState(g, tick=0)
    cook = make_player()

    observe_area(cook, gs)
    after_first = len(cook.memories)
    first_tick = cook.observation_tick("area_pantry")

    for tick in range(1, 25):
        gs.time_ticks = tick
        observe_area(cook, gs)

    assert len(cook.memories) == after_first
    assert cook.observation_tick("area_pantry") == 24
    assert cook.observation_tick("area_pantry") != first_tick
    assert cook.observation_memory("area_pantry")["visits"] == 25


def test_only_the_first_visit_is_novel():
    g = make_graph()
    gs = GameState(g)
    cook = make_player()

    assert observe_area(cook, gs)["novel"]
    assert observe_area(cook, gs)["novel"] == []


def test_leaving_and_returning_is_not_novel_but_the_tick_advances():
    """Novelty is per subject, not per visit — an area stays known."""
    g = make_graph()
    gs = GameState(g, tick=0)
    cook = make_player()

    observe_area(cook, gs)
    cook.current_area = "Elsewhere"
    gs.time_ticks = 100
    observe_area(cook, gs)
    cook.current_area = "Pantry"
    gs.time_ticks = 200

    assert observe_area(cook, gs)["novel"] == []
    assert cook.observation_tick("area_pantry") == 200


def test_memory_index_is_kept_in_step_with_the_store():
    g = make_graph()
    gs = GameState(g)
    cook = make_player()
    observe_area(cook, gs)

    for subject, entry_id in cook.memory_index.items():
        assert any(m["id"] == entry_id for m in cook.memories)
    assert cook.memory_index["area_pantry"] == cook.observation_memory("area_pantry")["id"]


def test_index_is_rebuilt_by_scan_when_missing():
    """A memory written outside record_observation must still be findable."""
    cook = Player("Cook")
    cook.add_memory("The pantry is behind the kitchen.", 5,
                    entity_ids=["area_pantry"], source="manual")
    assert cook.memory_index == {}
    assert cook.has_seen("area_pantry")
    assert cook.memory_index["area_pantry"]


def test_superseding_retires_a_belief():
    g = make_graph()
    gs = GameState(g)
    cook = make_player()
    observe_area(cook, gs)

    bread_id = cook.observation_memory("item_bread")["id"]
    assert cook.supersede_observation("item_bread", reason="eaten")
    assert not cook.has_seen("item_bread")
    assert cook.observation_tick("item_bread") is None
    assert "item_bread" not in cook.memory_index
    # A retired belief must not resurface through recall.
    assert bread_id not in [m["id"] for m in cook.get_relevant_memories("Bread seen")]
    assert not cook.supersede_observation("item_bread")


def test_a_dark_room_still_records_where_you_are():
    """You know which room you stand in with the lights out — but not what is in it."""
    g = make_graph()
    gs = GameState(g, lighting=Lighting(ambient=0))
    cook = make_player()

    result = observe_area(cook, gs)

    assert cook.has_seen("area_pantry")
    assert not cook.has_seen("item_bread")
    assert not cook.has_seen("character_scout")
    assert result["novel"] == ["area_pantry"]


def test_darkvision_sees_in_the_dark():
    g = make_graph()
    gs = GameState(g, lighting=Lighting(ambient=0, darkvision={"Cook"}))
    cook = make_player()

    observe_area(cook, gs)

    assert cook.has_seen("item_bread")


def test_an_asleep_character_does_not_observe_the_room():
    g = make_graph()
    gs = GameState(g)
    cook = make_player()
    cook.activity = {"type": "sleeping", "started_at_tick": 0}

    observe_area(cook, gs)
    assert cook.has_seen("area_pantry")
    assert not cook.has_seen("item_bread")


def test_can_perceive_rejects_the_dead_and_unconscious():
    g = make_graph()
    gs = GameState(g)
    cook = make_player()
    node = g.get_node("area_pantry")

    assert can_perceive(cook, gs, node)
    cook.state = "unconscious"
    assert not can_perceive(cook, gs, node)
    cook.state = "dead"
    assert not can_perceive(cook, gs, node)


def test_authored_known_item_is_observed_even_when_hidden():
    g = make_graph()
    gs = GameState(g)
    cook = make_player()
    cook.known = ["item_ledger"]

    observe_area(cook, gs)
    assert cook.has_seen("item_ledger")


def test_eviction_removes_the_subject_from_the_index(monkeypatch):
    """Forgetting re-enchants the world: an evicted subject is unknown again."""
    import player as player_module
    monkeypatch.setattr(player_module, "_memory_limit", lambda: 1)
    g = make_graph()
    gs = GameState(g)
    cook = make_player()

    observe_area(cook, gs)  # writes 3 observations, capped to 1
    assert len(cook.memories) == 1
    assert len(cook.memory_index) == 1
    for subject in ("area_pantry", "item_bread", "character_scout"):
        if not cook.has_seen(subject):
            assert subject not in cook.memory_index


# ── task-434: meeting a person pays once, and only the meeting pays ──────


def make_graph_with_real_character_node(name="Scout"):
    """The camp's character nodes are named by `Player.node_id_for`, and the
    meeting grant keys on exactly that id."""
    from player import Player
    g = WorldGraph()
    g.add_node(Node(id="area_pantry", type="area", name="Pantry"))
    g.add_node(Node(id=Player.node_id_for(name), type="character", name=name))
    g.add_edge(Edge(source=Player.node_id_for(name), target="area_pantry",
                    type=EDGE_IN))
    return g


def _perceive_and_grant(player, gs):
    """The real arrival path: `observe_area` reports novelty, and movement's
    `_grant_arrival_entertainment` is what pays it."""
    from engine.movement import MovementSystem
    mover = MovementSystem.__new__(MovementSystem)
    mover.gs = gs
    perception = observe_area(player, gs)
    mover._grant_arrival_entertainment(player, perception)
    return perception


def test_arriving_where_someone_stands_does_not_pay_for_them():
    """Only the meeting pays, so there is no second path to double-pay with."""
    from engine.novelty import NOVELTY_MAX
    g = make_graph_with_real_character_node()
    gs = GameState(g)
    cook = make_player()
    cook.vitals = {"Entertainment": 50}

    perception = _perceive_and_grant(cook, gs)

    assert perception["freshness"] == {"area_pantry": 1.0}
    assert cook.vitals["Entertainment"] == 50 + NOVELTY_MAX  # the room only


def test_meeting_pays_once_and_only_once():
    from engine.novelty import NOVELTY_MAX
    cook = make_player()
    cook.vitals = {"Entertainment": 50}

    cook.register_first_meeting("Scout", tick=0)
    assert cook.vitals["Entertainment"] == 50 + NOVELTY_MAX
    after = cook.vitals["Entertainment"]

    cook.register_first_meeting("Scout", tick=1)
    assert cook.vitals["Entertainment"] == after


def test_a_meeting_records_an_observation_of_that_person():
    """So "have I met this person" is a lookup, and a re-meet inside the window
    cannot pay again through the novelty path."""
    cook = make_player()
    cook.vitals = {"Entertainment": 50}
    cook.register_first_meeting("Scout", tick=7)
    assert cook.has_seen("player_Scout")
    assert cook.observation_tick("player_Scout") == 7
