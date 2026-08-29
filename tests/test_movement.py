"""Tests for the dash movement action (task-162) and size/passage movement (task-187)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from virtual_world_engine import VirtualWorld
from area import Area
from graph import Node, Edge, EDGE_IN, EDGE_TRIGGERS, EDGE_AT
from player import Player


@pytest.fixture
def dash_world():
    """A world with three areas in a line (A -> B -> C via north/south)."""
    world = VirtualWorld()
    world.movement.add_area(Area("Room A", "First room.", []))
    world.movement.add_area(Area("Room B", "Middle room.", []))
    world.movement.add_area(Area("Room C", "Last room.", []))
    world.movement.connect_areas("Room A", "Room B", "north", "south", state="open")
    world.movement.connect_areas("Room B", "Room C", "north", "south", state="open")

    world.name_matcher._set_player_area(world.active_player, "Room A")
    player = world.player_manager.get_player(world.active_player)
    player.vitals["Energy"] = 100
    return world


class TestRoomApproach:
    """'go X' where X is a room item/character = walk over to it (at relation)."""

    def test_go_to_item_positions_player(self):
        world = VirtualWorld()
        world.movement.add_area(Area("Room A", "One table in it.", []))
        world.name_matcher._set_player_area(world.active_player, "Room A")
        area_id = world.area_node_id("Room A")
        table = Node(id="item_table", type="item", name="Booth Table",
                     properties={"current_state": "normal"})
        world.graph.add_node(table)
        world.graph.add_edge(Edge(source=table.id, target=area_id, type=EDGE_IN))

        out = world.move_to_area("the booth table")

        assert "Booth Table" in out
        pid = world.player_manager.get_player_node_id(world.active_player)
        at_edges = world.graph.get_edges_for_source(pid, EDGE_AT)
        assert any(e.type == EDGE_AT and e.target == "item_table" for e in at_edges)
        # No area change — it's a positioning, not an exit
        assert world.player.current_area == "Room A"

    def test_go_to_character_positions_player(self):
        world = VirtualWorld()
        world.movement.add_area(Area("Room A", "Two people.", []))
        world.name_matcher._set_player_area(world.active_player, "Room A")
        world.add_player(Player("Miki"))
        world.player_manager.players["Miki"].current_area = "Room A"
        world.set_player_area("Miki", "Room A")
        # add_player makes the NEWEST player active — restore the moving character
        world.set_active_player("Traveler")

        out = world.move_to_area("go to miki")

        assert "Miki" in out
        pid = world.player_manager.get_player_node_id(world.active_player)
        spatial_edges = world.graph.get_edges_for_source(pid)
        assert any(e.target == "player_Miki" and e.type in ("at", "beside") for e in spatial_edges)

    def test_go_article_strip_resolves_exit(self, dash_world):
        # "the north" / "the door" — leading articles no longer break exit matching
        out = dash_world.move_to_area("the north")
        assert dash_world.player.current_area == "Room B"
        assert out.strip()

    def test_go_unknown_still_fails(self, dash_world):
        with pytest.raises(ValueError, match="No exit"):
            dash_world.move_to_area("the cake")


class TestRelieveShame:
    """Public relieve = shame event (T4): Sanity hit always, Social only when
    witnessed. Restroom (toilet item or area tag) → no hit."""

    def _world_with_public_area(self):
        from app import create_app
        app = create_app({"TESTING": True})
        world = app.world
        pname = next(iter(world.player_manager.players))
        world.movement.add_area(Area("Test Lobby", "empty public area.", []))
        world.name_matcher._set_player_area(pname, "Test Lobby")
        world.player_manager.players[pname].current_area = "Test Lobby"
        world.set_active_player(pname)
        p = world.player_manager.players[pname]
        p.vitals["Bladder"] = 90
        p.vitals["Sanity"] = 100
        p.vitals["Social"] = 100
        return world, app.test_client(), p, pname

    def test_public_relieve_hits_sanity_alone(self):
        world, client, p, pname = self._world_with_public_area()
        client.post("/api/action", json={"command": "relieve", "character": pname})
        assert p.vitals["Sanity"] == 98   # shame hit even with no witnesses
        assert p.vitals["Social"] == 100  # alone → no social penalty
        assert p.vitals["Bladder"] == 0

    def test_witnessed_relieve_hits_social(self):
        world, client, p, pname = self._world_with_public_area()
        world.add_player(Player("Miki"))
        world.player_manager.players["Miki"].current_area = "Test Lobby"
        world.set_player_area("Miki", "Test Lobby")
        world.set_active_player(pname)
        client.post("/api/action", json={"command": "relieve", "character": pname})
        assert p.vitals["Sanity"] == 98
        assert p.vitals["Social"] == 97  # 3-point social hit when someone sees it


class TestDash:
    """Dash movement action checks.

    dash is a single fast ``go`` hop — the agent engine chains a follow-up
    decision (another ``go``) so a dash can cross several rooms in one turn.
    This class covers the backend hop only.
    """

    def test_dash_moves_one_area(self, dash_world):
        result = dash_world.dash_to_area("north")

        # Single hop — ended one area away from the start
        assert dash_world.player.current_area == "Room B"
        assert result.strip()  # returns the movement line

    def test_dash_returns_single_hop(self, dash_world):
        # dash_to_area performs ONE move — the second hop is a separate
        # chained decision made by the agent engine, not part of this call.
        hops = dash_world.dash_to_area("north")
        assert len(hops.split("\n")) == 1
        assert dash_world.player.current_area == "Room B"

    def test_dash_applies_energy_cost(self, dash_world):
        energy_before = dash_world.player.vitals["Energy"]
        dash_world.dash_to_area("north")
        assert dash_world.player.vitals["Energy"] < energy_before

    def test_dash_blocked_by_locked_door(self):
        world = VirtualWorld()
        world.movement.add_area(Area("Room A", "First room.", []))
        world.movement.add_area(Area("Room B", "Second room.", []))
        world.movement.connect_areas("Room A", "Room B", "north", "south", state="locked")
        world.name_matcher._set_player_area(world.active_player, "Room A")

        with pytest.raises(ValueError, match="locked"):
            world.dash_to_area("north")

    def test_dash_failed_hop_raises(self):
        # With no second hop baked in, a dash through a dead exit raises
        # instead of returning a partial result — the engine surfaces the
        # blocked move directly.
        world = VirtualWorld()
        world.movement.add_area(Area("Room A", "First room.", []))
        world.name_matcher._set_player_area(world.active_player, "Room A")

        with pytest.raises(ValueError, match="No exit"):
            world.dash_to_area("north")


class TestSizePassage:
    """Size-gated and crawl/climb/jump passage movement (task-187).

    Ways can carry ``max_size`` (tight tunnel) and ``requires``
    (crawl|climb|jump) properties. ``go`` auto-crawls tight ways, crawl-only
    ways convert to a crawl, climb/jump ways need the matching verb, and
    failed climb/jump rolls fire the way's ``on_fail_*`` trigger.
    """

    def _way(self, world):
        return world.graph.get_node("way_Room A_north")

    def _make_huge(self, world):
        player = world.player_manager.get_player(world.active_player)
        player.traits["size_huge"] = {}

    def test_go_passes_through_plain_way(self, dash_world):
        result = dash_world.move_to_area("north")
        assert "head through" in result
        assert dash_world.player.current_area == "Room B"

    def test_tight_fit_auto_crawls_without_scaling_cost(self, dash_world):
        # Crawl is flavor + gating today: it does NOT double the way's cost
        # (the `time` field is a duration hint for future stateful actions,
        # not per-action clock advancement — the clock moves once per turn).
        way = self._way(dash_world)
        way.properties["max_size"] = "small"
        way.properties["cost"] = {"time": 2, "energy": 1}

        captured = {}
        def fake_apply(action, cost, player=None):
            captured["cost"] = cost
        dash_world.apply_action = fake_apply

        result = dash_world.move_to_area("north")

        assert "crawl" in result.lower()
        assert captured["cost"] == {"time": 2, "energy": 1}
        assert dash_world.player.current_area == "Room B"

    def test_two_tiers_over_max_size_blocked(self, dash_world):
        self._way(dash_world).properties["max_size"] = "small"
        self._make_huge(dash_world)  # huge = 2 tiers over small

        with pytest.raises(ValueError, match="don't fit"):
            dash_world.move_to_area("north")
        assert dash_world.player.current_area == "Room A"

    def test_one_tier_over_climb_way_blocked(self, dash_world):
        self._way(dash_world).properties["max_size"] = "small"
        self._make_huge(dash_world)

        with pytest.raises(ValueError, match="don't fit"):
            dash_world.climb_to_area("north")

    def test_crawl_only_way_converts_go_to_crawl(self, dash_world):
        self._way(dash_world).properties["requires"] = "crawl"
        result = dash_world.move_to_area("north")
        assert "crawl" in result.lower()
        assert dash_world.player.current_area == "Room B"

    def test_climb_way_rejects_go(self, dash_world):
        self._way(dash_world).properties["requires"] = "climb"
        with pytest.raises(ValueError, match="need to climb"):
            dash_world.move_to_area("north")
        assert dash_world.player.current_area == "Room A"

    def test_climb_success_moves(self, dash_world):
        self._way(dash_world).properties["requires"] = "climb"
        dash_world.skill_check = lambda skill, dc: (True, 18, "clambered up")
        result = dash_world.climb_to_area("north")
        assert "climb" in result.lower()
        assert dash_world.player.current_area == "Room B"

    def test_jump_failure_fires_on_fail_jump_trigger(self, dash_world):
        way = self._way(dash_world)
        way.properties["requires"] = "jump"
        way.properties["jump_dc"] = 15
        dash_world.graph.add_edge(Edge(
            source=way.id,
            target="trigger_fail_jump",
            type=EDGE_TRIGGERS,
            properties={
                "trigger_type": "on_fail_jump",
                "effects": [{
                    "type": "message",
                    "params": {"message": "You slip on the edge and tumble back!"},
                }],
            },
        ))
        dash_world.skill_check = lambda skill, dc: (False, 4, "slipped")

        with pytest.raises(ValueError, match="tumble back"):
            dash_world.jump_to_area("north")
        assert dash_world.player.current_area == "Room A"

    def test_jump_success_moves(self, dash_world):
        self._way(dash_world).properties["requires"] = "jump"
        dash_world.skill_check = lambda skill, dc: (True, 20, "soared over")
        result = dash_world.jump_to_area("north")
        assert "leap" in result.lower()
        assert dash_world.player.current_area == "Room B"

    def test_jump_failure_without_trigger_uses_generic_message(self, dash_world):
        self._way(dash_world).properties["requires"] = "jump"
        dash_world.skill_check = lambda skill, dc: (False, 3, "slipped")
        with pytest.raises(ValueError, match="fail to jump"):
            dash_world.jump_to_area("north")


class TestConditionMovement:
    """Condition-driven movement — prone crawls, exhaustion gates speed."""

    def test_prone_go_becomes_crawl(self, dash_world):
        dash_world.player_manager.get_player(dash_world.active_player).add_condition(
            "prone", duration=None, source="broken_leg")
        result = dash_world.move_to_area("north")
        assert "crawl" in result.lower()
        assert dash_world.player.current_area == "Room B"

    def test_prone_climb_blocked(self, dash_world):
        dash_world.player_manager.get_player(dash_world.active_player).add_condition("prone")
        with pytest.raises(ValueError, match="prone"):
            dash_world.climb_to_area("north")
        assert dash_world.player.current_area == "Room A"

    def test_exhausted_level_six_blocks_move(self, dash_world):
        p = dash_world.player_manager.get_player(dash_world.active_player)
        p.add_condition("exhausted", duration=None)  # level 1
        for _ in range(5):
            p.add_condition("exhausted", duration=None)  # → level 6
        assert p.conditions["exhausted"][0]["level"] == 6
        with pytest.raises(ValueError, match="too exhausted"):
            dash_world.move_to_area("north")
        assert dash_world.player.current_area == "Room A"

    def test_dash_blocked_when_winded(self, dash_world):
        p = dash_world.player_manager.get_player(dash_world.active_player)
        for _ in range(3):
            p.add_condition("exhausted", duration=None)  # level 3 → speed 0.25
        with pytest.raises(ValueError, match="winded"):
            dash_world.dash_to_area("north")


class TestEncumbranceMovement:
    """Carry-load encumbrance gates movement energy cost and sprint (task-205)."""

    def _add_heavy_items(self, world, total_kg):
        from graph import Node, Edge, EDGE_CARRYING
        pname = world.active_player
        node_id = f"item_weight_{total_kg}".replace(".", "_")
        item = Node(id=node_id, type="item", name=f"weight_{total_kg}",
                    properties={"name": f"weight_{total_kg}", "weight": total_kg,
                                "actions": ["take"], "current_state": "normal"})
        world.graph.add_node(item)
        world.graph.add_edge(Edge(source=item.id, target=world._get_current_area_id(), type=EDGE_IN))
        if total_kg <= 100.0:
            world.item_actions.take_item(world, f"weight_{total_kg}")
        else:
            player_id = world.player_manager.get_player_node_id(pname)
            world.graph.add_edge(Edge(source=item.id, target=player_id, type=EDGE_CARRYING))

    def test_light_load_no_penalty(self, dash_world):
        self._add_heavy_items(dash_world, 20.0)
        energy_before = dash_world.player.vitals["Energy"]
        dash_world.move_to_area("north")
        assert dash_world.player.vitals["Energy"] < energy_before

    def test_moderate_load_adds_one_energy(self, dash_world):
        self._add_heavy_items(dash_world, 60.0)
        energy_before = dash_world.player.vitals["Energy"]
        dash_world.move_to_area("north")
        # base move costs 1 energy, moderate load adds 1 → total 2
        assert dash_world.player.vitals["Energy"] == energy_before - 2

    def test_heavy_load_adds_two_energy(self, dash_world):
        self._add_heavy_items(dash_world, 90.0)
        energy_before = dash_world.player.vitals["Energy"]
        dash_world.move_to_area("north")
        # base move costs 1 energy, heavy load adds 2 → total 3
        assert dash_world.player.vitals["Energy"] == energy_before - 3

    def test_dash_blocked_when_heavily_encumbered(self, dash_world):
        self._add_heavy_items(dash_world, 90.0)
        with pytest.raises(ValueError, match="heavily encumbered"):
            dash_world.dash_to_area("north")
        assert dash_world.player.current_area == "Room A"

    def test_over_capacity_blocks_movement(self, dash_world):
        self._add_heavy_items(dash_world, 150.0)
        with pytest.raises(ValueError, match="overencumbered"):
            dash_world.move_to_area("north")
        assert dash_world.player.current_area == "Room A"


class TestOpenPassageGuards:
    """Task-223 — jump/climb/crawl ways and prevent_close flags can't be
    toggled by characters; only triggers/authoring can change their state."""

    @pytest.fixture
    def passage_world(self):
        world = VirtualWorld()
        world.movement.add_area(Area("Room A", "First room.", []))
        world.movement.add_area(Area("Room B", "Second room.", []))
        world.movement.connect_areas("Room A", "Room B", "north", "south", state="open")
        world.name_matcher._set_player_area(world.active_player, "Room A")
        return world

    def _set_requires(self, world, requires):
        way_id = world._way_node_id("Room A_north")
        way = world.graph.get_node(way_id)
        way.properties["requires"] = requires
        return way_id

    @pytest.mark.parametrize("requires", ["jump", "climb", "crawl"])
    def test_cannot_close_traversal_way(self, passage_world, requires):
        passage_world.movement.toggle_way("north", "open")
        way_id = self._set_requires(passage_world, requires)
        with pytest.raises(ValueError, match="open jump passage|passage"):
            passage_world.movement.toggle_way("north", "close")
        way = passage_world.graph.get_node(way_id)
        assert way.properties["current_state"] == "open"

    @pytest.mark.parametrize("requires", ["jump", "climb", "crawl"])
    def test_cannot_open_traversal_way(self, passage_world, requires):
        passage_world.movement.toggle_way("north", "close")
        way_id = self._set_requires(passage_world, requires)
        with pytest.raises(ValueError, match="passage"):
            passage_world.movement.toggle_way("north", "open")
        way = passage_world.graph.get_node(way_id)
        assert way.properties["current_state"] == "closed"

    def test_toggle_way_by_id_blocked(self, passage_world):
        way_id = self._set_requires(passage_world, "jump")
        with pytest.raises(ValueError, match="passage"):
            passage_world.movement.toggle_way_by_id(way_id, "close")
        way = passage_world.graph.get_node(way_id)
        assert way.properties["current_state"] == "open"

    def test_prevent_close_flag_blocks_close(self, passage_world):
        passage_world.movement.toggle_way("north", "open")
        way_id = passage_world._way_node_id("Room A_north")
        way = passage_world.graph.get_node(way_id)
        way.properties["prevent_close"] = True
        with pytest.raises(ValueError, match="permanent"):
            passage_world.movement.toggle_way("north", "close")
        way = passage_world.graph.get_node(way_id)
        assert way.properties["current_state"] == "open"

    def test_prevent_close_flag_allows_open(self, passage_world):
        passage_world.movement.toggle_way("north", "close")
        way_id = passage_world._way_node_id("Room A_north")
        way = passage_world.graph.get_node(way_id)
        way.properties["prevent_close"] = True
        result = passage_world.movement.toggle_way("north", "open")
        assert "open the north" in result

    def test_normal_door_still_toggles(self, passage_world):
        result = passage_world.movement.toggle_way("north", "close")
        assert "close the north" in result
        way = passage_world.graph.get_node(passage_world._way_node_id("Room A_north"))
        assert way.properties["current_state"] == "closed"
        passage_world.movement.toggle_way("north", "open")
        assert way.properties["current_state"] == "open"


class TestGoToApproach:
    """'go to the <door>' / 'go toward <way>' = walk UP TO the way and stop —
    not pass through it. Bare 'go <handle>' / 'go <area>' / 'go <direction>'
    still cross. Agents mean "reach the doorway" with 'to' phrasing."""

    def _door_world(self):
        world = VirtualWorld()
        world.movement.add_area(Area("Room A", "First room.", []))
        world.movement.add_area(Area("Room B", "Second room.", []))
        world.movement.connect_areas("Room A", "Room B", "north", "south", state="open")
        world.name_matcher._set_player_area(world.active_player, "Room A")
        player = world.player_manager.get_player(world.active_player)
        player.vitals["Energy"] = 100
        return world

    def test_go_to_direction_word_still_crosses(self):
        world = self._door_world()
        world.move_to_area("to the north")
        assert world.player.current_area == "Room B"

    def test_go_to_destination_area_still_crosses(self):
        world = self._door_world()
        world.move_to_area("to the room b")
        assert world.player.current_area == "Room B"

    def test_go_to_way_approaches_and_positions(self):
        world = self._door_world()
        out = world.move_to_area("to the north door")
        assert world.player.current_area == "Room A"  # NOT through
        assert "walk over" in out.lower()
        pid = world.player_manager.get_player_node_id(world.active_player)
        at_edges = world.graph.get_edges_for_source(pid, EDGE_AT)
        assert any(e.type == EDGE_AT for e in at_edges)  # positioned at a way

    def test_go_through_way_crosses(self):
        world = self._door_world()
        world.move_to_area("through the north door")
        assert world.player.current_area == "Room B"

    def test_bare_go_way_crosses(self):
        world = self._door_world()
        world.move_to_area("north door")
        assert world.player.current_area == "Room B"

    def test_approach_verb_stops_at_item(self):
        world = VirtualWorld()
        world.movement.add_area(Area("Room A", "One table in it.", []))
        world.name_matcher._set_player_area(world.active_player, "Room A")
        area_id = world.area_node_id("Room A")
        table = Node(id="item_table", type="item", name="Booth Table",
                     properties={"current_state": "normal"})
        world.graph.add_node(table)
        world.graph.add_edge(Edge(source=table.id, target=area_id, type=EDGE_IN))
        out = world.approach("the booth table")
        assert "Booth Table" in out

    def test_approach_verb_stops_at_way(self):
        world = self._door_world()
        out = world.approach("the north")
        assert world.player.current_area == "Room A"
        assert "walk over to the north" in out.lower()

    def test_approach_verb_slug_matches_named_door(self):
        world = self._door_world()
        # "north door" phrasing on a way whose handle is "north" still resolves
        out = world.approach("the north door")
        assert world.player.current_area == "Room A"
        assert "walk over" in out.lower()

    def test_approach_verb_dash_not_affected(self):
        world = self._door_world()
        world.dash_to_area("north")
        assert world.player.current_area == "Room B"

    def test_go_to_unknown_still_fails(self):
        world = self._door_world()
        with pytest.raises(ValueError, match="No exit"):
            world.move_to_area("to the cake")
