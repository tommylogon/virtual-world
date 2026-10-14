"""Reusable pursuit templates: schema, validation and binding (task-701).

These tests pin the mechanism, not the presence of files. Each one names the
value that was read or the branch that ran, so a passing test cannot pass for
the wrong reason: a literal where a binding belongs is rejected because the
validator read the ``bound`` tuple, an unknown condition leaf fails closed
because the validator read the shared ``CONDITION_TYPES``, and a template with
no timing block is timely because the timing branch never ran.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import engine.pursuit_templates as pt
from engine.plan_steps import (
    STEP_KIND_COUNT,
    library_ref_problems,
    step_problem,
)


def _app():
    from app import create_app
    return create_app({"TESTING": True})


# ─────────────────────────── the declared vocabulary ─────────────────────────

def test_step_vocabulary_is_declared_once():
    """The count is stated so nobody enumerates the set from one member."""
    assert STEP_KIND_COUNT == 5
    assert sorted(pt.STEP_KINDS) == ["activity", "drop", "take", "travel", "wait"]


def test_literal_area_is_rejected_where_a_binding_belongs():
    """A hardcoded place is a character-specific script, not a template.

    ``travel.area`` is in the declared ``bound`` tuple, so the validator reads
    that tuple and refuses the literal. This is the branch task-701's "no
    character-specific proper names" criterion depends on.
    """
    problem = step_problem({"kind": "travel", "area": "Scrap Pile"}, 0)
    assert problem is not None
    assert "binding" in problem


def test_undeclared_field_is_rejected():
    problem = step_problem({"kind": "travel", "area": {"$binding": "x"}, "bogus": 1}, 0)
    assert problem is not None
    assert "undeclared field" in problem


def test_travel_requires_exactly_one_bound_destination():
    assert "exactly one" in step_problem({"kind": "travel"}, 0)
    assert "exactly one" in step_problem({
        "kind": "travel", "area": {"$binding": "home"},
        "tags": {"$binding": "destination_tags"},
    }, 0)


def test_step_with_unknown_activity_catalog_fails_closed():
    problem = library_ref_problems(
        {"kind": "activity", "activity": "sleeping"}, 0, None)
    assert problem is not None
    assert "cannot resolve Activity catalog" in problem


# ─────────────────────────── the authored catalog ───────────────────────────

def test_catalog_loads_every_authored_template():
    catalog = pt.load()
    assert sorted(catalog) == [
        "fish-and-bring-home", "gather", "haul", "meal",
        "rally", "scout-and-report", "sleep-at-venue",
    ]
    assert pt.problems() == []


def _write_template(tmp_path, template):
    """Drop one template into a scratch library directory.

    ``_read_library`` resolves ``<data_dir>/library/pursuit_templates``, so the
    scratch tree has to carry that nesting rather than being the directory
    itself.
    """
    import json
    directory = tmp_path / "library" / "pursuit_templates"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{template['id']}.json").write_text(
        json.dumps(template), encoding="utf-8")
    return directory


def test_unknown_condition_leaf_fails_closed(tmp_path):
    """An unusable file is reported, never silently half-loaded.

    The validator reads ``engine.trigger_validator.CONDITION_TYPES``; a leaf
    outside that set is a leaf the engine cannot evaluate, so it would resolve
    to False at runtime and read as "the condition never held".
    """
    _write_template(tmp_path, {
        "id": "bogus_leaf", "version": 1,
        "purpose": "x", "parameters": {},
        "requirements": [{"type": "not_a_real_leaf"}],
        "steps": [{"kind": "wait", "activity": "waiting"}],
    })
    catalog, problems = pt._read_library(str(tmp_path))
    assert "bogus_leaf" not in catalog
    assert any("unknown condition type" in reason for _, reason in problems)


def test_steps_may_only_reference_declared_bindings(tmp_path):
    _write_template(tmp_path, {
        "id": "undeclared", "version": 1,
        "purpose": "x",
        "parameters": {"home": {"type": "area", "required": True}},
        "steps": [{"kind": "travel", "area": {"$binding": "nowhere"}}],
    })
    catalog, problems = pt._read_library(str(tmp_path))
    assert "undeclared" not in catalog
    assert any("undeclared bindings" in reason for _, reason in problems)


def test_all_structured_template_fields_bind_into_the_instance(tmp_path):
    _write_template(tmp_path, {
        "id": "structured",
        "version": 1,
        "purpose": "return to a bound home",
        "parameters": {"home": {"type": "area", "required": True}},
        "requirements": [{"type": "in_area", "area": {"$binding": "home"}}],
        "supplies": [{"tags": ["water"]}],
        "timing": {"date": {"day": 2}},
        "progress": [{
            "id": "at-home",
            "check": {"type": "in_area", "area": {"$binding": "home"}},
        }],
        "duration": {"minutes": 60},
        "stop_conditions": [{"type": "in_area", "area": {"$binding": "home"}}],
        "recipe": {"id": "camp-meal"},
        "steps": [{"kind": "travel", "area": {"$binding": "home"}}],
    })
    pt.reload(str(tmp_path))
    instance = pt.instantiate("structured", {"home": "Chief's Pit"}, data_dir=str(tmp_path))
    assert instance is not None
    assert instance["requirements"][0]["area"] == "Chief's Pit"
    assert instance["progress"][0]["check"]["area"] == "Chief's Pit"
    assert instance["stop_conditions"][0]["area"] == "Chief's Pit"
    assert instance["supplies"] == [{"tags": ["water"]}]
    assert instance["timing"] == {"date": {"day": 2}}
    assert instance["duration"] == {"minutes": 60}
    assert instance["recipe"] == {"id": "camp-meal"}


def test_unknown_activity_reference_fails_closed(tmp_path):
    """A step naming an Activity nothing defines starts nothing."""
    _write_template(tmp_path, {
        "id": "dead_activity", "version": 1,
        "purpose": "x", "parameters": {},
        "steps": [{"kind": "activity", "activity": "not_an_activity"}],
    })
    catalog, problems = pt._read_library(str(tmp_path))
    assert "dead_activity" not in catalog
    assert any("unknown activity" in reason for _, reason in problems)


# ─────────────────────────── binding an instance ────────────────────────────

def test_bind_resolves_authored_assignment():
    """``bind`` reads the assignment properties, not the template.

    The authored ``item`` key is the matching tag, so the bound spec carries it
    in ``tags``; a literal area name arrives only through the ``home`` binding.
    """
    instance = pt.bind("gather", {
        "source_tags": ["wild"], "item": "herb", "home": "G Home"})
    assert instance is not None
    assert instance["template_id"] == "gather"
    assert instance["steps"][0] == {"kind": "travel", "tags": ["wild"], "to": "source"}
    assert instance["steps"][1] == {"kind": "take", "spec": {"tags": ["herb"], "name": None}}
    assert instance["steps"][2]["area"] == "G Home"


def test_bind_fails_closed_on_a_missing_required_binding():
    assert pt.bind("gather", {"source_tags": ["wild"], "item": "herb"}) is None
    assert pt.bind("no_such_template", {"home": "x"}) is None


def test_instantiate_rejects_a_malformed_binding():
    assert pt.instantiate("gather", {"home": ""}) is None
    assert pt.instantiate("gather", {"home": 42}) is None


# ─────────────────────────── timing reads the world clock ───────────────────

class _ClockWorld:
    """A stand-in carrying the world's own accessors as properties."""
    current_game_hour = 8
    current_season = "summer"
    current_moon_phase = {"name": "full moon"}
    forecast_schedule = {"current_state": "sunny"}
    game_day = 32
    game_month = 2
    game_year = 1
    calendar_config = {"days_per_month": 30}


def test_timing_reads_the_worlds_own_clock():
    entry = {
        "timing": {
            "hours": {"after": "06:00", "before": "18:00"},
            "season": ["summer"],
            "weather": ["sunny"],
            "moon_phase": ["full moon"],
            "daylight": True,
        }
    }
    assert pt.timing_matches(entry, _ClockWorld()) is True


def test_timing_fails_when_the_hour_is_outside_the_window():
    entry = {"timing": {"hours": {"after": "22:00"}}}
    assert pt.timing_matches(entry, _ClockWorld()) is False


def test_timing_fails_when_the_season_is_wrong():
    entry = {"timing": {"season": ["winter"]}}
    assert pt.timing_matches(entry, _ClockWorld()) is False


def test_timing_fails_when_the_weather_is_wrong():
    entry = {"timing": {"weather": ["rain"]}}
    assert pt.timing_matches(entry, _ClockWorld()) is False


def test_timing_fails_when_the_moon_is_wrong():
    entry = {"timing": {"moon_phase": ["new moon"]}}
    assert pt.timing_matches(entry, _ClockWorld()) is False


def test_timing_fails_when_daylight_is_required_at_night():
    entry = {"timing": {"daylight": True}}
    night = _ClockWorld()
    night.current_game_hour = 23
    assert pt.timing_matches(entry, night) is False


def test_timing_reads_the_existing_world_date():
    entry = {"timing": {"date": {"day": 2, "month": [2, 3], "year": 1}}}
    assert pt.timing_matches(entry, _ClockWorld()) is True
    assert pt.timing_matches({"timing": {"date": {"day": 3}}}, _ClockWorld()) is False


def test_timing_reads_sun_from_the_existing_on_day_interval():
    assert pt.timing_matches({"timing": {"sun": "up"}}, _ClockWorld()) is True
    night = _ClockWorld()
    night.current_game_hour = 23
    assert pt.timing_matches({"timing": {"sun": "down"}}, night) is True
    assert pt.timing_matches({"timing": {"sun": "up"}}, night) is False


def test_a_template_with_no_timing_block_is_always_timely():
    assert pt.timing_matches({}, _ClockWorld()) is True
    assert pt.timing_matches({"timing": {}}, _ClockWorld()) is True


def test_timing_never_reads_a_second_calendar():
    """The world is the only clock; a stand-in with no accessors fails closed."""
    assert pt.timing_matches({"timing": {"hours": {"after": "06:00"}}}, None) is False
    assert pt.timing_matches({"timing": {"season": ["summer"]}}, object()) is False


# ─────────────────────────── the library registry round-trip ────────────────

def test_the_library_registry_round_trips_through_the_editor():
    """Save/load preserves authored fields without a second source of truth.

    The write goes through the same route the library editor uses, so the
    engine catalog is reloaded from the file the editor wrote.
    """
    from routes.library_ops import write_library_entry
    app = _app()
    entry = {
        "id": "round_trip_probe", "version": 1,
        "name": "Round trip probe",
        "purpose": "prove the registry round-trips",
        "parameters": {"home": {"type": "area", "required": True}},
        "steps": [{"kind": "travel", "area": {"$binding": "home"}}],
    }
    write_library_entry(app, "pursuit_templates", "round_trip_probe", entry)
    try:
        catalog = pt.reload(app.config["DATA_DIR"])
        stored = catalog["round_trip_probe"]
        assert stored["purpose"] == "prove the registry round-trips"
        assert stored["steps"][0]["area"] == {"$binding": "home"}
        assert stored["version"] == 1
    finally:
        from routes.library_ops import delete_library_entry
        delete_library_entry(app, "pursuit_templates", "round_trip_probe")
        pt.reload(app.config["DATA_DIR"])


def test_the_library_registry_refuses_an_unusable_entry():
    """A bad entry is written but never loaded: validation is the load gate.

    The editor is a dumb upsert (``save_registry`` never deletes), so an
    unusable entry reaches disk. What keeps it out of the simulation is the
    load-time validator, which is why the catalog reload must exclude it.
    """
    from routes.library_ops import write_library_entry
    app = _app()
    write_library_entry(app, "pursuit_templates", "bad_probe", {
        "id": "bad_probe", "version": 0, "purpose": "",
        "parameters": {}, "steps": [],
    })
    try:
        catalog = pt.reload(app.config["DATA_DIR"])
        assert "bad_probe" not in catalog
        assert any("bad_probe" in name for name, _ in pt.problems(app.config["DATA_DIR"]))
    finally:
        from routes.library_ops import delete_library_entry
        delete_library_entry(app, "pursuit_templates", "bad_probe")
        pt.reload(app.config["DATA_DIR"])


# ───────────────────── the templates are executable, not just loadable ──────

def _world():
    from app import create_app
    app = create_app({"TESTING": True})
    app.world.time_per_tick_minutes = 1
    return app, app.world, app.test_client()


def _connect(client, a, b):
    return client.post('/api/build/connect', json={
        'room1': a, 'room2': b, 'dir1': 'north', 'dir2': 'south', 'state': 'open'})


def _bg_player(world, name, area):
    from player import Player
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


def test_scout_and_report_template_runs_end_to_end():
    """The authored template is executable through the existing runner.

    ``build_plan`` reads the catalog and binds ``scout_area``/``report_area``
    from the assignment, so the steps the executor receives are the bound ones
    - a template that only loads but never runs would leave the character home.
    """
    from engine.background_plans import build_plan
    app, w, client = _world()
    client.post('/api/build/area', json={'name': 'Scout Target'})
    client.post('/api/build/area', json={'name': 'Scout Camp'})
    _connect(client, 'Scout Camp', 'Scout Target')
    p = _bg_player(w, 'Vekka', 'Scout Camp')

    plan = build_plan({
        "assignment_id": "pursuit_vekka_scout",
        "template_id": "scout-and-report",
        "label": "vekka_scout",
        "reason": "the chief wants the ridge looked at",
        "bindings": {"scout_area": "Scout Target", "report_area": "Scout Camp"},
    })
    assert plan is not None, "the authored template did not bind"
    assert plan["steps"][0]["area"] == "Scout Target"
    assert plan["steps"][1]["area"] == "Scout Camp"

    p.active_pursuit = {
        "assignment_id": "pursuit_vekka_scout",
        "template_id": "scout-and-report",
        "label": "vekka_scout",
        "reason": "the chief wants the ridge looked at",
        "bindings": {"scout_area": "Scout Target", "report_area": "Scout Camp"},
        "step_index": 0,
    }
    p.plan = plan

    for _ in range(30):
        w.tick_turn()
        if p.plan is None:
            break

    assert p.current_area == 'Scout Camp', "the scout never reported back"
    whys = [e.get("why") for e in p.lived_log]
    assert "pursuit:vekka_scout:done" in whys


def test_sleep_at_venue_template_binds_the_exact_activity_target_item():
    """The bed's opaque node id reaches ActivitySystem's target_item field.

    The background runner reads ``target_item`` when it starts an Activity; a
    similarly named ``target`` key would silently lose the bed reference.
    """
    from engine.background_plans import build_plan
    bed_id = "item_bed_1791229267206_939"
    plan = build_plan({
        "assignment_id": "pursuit_sleep",
        "template_id": "sleep-at-venue",
        "label": "sleep",
        "bindings": {"bed_id": bed_id, "venue": "Longhouse"},
    })
    assert plan is not None
    assert plan["steps"][0]["area"] == "Longhouse"
    assert plan["steps"][1]["kind"] == "activity"
    assert plan["steps"][1]["activity"] == "sleeping"
    assert plan["steps"][1]["target_item"] == bed_id


def test_sleep_pursuit_starts_activity_on_the_bound_existing_bed():
    """The live background caller reaches ActivitySystem with the bound bed id."""
    from graph import Edge, Node, EDGE_IN

    app, world, client = _world()
    client.post('/api/build/area', json={'name': 'Bed Road'})
    client.post('/api/build/area', json={'name': 'Bed Room'})
    _connect(client, 'Bed Road', 'Bed Room')
    bed_id = 'item_sleep_template_bed'
    bed = Node(
        id=bed_id, type='item', name='Four-poster bed',
        properties={'tags': ['bed', 'sleeping'], 'library_id': 'bed'},
    )
    world.graph.add_node(bed)
    world.graph.add_edge(Edge(
        source=bed_id, target=world.area_node_id('Bed Room'), type=EDGE_IN,
    ))
    p = _bg_player(world, 'Template Sleeper', 'Bed Road')
    p.active_pursuit = {
        'assignment_id': 'pursuit_template_sleep',
        'template_id': 'sleep-at-venue',
        'label': 'template_sleep',
        'reason': 'return to the bed and rest',
        'bindings': {'bed_id': bed_id, 'venue': 'Bed Room'},
        'step_index': 0,
    }

    for _ in range(8):
        world.tick_turn()
        if p.activity:
            break

    assert p.current_area == 'Bed Room'
    assert world.graph.get_node(bed_id) is bed
    assert p.activity['type'] == 'sleeping'
    assert p.activity['target_item'] == bed_id
    assert p.active_pursuit['assignment_id'] == 'pursuit_template_sleep'


def test_item_id_parameter_reads_the_named_assignment_property():
    """The binder reads ``bed_id`` as a specific graph ID, not as a tag spec."""
    instance = pt.bind("sleep-at-venue", {
        "bed_id": "item_bed_1791229267206_939",
        "venue": "Longhouse",
    })
    assert instance is not None
    assert instance["bindings"]["bed_id"] == "item_bed_1791229267206_939"
    assert instance["steps"][1]["target_item"] == "item_bed_1791229267206_939"


def test_meal_template_uses_the_existing_eating_activity():
    """The meal pursuit references the existing Activity system, not a record."""
    from engine.background_plans import build_plan
    plan = build_plan({
        "assignment_id": "pursuit_meal",
        "template_id": "meal",
        "label": "meal",
        "bindings": {"food_spec": {"tags": ["food"]}, "home": "Longhouse"},
    })
    assert plan is not None
    assert plan["steps"][0]["area"] == "Longhouse"
    assert plan["steps"][1]["kind"] == "activity"
    assert plan["steps"][1]["activity"] == "eating"
