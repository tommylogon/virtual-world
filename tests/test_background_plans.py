"""Authored multi-step background plans (task-426).

A plan is stored on the player and advanced one step per action, so it survives
a need interruption. These tests pin the mechanism (haul end to end, resume,
clean failure) before any scenario content is authored.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from graph import Edge, Node, EDGE_CARRYING, EDGE_IN
from player import Player


def _app():
    from app import create_app
    app = create_app({"TESTING": True})
    # One game minute per turn, so a tick advances one action and the plan's
    # multi-step flow is observable rather than completing inside a single tick.
    app.world.time_per_tick_minutes = 1
    return app, app.world, app.test_client()


def _connect(client, a, b):
    return client.post('/api/build/connect', json={
        'room1': a, 'room2': b, 'dir1': 'north', 'dir2': 'south', 'state': 'open'})


def _bg_player(world, name, area):
    p = Player(name)
    world.add_player(p)
    p.current_area = area
    world.set_player_area(name, area)
    p.simulation_mode = "background"
    p.next_due_tick = 0
    for stat, value in {
        "Hunger": 10, "Thirst": 10, "Energy": 90, "Bladder": 0,
        "Hygiene": 100, "Sanity": 100, "Entertainment": 100, "Social": 100,
    }.items():
        p.vitals[stat] = value
    return p


def _add_item(world, area, name, tags, item_id=None):
    area_id = world.area_node_id(area)
    node = Node(
        id=item_id or f"item_{name.lower().replace(' ', '_')}", type="item", name=name,
        properties={"name": name, "tags": list(tags), "weight": 1.0, "uses": -1})
    world.graph.add_node(node)
    world.graph.add_edge(Edge(source=node.id, target=area_id, type=EDGE_IN))
    return node


def _plan_node(world, label, **props):
    props.setdefault("label", label)
    node = Node(id=f"plan_{label}", type="plan", name=label, properties=props)
    world.graph.add_node(node)
    return node


def _carried_ids(world, player_name):
    pid = world._player_node_id(player_name)
    return {e.source for e in world.graph.get_edges_for_target(pid, EDGE_CARRYING)}


def _in_area(world, item_id, area):
    area_id = world.area_node_id(area)
    return any(e.source == item_id and e.target == area_id and e.type == EDGE_IN
               for e in world.graph.edges)


def test_haul_moves_item_source_to_sink():
    app, w, client = _app()
    client.post('/api/build/area', json={'name': 'Haul Source'})
    client.post('/api/build/area', json={'name': 'Haul Sink'})
    _connect(client, 'Haul Source', 'Haul Sink')
    p = _bg_player(w, 'Hauler', 'Haul Source')
    scrap = _add_item(w, 'Haul Source', 'Scrap', ['scrap'])
    _plan_node(w, 'scrap_run', template='haul', actor='Hauler',
               source='Haul Source', item='scrap', sink='Haul Sink')

    for _ in range(30):
        w.tick_turn()
        if p.plan is None:
            break

    assert _in_area(w, scrap.id, 'Haul Sink'), "scrap did not arrive at the sink"
    assert scrap.id not in _carried_ids(w, 'Hauler')
    whys = [e.get("why") for e in p.lived_log]
    assert "plan:scrap_run:start" in whys, "plan never started"
    assert "plan:scrap_run" in whys, "no plan step recorded"
    assert "plan:scrap_run:done" in whys, "plan not marked done"


def test_plan_survives_a_need_interruption():
    app, w, client = _app()
    client.post('/api/build/area', json={'name': 'R Source'})
    client.post('/api/build/area', json={'name': 'R Sink'})
    _connect(client, 'R Source', 'R Sink')
    p = _bg_player(w, 'Resumer', 'R Source')
    scrap = _add_item(w, 'R Source', 'Scrap', ['scrap'])
    _add_item(w, 'R Source', 'ration', ['food'])
    _plan_node(w, 'resume_run', template='haul', actor='Resumer',
               source='R Source', item='scrap', sink='R Sink')

    w.tick_turn()                      # start + take
    assert p.plan is not None, "plan not started"
    p.vitals["Hunger"] = 90            # a need now interrupts
    w.tick_turn()
    assert p.plan is not None, "plan lost when a need interrupted it"

    for _ in range(30):
        p.vitals["Hunger"] = 10
        w.tick_turn()
        if p.plan is None:
            break
    assert _in_area(w, scrap.id, 'R Sink'), "plan did not resume to completion"


def test_haul_fails_cleanly_when_the_source_is_empty():
    app, w, client = _app()
    client.post('/api/build/area', json={'name': 'E Source'})
    client.post('/api/build/area', json={'name': 'E Sink'})
    _connect(client, 'E Source', 'E Sink')
    p = _bg_player(w, 'Empty', 'E Source')
    _plan_node(w, 'empty_run', template='haul', actor='Empty',
               source='E Source', item='scrap', sink='E Sink')

    for _ in range(5):
        w.tick_turn()
        if p.plan is None:
            break

    whys = [e.get("why") for e in p.lived_log]
    assert "plan:empty_run:failed" in whys, "empty source should fail the plan"
    assert p.plan is None, "failed plan should be cleared"
    assert p.completed_plans and p.completed_plans[0] == "plan_empty_run"


def test_plan_survives_save_load():
    app, w, client = _app()
    client.post('/api/build/area', json={'name': 'S Source'})
    client.post('/api/build/area', json={'name': 'S Sink'})
    _connect(client, 'S Source', 'S Sink')
    p = _bg_player(w, 'Saver', 'S Source')
    _add_item(w, 'S Source', 'Scrap', ['scrap'])
    _plan_node(w, 'save_run', template='haul', actor='Saver',
               source='S Source', item='scrap', sink='S Sink')

    w.tick_turn()
    assert p.plan is not None
    plan = p.plan
    assert plan["template"] == "haul"
    d = p.to_dict()
    assert d["plan"] is not None
    assert d["plan"]["label"] == "save_run"


def test_gather_fetches_tagged_resource_home():
    app, w, client = _app()
    client.post('/api/build/area', json={'name': 'G Home'})
    client.post('/api/build/area', json={'name': 'G Wild'})
    _connect(client, 'G Home', 'G Wild')
    wild = w.graph.get_node(w.area_node_id('G Wild'))
    wild.properties.setdefault('tags', []).append('wild')
    p = _bg_player(w, 'Gatherer', 'G Home')
    herb = _add_item(w, 'G Wild', 'Herb', ['herb'])
    _plan_node(w, 'gather_run', template='gather', actor='Gatherer',
               source_tags=['wild'], item='herb', home='G Home')

    for _ in range(40):
        w.tick_turn()
        if p.plan is None:
            break
    assert _in_area(w, herb.id, 'G Home'), "gathered resource did not come home"
    assert 'plan:gather_run:done' in [e.get('why') for e in p.lived_log]


def test_group_rally_converges_participants():
    app, w, client = _app()
    for n in ('Rally Hub', 'Rally A', 'Rally B', 'Rally C'):
        client.post('/api/build/area', json={'name': n})
    _connect(client, 'Rally Hub', 'Rally A')
    _connect(client, 'Rally Hub', 'Rally B')
    _connect(client, 'Rally Hub', 'Rally C')
    names = ['Member0', 'Member1', 'Member2']
    for name, area in zip(names, ('Rally A', 'Rally B', 'Rally C')):
        _bg_player(w, name, area)
    _plan_node(w, 'rally_test', template='rally', participants=names,
               rally_area='Rally Hub')

    for _ in range(40):
        w.tick_turn()
        if all(w.players[n].plan is None for n in names):
            break
    assert [w.players[n].current_area for n in names] == ['Rally Hub'] * 3


def test_group_rally_degrades_when_one_cannot_reach():
    app, w, client = _app()
    for n in ('D Hub', 'D A', 'D B', 'D Cut'):
        client.post('/api/build/area', json={'name': n})
    _connect(client, 'D Hub', 'D A')
    _connect(client, 'D Hub', 'D B')
    # 'D Cut' is left unconnected: its member is knowledge-gated out of the plan.
    names = ['Reach0', 'Reach1', 'CutOff']
    for name, area in zip(names, ('D A', 'D B', 'D Cut')):
        _bg_player(w, name, area)
    _plan_node(w, 'rally_deg', template='rally', participants=names,
               rally_area='D Hub')

    for _ in range(40):
        w.tick_turn()
    assert w.players['Reach0'].current_area == 'D Hub'
    assert w.players['Reach1'].current_area == 'D Hub'
    assert w.players['CutOff'].current_area == 'D Cut', "unreachable member should not arrive"


def test_plan_selected_by_role_tag():
    app, w, client = _app()
    client.post('/api/build/area', json={'name': 'Role Source'})
    client.post('/api/build/area', json={'name': 'Role Sink'})
    _connect(client, 'Role Source', 'Role Sink')
    p = _bg_player(w, 'Tinker', 'Role Source')
    p.tags = list(p.tags) + ['tinkerer']
    scrap = _add_item(w, 'Role Source', 'Scrap', ['scrap'])
    # No actor: any character tagged 'tinkerer' claims the plan.
    _plan_node(w, 'role_run', template='haul', role='tinkerer',
               source='Role Source', item='scrap', sink='Role Sink')

    for _ in range(30):
        w.tick_turn()
        if p.plan is None:
            break
    assert _in_area(w, scrap.id, 'Role Sink'), "role-selected plan did not run"
