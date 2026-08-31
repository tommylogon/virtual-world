"""Stackable instance tests (task-155): weight reconciliation, combine, split."""

from area import Area
from graph import Node, Edge, EDGE_CARRYING, EDGE_IN


def make_world():
    from virtual_world_engine import VirtualWorld
    world = VirtualWorld()
    world.movement.add_area(Area("Room A", "First room.", []))
    pname = world.active_player
    world.name_matcher._set_player_area(pname, "Room A")
    return world, pname


def add_item(world, name, props=None):
    n = Node(id=f"item_{name.replace(' ', '_')}", type="item", name=name, properties={
        "name": name, "weight": 0.5, "tags": [], "current_state": "normal",
        "actions": ["examine", "take", "use"],
    })
    if props:
        n.properties.update(props)
    world.graph.add_node(n)
    area_id = world._get_current_area_id()
    world.graph.add_edge(Edge(source=n.id, target=area_id, type=EDGE_IN))
    return n


def test_weight_reconciles_on_uses_change():
    world, pname = make_world()
    bread = add_item(world, "bread", {
        "uses": 2, "max_uses": 4,
    })
    player_id = world._player_node_id(pname)
    world.graph.add_edge(Edge(source=bread.id, target=player_id, type=EDGE_CARRYING))
    assert bread.properties["weight"] == 0.5
    bread.properties["uses"] = 1
    from engine.items.carry_weight import reconcile_item_weight
    reconcile_item_weight(bread)
    assert bread.properties["base_weight"] == 0.5
    assert bread.properties["weight"] == pytest_approx(0.125)
    bread.properties["uses"] = 4
    reconcile_item_weight(bread)
    assert bread.properties["weight"] == 0.5


def pytest_approx(v):
    return round(v, 3)


def test_infinite_uses_keep_static_weight():
    from engine.items.carry_weight import reconcile_item_weight
    node = Node(id="item_stone", type="item", name="Stone", properties={
        "uses": -1, "max_uses": 4, "weight": 2.0,
    })
    reconcile_item_weight(node)
    assert node.properties["weight"] == 2.0


def test_combine_sums_uses_weight_and_destroys_source():
    world, pname = make_world()
    a = add_item(world, "bread", {"uses": 4, "max_uses": 8})
    b = add_item(world, "bread", {"uses": 3, "max_uses": 8})
    player_id = world._player_node_id(pname)
    world.graph.add_edge(Edge(source=a.id, target=player_id, type=EDGE_CARRYING))
    world.graph.add_edge(Edge(source=b.id, target=player_id, type=EDGE_CARRYING))

    result = world.combine_items("bread", "bread")
    assert "combine" in result.lower()
    # exactly one survivor with summed uses (source destroyed)
    survivors = [n for n in world.graph.nodes.values()
                 if n.type == "item" and "bread" in n.name.lower() and "part" not in n.id]
    assert len(survivors) == 1
    assert survivors[0].properties["uses"] == 7


def test_combine_clamps_at_max_uses():
    world, pname = make_world()
    a = add_item(world, "bread", {"uses": 6, "max_uses": 8})
    b = add_item(world, "bread", {"uses": 6, "max_uses": 8})
    player_id = world._player_node_id(pname)
    world.graph.add_edge(Edge(source=a.id, target=player_id, type=EDGE_CARRYING))
    world.graph.add_edge(Edge(source=b.id, target=player_id, type=EDGE_CARRYING))
    world.combine_items("bread", "bread")
    survivors = [n for n in world.graph.nodes.values()
                 if n.type == "item" and "bread" in n.name.lower()]
    assert len(survivors) == 1
    assert survivors[0].properties["uses"] == 8


def test_combine_different_states_rejected():
    world, pname = make_world()
    a = add_item(world, "bread", {"uses": 4, "max_uses": 8})
    b = add_item(world, "bread", {"uses": 4, "max_uses": 8, "current_state": "stale"})
    player_id = world._player_node_id(pname)
    world.graph.add_edge(Edge(source=a.id, target=player_id, type=EDGE_CARRYING))
    world.graph.add_edge(Edge(source=b.id, target=player_id, type=EDGE_CARRYING))
    try:
        world.combine_items("bread", "bread")
        assert False, "expected ValueError"
    except Exception as e:
        assert "can't be combined" in str(e)


def test_split_halves_uses_and_creates_partner():
    world, pname = make_world()
    a = add_item(world, "bread", {"uses": 4, "max_uses": 8})
    player_id = world._player_node_id(pname)
    world.graph.add_edge(Edge(source=a.id, target=player_id, type=EDGE_CARRYING))
    result = world.split_item("bread")
    assert "split" in result.lower()
    assert a.properties["uses"] == 2
    parts = [e.source for e in world.graph.get_edges_for_target(player_id, EDGE_CARRYING)]
    assert len(parts) == 2
    partner = world.graph.get_node(parts[0] if parts[0] != a.id else parts[1])
    assert partner.properties["uses"] == 2
