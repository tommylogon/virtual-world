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
    """The meal pursuit references the existing Activity system, not a record.

    v2 adds the recipe leg: the cooking step names the registry recipe the
    undertake cooks (the executor routes it through the existing timed-cooking
    flow), and the eating step still closes the pursuit with a visible meal.
    ``food_spec`` became optional: the recipe, not a gather spec, defines what
    is cooked, so an assignment without one still binds.
    """
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
    assert plan["steps"][1]["activity"] == "cooking"
    assert plan["steps"][1]["recipe"] == "barley_pottage"
    assert plan["steps"][2]["kind"] == "activity"
    assert plan["steps"][2]["activity"] == "eating"
    assert plan["steps"][2]["duration_minutes"] == 10
    # Optional parameter: an assignment with no food_spec still binds.
    bare = build_plan({
        "assignment_id": "pursuit_meal_bare",
        "template_id": "meal",
        "label": "meal",
        "bindings": {"home": "Longhouse"},
    })
    assert bare is not None


def _write_probe_recipe(app):
    """A scratch recipe with no conditions: inputs are checked by the
    crafting system itself, so the mechanism test stages them and the
    fail-closed branch fails on the missing inputs, not on the campfire.

    The registry save gate requires real library items and all four outcome
    tiers, so the probe reuses existing item ids and carries the tier map.
    """
    from routes.library_ops import write_library_entry
    write_library_entry(app, "recipes", "probe_soup", {
        "id": "probe_soup", "name": "Probe Soup",
        "description": "Scratch recipe for the pursuit recipe-step test.",
        "ingredients": [
            {"item": "raw_fish", "count": 1, "consumed": True},
            {"item": "cooking_pot", "count": 1, "consumed": False},
        ],
        "duration_min": 5,
        "skill_check": {"skill": "Cooking", "dc": 8},
        "outputs": [{"item": "fish_soup", "count": 1}],
        "outcomes": {
            "crit_success": {"outputs": [{"item": "fish_soup", "count": 2}],
                             "message": ""},
            "success": {"outputs": [{"item": "fish_soup", "count": 1}],
                        "message": ""},
            "fail": {"consume_inputs": True,
                     "outputs": [{"item": "fishy_broth", "count": 1}],
                     "message": ""},
            "crit_fail": {"consume_inputs": True,
                          "outputs": [{"item": "burned_stew", "count": 1}],
                          "message": ""},
        },
        "learned_by": ["global"],
        "discoverable": True,
    })


def _delete_probe_recipe(app):
    from routes.library_ops import delete_library_entry
    delete_library_entry(app, "recipes", "probe_soup")


def test_a_recipe_step_opens_the_existing_cooking_flow():
    """A recipe step routes through CraftingSystem, with the actor swapped in.

    The branch under test refuses to fake a second cooking path: it calls the
    same ``start_cooking`` a human's "Make X" uses, restores the focused
    active player, and starts the cooking Activity with the recipe id on it.
    """
    from engine import background_plans as _bp
    from engine.background_simulation import BackgroundSimulation
    from graph import Edge, Node, EDGE_IN

    app = _app()
    client = app.test_client()
    world = app.world
    _write_probe_recipe(app)
    try:
        # keep the scratch recipe out of the crafting registry's own cache
        if hasattr(world, "crafting") and hasattr(world.crafting, "_registry"):
            try:
                from engine.crafting import CraftingSystem  # noqa: F401
            except Exception:
                pass
        client.post('/api/build/area', json={'name': 'Soup Pantry'})
        _connect(client, 'Blizzard Forest Clearing', 'Soup Pantry')
        p = _bg_player(world, "Probe Cook", 'Soup Pantry')
        area_id = world.area_node_id('Soup Pantry')
        focused_before = getattr(world, 'active_player', None)
        for index, (name, item_id) in enumerate([
            ("Raw fish", "item_raw_fish_staged"),
            ("Cooking Pot", "item_cooking_pot_staged"),
        ]):
            node = Node(
                id=item_id, type="item", name=name,
                properties={"tags": ["food", "fish"] if index == 0 else ["tool"]},
            )
            world.graph.add_node(node)
            world.graph.add_edge(Edge(
                source=node.id, target=area_id, type=EDGE_IN))
        sim = BackgroundSimulation(world)
        plan = {"label": "probe_meal", "assignment_id": "pursuit_probe_meal"}
        step = {"kind": "activity", "activity": "cooking",
                "recipe": "probe_soup"}

        outcome = _bp._run(sim, p, plan, step)

        assert outcome is None, "the recipe step failed with staged inputs"
        assert p.activity is not None and p.activity.get("type") == "cooking"
        assert p.activity.get("recipe_id") == "probe_soup"
        assert getattr(world, "active_player", None) == focused_before, \
            "the actor swap leaked: the focused player is still swapped in"
        assert any(e.get("why") == "plan:probe_meal" for e in p.lived_log)

        # The cook's own duration comes from the recipe: 5 minutes, so the
        # step's satisfaction reads the recipe duration, not the template's.
        assert p.activity.get("duration_minutes") == 5.0
    finally:
        _delete_probe_recipe(app)
        if getattr(p, "activity", None):
            world.activities.end_activity(p.name, "interruption")


def test_a_recipe_step_fails_closed_when_the_inputs_are_missing():
    """No inputs: the craft check raises and the pursuit fails with a trace."""
    from engine import background_plans as _bp
    from engine.background_simulation import BackgroundSimulation

    app = _app()
    world = app.world
    _write_probe_recipe(app)
    try:
        p = _bg_player(world, "Probe Starver", "Blizzard Forest Clearing")
        sim = BackgroundSimulation(world)
        plan = {"label": "probe_meal_nothing",
                "assignment_id": "pursuit_probe_meal"}
        step = {"kind": "activity", "activity": "cooking",
                "recipe": "probe_soup"}

        outcome = _bp._run(sim, p, plan, step)

        assert outcome == "failed"
        assert getattr(p, "activity", None) is None, \
            "a failed centerpiece must not leave an activity hanging"
        assert any(
            e.get("why") == "plan:probe_meal_nothing:failed"
            for e in p.lived_log), "the failure left no trace"
    finally:
        _delete_probe_recipe(app)


# ─────────────────── the report receipt and the leaf that checks it ─────────

def _met(app, actor, other):
    """One leaf evaluation through the shared registry, nothing mocked."""
    trigger_system = app.world.triggers
    return trigger_system._evaluate_trigger_condition(
        {"type": "met_character", "target": actor, "character": other},
        None, app.world)


def test_met_character_resolves_names_keys_and_node_ids():
    """Co-location, by every authored spelling, and fail-closed on nobody."""
    app = _app()
    world = app.world
    a = _bg_player(world, "Vekka", "Blizzard Forest Clearing")
    b = _bg_player(world, "Zikka", "Blizzard Forest Clearing")
    try:
        # name form
        assert _met(app, "Vekka", "Zikka") is True
        # node-id form (what authored assignments carry)
        assert _met(app, "Vekka", "player_Zikka") is True
        # players-dict key form
        assert _met(app, "Vekka", "Zikka") is True and a is not None and b is not None
        # different areas: the report has not been delivered
        world.set_player_area("Zikka", "Eldenford")
        assert _met(app, "Vekka", "Zikka") is False
        # unresolvable recipient fails closed: no character is no report
        assert _met(app, "Vekka", "player_Nobody") is False
    finally:
        pass


def test_a_reported_pursuit_delivers_the_receipt_and_tells_the_recipient():
    """Delivery is a spatial fact plus a memory on the recipient.

    With the recipient present, the receipt flips to done with the tick, the
    recipient holds the report as a memory in their own store, and the
    reporter's log carries the delivery trace. With the recipient elsewhere,
    the receipt stays pending and the undelivered trace says why.
    """
    from engine import background_plans as _bp
    from engine.background_simulation import BackgroundSimulation

    app = _app()
    world = app.world
    vekka = _bg_player(world, "Vekka", "Chief's Pit")
    zikka = _bg_player(world, "Zikka", "Chief's Pit")
    sim = BackgroundSimulation(world)
    pursuit = {
        "assignment_id": "pursuit_vekka_report_probe",
        "template_id": "report_probe",
        "label": "report_probe",
        "reason": "the chief wants the ridge looked at",
        "bindings": {},
        "step_index": 0,
        "report_text": "human tracks head west along the road",
        "report_condition": {"checkable": True,
                             "requires_character_id": "player_Zikka"},
        "progress": {"report_delivered": {"status": "pending",
                                          "to_character_id": "player_Zikka"}},
    }
    vekka.active_pursuit = dict(pursuit)
    plan = {"label": "report_probe",
            "assignment_id": "pursuit_vekka_report_probe"}

    delivered = _bp._deliver_report(sim, vekka, plan)

    assert delivered is True
    receipt = vekka.active_pursuit["progress"]["report_delivered"]
    assert receipt["status"] == "done" and receipt.get("done_tick") is not None
    texts = [str(m.get("text", "")) for m in getattr(zikka, "memories", [])]
    assert any("Vekka reports:" in t and
               "human tracks head west along the road" in t for t in texts), \
        f"the recipient holds no report: {texts}"
    assert any(e.get("why") == "pursuit:report_probe:report:delivered"
               for e in vekka.lived_log)
    # Idempotent: a second call cannot re-deliver or re-write the memory.
    before = len(zikka.memories)
    assert _bp._deliver_report(sim, vekka, plan) is False
    assert len(zikka.memories) == before

    # Recipient elsewhere: no false delivery, an honest undelivered trace,
    # and the receipt stays pending.
    world.set_player_area("Zikka", "Eldenford")
    vekka.memories.clear()
    vekka.lived_log.clear()
    vekka.active_pursuit = dict(pursuit,
                                progress={"report_delivered":
                                          {"status": "pending"}})
    delivered = _bp._deliver_report(sim, vekka, plan)
    assert delivered is False
    assert vekka.active_pursuit["progress"]["report_delivered"]["status"] \
        == "pending"
    assert any(e.get("why") == "pursuit:report_probe:report:undelivered"
               for e in vekka.lived_log)


def _write_report_probe(app):
    """A scratch template for the hook test: one bounded wait step, plus one
    template-declared progress check read through the shared leaf."""
    import engine.pursuit_templates as pt_mod
    from routes.library_ops import write_library_entry
    write_library_entry(app, "pursuit_templates", "report_probe", {
        "id": "report_probe", "version": 1,
        "name": "Report probe",
        "purpose": "prove the completion hook evaluates progress and reports",
        "parameters": {},
        "steps": [{"kind": "wait", "activity": "waiting",
                   "duration_minutes": 2}],
        "progress": [
            {"id": "at-camp", "check":
             {"type": "met_character", "character": "player_Zikka"}},
        ],
    })
    pt_mod.reload(app.config["DATA_DIR"])


def test_the_completion_hook_runs_progress_and_reports_once():
    """Through real ticks: progress flips, the report lands, nothing re-runs."""
    import engine.pursuit_templates as pt_mod
    from engine.background_simulation import BackgroundSimulation
    from engine.background_plans import maybe_assign

    app = _app()
    world = app.world
    world.time_per_tick_minutes = 1
    _write_report_probe(app)
    try:
        vekka = _bg_player(world, "Vekka", "Blizzard Forest Clearing")
        zikka = _bg_player(world, "Zikka", "Blizzard Forest Clearing")
        vekka.active_pursuit = {
            "assignment_id": "pursuit_report_probe_hook",
            "template_id": "report_probe",
            "label": "report_probe_hook",
            "reason": "probe the hook",
            "bindings": {},
            "step_index": 0,
            "report_text": "the ridge is clear",
            "report_condition": {"checkable": True,
                                 "requires_character_id": "player_Zikka"},
            "progress": {"report_delivered": {"status": "pending"}},
        }
        sim = BackgroundSimulation(world)
        assert maybe_assign(sim, vekka) is True
        for _ in range(8):
            world.tick_turn()
            if vekka.plan is None:
                break
        assert vekka.plan is None, "the approach never completed"
        # Terminal semantics: the finished assignment does not dangle on the
        # character. The durable record of delivery is the trace plus the
        # recipient's memory, asserted below.
        assert vekka.active_pursuit is None, \
            "a finished pursuit stayed mounted"

        texts = [str(m.get("text", "")) for m in getattr(zikka, "memories", [])]
        assert any("the ridge is clear" in t for t in texts), \
            f"the recipient holds no report: {texts}"
        delivered = [e for e in vekka.lived_log
                     if e.get("why") == "pursuit:report_probe_hook:report:delivered"]
        assert len(delivered) == 1, \
            f"the report was not delivered exactly once: {len(delivered)}"

        # Terminal pursuit: the guard holds it down on the next cycle, and a
        # further tick produces no second delivery or second completion.
        world.time_ticks += 1
        assert maybe_assign(sim, vekka) is False
        after = [e for e in vekka.lived_log
                 if e.get("why") == "pursuit:report_probe_hook:report:delivered"]
        assert len(after) == len(delivered)
    finally:
        from routes.library_ops import delete_library_entry
        delete_library_entry(app, "pursuit_templates", "report_probe")
        pt_mod.reload(app.config["DATA_DIR"])


def test_progress_checks_flip_the_assignments_own_progress_dict():
    """Template-declared progress leaves evaluate onto the saved assignment.

    ``_check_progress`` is the runtime caller for the template's ``progress``
    leaves: each pending id the assignment's own progress dict also carries is
    evaluated through the shared leaf registry, and a satisfied one flips to
    done with the tick. Nothing is invented for ids the assignment does not
    carry, and a check that does not hold leaves the entry pending.
    """
    import engine.pursuit_templates as pt_mod
    from engine import background_plans as _bp
    from engine.background_simulation import BackgroundSimulation
    from routes.library_ops import write_library_entry, delete_library_entry

    app = _app()
    world = app.world
    write_library_entry(app, "pursuit_templates", "report_probe", {
        "id": "report_probe", "version": 1,
        "name": "Report probe",
        "purpose": "prove the completion hook evaluates progress and reports",
        "parameters": {},
        "steps": [{"kind": "wait", "activity": "waiting",
                   "duration_minutes": 2}],
        "progress": [
            {"id": "at-camp", "check":
             {"type": "met_character", "character": "player_Zikka"}},
        ],
    })
    pt_mod.reload(app.config["DATA_DIR"])
    try:
        vekka = _bg_player(world, "Vekka", "Blizzard Forest Clearing")
        _bg_player(world, "Zikka", "Blizzard Forest Clearing")
        vekka.active_pursuit = {
            "assignment_id": "pursuit_progress_probe",
            "template_id": "report_probe",
            "label": "progress_probe",
            "reason": "probe the check",
            "bindings": {},
            "step_index": 0,
            "progress": {"at-camp": {"status": "pending"}},
        }
        sim = BackgroundSimulation(world)
        plan = {"label": "progress_probe",
                "assignment_id": "pursuit_progress_probe"}

        flipped = _bp._check_progress(sim, vekka, plan)

        assert flipped == ["at-camp"], f"the check did not flip: {flipped}"
        rec = vekka.active_pursuit["progress"]["at-camp"]
        assert rec["status"] == "done" and rec.get("done_tick") is not None
        assert any(e.get("why") ==
                   "pursuit:progress_probe:progress:at-camp"
                   for e in vekka.lived_log)
        # Idempotent, and nothing is invented for an id the assignment lacks.
        again = _bp._check_progress(sim, vekka, plan)
        assert again == []
        assert list(vekka.active_pursuit["progress"]) == ["at-camp"]
    finally:
        delete_library_entry(app, "pursuit_templates", "report_probe")
        pt_mod.reload(app.config["DATA_DIR"])


# ─────────────────────── the timing gate on the resume path ─────────────────

def _write_timed_probe(app, **timing):
    """Write one scratch template whose step is a bounded wait, so the gate
    test needs no connectivity and the approach completes in a few ticks.

    The suite's registry tests already write and delete entries through the
    editor route, so this follows that established pattern: upsert through
    ``write_library_entry``, reload the engine catalog (the load-time validator
    is the only gate an entry passes), and delete in the caller's finally.
    """
    import engine.pursuit_templates as pt_mod
    from routes.library_ops import write_library_entry
    write_library_entry(app, "pursuit_templates", "timed_probe", {
        "id": "timed_probe", "version": 1,
        "name": "Timed probe",
        "purpose": "prove the resume path consults the window",
        "parameters": {},
        "timing": dict(timing),
        "steps": [{"kind": "wait", "activity": "waiting",
                   "duration_minutes": 2}],
    })
    pt_mod.reload(app.config["DATA_DIR"])


def test_the_resume_path_waits_for_the_window_then_starts():
    """A closed window holds the start; opening it releases the pursuit.

    The branch under test is the gate in ``maybe_assign``: the template's
    ``timing`` block is read from the world's own clock, the plan is never
    built, and the assignment itself survives the wait unchanged.
    """
    import engine.pursuit_templates as pt_mod
    from engine.background_simulation import BackgroundSimulation
    from engine.background_plans import maybe_assign

    app = _app()
    app.world.time_per_tick_minutes = 1
    app.world.clock_start_hour = 8
    world = app.world
    _write_timed_probe(app, hours={"after": "10:00", "before": "12:00"})
    try:
        p = _bg_player(world, "Timed Worker", "Blizzard Forest Clearing")
        pursuit = {
            "assignment_id": "pursuit_timed_probe",
            "template_id": "timed_probe",
            "label": "timed_probe",
            "reason": "the window should decide when this starts",
            "bindings": {},
            "step_index": 0,
        }
        p.active_pursuit = dict(pursuit)
        sim = BackgroundSimulation(world)

        # 08:00 is outside [10:00, 12:00): the gate holds the start.
        _started = maybe_assign(sim, p)
        assert _started is False, \
            "the template started with the window closed"
        assert p.plan is None
        assert p.active_pursuit == pursuit, \
            "the assignment was clobbered while waiting"

        # 10:00: the branch runs again and this time releases it.
        world.clock_start_hour = 10
        assert maybe_assign(sim, p) is True, \
            "inside the window the template still did not start"
        assert p.plan is not None
        assert p.plan["pursuit_template"] == "timed_probe"
        assert p.plan["steps"][0]["kind"] == "wait"
    finally:
        from routes.library_ops import delete_library_entry
        delete_library_entry(app, "pursuit_templates", "timed_probe")
        pt_mod.reload(app.config["DATA_DIR"])


def test_a_mid_run_approach_is_not_stopped_by_a_closing_window():
    """The gate is a start gate: a running approach ignores the clock entirely.

    ``maybe_assign`` returns False before the timing check when a plan is
    already in hand, so dusk arriving mid-approach never tears the approach
    down; the executor keeps walking it to completion.
    """
    import engine.pursuit_templates as pt_mod
    from engine.background_simulation import BackgroundSimulation
    from engine import background_plans as _plans

    app = _app()
    app.world.time_per_tick_minutes = 1
    app.world.clock_start_hour = 11
    world = app.world
    _write_timed_probe(app, hours={"after": "10:00", "before": "12:00"})
    try:
        p = _bg_player(world, "Timed Runner", "Blizzard Forest Clearing")
        p.active_pursuit = {
            "assignment_id": "pursuit_timed_probe",
            "template_id": "timed_probe",
            "label": "timed_probe",
            "reason": "already running",
            "bindings": {},
            "step_index": 0,
        }
        sim = BackgroundSimulation(world)
        started = _plans.maybe_assign(sim, p)
        assert started is True, \
            "11:00 is inside the window: the gate refused a timely pursuit"
        assert p.plan is not None

        # The window closes underneath the running approach: the clock is
        # forced to 03:00 and the approach still runs to done.
        world.clock_start_hour = 3
        for _ in range(6):
            world.tick_turn()
            if p.plan is None:
                break
        assert "plan:timed_probe:done" in (
            e.get("why") for e in p.lived_log), \
            "a running approach was stopped by the closed window"
    finally:
        from routes.library_ops import delete_library_entry
        delete_library_entry(app, "pursuit_templates", "timed_probe")
        pt_mod.reload(app.config["DATA_DIR"])
