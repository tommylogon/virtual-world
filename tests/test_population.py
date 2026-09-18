"""Tests for the tag-chain population engine (task-9)."""

import random

from engine.population import LibraryIndex, apply_population, plan_population

ENTRIES = {
    "wooden_shelf": {"name": "Wooden Shelf", "tags": ["furniture", "display", "kitchen"]},
    "pantry_cabinet": {"name": "Pantry Cabinet", "tags": ["furniture", "container", "storage", "kitchen"]},
    "bread": {"name": "Bread", "tags": ["food", "kitchen"]},
    "apple": {"name": "Apple", "tags": ["food", "kitchen"]},
    "sack_of_flour": {"name": "Sack of Flour", "tags": ["food", "kitchen", "storage"]},
    "sword": {"name": "Sword", "tags": ["weapon", "armory"]},
    "altar": {"name": "Altar", "tags": ["furniture", "display", "shrine"]},
    "candle": {"name": "Candle", "tags": ["shrine", "light"]},
}


def _index():
    return LibraryIndex(ENTRIES)


def test_index_tags_and_roles():
    idx = _index()
    assert idx.is_furniture("pantry_cabinet")
    assert "container" in idx.roles_of("pantry_cabinet")
    assert "display" in idx.roles_of("wooden_shelf")
    assert idx.name_of("bread") == "Bread"


def test_plan_is_deterministic_for_seed():
    idx = _index()
    p1 = plan_population(["kitchen"], idx, random.Random(42))
    p2 = plan_population(["kitchen"], idx, random.Random(42))
    assert p1 == p2
    p3 = plan_population(["kitchen"], idx, random.Random(43))
    # different seed may reorder selection; at least the shape is stable
    assert (len(p1.furniture), len(p1.items)) == (len(p3.furniture), len(p3.items))


def test_plan_selects_furniture_with_roles_and_domain_items():
    idx = _index()
    plan = plan_population(["kitchen"], idx, random.Random(1), items_per_area=4)
    assert plan.domains == ["kitchen"]
    assert plan.furniture, "expected kitchen furniture"
    for furn in plan.furniture:
        assert furn.library_id in ("wooden_shelf", "pantry_cabinet")
        assert furn.relation in ("in", "on")
    placed_ids = {p.library_id for p in plan.items}
    assert placed_ids, "expected kitchen items"
    assert placed_ids <= {"bread", "apple", "sack_of_flour"}
    assert "sword" not in placed_ids, "cross-domain item leaked in"
    assert all(p.relation in ("in", "on", "at") for p in plan.items)


def test_container_furniture_receives_in_items():
    idx = _index()
    plan = plan_population(["kitchen"], idx, random.Random(7), items_per_area=6)
    container_idx = [i for i, p in enumerate(plan.furniture) if p.relation == "in"]
    if container_idx:
        assert any(p.parent_index == container_idx[0] for p in plan.items)


def test_no_candidates_reports_unresolved_without_substitution():
    idx = _index()
    plan = plan_population(["void_domain"], idx, random.Random(1))
    assert plan.is_empty
    assert plan.unresolved_domains == ["void_domain"]


def test_untagged_area_is_empty():
    plan = plan_population([], _index(), random.Random(1))
    assert plan.is_empty
    assert plan.notes


def test_apply_population_uses_callbacks_and_parents():
    idx = _index()
    plan = plan_population(["kitchen"], idx, random.Random(3), items_per_area=4)
    spawned, relations = [], []

    def spawn(library_id):
        node_id = f"n{len(spawned)}_{library_id}"
        spawned.append(library_id)
        return node_id

    def relate(child, parent, relation):
        relations.append((child, parent, relation))

    furniture_nodes = apply_population(plan, spawn, relate, "area_kitchen")
    assert len(furniture_nodes) == len(plan.furniture)
    # every placement produced exactly one spawn + one relation
    assert len(spawned) == len(plan.furniture) + len(plan.items)
    assert len(relations) == len(spawned)
    # items with a furniture parent relate to that furniture node, not the area
    parented = [r for r in relations if r[2] in ("in", "on") and r[0] not in furniture_nodes.values()]
    assert parented, "expected items parented to furniture"
