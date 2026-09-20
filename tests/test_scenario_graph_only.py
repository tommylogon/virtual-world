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
        assert "rooms" not in scenario
        assert "ways" not in scenario
        assert "item_registry" not in scenario

    def test_derived_area_fields_absent(self):
        scenario = _world().to_scenario_dict()
        assert scenario.get("areas"), "areas must still be present for the wizard/fingerprint"
        for name, entry in scenario["areas"].items():
            assert "properties" not in entry, name
            assert "ambient_light" not in entry, name
            assert "light_description" not in entry, name
            assert "items" not in entry, name

    def test_fingerprint_fields_survive(self):
        """routes/saveload.py compares description/environment to detect changes."""
        entry = _world().to_scenario_dict()["areas"]["Room A"]
        assert "description" in entry
        assert "environment" in entry
        assert "floor" in entry

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


class TestLivePayloadKeepsBackCompat:
    def test_to_dict_still_exposes_rooms_ways_item_registry(self):
        live = _world().to_dict()
        assert "areas" in live
        assert "rooms" in live
        assert "ways" in live
        assert "item_registry" in live
