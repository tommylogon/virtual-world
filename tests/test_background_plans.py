"""Assigned background pursuits carried out through short-term plans (task-426).

The pursuit is stored on the player while its current plan advances one step
per action, so it survives a need interruption. These tests pin the mechanism
(haul end to end, resume, clean failure) with authored scenario content.
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


def _assign(p, label, template, **fields):
    """Set the character-side pursuit assignment (task-818: character data, no node)."""
    repeat = bool(fields.pop("repeat", False))
    reason = fields.pop("reason", f"assigned {label}")
    p.active_pursuit = {
        "assignment_id": f"pursuit_{label}",
        "template_id": template,
        "label": label,
        "reason": reason,
        "bindings": dict(fields),
        "step_index": 0,
        "repeat": repeat,
    }
    return p.active_pursuit


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
    _assign(p, 'scrap_run', 'haul', source='Haul Source', item='scrap', sink='Haul Sink')

    for _ in range(30):
        w.tick_turn()
        if p.plan is None:
            break

    assert _in_area(w, scrap.id, 'Haul Sink'), "scrap did not arrive at the sink"
    assert scrap.id not in _carried_ids(w, 'Hauler')
    whys = [e.get("why") for e in p.lived_log]
    assert "pursuit:scrap_run:start" in whys, "pursuit never started"
    assert "plan:scrap_run" in whys, "no plan step recorded"
    assert "pursuit:scrap_run:done" in whys, "pursuit not marked done"


def test_plan_survives_a_need_interruption():
    app, w, client = _app()
    client.post('/api/build/area', json={'name': 'R Source'})
    client.post('/api/build/area', json={'name': 'R Sink'})
    _connect(client, 'R Source', 'R Sink')
    p = _bg_player(w, 'Resumer', 'R Source')
    scrap = _add_item(w, 'R Source', 'Scrap', ['scrap'])
    _add_item(w, 'R Source', 'ration', ['food'])
    _assign(p, 'resume_run', 'haul', source='R Source', item='scrap', sink='R Sink')

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
    _assign(p, 'empty_run', 'haul', source='E Source', item='scrap', sink='E Sink')

    for _ in range(5):
        w.tick_turn()
        if p.plan is None:
            break

    whys = [e.get("why") for e in p.lived_log]
    assert "pursuit:empty_run:failed" in whys, "empty source should fail the pursuit"
    assert p.plan is None, "failed plan should be cleared"
    assert p.completed_pursuits and p.completed_pursuits[0] == "pursuit_empty_run"


def test_plan_survives_save_load():
    app, w, client = _app()
    client.post('/api/build/area', json={'name': 'S Source'})
    client.post('/api/build/area', json={'name': 'S Sink'})
    _connect(client, 'S Source', 'S Sink')
    p = _bg_player(w, 'Saver', 'S Source')
    _add_item(w, 'S Source', 'Scrap', ['scrap'])
    _assign(p, 'save_run', 'haul', source='S Source', item='scrap', sink='S Sink')

    w.tick_turn()
    assert p.plan is not None
    plan = p.plan
    assert plan["pursuit_template"] == "haul"
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
    _assign(p, 'gather_run', 'gather', source_tags=['wild'], item='herb', home='G Home')

    for _ in range(40):
        w.tick_turn()
        if p.plan is None:
            break
    assert _in_area(w, herb.id, 'G Home'), "gathered resource did not come home"
    assert 'pursuit:gather_run:done' in [e.get('why') for e in p.lived_log]


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
    for name in names:
        _assign(w.players[name], 'rally_test', 'rally', rally_area='Rally Hub')

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
    for name in names:
        _assign(w.players[name], 'rally_deg', 'rally', rally_area='D Hub')

    for _ in range(40):
        w.tick_turn()
    assert w.players['Reach0'].current_area == 'D Hub'
    assert w.players['Reach1'].current_area == 'D Hub'
    assert w.players['CutOff'].current_area == 'D Cut', "unreachable member should not arrive"


def test_a_pursuit_node_is_no_longer_selected():
    """task-818: the runner resumes character data, not graph nodes.

    A leftover ``pursuit``-typed node must start nothing - the node type is
    retired, so selection reads ``Player.active_pursuit`` alone.
    """
    app, w, client = _app()
    client.post('/api/build/area', json={'name': 'N Source'})
    p = _bg_player(w, 'NoOp', 'N Source')
    _add_item(w, 'N Source', 'Scrap', ['scrap'])
    stale = Node(id='pursuit_stale', type='pursuit', name='stale',
                 properties={'pursuit_template': 'haul', 'actor': 'NoOp',
                             'source': 'N Source', 'item': 'scrap'})
    w.graph.add_node(stale)

    for _ in range(5):
        w.tick_turn()

    assert p.plan is None, "a pursuit node must no longer be selected"
    assert p.active_pursuit is None


def test_a_finished_pursuit_is_cleared_and_not_re_finished():
    """A completed pursuit leaves the character instead of looping forever.

    ``_finish`` compared the plan's ``node_id`` against the pursuit's
    ``assignment_id``. A plan has never carried ``node_id`` (task-818 retired
    the pursuit node type), so the test was permanently False: the finished
    pursuit stayed on the character, and ``maybe_assign`` rebuilt it from the
    saved ``step_index`` on every later tick, re-finishing the same undertaking
    once per tick. Measured before the fix: one pursuit marked done 38 times in
    40 ticks.
    """
    app, w, client = _app()
    client.post('/api/build/area', json={'name': 'F Source'})
    client.post('/api/build/area', json={'name': 'F Sink'})
    _connect(client, 'F Source', 'F Sink')
    p = _bg_player(w, 'Finisher', 'F Source')
    _add_item(w, 'F Source', 'Scrap', ['scrap'])
    _assign(p, 'finish_run', 'haul', source='F Source', item='scrap', sink='F Sink')

    for _ in range(40):
        w.tick_turn()

    whys = [e.get("why") for e in p.lived_log]
    assert whys.count("pursuit:finish_run:done") == 1, (
        "a finished pursuit must be marked done exactly once")
    assert whys.count("pursuit:finish_run:start") == 1
    assert p.active_pursuit is None, "the finished pursuit must leave the character"
    assert p.plan is None
    assert p.completed_pursuits.count("pursuit_finish_run") == 1
