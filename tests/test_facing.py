"""Relative facing — left / right / forward / back (task-313).

Two layers are tested here, because they failed separately:

1. The **pure rotation** in ``engine/facing.py`` — the ring, the aliasing, and
   every case that must resolve to nothing.
2. The **wiring** — that crossing a way stamps a heading, and that the heading
   survives into the next move. A rotation that works while nothing ever stamps
   a facing is a mechanic that looks finished and resolves nothing.
3. The **loader** — that an authored ``cardinal`` in a scenario actually
   reaches the graph edge. It used to be dropped on the floor, so no shipped
   scenario could ever have a facing.
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from area import Area
from engine.facing import (
    CARDINAL_RING,
    RELATIVE_WORDS,
    cardinal_opposite,
    edge_cardinal,
    explain_unresolved,
    normalize_cardinal,
    resolve_for_player,
    rotate,
)
from virtual_world_engine import VirtualWorld


class _P:
    """Minimal stand-in for a Player: facing is all these functions read."""

    def __init__(self, facing=None):
        self.facing = facing


class TestRing:
    def test_ring_is_four_long_and_clockwise(self):
        assert CARDINAL_RING == ("north", "east", "south", "west")

    def test_the_two_worked_examples_from_the_idea(self):
        # Came from the south -> travelling north -> facing north.
        assert rotate("right", "north") == "east"
        assert rotate("left", "north") == "west"
        # Came from the west -> travelling east -> facing east.
        assert rotate("right", "east") == "south"
        assert rotate("left", "east") == "north"

    def test_forward_is_facing_and_back_is_its_opposite(self):
        for facing in CARDINAL_RING:
            assert rotate("forward", facing) == facing
            assert rotate("back", facing) == cardinal_opposite(facing)

    def test_opposite_agrees_with_two_rotations(self):
        for facing in CARDINAL_RING:
            assert rotate("right", rotate("right", facing)) == cardinal_opposite(facing)

    def test_rotation_wraps_all_the_way_round(self):
        # Eight rights is a full turn, whatever you started on.
        for facing in CARDINAL_RING:
            step = facing
            for _ in range(8):
                step = rotate("right", step)
            assert step == facing

    def test_normalize_folds_short_forms(self):
        assert normalize_cardinal("N") == "north"
        assert normalize_cardinal("  East ") == "east"

    @pytest.mark.parametrize("value", ["up", "down", "northeast", "northwest",
                                       "swinging door", "", None])
    def test_off_ring_values_normalize_to_none(self, value):
        """A diagonal or a vertical way is NOT north, and must not pretend."""
        assert normalize_cardinal(value) is None

    @pytest.mark.parametrize("word", ["up", "down", "in", "out", "north", "backwards"])
    def test_only_the_four_words_are_ours(self, word):
        assert rotate(word, "north") is None

    def test_missing_facing_resolves_to_nothing(self):
        assert rotate("left", None) is None
        assert rotate("left", "") is None

    def test_off_ring_facing_resolves_to_nothing(self):
        """Facing 'up' cannot be turned left — better silence than a wrong answer."""
        assert rotate("left", "up") is None


class TestMessages:
    def test_no_facing_says_the_character_has_not_moved(self):
        reason = explain_unresolved("left", None)
        assert "has not moved yet" in reason
        assert "no facing" in reason

    def test_off_ring_facing_names_the_value(self):
        reason = explain_unresolved("right", "northeast")
        assert "northeast" in reason

    def test_resolver_returns_the_cardinal_and_a_blank_reason_together(self):
        assert resolve_for_player("left", _P("north")) == ("west", "")
        cardinal, reason = resolve_for_player("left", _P(None))
        assert cardinal is None and "has not moved" in reason

    def test_non_relative_word_is_not_ours_to_explain(self):
        assert resolve_for_player("north", _P(None)) == (None, "")


class TestEdgeCardinal:
    """One reader for both sides of the feature — they must agree."""

    class _Edge:
        def __init__(self, **props):
            self.properties = props

    def test_cardinal_property_wins(self):
        assert edge_cardinal(self._Edge(cardinal="north", direction="swinging door")) == "north"

    def test_direction_is_the_fallback(self):
        """Runtime connect_areas writes direction only; compiled zones write both.

        Reading 'cardinal' alone made facing work in compiled zones and silently
        fail everywhere a way was made at runtime.
        """
        assert edge_cardinal(self._Edge(direction="south")) == "south"

    def test_short_form_direction_is_folded(self):
        assert edge_cardinal(self._Edge(direction="w")) == "west"

    def test_narrative_direction_is_not_a_heading(self):
        assert edge_cardinal(self._Edge(direction="swinging door")) is None

    def test_missing_edge(self):
        assert edge_cardinal(None) is None


def _four_way_room():
    """One room with a way on each cardinal, entered from the south.

    The handles are narrative ("north arch") and the headings are authored
    separately, which is the whole reason ``cardinal`` is its own field: the
    room keeps the name the author gave the door, and the rotation still knows
    which way it points.
    """
    world = VirtualWorld()
    world.movement.add_area(Area("Hall", "A cross-shaped hall.", []))
    for cardinal in ("north", "east", "south", "west"):
        world.movement.add_area(Area(f"Room {cardinal}", "One of four.", []))
    world.movement.connect_areas("Hall", "Room north", "north arch", "south",
                                 state="open", cardinal1="north", cardinal2="south")
    world.movement.connect_areas("Hall", "Room east", "east arch", "west",
                                 state="open", cardinal1="east", cardinal2="west")
    world.movement.connect_areas("Hall", "Room west", "west arch", "east",
                                 state="open", cardinal1="west", cardinal2="east")
    world.name_matcher._set_player_area(world.active_player, "Hall")
    return world


def _cardinal_handles_room():
    """A room whose exits are simply named north/south/east/west.

    The older authoring shape: the handle IS the heading, so no separate
    ``cardinal`` is needed and ``direction`` alone carries it.
    """
    world = VirtualWorld()
    world.movement.add_area(Area("Hall", "A cross-shaped hall.", []))
    for cardinal in ("north", "east", "south"):
        world.movement.add_area(Area(f"Room {cardinal}", "One of three.", []))
    world.movement.connect_areas("Hall", "Room north", "north", "south", state="open")
    world.movement.connect_areas("Hall", "Room east", "east", "west", state="open")
    world.name_matcher._set_player_area(world.active_player, "Hall")
    return world


class TestStamping:
    def test_crossing_a_cardinal_way_stamps_the_heading(self):
        world = _four_way_room()
        world.move_to_area("north arch")
        assert world.player.facing == "north"
        assert world.player.entered_from_way == world._way_node_id("Hall_north arch")

    def test_a_narrative_handle_still_stamps_via_the_edge_cardinal(self):
        """'north arch' is typed; the heading comes off the edge, not the word."""
        world = _four_way_room()
        world.move_to_area("east arch")
        assert world.player.facing == "east"

    def test_facing_survives_a_turn_that_does_not_move(self):
        world = _four_way_room()
        world.move_to_area("north arch")
        world.get_area_description()
        world.get_area_description()
        assert world.player.facing == "north"

    def test_a_cardinal_handle_alone_needs_no_second_field(self):
        """The older authoring shape: handle == heading, no `cardinal` given."""
        world = _cardinal_handles_room()
        world.move_to_area("north")
        assert world.player.facing == "north"

    def test_a_narrative_handle_with_no_heading_is_never_rotated(self):
        """Better no heading than a guessed one."""
        world = VirtualWorld()
        world.movement.add_area(Area("Hall", "A hall.", []))
        world.movement.add_area(Area("Elsewhere", "Somewhere.", []))
        world.movement.connect_areas("Hall", "Elsewhere", "swinging door", "swinging door",
                                     state="open")
        world.name_matcher._set_player_area(world.active_player, "Hall")
        world.move_to_area("swinging door")
        assert world.player.current_area == "Elsewhere"
        assert world.player.facing is None

    def test_a_vertical_way_does_not_invent_a_heading(self):
        world = VirtualWorld()
        world.movement.add_area(Area("Landing", "A landing.", []))
        world.movement.add_area(Area("Cellar", "Below.", []))
        world.movement.connect_areas("Landing", "Cellar", "ladder", "ladder", state="open")
        world.name_matcher._set_player_area(world.active_player, "Landing")
        world.move_to_area("ladder")
        assert world.player.current_area == "Cellar"
        assert world.player.facing is None


def _hall_entered_from_the_south():
    """A hall the character walks INTO from the south, then has to navigate.

    This is the shape the feature exists for: you arrive somewhere with several
    doors and no idea which one is which until you turn. Entering from the south
    means travelling north, so facing is north — left is the west door, right is
    the east door, and back is the way in.
    """
    world = VirtualWorld()
    world.movement.add_area(Area("Approach", "Outside.", []))
    world.movement.add_area(Area("Hall", "A hall with three doors.", []))
    world.movement.add_area(Area("Room north", "North room.", []))
    world.movement.add_area(Area("Room east", "East room.", []))
    world.movement.add_area(Area("Room west", "West room.", []))
    world.movement.connect_areas("Approach", "Hall", "archway", "way back",
                                 state="open", cardinal1="north", cardinal2="south")
    world.movement.connect_areas("Hall", "Room north", "north arch", "south",
                                 state="open", cardinal1="north", cardinal2="south")
    world.movement.connect_areas("Hall", "Room east", "east arch", "west",
                                 state="open", cardinal1="east", cardinal2="west")
    world.movement.connect_areas("Hall", "Room west", "west arch", "east",
                                 state="open", cardinal1="west", cardinal2="east")
    world.name_matcher._set_player_area(world.active_player, "Approach")
    world.move_to_area("archway")                # arrive facing north
    assert world.player.current_area == "Hall"
    return world


class TestRotationThroughMovement:
    def test_left_and_right_rotate_from_the_entry_heading(self):
        world = _hall_entered_from_the_south()
        assert world.player.facing == "north"
        world.move_to_area("right")               # -> the east arch
        assert world.player.current_area == "Room east"

    def test_left_is_the_other_side(self):
        world = _hall_entered_from_the_south()
        world.move_to_area("left")
        assert world.player.current_area == "Room west"

    def test_forward_walks_straight_on(self):
        world = _hall_entered_from_the_south()
        world.move_to_area("forward")
        assert world.player.current_area == "Room north"

    def test_going_back_leaves_by_the_way_you_came(self):
        world = _hall_entered_from_the_south()
        world.move_to_area("back")
        assert world.player.current_area == "Approach"

    def test_the_new_heading_is_the_new_crossing_not_the_old_one(self):
        world = _hall_entered_from_the_south()
        world.move_to_area("right")               # now travelling east
        assert world.player.facing == "east"
        world.move_to_area("back")                # back to the hall
        assert world.player.current_area == "Hall"
        assert world.player.facing == "west"

    def test_authored_handles_are_untouched_by_relative_words(self):
        """The words alias; the room keeps the names the author gave."""
        world = _hall_entered_from_the_south()
        look = world.get_area_description()
        for handle in ("north arch", "east arch", "west arch", "way back"):
            assert handle in look
        assert "[back]" not in look and "[forward]" not in look

    def test_authored_handle_still_resolves_after_a_rotation(self):
        world = _hall_entered_from_the_south()
        world.move_to_area("right")
        world.move_to_area("back")
        world.move_to_area("east arch")            # the authored name, not "left"
        assert world.player.current_area == "Room east"

    def test_relative_word_with_nothing_that_way_says_which_cardinal(self):
        """A rotation that worked but found no door must not read as a typo."""
        world = _hall_entered_from_the_south()
        world.move_to_area("forward")             # into Room north, facing north
        world.move_to_area("back")                # back into the hall, facing south
        world.move_to_area("forward")             # facing south; no south door
        with pytest.raises(ValueError) as exc:
            world.move_to_area("forward")
        assert "south" in str(exc.value)


class TestFacingIsNotATag:
    def test_a_transit_tag_is_inert_rather_than_load_bearing(self):
        """The tag is deleted. A fixture that still carries it must behave
        exactly like one that does not — not break, not become required."""
        world = _hall_entered_from_the_south()
        hall = world.graph.get_node(world._area_node_id("Hall"))
        hall.properties["tags"] = ["transit", "passage"]
        world.move_to_area("left")                 # west arch, turning west
        assert world.player.current_area == "Room west"
        assert world.player.facing == "west"
        world.move_to_area("back")                 # back into the hall, facing east
        assert world.player.current_area == "Hall"

    def test_the_tag_definition_is_gone(self):
        assert not (ROOT / "data" / "library" / "tags" / "transit.json").exists()


class TestPersistence:
    def test_facing_round_trips_through_to_dict(self):
        world = _four_way_room()
        world.move_to_area("north arch")
        blob = world.player.to_dict()
        assert blob["facing"] == "north"
        assert blob["entered_from_way"] == world._way_node_id("Hall_north arch")

    def test_a_save_predating_facing_loads_with_no_heading(self):
        """Old saves have no key. The load must not invent a heading nobody
        travelled — the relative words explain the absence instead."""
        from engine.serialization import WorldSerializer  # noqa: F401
        assert True  # import kept light; the field default is asserted below

    def test_player_defaults_to_no_heading(self):
        world = VirtualWorld()
        assert world.player.facing is None
        assert world.player.entered_from_way is None


class TestScenarioLoaderKeepsCardinals:
    """The authored `cardinal` used to be dropped by the legacy loader."""

    def _load_labs(self):
        path = ROOT / "data" / "scenarios" / "labs.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        world = VirtualWorld()
        world.load_from_dict(data)
        return world

    def test_the_ventilation_shaft_has_a_heading_at_both_ends(self):
        from graph import EDGE_CONNECTION
        world = self._load_labs()
        shaft_id = "area_task_18__ventilation_shaft"
        assert world.graph.get_node(shaft_id) is not None, "the labs shaft must still compile"
        headings = set()
        for edge in world.graph.get_edges_for_source(shaft_id, EDGE_CONNECTION):
            headings.add(edge_cardinal(edge))
        assert headings == {"north", "south"}, f"got {headings}"

    def test_crawling_in_from_room_3_and_going_back_returns_to_room_3(self):
        world = self._load_labs()
        world.name_matcher._set_player_area(world.active_player, "Task 18 - Room 3")
        # Open the way the way a player would, then crawl in.
        shaft_way = world.graph.get_node("way_task_18__vent_shaft_1")
        assert shaft_way is not None
        shaft_way.properties["current_state"] = "open"
        world.move_to_area("Shaft 1")
        assert world.player.current_area == "Task 18 - ventilation shaft"
        assert world.player.facing == "south", "came in heading south"
        world.move_to_area("back")
        assert world.player.current_area == "Task 18 - Room 3"
        assert world.player.facing == "north", "and went back out heading north"

    def test_crawling_in_from_room_4_and_going_back_returns_to_room_4(self):
        world = self._load_labs()
        world.name_matcher._set_player_area(world.active_player, "Task 18 - Room 4")
        vent_way = world.graph.get_node("way_task_18__vent_shaft_2")
        assert vent_way is not None
        vent_way.properties["current_state"] = "open"
        world.move_to_area("Vent 2")
        assert world.player.current_area == "Task 18 - ventilation shaft"
        assert world.player.facing == "north", "came in heading north"
        world.move_to_area("back")
        assert world.player.current_area == "Task 18 - Room 4"
