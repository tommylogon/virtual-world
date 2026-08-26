"""Phase 3 tests — save_on world-event hooks and the frightened source gates."""
import pytest
from area import Area
from graph import Node, Edge, EDGE_IN, EDGE_TRIGGERS
from engine.traits import TRAIT_DEFINITIONS


@pytest.fixture
def lined_world():
    """Two areas connected north/south with an open door."""
    from virtual_world_engine import VirtualWorld
    world = VirtualWorld()
    world.movement.add_area(Area("Room A", "First room.", []))
    world.movement.add_area(Area("Room B", "Second room.", []))
    world.movement.connect_areas("Room A", "Room B", "north", "south", state="open")
    world.name_matcher._set_player_area(world.active_player, "Room A")
    world.skills.roll_dice = lambda *args: 5  # fail saves by default
    return world


def _player(world):
    return world.player_manager.get_player(world.active_player)


class TestSaveOnReference:
    """The claustrophobic crawl flow — the reference implementation."""

    def test_claustrophobic_crawl_fails_save(self, lined_world):
        world = lined_world
        p = _player(world)
        p.traits["claustrophobic"] = True
        p.vitals["Sanity"] = 80
        world.graph.get_node("way_Room A_north").properties["requires"] = "crawl"

        world.move_to_area("north")

        assert p.has_condition("frightened")
        inst = p.conditions["frightened"][0]
        assert inst["duration"] == 3
        assert inst["source_type"] == "way"       # fear is about the passage
        assert inst["source"] == "Room A-north"   # the way node's name
        assert p.vitals["Sanity"] == 70  # -10 on failure

    def test_claustrophobic_crawl_save_success_no_effect(self, lined_world):
        world = lined_world
        p = _player(world)
        p.traits["claustrophobic"] = True
        p.vitals["Sanity"] = 80
        world.graph.get_node("way_Room A_north").properties["requires"] = "crawl"
        world.skills.roll_dice = lambda *args: 20  # success

        world.move_to_area("north")

        assert not p.has_condition("frightened")
        assert p.vitals["Sanity"] == 80

    def test_enter_area_tag_filter(self, lined_world):
        world = lined_world
        p = _player(world)
        p.traits["agoraphobic"] = True
        p.vitals["Sanity"] = 80
        world.graph.get_node("area_room_b").properties["tags"] = ["open"]

        world.move_to_area("north")

        assert p.has_condition("frightened")
        assert p.vitals["Sanity"] == 70

    def test_enter_area_tag_mismatch_no_effect(self, lined_world):
        world = lined_world
        p = _player(world)
        p.traits["agoraphobic"] = True
        p.vitals["Sanity"] = 80
        world.graph.get_node("area_room_b").properties["tags"] = ["closed"]

        world.move_to_area("north")

        assert not p.has_condition("frightened")
        assert p.vitals["Sanity"] == 80


class TestSaveOnEventTypes:
    """Every event in the catalog resolves through the emitter."""

    def test_each_event_type_resolves(self, lined_world):
        world = lined_world
        pname = world.active_player
        p = _player(world)
        events = ["crawl_tight_way", "climb_way", "jump_way", "enter_area",
                  "see_item", "loud_noise", "takes_damage", "alone_in_dark"]
        TRAIT_DEFINITIONS["_test_save_on_all"] = {
            "name": "Test", "description": "", "category": "mental",
            "effects": {},
            "save_on": [
                {"event": e, "stat": "WIS", "dc": 12,
                 "on_fail": [{"condition": "frightened", "duration": 1}]}
                for e in events
            ],
        }
        try:
            p.traits["_test_save_on_all"] = True
            for e in events:
                world._emit_save_on(pname, e, {"source": "x"})
            assert p.has_condition("frightened")
        finally:
            del TRAIT_DEFINITIONS["_test_save_on_all"]

    def test_see_item_hemophobic(self, lined_world):
        world = lined_world
        pname = world.active_player
        p = _player(world)
        p.traits["hemophobic"] = True
        p.vitals["Sanity"] = 80
        rag = Node(id="item_bloody_rag", type="item", name="Bloody Rag",
                   properties={"name": "Bloody Rag", "tags": ["blood"], "description": "A wet rag."})
        world.graph.add_node(rag)
        area_id = world._get_current_area_id()
        world.graph.add_edge(Edge(source=rag.id, target=area_id, type=EDGE_IN))

        world.get_item_desc("Bloody Rag")

        assert p.vitals["Sanity"] == 75  # hemophobic -5 on fail
        # the fear is sourced to the item and gates touching it
        assert p.has_condition("frightened")
        inst = p.conditions["frightened"][0]
        assert inst["source"] == "Bloody Rag"
        assert inst["source_type"] == "item"
        with pytest.raises(ValueError, match="too afraid"):
            world.take_item("Bloody Rag")

    def test_source_type_filter(self, lined_world):
        """A save_on entry may restrict itself to one source_type."""
        from engine.traits import TraitSystem
        world = lined_world
        p = _player(world)
        TRAIT_DEFINITIONS["_test_st_filter"] = {
            "name": "Test", "description": "", "category": "mental",
            "effects": {},
            "save_on": [{"event": "see_item", "source_type": "item",
                         "stat": "WIS", "dc": 12,
                         "on_fail": [{"condition": "frightened", "duration": 1}]}],
        }
        try:
            p.traits["_test_st_filter"] = True
            assert TraitSystem.get_save_on_entries(
                p, "see_item", {"source_type": "item"}
            )
            assert not TraitSystem.get_save_on_entries(
                p, "see_item", {"source_type": "way"}
            )
            assert not TraitSystem.get_save_on_entries(p, "see_item", {})
        finally:
            del TRAIT_DEFINITIONS["_test_st_filter"]

    def test_takes_damage_cowardly(self, lined_world):
        world = lined_world
        pname = world.active_player
        p = _player(world)
        p.traits["cowardly"] = True
        # combat damage carries the attacker as a character-source fear
        world.activities.wake_on_damage(pname, source="Brutus", source_type="character")
        assert p.has_condition("frightened")
        inst = p.conditions["frightened"][0]
        assert inst["source"] == "Brutus"
        assert inst["source_type"] == "character"

    def test_takes_damage_generic_source_does_not_match_character_filter(self, lined_world):
        """A trap/effect hit (no source_type) doesn't trigger a character fear."""
        world = lined_world
        pname = world.active_player
        p = _player(world)
        p.traits["cowardly"] = True
        world.activities.wake_on_damage(pname)  # generic damage, no source_type
        assert not p.has_condition("frightened")

    def test_alone_in_dark_nyctophobic(self, lined_world):
        world = lined_world
        pname = world.active_player
        p = _player(world)
        p.traits["nyctophobic"] = True
        p.vitals["Sanity"] = 80
        world._emit_save_on(pname, "alone_in_dark", {"light": 0})
        assert p.has_condition("frightened")
        assert p.vitals["Sanity"] == 75


class TestFrightenedAreaGate:
    """A frightened character won't re-enter the source area (owner-defined)."""

    def test_blocks_reexiting_source_area(self, lined_world):
        world = lined_world
        p = _player(world)
        # frightened OF Room B (e.g. from a direct authoring / agoraphobic enter)
        p.add_condition("frightened", duration=3, source="Room B")
        with pytest.raises(ValueError, match="too afraid"):
            world.move_to_area("north")
        assert world.player_manager.get_player(world.active_player).current_area == "Room A"

    def test_blocks_reexiting_source_area_typed(self, lined_world):
        """source_type='area' gates the same way as legacy untyped sources."""
        world = lined_world
        p = _player(world)
        p.add_condition("frightened", duration=3, source="Room B", source_type="area")
        with pytest.raises(ValueError, match="too afraid"):
            world.move_to_area("north")
        assert world.player_manager.get_player(world.active_player).current_area == "Room A"

    def test_does_not_block_other_areas(self, lined_world):
        world = lined_world
        p = _player(world)
        p.add_condition("frightened", duration=3, source="SomewhereElse")
        world.move_to_area("north")  # Room B is not the feared area
        assert world.player_manager.get_player(world.active_player).current_area == "Room B"


class TestFrightenedSourceGates:
    """source_type gates: way / item / character each block their own thing."""

    def test_way_gate_blocks_reusing_the_way(self, lined_world):
        world = lined_world
        p = _player(world)
        p.add_condition("frightened", duration=3, source="Room A-north", source_type="way")
        with pytest.raises(ValueError, match="too afraid"):
            world.move_to_area("north")
        assert world.player_manager.get_player(world.active_player).current_area == "Room A"

    def test_way_gate_does_not_block_other_ways(self, lined_world):
        world = lined_world
        p = _player(world)
        p.add_condition("frightened", duration=3, source="SomeOtherWay", source_type="way")
        world.move_to_area("north")
        assert world.player_manager.get_player(world.active_player).current_area == "Room B"

    def test_item_gate_blocks_take(self, lined_world):
        world = lined_world
        p = _player(world)
        p.add_condition("frightened", duration=3, source="Writhing Blade", source_type="item")
        blade = Node(id="item_writhing_blade", type="item", name="Writhing Blade",
                     properties={"name": "Writhing Blade", "actions": ["take"], "tags": []})
        world.graph.add_node(blade)
        area_id = world._get_current_area_id()
        world.graph.add_edge(Edge(source=blade.id, target=area_id, type=EDGE_IN))
        with pytest.raises(ValueError, match="too afraid"):
            world.take_item("Writhing Blade")

    def test_character_gate_blocks_attack(self, lined_world):
        from player import Player
        world = lined_world
        hero_name = world.active_player
        p = _player(world)
        world.add_player(Player("Brutus"))
        world.set_active_player(hero_name)
        world.player_manager.get_player("Brutus").current_area = "Room A"
        p.add_condition("frightened", duration=3, source="Brutus", source_type="character")
        result = world.combat.player_attack(world.active_player, "Brutus")
        assert "too afraid" in result
        assert "trembles" in result

    def test_character_gate_blocks_entry_while_present(self, lined_world):
        from player import Player
        world = lined_world
        hero_name = world.active_player
        p = _player(world)
        world.add_player(Player("Brutus"))
        world.set_active_player(hero_name)
        world.player_manager.get_player("Brutus").current_area = "Room B"
        p.add_condition("frightened", duration=3, source="Brutus", source_type="character")
        with pytest.raises(ValueError, match="too afraid"):
            world.move_to_area("north")
        assert world.player_manager.get_player(world.active_player).current_area == "Room A"


class TestSaveTriggerOnWay:
    """A way can author its own fear save via an on_enter trigger (fleshy orifice)."""

    def _attach_fear_save_trigger(self, world):
        way_id = "way_Room A_north"
        trigger = Node(
            id="trig_orifice_fear", type="logic_trigger", name="orifice fear save",
            properties={},
        )
        world.graph.add_node(trigger)
        world.graph.add_edge(Edge(
            source=way_id, target=trigger.id, type=EDGE_TRIGGERS,
            properties={
                "trigger_type": "on_enter",
                "effects": [{
                    "type": "save",
                    "params": {
                        "stat": "WIS", "dc": 12,
                        "on_fail": [{
                            "type": "apply_condition",
                            "params": {
                                "condition": "frightened", "duration": 4,
                                "source_type": "way",
                                "message": "The orifice pulses as you pass through.",
                            },
                        }],
                        "on_success": [],
                    },
                }],
            },
        ))

    def test_failed_save_applies_frightened_sourced_to_way(self, lined_world):
        world = lined_world
        p = _player(world)
        self._attach_fear_save_trigger(world)
        world.skills.roll_dice = lambda *args: 5  # fail the save

        world.move_to_area("north")

        assert p.has_condition("frightened")
        inst = p.conditions["frightened"][0]
        assert inst["duration"] == 4
        assert inst["source"] == "Room A-north"   # defaulted from the way node
        assert inst["source_type"] == "way"
        # the newly-learned fear now gates re-entry through that way
        world.name_matcher._set_player_area(world.active_player, "Room A")
        with pytest.raises(ValueError, match="too afraid"):
            world.move_to_area("north")

    def test_successful_save_leaves_no_fear(self, lined_world):
        world = lined_world
        p = _player(world)
        self._attach_fear_save_trigger(world)
        world.skills.roll_dice = lambda *args: 20  # pass the save

        world.move_to_area("north")

        assert not p.has_condition("frightened")
        assert world.player_manager.get_player(world.active_player).current_area == "Room B"
