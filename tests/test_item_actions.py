"""Verification tests for steal-item (task-158) and put-in-container (task-157).

Both features were already implemented; these tests pin the checklist
behaviour so they can be closed out as done.
"""
import pytest
from unittest.mock import MagicMock, patch

from graph import WorldGraph, Node, Edge, EDGE_IN, EDGE_CARRYING, EDGE_EQUIPPED, EDGE_ON, EDGE_UNDER, EDGE_BESIDE
from engine.item_actions import ItemActions, AmbiguousItemError


@pytest.fixture
def graph():
    g = WorldGraph()
    area = Node(id="area_test", type="area", name="Test", properties={"environment": {"light": 80}})
    g.add_node(area)
    return g


def add_player(g, name):
    node = Node(id=f"player_{name}", type="character", name=name, properties={})
    g.add_node(node)
    g.add_edge(Edge(source=node.id, target="area_test", type=EDGE_IN))
    return node


def add_item(g, name, tags=None, weight=0.1, properties=None):
    node = Node(id=f"item_{name}", type="item", name=name, properties={
        "name": name,
        "weight": weight,
        "tags": tags or [],
        "current_state": "normal",
        "actions": ["examine", "take", "use"],
    })
    if properties:
        node.properties.update(properties)
    g.add_node(node)
    return node


def is_reachable(g, player_id, area_id, item_id):
    """Reachability copy of engine/matching.py:_is_item_reachable.

    get_edges_for_target(area, EDGE_IN) already expands spatial edges
    (on/under/beside/behind/at placed on surfaces in the area), so the
    first loop catches both direct and spatially-placed items.
    """
    for edge in g.get_edges_for_target(area_id, EDGE_IN):
        if edge.source == item_id:
            return True
    for edge in g.get_edges_for_target(player_id, EDGE_CARRYING):
        if edge.source == item_id:
            return True
    for ce in g.get_edges_for_target(area_id, EDGE_IN):
        for content_edge in g.get_edges_for_target(ce.source, EDGE_IN):
            if content_edge.source == item_id:
                node = g.get_node(item_id)
                if node and node.properties.get("current_state") != "hidden":
                    return True
    for ce in g.get_edges_for_target(player_id, EDGE_CARRYING):
        for content_edge in g.get_edges_for_target(ce.source, EDGE_IN):
            if content_edge.source == item_id:
                node = g.get_node(item_id)
                if node and node.properties.get("current_state") != "hidden":
                    return True
    return False


@pytest.fixture
def player_manager(graph):
    pm = MagicMock()
    pm.graph = graph
    pm.active_player = "Hero"
    pm.current_area = MagicMock()
    pm.current_area.name = "Test"
    pm.ghost_mode = False
    pm.record_turn_event = MagicMock()
    pm.add_log_entry = MagicMock()
    pm.apply_action = MagicMock()
    pm.lighting = MagicMock()
    pm.lighting.can_see_in_dark = MagicMock(return_value=True)
    pm.lighting.get_ambient_light = MagicMock(return_value=80)

    hero = MagicMock()
    hero.name = "Hero"
    hero.state = "awake"
    hero.skills = {"Sleight of Hand": 10, "Perception": 5}
    hero.vitals = {}
    pm.players = {"Hero": hero}
    pm.player = hero

    def _get_current_area_id():
        return "area_test"

    def _player_node_id(name):
        return f"player_{name}"

    def get_player_node_id(name):
        return f"player_{name}"

    def _find_item_node(name):
        nid = f"item_{name}"
        node = graph.get_node(nid)
        if node:
            return node
        # scan carrying + equipped + area edges
        for edge_type in (EDGE_CARRYING, EDGE_EQUIPPED):
            for edge in graph.get_edges_for_target(f"player_{pm.active_player}", edge_type):
                n = graph.get_node(edge.source)
                if n and n.name == name:
                    return n
        for edge in graph.get_edges_for_target("area_test", EDGE_IN):
            n = graph.get_node(edge.source)
            if n and n.name == name:
                return n
        return None

    pm._get_current_area_id = _get_current_area_id
    pm._player_node_id = _player_node_id
    pm.get_player_node_id = get_player_node_id
    pm.find_item_node = _find_item_node
    return pm


@pytest.fixture
def item_actions(graph, player_manager):
    ia = ItemActions.__new__(ItemActions)
    ia.graph = graph
    ia.matching = MagicMock()
    ia.matching._is_item_reachable = MagicMock(
        side_effect=lambda iid, aid: is_reachable(graph, f"player_{player_manager.active_player}", aid, iid)
    )
    ia.matching._match_item_name = MagicMock(return_value=None)
    ia.matching._match_character_name = MagicMock(return_value=(None, []))
    ia.matching.resolve_exit = MagicMock(return_value=(None, None, ""))
    ia.matching.way_handle = MagicMock(return_value="door")
    ia.trigger_system = MagicMock()
    ia.trigger_system._get_available_actions = MagicMock(return_value=[])
    ia.trigger_system._contextual_failure = MagicMock(return_value="")
    ia.trigger_system._execute_triggers = MagicMock(return_value=[])
    ia.equipment = MagicMock()
    # real Player carries exhaustion_count; give the hero mock one so consume
    # paths (eat/drink) don't blow up comparing MagicMock > 0
    if player_manager.player is not None:
        try:
            player_manager.player.exhaustion_count = 0
        except Exception:
            pass
    ia.ghost_system = MagicMock()
    ia.ghost_system.check_ghost_action = MagicMock(return_value=None)
    ia.world = MagicMock()
    return ia


# ═══════════════ TASK 157: PUT IN CONTAINER ═══════════════


class TestPutInContainer:
    def test_put_moves_item_into_carried_container(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        apple = add_item(graph, "apple", weight=0.2)
        backpack = add_item(graph, "backpack", tags=["container"], weight=0.5,
                            properties={"max_weight_capacity": 10})
        graph.add_edge(Edge(source=apple.id, target="player_Hero", type=EDGE_CARRYING))
        graph.add_edge(Edge(source=backpack.id, target="player_Hero", type=EDGE_CARRYING))

        result = item_actions.put_item_in_container(player_manager, "apple", "backpack")

        assert "backpack" in result
        # apple is now inside the backpack
        assert any(e.source == apple.id for e in graph.get_edges_for_target(backpack.id, EDGE_IN))
        # apple no longer carried directly
        assert not any(e.source == apple.id for e in graph.get_edges_for_target("player_Hero", EDGE_CARRYING))

    def test_capacity_error_when_full(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        apple = add_item(graph, "apple", weight=5)
        backpack = add_item(graph, "backpack", tags=["container"],
                            properties={"max_weight_capacity": 2})
        graph.add_edge(Edge(source=apple.id, target="player_Hero", type=EDGE_CARRYING))
        graph.add_edge(Edge(source=backpack.id, target="player_Hero", type=EDGE_CARRYING))

        with pytest.raises(ValueError, match="can't hold"):
            item_actions.put_item_in_container(player_manager, "apple", "backpack")
        # apple stays carried
        assert any(e.source == apple.id for e in graph.get_edges_for_target("player_Hero", EDGE_CARRYING))

    def test_take_from_container_works(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        apple = add_item(graph, "apple", weight=0.2)
        backpack = add_item(graph, "backpack", tags=["container"], weight=0.5,
                            properties={"max_weight_capacity": 10})
        graph.add_edge(Edge(source=apple.id, target="player_Hero", type=EDGE_CARRYING))
        graph.add_edge(Edge(source=backpack.id, target="player_Hero", type=EDGE_CARRYING))
        item_actions.put_item_in_container(player_manager, "apple", "backpack")

        result = item_actions.take_item(player_manager, "apple")

        assert "apple" in result
        assert any(e.source == apple.id for e in graph.get_edges_for_target("player_Hero", EDGE_CARRYING))
        assert not any(e.source == apple.id for e in graph.get_edges_for_target(backpack.id, EDGE_IN))

    def test_container_contents_are_reachable(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        apple = add_item(graph, "apple", weight=0.2)
        backpack = add_item(graph, "backpack", tags=["container"],
                            properties={"max_weight_capacity": 10})
        graph.add_edge(Edge(source=apple.id, target="player_Hero", type=EDGE_CARRYING))
        graph.add_edge(Edge(source=backpack.id, target="player_Hero", type=EDGE_CARRYING))
        item_actions.put_item_in_container(player_manager, "apple", "backpack")
        # contents are discoverable (what examine output is built from)
        assert is_reachable(graph, "player_Hero", "area_test", apple.id)

    def test_world_placed_container_works(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        apple = add_item(graph, "apple", weight=0.2)
        crate = add_item(graph, "crate", tags=["container"], weight=3,
                         properties={"max_weight_capacity": 50})
        # crate sits in the world
        graph.add_edge(Edge(source=crate.id, target="area_test", type=EDGE_IN))
        graph.add_edge(Edge(source=apple.id, target="player_Hero", type=EDGE_CARRYING))

        result = item_actions.put_item_in_container(player_manager, "apple", "crate")
        assert "crate" in result
        assert any(e.source == apple.id for e in graph.get_edges_for_target(crate.id, EDGE_IN))

        # take it back out of the world-placed crate
        result = item_actions.take_item(player_manager, "apple")
        assert "apple" in result
        assert any(e.source == apple.id for e in graph.get_edges_for_target("player_Hero", EDGE_CARRYING))

    def test_non_container_rejected(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        apple = add_item(graph, "apple", weight=0.2)
        rock = add_item(graph, "rock", weight=1.0)
        graph.add_edge(Edge(source=apple.id, target="player_Hero", type=EDGE_CARRYING))
        graph.add_edge(Edge(source=rock.id, target="player_Hero", type=EDGE_CARRYING))

        with pytest.raises(ValueError, match="isn't a container"):
            item_actions.put_item_in_container(player_manager, "apple", "rock")


# ═══════════════ TASK 158: STEAL ITEM ═══════════════


class TestStealItem:
    def _setup_steal(self, graph, equipped=False):
        add_player(graph, "Hero")
        add_player(graph, "Bandit")
        item = add_item(graph, "gold_coin", tags=["valuable"])
        if equipped:
            graph.add_edge(Edge(source=item.id, target="player_Bandit", type=EDGE_EQUIPPED))
        else:
            graph.add_edge(Edge(source=item.id, target="player_Bandit", type=EDGE_CARRYING))
        bandit = MagicMock()
        bandit.name = "Bandit"
        bandit.state = "awake"
        bandit.current_area = "Test"
        bandit.skills = {"Perception": 0}
        return item, bandit

    def test_steal_succeeds_when_roll_beats(self, graph, player_manager, item_actions):
        item, bandit = self._setup_steal(graph)
        player_manager.players["Bandit"] = bandit

        with patch("engine.items.transfer_actions.random.randint", return_value=10):
            result = item_actions.steal_item(player_manager, "gold_coin", "Bandit")

        assert "slip" in result
        # item moved to hero
        assert any(e.source == item.id for e in graph.get_edges_for_target("player_Hero", EDGE_CARRYING))
        # no longer on bandit
        assert not any(e.source == item.id for e in graph.get_edges_for_target("player_Bandit", EDGE_CARRYING))

    def test_steal_failure_keeps_item(self, graph, player_manager, item_actions):
        item, bandit = self._setup_steal(graph)
        # force failure: hero Sleight 0 + roll vs bandit Perception 10 + roll
        player_manager.player.skills = {"Sleight of Hand": 0}
        bandit.skills = {"Perception": 10}
        player_manager.players["Bandit"] = bandit

        with patch("engine.items.transfer_actions.random.randint", return_value=10):
            with pytest.raises(ValueError, match="notices you"):
                item_actions.steal_item(player_manager, "gold_coin", "Bandit")

        # item stays on bandit
        assert any(e.source == item.id for e in graph.get_edges_for_target("player_Bandit", EDGE_CARRYING))
        assert not any(e.source == item.id for e in graph.get_edges_for_target("player_Hero", EDGE_CARRYING))

    def test_cannot_steal_from_other_area(self, graph, player_manager, item_actions):
        item, bandit = self._setup_steal(graph)
        bandit.current_area = "Other"
        player_manager.players["Bandit"] = bandit

        with pytest.raises(ValueError, match="isn't in the same area"):
            item_actions.steal_item(player_manager, "gold_coin", "Bandit")

    def test_can_steal_equipped_item(self, graph, player_manager, item_actions):
        item, bandit = self._setup_steal(graph, equipped=True)
        player_manager.players["Bandit"] = bandit

        with patch("engine.items.transfer_actions.random.randint", return_value=10):
            result = item_actions.steal_item(player_manager, "gold_coin", "Bandit")

        assert "slip" in result
        assert any(e.source == item.id for e in graph.get_edges_for_target("player_Hero", EDGE_CARRYING))
        assert not any(e.source == item.id for e in graph.get_edges_for_target("player_Bandit", EDGE_EQUIPPED))


# ═══════════════ TASK 136: ITEM DISCOVERY ENTERTAINMENT ═══════════════


class TestItemDiscovery:
    """First-seen items grant an Entertainment novelty boost (task-136)."""

    def test_discover_new_item_boosts_entertainment(self, item_actions, player_manager):
        """Examining/taking a never-seen item adds to discovered_items and boosts Entertainment."""
        player_manager.player.vitals = {"Entertainment": 50}
        player_manager.player.discovered_items = set()

        was_new = item_actions._register_item_discovery(player_manager, "Kindling")

        assert was_new is True
        assert "Kindling" in player_manager.player.discovered_items
        assert player_manager.player.vitals["Entertainment"] == 58  # base boost 8

    def test_rediscovering_item_gives_no_boost(self, item_actions, player_manager):
        """Same item again: no double boost, no re-add."""
        player_manager.player.vitals = {"Entertainment": 50}
        player_manager.player.discovered_items = {"Kindling"}

        was_new = item_actions._register_item_discovery(player_manager, "Kindling")

        assert was_new is False
        assert player_manager.player.vitals["Entertainment"] == 50

    def test_discover_does_not_exceed_cap(self, item_actions, player_manager):
        """Entertainment boost is clamped at 100."""
        player_manager.player.vitals = {"Entertainment": 98}
        player_manager.player.discovered_items = set()

        item_actions._register_item_discovery(player_manager, "Kindling")

        assert player_manager.player.vitals["Entertainment"] == 100

    def test_examine_registers_discovery(self, graph, player_manager, item_actions):
        """Examine of a real area item marks it discovered."""
        add_player(graph, "Hero")
        add_item(graph, "kindling", properties={"description": "A bundle of dry twigs."})
        graph.add_edge(Edge(source="item_kindling", target="area_test", type=EDGE_IN))
        player_manager.player.vitals = {"Entertainment": 50}
        player_manager.player.discovered_items = set()
        player_manager.lighting.can_see_in_dark = MagicMock(return_value=True)
        item_actions.matching._match_item_name = MagicMock(return_value="kindling")

        item_actions.get_item_desc(player_manager, "kindling")

        assert "kindling" in player_manager.player.discovered_items
        assert player_manager.player.vitals["Entertainment"] == 58

    def test_examine_shows_remaining_uses(self, graph, player_manager, item_actions):
        """Examine of a consumable shows remaining uses and minutes."""
        add_player(graph, "Hero")
        add_item(graph, "ember", properties={
            "description": "A small flame.",
            "uses": 3,
            "current_state": "lit",
        })
        graph.add_edge(Edge(source="item_ember", target="area_test", type=EDGE_IN))
        player_manager.lighting.can_see_in_dark = MagicMock(return_value=True)
        player_manager.time_per_tick_minutes = 5
        item_actions.matching._match_item_name = MagicMock(return_value="ember")

        result = item_actions.get_item_desc(player_manager, "ember")

        assert "3 uses left" in result
        assert "15 minutes" in result

    def test_examine_skips_uses_for_permanent_items(self, graph, player_manager, item_actions):
        """Permanent items (uses -1) don't show a uses line."""
        add_player(graph, "Hero")
        add_item(graph, "rock", properties={
            "description": "A plain rock.",
            "uses": -1,
        })
        graph.add_edge(Edge(source="item_rock", target="area_test", type=EDGE_IN))
        player_manager.lighting.can_see_in_dark = MagicMock(return_value=True)
        item_actions.matching._match_item_name = MagicMock(return_value="rock")

        result = item_actions.get_item_desc(player_manager, "rock")

        assert "uses left" not in result

    def test_examine_character_by_description(self, graph, player_manager, item_actions):
        """'examine the tall woman' resolves to a character by description (task-154)."""
        from engine.matching import NameMatching

        add_player(graph, "Hero")
        lyrie = type("P", (), {
            "name": "Lyrie",
            "description": "A tall woman with long auburn hair and a green cloak.",
            "base_description": "",
            "current_area": "Test",
        })()
        player_manager.players["Lyrie"] = lyrie
        player_manager.current_area.name = "Test"
        player_manager.lighting.can_see_in_dark = MagicMock(return_value=True)

        item_actions.matching = NameMatching(graph, player_manager)
        item_actions.equipment.get_equipment_narrative = MagicMock(return_value="")

        result = item_actions.get_item_desc(player_manager, "the tall woman")

        assert "tall woman" in result.lower() or "auburn" in result.lower()

    def test_examine_list_anonymizes_unmet_characters(self, graph, player_manager, item_actions):
        """The examineable list shows unmet characters by appearance, never
        their database name, and skips the actor (task-154 leak fix)."""
        from player import Player

        add_player(graph, "Hero")
        add_player(graph, "Lyrie")
        lyrie = Player("Lyrie")
        lyrie.description = "A hooded woman with a scarred cheek."
        lyrie.current_area = "Test"
        player_manager.players["Lyrie"] = lyrie
        player_manager.player.has_met = MagicMock(return_value=False)
        player_manager.current_area.name = "Test"
        player_manager.lighting.can_see_in_dark = MagicMock(return_value=True)
        item_actions.matching._match_character_name = MagicMock(return_value=(None, []))
        item_actions.matching._match_item_name = MagicMock(return_value=None)
        item_actions.matching._match_exit_direction = MagicMock(return_value=None)

        with pytest.raises(ValueError) as exc_info:
            item_actions.get_item_desc(player_manager, "the quantum widget")
        result = str(exc_info.value)

        assert "Lyrie" not in result
        assert "hooded woman" in result
        assert "Hero" not in result


# ═══════════════ TASK 4 / SPATIAL RELATIONS IN EXAMINE ═══════════════


class TestSpatialRelationExamine:
    """examine [object] must preserve on/under/behind/beside relations per item
    (task-4 spatial reporting). Regression: all nested items were flattened
    under a single "Inside you see" label."""

    def _build_table_scene(self, graph):
        from graph import EDGE_ON, EDGE_UNDER, EDGE_BEHIND, EDGE_BESIDE, EDGE_IN

        add_player(graph, "Hero")
        add_item(graph, "table", properties={"description": "A long table."})
        graph.add_edge(Edge(source="item_table", target="area_test", type=EDGE_IN))
        for name, rel in [("Ink Pen", EDGE_ON), ("Painting of the Wandering Forests of Vald", EDGE_BEHIND),
                          ("toy_box", EDGE_BESIDE), ("rug", EDGE_UNDER)]:
            node = add_item(graph, name)
            graph.add_edge(Edge(source=node.id, target="item_table", type=rel))
        return "item_table"

    def test_examine_table_preserves_spatial_relations(self, graph, player_manager, item_actions):
        table_id = self._build_table_scene(graph)
        player_manager.lighting.can_see_in_dark = MagicMock(return_value=True)
        player_manager.player.discovered_items = set()
        item_actions.matching._match_item_name = MagicMock(return_value="table")

        result = item_actions.get_item_desc(player_manager, "table")

        assert "On the table: Ink Pen." in result
        assert "Behind the table: Painting of the Wandering Forests of Vald." in result
        assert "Beside the table: toy_box." in result
        assert "Under the table: rug." in result
        assert "Inside you see" not in result

    def test_examine_container_still_uses_inside_label(self, graph, player_manager, item_actions):
        from graph import EDGE_IN

        add_player(graph, "Hero")
        add_item(graph, "chest", tags=["container"], properties={"description": "A wooden chest."})
        graph.add_edge(Edge(source="item_chest", target="area_test", type=EDGE_IN))
        add_item(graph, "loot")
        graph.add_edge(Edge(source="item_loot", target="item_chest", type=EDGE_IN))
        player_manager.lighting.can_see_in_dark = MagicMock(return_value=True)
        player_manager.player.discovered_items = set()
        item_actions.matching._match_item_name = MagicMock(return_value="chest")

        result = item_actions.get_item_desc(player_manager, "chest")

        assert "Inside you see: loot." in result

    def test_examine_nested_container_in_toy_box(self, graph, player_manager, item_actions):
        """A beside-table container still reports its own contents as inside."""
        from graph import EDGE_BESIDE, EDGE_IN

        add_player(graph, "Hero")
        add_item(graph, "toy_box", tags=["container"], properties={"description": "A toy box."})
        graph.add_edge(Edge(source="item_toy_box", target="area_test", type=EDGE_IN))
        add_item(graph, "toy_soldiers")
        graph.add_edge(Edge(source="item_toy_soldiers", target="item_toy_box", type=EDGE_IN))
        add_item(graph, "table", properties={"description": "A long table."})
        graph.add_edge(Edge(source="item_table", target="area_test", type=EDGE_IN))
        graph.add_edge(Edge(source="item_toy_box", target="item_table", type=EDGE_BESIDE))
        player_manager.lighting.can_see_in_dark = MagicMock(return_value=True)
        player_manager.player.discovered_items = set()

        item_actions.matching._match_item_name = MagicMock(return_value="toy_box")
        box_result = item_actions.get_item_desc(player_manager, "toy_box")
        assert "Inside you see: toy_soldiers." in box_result

        item_actions.matching._match_item_name = MagicMock(return_value="table")
        table_result = item_actions.get_item_desc(player_manager, "table")
        assert "Beside the table: toy_box." in table_result


class TestHiddenAsState:
    """Item visibility uses current_state == 'hidden' (task-177).

    Guards the old asymmetry where area_description defaulted hidden to
    visible but matching/player_manager defaulted it to invisible, making
    an item describable but unmatchable.
    """

    def test_item_without_state_is_visible_and_reachable(self, graph):
        from graph import EDGE_IN

        add_player(graph, "Hero")
        add_item(graph, "plain_item")
        del graph.get_node("item_plain_item").properties["current_state"]
        graph.add_edge(Edge(source="item_plain_item", target="area_test", type=EDGE_IN))

        assert graph.get_node("item_plain_item").properties.get("current_state") is None
        assert is_reachable(graph, "player_Hero", "area_test", "item_plain_item") is True

    def test_hidden_item_not_reachable_until_unhidden(self, graph):
        add_player(graph, "Hero")
        add_item(graph, "crate", tags=["container"])
        graph.add_edge(Edge(source="item_crate", target="area_test", type=EDGE_IN))
        add_item(graph, "loot", properties={"current_state": "hidden"})
        graph.add_edge(Edge(source="item_loot", target="item_crate", type=EDGE_IN))

        assert is_reachable(graph, "player_Hero", "area_test", "item_loot") is False

        loot = graph.get_node("item_loot")
        loot.properties["current_state"] = "normal"
        assert is_reachable(graph, "player_Hero", "area_test", "item_loot") is True

    def test_examine_does_not_hide_normal_state_contents(self, graph, player_manager, item_actions):
        from graph import EDGE_IN

        add_player(graph, "Hero")
        add_item(graph, "chest", tags=["container"], properties={"description": "A wooden chest."})
        graph.add_edge(Edge(source="item_chest", target="area_test", type=EDGE_IN))
        add_item(graph, "loot")
        graph.add_edge(Edge(source="item_loot", target="item_chest", type=EDGE_IN))
        player_manager.lighting.can_see_in_dark = MagicMock(return_value=True)
        player_manager.player.discovered_items = set()
        item_actions.matching._match_item_name = MagicMock(return_value="chest")

        result = item_actions.get_item_desc(player_manager, "chest")

        assert "Inside you see: loot." in result
        assert graph.get_node("item_loot").properties.get("current_state") == "normal"


# ═══════════════ TASK 160: SPATIAL PLACEMENT & GIVE ═══════════════


class TestSpatialPlacement:
    def test_place_item_on_surface(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        pen = add_item(graph, "pen")
        table = add_item(graph, "table", tags=["furniture"])
        graph.add_edge(Edge(source=pen.id, target="player_Hero", type=EDGE_CARRYING))
        graph.add_edge(Edge(source=table.id, target="area_test", type=EDGE_IN))

        result = item_actions.place_item(player_manager, "pen", "table", "on")

        assert "on the table" in result
        assert any(e.source == pen.id and e.type == EDGE_ON for e in graph.get_edges_for_target(table.id, EDGE_ON))
        assert not any(e.source == pen.id for e in graph.get_edges_for_target("player_Hero", EDGE_CARRYING))

    def test_place_item_under_surface(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        key = add_item(graph, "key")
        rug = add_item(graph, "rug", tags=["furniture"])
        graph.add_edge(Edge(source=key.id, target="player_Hero", type=EDGE_CARRYING))
        graph.add_edge(Edge(source=rug.id, target="area_test", type=EDGE_IN))

        result = item_actions.place_item(player_manager, "key", "rug", "under")

        assert "under the rug" in result
        assert any(e.source == key.id and e.type == EDGE_UNDER for e in graph.get_edges_for_target(rug.id, EDGE_UNDER))

    def test_place_into_non_container_rejects_in(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        pen = add_item(graph, "pen")
        table = add_item(graph, "table", tags=["furniture"])
        graph.add_edge(Edge(source=pen.id, target="player_Hero", type=EDGE_CARRYING))
        graph.add_edge(Edge(source=table.id, target="area_test", type=EDGE_IN))

        with pytest.raises(ValueError, match="isn't a container"):
            item_actions.place_item(player_manager, "pen", "table", "in")

    def test_place_into_container_uses_in(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        key = add_item(graph, "key")
        box = add_item(graph, "box", tags=["container"])
        graph.add_edge(Edge(source=key.id, target="player_Hero", type=EDGE_CARRYING))
        graph.add_edge(Edge(source=box.id, target="area_test", type=EDGE_IN))

        result = item_actions.place_item(player_manager, "key", "box", "in")

        assert "in the box" in result
        assert any(e.source == key.id and e.type == EDGE_IN for e in graph.get_edges_for_target(box.id, EDGE_IN))

    def test_place_missing_target(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        pen = add_item(graph, "pen")
        graph.add_edge(Edge(source=pen.id, target="player_Hero", type=EDGE_CARRYING))

        with pytest.raises(ValueError, match="don't see"):
            item_actions.place_item(player_manager, "pen", "nowhere", "on")


class TestGiveItem:
    def test_give_moves_item_to_target(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        add_player(graph, "Lyrie")
        key = add_item(graph, "key")
        graph.add_edge(Edge(source=key.id, target="player_Hero", type=EDGE_CARRYING))

        lyrie = MagicMock()
        lyrie.name = "Lyrie"
        lyrie.current_area = "Test"
        lyrie.state = "awake"
        player_manager.players["Lyrie"] = lyrie

        result = item_actions.give_item(player_manager, "key", "Lyrie")

        assert "to Lyrie" in result
        assert any(e.source == key.id for e in graph.get_edges_for_target("player_Lyrie", EDGE_CARRYING))
        assert not any(e.source == key.id for e in graph.get_edges_for_target("player_Hero", EDGE_CARRYING))

    def test_give_target_not_in_area(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        key = add_item(graph, "key")
        graph.add_edge(Edge(source=key.id, target="player_Hero", type=EDGE_CARRYING))

        far = MagicMock()
        far.name = "Elsewhere"
        far.current_area = "Other"
        player_manager.players["Elsewhere"] = far

        with pytest.raises(ValueError, match="isn't in the same area"):
            item_actions.give_item(player_manager, "key", "Elsewhere")


class TestSpatialReachability:
    def test_item_on_surface_is_reachable(self, graph):
        add_player(graph, "Hero")
        table = add_item(graph, "table", tags=["furniture"])
        graph.add_edge(Edge(source=table.id, target="area_test", type=EDGE_IN))
        pen = add_item(graph, "pen")
        graph.add_edge(Edge(source=pen.id, target=table.id, type=EDGE_ON))

        assert is_reachable(graph, "player_Hero", "area_test", pen.id) is True

    def test_item_under_surface_is_reachable(self, graph):
        add_player(graph, "Hero")
        rug = add_item(graph, "rug", tags=["furniture"])
        graph.add_edge(Edge(source=rug.id, target="area_test", type=EDGE_IN))
        key = add_item(graph, "key")
        graph.add_edge(Edge(source=key.id, target=rug.id, type=EDGE_UNDER))

        assert is_reachable(graph, "player_Hero", "area_test", key.id) is True

# ═══════════════ AMBIGUOUS NAME RESOLUTION ═══════════════


class TestAutoSelectIdenticalCopies:
    """take <name> auto-picks the first copy when all matches are identical
    (same name/description/tags/state), instead of asking "Which one?".
    Distinct copies keep the ambiguity prompt."""

    def _two_area_items(self, graph, name, desc_a, desc_b, tags_a=None, tags_b=None):
        # Build nodes directly with distinct ids — WorldGraph.add_node
        # auto-renames a duplicate id with a hex suffix, so two add_item
        # calls would NOT produce two same-named nodes.
        def make(iid, desc, tags):
            n = Node(id=iid, type="item", name=name, properties={
                "name": name,
                "weight": 0.1,
                "tags": tags or [],
                "current_state": "normal",
                "actions": ["examine", "take", "use"],
                "description": desc,
            })
            graph.add_node(n)
            return n
        a = make(f"item_{name}_1", desc_a, tags_a)
        b = make(f"item_{name}_2", desc_b, tags_b)
        graph.add_edge(Edge(source=a.id, target="area_test", type=EDGE_IN))
        graph.add_edge(Edge(source=b.id, target="area_test", type=EDGE_IN))
        return a, b

    def test_identical_copies_auto_selects_first(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        a, b = self._two_area_items(graph, "apple", "A red apple.", "A red apple.")

        result = item_actions.take_item(player_manager, "apple")

        assert "apple" in result
        taken = [e.source for e in graph.get_edges_for_target("player_Hero", EDGE_CARRYING)]
        assert taken == [a.id]

    def test_identical_copies_in_capitalized_name_case(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        a = Node(id="item_Jumpsuit_1", type="item", name="Jumpsuit", properties={
            "name": "Jumpsuit", "weight": 0.1, "tags": [], "current_state": "normal",
            "actions": ["examine", "take", "use"], "description": "A sleek jumpsuit.",
        })
        b = Node(id="item_Jumpsuit_2", type="item", name="Jumpsuit", properties={
            "name": "Jumpsuit", "weight": 0.1, "tags": [], "current_state": "normal",
            "actions": ["examine", "take", "use"], "description": "A sleek jumpsuit.",
        })
        graph.add_node(a)
        graph.add_node(b)
        graph.add_edge(Edge(source=a.id, target="area_test", type=EDGE_IN))
        graph.add_edge(Edge(source=b.id, target="area_test", type=EDGE_IN))

        result = item_actions.take_item(player_manager, "jumpsuit")

        taken = [e.source for e in graph.get_edges_for_target("player_Hero", EDGE_CARRYING)]
        assert taken == [a.id]

    def test_distinct_copies_still_prompt(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        self._two_area_items(graph, "apple", "A red apple.", "A green apple.")

        with pytest.raises(AmbiguousItemError, match="Which one"):
            item_actions.take_item(player_manager, "apple")

    def test_distinct_by_tags_still_prompt(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        self._two_area_items(graph, "key", "A key.", "A key.", tags_a=["brass"], tags_b=["iron"])

        with pytest.raises(AmbiguousItemError, match="Which one"):
            item_actions.take_item(player_manager, "key")


class TestTakeAlreadyHeld:
    """take on a carried/worn item is a friendly no-op, not a search
    failure the LLM spirals over (taco_bell 2026-08-24: miki 'took' the
    sauce she was already holding and panicked about it vanishing)."""

    def test_take_carried_item_says_already_carrying(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        apple = add_item(graph, "apple")
        graph.add_edge(Edge(source=apple.id, target="player_Hero", type=EDGE_CARRYING))

        result = item_actions.take_item(player_manager, "apple")

        assert "already carrying" in result.lower()

    def test_take_worn_item_says_already_wearing(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        ring = add_item(graph, "ring")
        graph.add_edge(Edge(source=ring.id, target="player_Hero", type=EDGE_EQUIPPED))

        result = item_actions.take_item(player_manager, "ring")

        assert "already wearing" in result.lower()

    def test_not_found_hint_lists_items_only(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        rock = add_item(graph, "rock")
        graph.add_edge(Edge(source=rock.id, target="area_test", type=EDGE_IN))

        with pytest.raises(ValueError, match="Items you can see: rock"):
            item_actions.take_item(player_manager, "sword")


class TestConsumeItem:
    """eat/drink path — regression: _consume_item referenced an undefined
    past_verb and crashed every eat/drink action (found while building a
    poison vial whose on_drink trigger applies the poisoned condition)."""

    def test_drink_item_returns_result(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        vial = add_item(graph, "poison vial", tags=["drink"])
        graph.add_edge(Edge(source=vial.id, target="player_Hero", type=EDGE_CARRYING))
        item_actions.trigger_system._execute_triggers = MagicMock(return_value=[])

        result = item_actions.drink_item(player_manager, "poison vial")
        assert "drink" in result.lower()

    def test_drink_item_with_trigger_output(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        vial = add_item(graph, "poison vial", tags=["drink"])
        graph.add_edge(Edge(source=vial.id, target="player_Hero", type=EDGE_CARRYING))
        item_actions.trigger_system._execute_triggers = MagicMock(return_value=["poisoned applied."])

        result = item_actions.drink_item(player_manager, "poison vial")
        assert "poisoned applied" in result

    def test_eat_item_without_food_tag_fails(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        item = add_item(graph, "rock")
        graph.add_edge(Edge(source=item.id, target="player_Hero", type=EDGE_CARRYING))

        # no "eat" action and no "food" tag → contextual failure path is hit.
        # task-340 follow-up: soft failures now raise so /api/action reports
        # success=false (the agent's plan tracker and result rows see FAILURE).
        with pytest.raises(ValueError):
            item_actions.eat_item(player_manager, "rock")
        assert item_actions.trigger_system._contextual_failure.called

    def test_bare_eat_auto_picks_reachable_food(self, graph, player_manager, item_actions):
        """task-335: bare eat auto-picks a consumable in reach instead of
        erroring on the empty name."""
        add_player(graph, "Hero")
        rock = add_item(graph, "rock")
        graph.add_edge(Edge(source=rock.id, target="player_Hero", type=EDGE_CARRYING))
        apple = add_item(graph, "apple", tags=["food"])
        graph.add_edge(Edge(source=apple.id, target="area_test", type=EDGE_IN))

        result = item_actions.eat_item(player_manager, "")

        assert "apple" in result.lower()

    def test_bare_eat_prefers_carried_over_room(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        sandwich = add_item(graph, "sandwich", tags=["food"])
        graph.add_edge(Edge(source=sandwich.id, target="player_Hero", type=EDGE_CARRYING))
        pie = add_item(graph, "pie", tags=["food"])
        graph.add_edge(Edge(source=pie.id, target="area_test", type=EDGE_IN))

        result = item_actions.eat_item(player_manager, "")

        assert "sandwich" in result.lower()
        assert "pie" not in result.lower()

    def test_bare_drink_picks_only_drink_items(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        apple = add_item(graph, "apple", tags=["food"])
        graph.add_edge(Edge(source=apple.id, target="player_Hero", type=EDGE_CARRYING))
        flask = add_item(graph, "water flask", tags=["drink"])
        graph.add_edge(Edge(source=flask.id, target="area_test", type=EDGE_IN))

        result = item_actions.drink_item(player_manager, "")

        assert "water flask" in result.lower()
        assert "apple" not in result.lower()

    def test_bare_eat_nothing_consumable_friendly_error(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        rock = add_item(graph, "rock")
        graph.add_edge(Edge(source=rock.id, target="player_Hero", type=EDGE_CARRYING))

        # a blank name must NOT containment-match the carried rock
        with pytest.raises(ValueError, match="nothing to eat"):
            item_actions.eat_item(player_manager, "")


class TestParameterRendering:
    """{param:<key>} resolves in descriptions via a real TriggerSystem."""

    def test_render_node_desc_resolves_param(self):
        from engine.trigger_system import TriggerSystem
        from engine.logging_events import GameLogger

        graph = WorldGraph()
        door = Node(
            id="way_door", type="way", name="Door",
            properties={"parameters": {"light": "green"},
                        "description": "A number sits above a {param:light} light."},
        )
        graph.add_node(door)
        ts = TriggerSystem(graph, MagicMock(), GameLogger())
        ia = ItemActions.__new__(ItemActions)
        ia.trigger_system = ts
        assert ia._render_node_desc(door) == "A number sits above a green light."

    def test_render_node_desc_leaves_unknown_param(self):
        from engine.trigger_system import TriggerSystem
        from engine.logging_events import GameLogger

        graph = WorldGraph()
        door = Node(
            id="way_door", type="way", name="Door",
            properties={"description": "A {param:missing} light."},
        )
        graph.add_node(door)
        ts = TriggerSystem(graph, MagicMock(), GameLogger())
        ia = ItemActions.__new__(ItemActions)
        ia.trigger_system = ts
        assert ia._render_node_desc(door) == "A {param:missing} light."


class TestCarryCapacity:
    """Carry weight system (task-205): recursive containers, equipped/container mods, load ratio."""

    def test_empty_character_has_zero_load(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        ratio = item_actions.get_carry_load_ratio(player_manager)
        assert ratio["current"] == 0.0
        assert ratio["capacity"] == 100.0
        assert ratio["ratio"] == 0.0

    def test_container_contents_count_toward_carry(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        backpack = add_item(graph, "backpack", tags=["container"], weight=0.5,
                            properties={"max_weight_capacity": 10})
        apple = add_item(graph, "apple", weight=0.2)
        graph.add_edge(Edge(source=backpack.id, target="player_Hero", type=EDGE_CARRYING))
        graph.add_edge(Edge(source=apple.id, target=backpack.id, type=EDGE_IN))

        ratio = item_actions.get_carry_load_ratio(player_manager)
        assert ratio["current"] == pytest.approx(0.7)
        assert ratio["ratio"] == pytest.approx(0.007)

    def test_equipped_weight_mod(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        sword = add_item(graph, "sword", weight=3.0,
                         properties={"equip_slots": ["hand_right"], "equipped_weight_mod": 0.75})
        graph.add_edge(Edge(source=sword.id, target="player_Hero", type=EDGE_EQUIPPED,
                            properties={"slot": "hand_right"}))

        ratio = item_actions.get_carry_load_ratio(player_manager)
        assert ratio["current"] == pytest.approx(2.25)

    def test_container_weight_mod(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        backpack = add_item(graph, "backpack", tags=["container"], weight=0.5,
                            properties={"max_weight_capacity": 10, "container_weight_mod": 0.8})
        book = add_item(graph, "book", weight=2.0)
        graph.add_edge(Edge(source=backpack.id, target="player_Hero", type=EDGE_CARRYING))
        graph.add_edge(Edge(source=book.id, target=backpack.id, type=EDGE_IN))

        ratio = item_actions.get_carry_load_ratio(player_manager)
        assert ratio["current"] == pytest.approx(0.5 + 2.0 * 0.8)

    def test_nested_container_mods_stack(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        duffel = add_item(graph, "duffel", tags=["container"], weight=1.0,
                          properties={"max_weight_capacity": 20, "container_weight_mod": 1.2})
        pouch = add_item(graph, "pouch", tags=["container"], weight=0.1,
                         properties={"max_weight_capacity": 5, "container_weight_mod": 0.9})
        gem = add_item(graph, "gem", weight=0.5)
        graph.add_edge(Edge(source=duffel.id, target="player_Hero", type=EDGE_CARRYING))
        graph.add_edge(Edge(source=pouch.id, target=duffel.id, type=EDGE_IN))
        graph.add_edge(Edge(source=gem.id, target=pouch.id, type=EDGE_IN))

        ratio = item_actions.get_carry_load_ratio(player_manager)
        expected = 1.0 + 0.1 * 1.2 + 0.5 * 1.2 * 0.9
        assert ratio["current"] == pytest.approx(expected)

    def test_strong_backed_doubles_capacity(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        player_manager.player.traits = {"strong_backed": True}
        ratio = item_actions.get_carry_load_ratio(player_manager)
        assert ratio["capacity"] == 200.0

    def test_capacity_check_uses_recursive_weight(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        backpack = add_item(graph, "backpack", tags=["container"], weight=0.5,
                            properties={"max_weight_capacity": 10})
        heavy = add_item(graph, "rock", weight=50.0)
        graph.add_edge(Edge(source=backpack.id, target="player_Hero", type=EDGE_CARRYING))
        graph.add_edge(Edge(source=heavy.id, target=backpack.id, type=EDGE_IN))

        # 50.5 kg carried, capacity 100 — adding another 60 kg should fail
        err = item_actions._check_player_capacity(player_manager, 60.0)
        assert err is not None
        assert "50.5" in err

    def test_equipped_and_carried_items_both_count(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        sword = add_item(graph, "sword", weight=2.0,
                         properties={"equip_slots": ["hand_right"], "equipped_weight_mod": 1.0})
        shield = add_item(graph, "shield", weight=3.0)
        graph.add_edge(Edge(source=sword.id, target="player_Hero", type=EDGE_EQUIPPED,
                            properties={"slot": "hand_right"}))
        graph.add_edge(Edge(source=shield.id, target="player_Hero", type=EDGE_CARRYING))

        ratio = item_actions.get_carry_load_ratio(player_manager)
        assert ratio["current"] == pytest.approx(5.0)


class TestPlayerCapacityParam:
    """_check_player_capacity(player_name=...) lets effects gate give_item (task-103 Phase 3)."""

    def test_defaults_to_active_player(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        assert item_actions._check_player_capacity(player_manager, 10) is None

    def test_named_player_over_capacity_returns_error(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        add_player(graph, "Other")
        # load Hero to 95 kg, then a 10 kg item must fail
        for name, weight in [("anvil", 60), ("boulder", 35)]:
            it = add_item(graph, name, weight=weight)
            graph.add_edge(Edge(source=it.id, target="player_Hero", type=EDGE_CARRYING))
        player_manager.players["Hero"].traits = {}
        err = item_actions._check_player_capacity(player_manager, 10, player_name="Hero")
        assert err is not None and "carrying capacity" in err

    def test_named_player_within_capacity_returns_none(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        add_player(graph, "Other")
        player_manager.players["Hero"].traits = {}
        assert item_actions._check_player_capacity(player_manager, 5, player_name="Hero") is None

    def test_named_character_without_player_object(self, graph, player_manager, item_actions):
        add_player(graph, "Hero")
        assert item_actions._check_player_capacity(player_manager, 10, player_name="Ghost") is None
