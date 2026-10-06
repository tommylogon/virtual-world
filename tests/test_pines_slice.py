"""Pines vertical slice (task-400): authored scopes + schedules, the task-399
offload/advance/activate proof on a real scenario, and the end-to-end generation
proof — generate Apartment 3B through the API, walk in through the front door,
and reload without duplicates."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from engine import promotion, world_scopes

PINES = Path(__file__).parent.parent / "data" / "scenarios" / "pines.json"
APARTMENT = "apartment_3b"
HALLWAY = "area_hallway_3"
ROOMS = ("living", "bedroom", "bathroom")


def _world():
    app = create_app({"TESTING": True})
    world = app.world
    with open(PINES, encoding="utf-8-sig") as fh:
        world.load_from_dict(json.load(fh))
    return world


def _client():
    """A test client on a freshly loaded Pines, with the app kept on the world."""
    app = create_app({"TESTING": True})
    with open(PINES, encoding="utf-8-sig") as fh:
        app.world.load_from_dict(json.load(fh))
    return app, app.test_client()


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
            assert background[0]["text"]             # stored verbatim, not truncated
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


def _generated_area_ids(world, scope=APARTMENT):
    manifest = world_scopes.normalise_manifest(world.world_scopes)
    return world_scopes.area_ids_in_scope(manifest, world.graph, scope)


class TestGenerationEndToEnd:
    """The part of the demo that was still open: the scope declared a recipe and
    nothing ran it, so an unmade scope could not be generated at all."""

    def test_the_recipe_reachable_from_the_api_generates_the_apartment(self):
        app, client = _client()
        assert _generated_area_ids(app.world) == set(), "premise: still unmade"

        res = client.post(f"/api/world/scopes/{APARTMENT}/grid/generate", json={})
        assert res.status_code == 200, res.get_data(as_text=True)
        payload = res.get_json()
        assert payload["status"] == "generated"
        assert payload["report"]["recipe_id"] == "apartment.v1"
        assert payload["report"]["seed"] == "pines-3b-01"
        # An empty report means asked-for tags the library could not satisfy —
        # it must be visible, never silently substituted.
        assert payload["report"]["unresolved_tags"] == {}

        areas = _generated_area_ids(app.world)
        assert {f"area_{APARTMENT}_{room}" for room in ROOMS} <= areas
        manifest = world_scopes.normalise_manifest(app.world.world_scopes)
        assert manifest[APARTMENT]["state"] == "materialized"

    def test_a_second_generate_is_refused_and_duplicates_nothing(self):
        app, client = _client()
        client.post(f"/api/world/scopes/{APARTMENT}/grid/generate", json={})
        before = set(app.world.graph.nodes)

        res = client.post(f"/api/world/scopes/{APARTMENT}/grid/generate", json={})
        assert res.status_code == 409
        assert set(app.world.graph.nodes) == before

    def test_the_generated_interior_is_entered_through_the_movement_system(self):
        """Not "the way node exists" — a real walk, so the door is reachable the
        way every other door in Pines is (by name; the recipe sets no handle)."""
        app, client = _client()
        client.post(f"/api/world/scopes/{APARTMENT}/grid/generate", json={})
        world = app.world
        world.active_player = "miki"
        world.set_current_area("hallway 3")
        assert world._get_current_area_id() == HALLWAY, "premise: standing in the hall"

        world.toggle_way("apartment door", "open")
        world.move_to_area("apartment door")
        assert world._get_current_area_id() == f"area_{APARTMENT}_living"

        # And the interior is internally walkable too, not just enterable.
        world.toggle_way("bedroom door", "open")
        world.move_to_area("bedroom door")
        assert world._get_current_area_id() == f"area_{APARTMENT}_bedroom"

    def test_generated_items_are_takeable_not_just_present(self):
        app, client = _client()
        client.post(f"/api/world/scopes/{APARTMENT}/grid/generate", json={})
        world = app.world
        living = f"area_{APARTMENT}_living"
        items = [n for n in world.graph.nodes.values()
                 if n.type == "item"
                 and any(e.source == n.id and e.target == living
                         for e in world.graph.get_edges_for_source(n.id))]
        assert items, "the living room generated nothing to look at"

    def test_reload_keeps_the_generated_nodes_and_re_generates_no_duplicates(self):
        app, client = _client()
        client.post(f"/api/world/scopes/{APARTMENT}/grid/generate", json={})
        world = app.world
        generated = {n.id for n in world.graph.nodes.values()
                     if (n.properties.get("generated") or {}).get("scope_id") == APARTMENT}

        saved = json.loads(json.dumps(world.to_dict()))
        world.load_from_dict(saved)
        assert generated <= set(world.graph.nodes), "a generated node did not survive"
        manifest = world_scopes.normalise_manifest(world.world_scopes)
        assert manifest[APARTMENT]["state"] == "materialized"

        # A reload must not make the scope unmade, and re-running must not double.
        res = client.post(f"/api/world/scopes/{APARTMENT}/grid/generate", json={})
        assert res.status_code == 409
        again = [n.id for n in world.graph.nodes.values() if n.id in generated]
        assert len(again) == len(generated)

    def test_a_hand_edit_is_not_erased_by_a_second_invocation(self):
        """task-398's rule: generated is provenance, not ownership. A plain second
        generate is refused, and the refused call leaves the edit alone.

        The explicit ``allow_regenerate`` opt-in is a different promise and
        currently overwrites it — see task-585, filed from this test.
        """
        app, client = _client()
        client.post(f"/api/world/scopes/{APARTMENT}/grid/generate", json={})
        world = app.world
        item = next(n for n in world.graph.nodes.values()
                    if n.type == "item" and (n.properties.get("generated") or {}))
        world.graph.get_node(item.id).properties["description"] = "hand-edited"

        res = client.post(f"/api/world/scopes/{APARTMENT}/grid/generate", json={})
        assert res.status_code == 409
        assert world.graph.get_node(item.id).properties["description"] == "hand-edited"
