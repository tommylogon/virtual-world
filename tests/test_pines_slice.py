"""Pines vertical slice (task-400): authored scopes + schedules, and the
task-399 offload/advance/activate proof on a real scenario."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from engine import promotion, world_scopes

PINES = Path(__file__).parent.parent / "data" / "scenarios" / "pines.json"


def _world():
    app = create_app({"TESTING": True})
    world = app.world
    with open(PINES, encoding="utf-8-sig") as fh:
        world.load_from_dict(json.load(fh))
    return world


class TestScopeManifest:
    def test_hierarchy_projects(self):
        world = _world()
        m = world_scopes.normalise_manifest(world.world_scopes)
        assert "millbrook_falls" in m
        children = world_scopes.direct_child_ids(m, "downtown")
        assert "the_pines" in children
        floor_2 = world_scopes.area_ids_in_scope(m, world.graph, "pines_floor_2")
        assert {"area_hallway_2", "area_apartment_2b"} <= floor_2

    def test_apartment_3b_is_unmade_with_a_recipe(self):
        world = _world()
        m = world_scopes.normalise_manifest(world.world_scopes)
        apartment = m["apartment_3b"]
        assert apartment["state"] == "unmade"
        assert apartment["recipe"] == "apartment.v1"
        assert apartment["seed"]

    def test_every_area_has_a_scope(self):
        world = _world()
        unassigned = [
            node.name for node in world.graph.nodes.values()
            if node.type == "area" and not node.properties.get("world_scope_id")
        ]
        assert unassigned == [], f"areas without a scope: {unassigned}"


class TestSchedules:
    RESIDENTS = ("miki", "rose", "kevin", "haruka", "mateo")

    def test_five_residents_have_a_schedule(self):
        world = _world()
        for name in self.RESIDENTS:
            player = world.players[name]
            assert player.schedule, f"{name} has no schedule"
            assert all("start" in step and "activity" in step for step in player.schedule)

    def test_schedules_span_the_day(self):
        world = _world()
        # `schedule.normalize` stores each `start` as minutes past midnight.
        starts = {step["start"] for step in world.players["miki"].schedule}
        assert {8 * 60, 17 * 60 + 30, 22 * 60} <= starts


class TestBackgroundProof:
    def test_offload_advance_activate_writes_one_bounded_memory(self):
        world = _world()
        world.time_per_tick_minutes = 15
        miki = world.players["miki"]

        assert promotion.offload(world, miki) is True
        for _ in range(32):  # eight in-game hours at 15 min/tick
            world.tick_turn()
        promotion.promote(world, miki)

        background = [m for m in miki.memories if m.get("source") == "background"]
        assert len(background) <= 1
        if background:
            assert len(background[0]["text"]) <= promotion.MEMORY_CHAR_LIMIT
            assert promotion.BACKGROUND_TAG in background[0]["tags"]

    def test_repeated_activation_does_not_duplicate(self):
        world = _world()
        world.time_per_tick_minutes = 15
        miki = world.players["miki"]

        promotion.offload(world, miki)
        for _ in range(8):
            world.tick_turn()
        promotion.promote(world, miki)
        # Promoting an already-attended character is a no-op.
        assert promotion.promote(world, miki) is None

        before = len([m for m in miki.memories if m.get("source") == "background"])
        promotion.offload(world, miki)
        for _ in range(8):
            world.tick_turn()
        promotion.promote(world, miki)
        after = len([m for m in miki.memories if m.get("source") == "background"])
        assert after - before <= 1
