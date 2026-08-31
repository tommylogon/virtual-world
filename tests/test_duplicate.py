"""Duplicate endpoint (task-377): area/item/way/character, single-write semantics.

Child direction convention (matches the graph): children point TO the node
(salt --[on]--> table), parents are what the node points at (table --[in]--> kitchen).
"""

import pytest

from graph import Edge, Node, EDGE_IN, EDGE_ON, EDGE_CARRYING, EDGE_EQUIPPED, EDGE_TRIGGERS
from app import create_app


@pytest.fixture
def app():
    return create_app({"TESTING": True})


@pytest.fixture
def client(app):
    return app.test_client()


def _world(app):
    return app.world


def _add_area(app, name):
    graph = _world(app).graph
    for n in graph.nodes.values():
        if n.type == "area" and n.name == name:
            return n
    node = Node(id=f"area_{name.lower().replace(' ', '_')}", type="area", name=name, properties={"description": f"{name} desc"})
    graph.add_node(node)
    return node


def _add_item(app, name, area_id=None, container_id=None, on=False):
    graph = _world(app).graph
    node = Node(id=name, type="item", name=name.title(), properties={"description": "item desc", "actions": ["examine"]})
    graph.add_node(node)
    if area_id:
        graph.add_edge(Edge(source=node.id, target=area_id, type=EDGE_IN))
    if container_id:
        graph.add_edge(Edge(source=node.id, target=container_id, type=EDGE_IN))
    if on:
        trig = Node(id=f"trigger_{name}_on_use", type="logic_trigger", name="on_use -> message",
                    properties={"trigger_type": "on_use", "effect_type": "message", "effect_params": {}})
        graph.add_node(trig)
        graph.add_edge(Edge(source=node.id, target=trig.id, type=EDGE_TRIGGERS, properties={"trigger_type": "on_use"}))
    return node


def test_duplicate_area_clones_items_contents_and_triggers(app, client):
    g = _world(app).graph
    area = _add_area(app, "Probe Kitchen 7783")
    box = _add_item(app, "pbox", area_id=area.id, on=True)
    coin = _add_item(app, "pcoin", container_id=box.id)
    resp = client.post("/api/graph/duplicate", json={"node_id": area.id})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "success"
    new_id = data["id"]
    assert new_id != area.id
    new_area = g.get_node(new_id)
    assert new_area.name == "Probe Kitchen 7783 (2)"
    # items cloned under the new area
    area_edges = [e for e in g.edges if e.target == new_id and e.type == EDGE_IN]
    assert len(area_edges) == 1
    new_box = g.get_node(area_edges[0].source)
    assert new_box.name == "Pbox (copy)"
    # contents cloned inside the new box (edge type preserved)
    box_edges = [e for e in g.edges if e.target == new_box.id and e.type == EDGE_IN]
    assert len(box_edges) == 1
    new_coin = g.get_node(box_edges[0].source)
    assert new_coin.name == "Pcoin (copy)"
    # triggers cloned with the box (new id, new link)
    trig_edges = [e for e in g.edges if e.source == new_box.id and e.type == EDGE_TRIGGERS]
    assert len(trig_edges) == 1
    new_trig = g.get_node(trig_edges[0].target)
    assert new_trig.properties["trigger_type"] == "on_use"
    assert new_trig.id != f"trigger_pbox_on_use"


def test_duplicate_item_keeps_placement_and_contents(app, client):
    g = _world(app).graph
    area = _add_area(app, "Cellar")
    box = _add_item(app, "chest", area_id=area.id)
    coin = _add_item(app, "gold", container_id=box.id)
    resp = client.post("/api/graph/duplicate", json={"node_id": box.id})
    assert resp.status_code == 200
    new_id = resp.get_json()["id"]
    new_box = g.get_node(new_id)
    assert new_box.name == "Chest (copy)"
    # placement preserved at the same area
    assert any(e.source == new_id and e.target == area.id and e.type == EDGE_IN for e in g.edges)
    # contents cloned
    assert any(e.source != "gold" and e.target == new_id and e.type == EDGE_IN
               and g.get_node(e.source).name == "Gold (copy)" for e in g.edges)


def test_duplicate_item_on_surface_keeps_same_parent(app, client):
    """SALT ON TABLE IN KITCHEN: duplicate table + salt, never the kitchen."""
    g = _world(app).graph
    kitchen = _add_area(app, "Kitchen")
    table = _add_item(app, "kit_table", area_id=kitchen.id)
    salt = _add_item(app, "salt")
    g.add_edge(Edge(source=salt.id, target=table.id, type=EDGE_ON))
    resp = client.post("/api/graph/duplicate", json={"node_id": table.id})
    assert resp.status_code == 200
    new_id = resp.get_json()["id"]
    new_table = g.get_node(new_id)
    # table copy is still in the SAME kitchen (parent shared, not cloned)
    assert any(e.source == new_id and e.target == kitchen.id and e.type == EDGE_IN for e in g.edges)
    # salt copy sits on the new table, edge type preserved (on, not in)
    salt_edges = [e for e in g.edges if e.target == new_id and e.type == EDGE_ON]
    assert len(salt_edges) == 1
    assert g.get_node(salt_edges[0].source).name == "Salt (copy)"
    # kitchen was NOT duplicated
    assert not any(n.type == "area" and "(2" in (n.name or "") for n in g.nodes.values())


def test_duplicate_equipped_item_not_the_character(app, client):
    """TOP EQUIPPED CHAR: duplicate top, not char. Copy drops into holder's area."""
    g = _world(app).graph
    area = _add_area(app, "Foyer")
    pname = next(iter(_world(app).player_manager.players))
    pnode = _world(app).player_manager.get_player_node_id(pname)
    top = _add_item(app, "band_tb", area_id=area.id)
    g.add_edge(Edge(source=top.id, target=pnode, type=EDGE_EQUIPPED, properties={"slot": "torso"}))
    before_players = len(_world(app).player_manager.players)
    resp = client.post("/api/graph/duplicate", json={"node_id": top.id})
    assert resp.status_code == 200
    new_id = resp.get_json()["id"]
    # no new character created
    assert len(_world(app).player_manager.players) == before_players
    # copy is not strapped on the char; it dropped into the char's area
    assert not any(e.source == new_id and e.target == pnode and e.type == EDGE_EQUIPPED for e in g.edges)
    assert any(e.source == new_id and e.target == area.id and e.type == EDGE_IN for e in g.edges)


def test_duplicate_way_reconnects_same_areas(app, client):
    g = _world(app).graph
    area_a = _add_area(app, "Hall A")
    area_b = _add_area(app, "Hall B")
    way = Node(id="way_hall_door", type="way", name="Hall Door", properties={})
    g.add_node(way)
    g.add_edge(Edge(source=area_a.id, target=way.id, type="connection"))
    g.add_edge(Edge(source=way.id, target=area_b.id, type="connection"))
    resp = client.post("/api/graph/duplicate", json={"node_id": way.id})
    assert resp.status_code == 200
    new_id = resp.get_json()["id"]
    new_way = g.get_node(new_id)
    assert new_way.name == "Hall Door (copy)"
    # connects to the same two areas (both directions recreated, areas not cloned)
    conns = [e for e in g.edges if e.source == new_id or e.target == new_id]
    assert len(conns) == 2
    assert {e.source for e in conns} == {area_a.id, new_id}
    assert {e.target for e in conns} == {new_id, area_b.id}
    assert not any(n.type == "area" and "(2" in (n.name or "") for n in g.nodes.values())


def test_duplicate_character_copies_player(app, client):
    g = _world(app).graph
    pname = next(iter(_world(app).player_manager.players))
    pnode = _world(app).player_manager.get_player_node_id(pname)
    resp = client.post("/api/graph/duplicate", json={"node_id": pnode})
    assert resp.status_code == 200
    new_id = resp.get_json()["id"]
    assert new_id != pnode
    new_pname = g.get_node(new_id).name
    assert "copy" in new_pname.lower()
    # a real player object exists, and sits where the original sits
    assert new_pname in _world(app).player_manager.players
    in_edges = [e for e in g.edges if e.source == new_id and e.type == EDGE_IN]
    assert len(in_edges) == 1
    area_node = g.get_node(in_edges[0].target)
    assert area_node is not None and area_node.type == "area"
    assert _world(app).player_manager.players[new_pname].current_area == area_node.name


def test_duplicate_trigger_node_rejected(app, client):
    g = _world(app).graph
    area = _add_area(app, "Trig Pit")
    box = _add_item(app, "tbox", area_id=area.id, on=True)
    trig_id = next(e.target for e in g.edges if e.source == box.id and e.type == EDGE_TRIGGERS)
    resp = client.post("/api/graph/duplicate", json={"node_id": trig_id})
    assert resp.status_code == 400
    assert "inspector" in resp.get_json()["error"].lower()


def test_duplicate_include_children_false(app, client):
    """include_children=false clones just the node + triggers, no subtree."""
    g = _world(app).graph
    area = _add_area(app, "Solo Pit")
    box = _add_item(app, "solo_box", area_id=area.id)
    _add_item(app, "solo_coin", container_id=box.id)
    resp = client.post("/api/graph/duplicate", json={"node_id": box.id, "include_children": False})
    assert resp.status_code == 200
    new_id = resp.get_json()["id"]
    # box cloned, but the coin wasn't
    assert not any(e.target == new_id and e.type == EDGE_IN for e in g.edges)


def test_duplicate_missing_or_unknown_type(app, client):
    assert client.post("/api/graph/duplicate", json={"node_id": "nope"}).status_code == 404
    bad = Node(id="beacon_x", type="beacon", name="Beacon", properties={})
    _world(app).graph.add_node(bad)
    assert client.post("/api/graph/duplicate", json={"node_id": "beacon_x"}).status_code == 400


def test_duplicate_cycle_guard(app, client):
    """A container that (transitively) contains itself must not recurse forever."""
    g = _world(app).graph
    area = _add_area(app, "Loop Pit")
    box = _add_item(app, "loopy_box", area_id=area.id)
    inner = _add_item(app, "loopy_inner")
    # box contains inner, and inner contains box → cycle
    g.add_edge(Edge(source=inner.id, target=box.id, type=EDGE_IN))
    g.add_edge(Edge(source=box.id, target=inner.id, type=EDGE_IN))
    resp = client.post("/api/graph/duplicate", json={"node_id": box.id})
    assert resp.status_code in (200, 400)  # must terminate, no timeout
    copies = [n for n in g.nodes.values() if '(copy' in (n.name or '').lower()]
    assert len(copies) <= 4  # bounded: box+inner, no recursive explosion


def test_duplicate_snapshot_before_mutation(app, client):
    """Duplicate pushes an undo snapshot first, so it can be rolled back."""
    area = _add_area(app, "Snap Pit")
    client.post("/api/graph/duplicate", json={"node_id": area.id})
    entries = client.get("/api/undo/list").get_json()["entries"]
    assert any("duplicate Snap Pit" in e["label"] for e in entries)
