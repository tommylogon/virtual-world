"""Saved scenarios must be graph-only: no duplicated projections.

task-222 established the principle for per-room `exits`; this suite guards the
rest of it. `to_scenario_dict()` (the FILE payload) must not carry `rooms`
(a byte-identical duplicate of `areas`), the legacy `ways`/`item_registry`
round-trip attrs, or per-area values that duplicate the graph node
(`properties`) or are recomputed at runtime (`ambient_light`,
`light_description`) or are always empty (`items`).

`to_dict()` (the LIVE /api/state payload) must keep them: the frontend reads
`data.ways` (static/js/world-state.js), so the strip belongs in the file path
only. Breaking that distinction is the failure mode this file exists to catch.
"""

from virtual_world_engine import VirtualWorld
from area import Area


def _world():
    world = VirtualWorld()
    world.movement.add_area(Area("Room A", "First room.", []))
    return world


class TestFilePayloadIsGraphOnly:
    def test_duplicate_and_legacy_keys_absent(self):
        scenario = _world().to_scenario_dict()
        assert "areas" not in scenario
        assert "rooms" not in scenario
        assert "ways" not in scenario
        assert "item_registry" not in scenario

    def test_area_data_lives_only_on_the_graph_node(self):
        """Nothing in `areas` was unique — the node already carries it, which is
        where routes/saveload.py's diff fingerprint now reads it from."""
        scenario = _world().to_scenario_dict()
        node = scenario["graph"]["nodes"]["area_room_a"]
        assert node["properties"].get("description") == "First room."

    def test_graph_is_still_the_source_of_truth(self):
        scenario = _world().to_scenario_dict()
        assert "graph" in scenario
        assert any(n.get("type") == "area" for n in scenario["graph"]["nodes"].values())

    def test_stripped_payload_round_trips(self):
        world = _world()
        scenario = world.to_scenario_dict()
        reloaded = VirtualWorld()
        reloaded.load_from_dict(scenario)
        assert len(reloaded.areas) == len(world.areas)
        assert reloaded.graph.get_node("area_room_a") is not None


class TestScenarioNameRoundTrips:
    """The name gates the frontend's local background-map cache
    (static/js/graph/graph-background.js `_scenarioIdentity`), so losing it on
    save made a saved map unloadable."""

    def test_name_is_written_to_the_file_payload(self):
        world = _world()
        world._scenario_name = "my_scenario"
        assert world.to_scenario_dict()["_scenario_name"] == "my_scenario"

    def test_name_survives_a_reload(self):
        world = _world()
        world._scenario_name = "my_scenario"
        reloaded = VirtualWorld()
        reloaded.load_from_dict(world.to_scenario_dict())
        assert reloaded._scenario_name == "my_scenario"

    def test_unnamed_world_does_not_invent_a_name(self):
        reloaded = VirtualWorld()
        reloaded.load_from_dict(_world().to_scenario_dict())
        assert not reloaded._scenario_name

    def test_unnamed_payload_omits_the_key_entirely(self):
        """An empty string would read as "unnamed" and outrank a real name."""
        assert "_scenario_name" not in _world().to_scenario_dict()


class TestLivePayloadKeepsBackCompat:
    def test_to_dict_still_exposes_rooms_ways_item_registry(self):
        live = _world().to_dict()
        assert "areas" in live
        assert "rooms" in live
        assert "ways" in live
        assert "item_registry" in live
