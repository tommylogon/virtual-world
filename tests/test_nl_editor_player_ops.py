"""task-738: the NL editor can stage Player-state ops (memories/relationships/emotion).

These are NOT graph edges, so `attach` cannot carry them. `update_player` writes
to the `Player` (memories list, relationships dict, emotion pulses). This pins
the apply path and the validator's rules for the op.
"""
from app import create_app
from engine.nl_editor_validation import errors_only, validate_ops


def _make_character(app, name="Test Char"):
    from routes.graph_ops import _apply_batch_op
    _apply_batch_op(app, "create_character", {"node": {"name": name}})
    return app.world.players[name]


def _apply(app, payload):
    from routes.graph_ops import _apply_batch_op
    return _apply_batch_op(app, "update_player", payload)


def _player_op(character, patch):
    return {"type": "update_player", "payload": {"character": character, "patch": patch}}


def test_update_player_appends_a_memory():
    app = create_app({"TESTING": True})
    player = _make_character(app, "Memo Probe")

    res = _apply(app, {"character": "Memo Probe",
                       "patch": {"memories": [{"text": "saw a red door", "importance": 7}]}})

    assert res.get("applied", {}).get("memories") == 1, res
    texts = [m.get("text") for m in player.memories]
    assert "saw a red door" in texts


def test_update_player_adjusts_and_removes_a_relationship():
    app = create_app({"TESTING": True})
    player = _make_character(app, "Rel Probe")

    res = _apply(app, {"character": "Rel Probe",
                       "patch": {"relationship": {"target": "Belne", "closeness": 5}}})
    assert res.get("applied", {}).get("relationship"), res
    recs = list(player.relationships.values())
    assert recs and recs[0].get("closeness") == 5, player.relationships

    res2 = _apply(app, {"character": "Rel Probe",
                        "patch": {"remove_relationship": "Belne"}})
    assert res2.get("applied", {}).get("removed_relationship") == "Belne", res2
    assert not player.relationships, "the relationship must be gone"


def test_update_player_spikes_an_emotion():
    app = create_app({"TESTING": True})
    player = _make_character(app, "Emo Probe")
    before = dict(player.emotions_map())
    dim = next(iter(before))  # a real baseline dimension

    res = _apply(app, {"character": "Emo Probe",
                       "patch": {"emotion": {"name": dim, "delta": 3}}})
    assert res.get("applied", {}).get("emotion") == dim, res
    assert player.emotions_map()[dim] != before[dim], "the pulse must change the dimension"


def test_update_player_sets_behaviours():
    app = create_app({"TESTING": True})
    player = _make_character(app, "Beh Probe")
    behaviours = [{"trigger": "on_tick", "interval": 2,
                   "actions": [{"type": "message", "text": "paces"}]}]

    res = _apply(app, {"character": "Beh Probe", "patch": {"behaviors": behaviours}})
    assert res.get("applied", {}).get("behaviors") == 1, res
    assert player.behaviors == behaviours


def test_validator_checks_the_behaviours_shape():
    app = create_app({"TESTING": True})
    _make_character(app, "Beh Valid")
    known = _known = {"nodes": app.world.graph}

    good = _player_op("Beh Valid", {"behaviors": [
        {"trigger": "on_tick", "actions": [{"type": "message", "text": "x"}]}]})
    assert errors_only(validate_ops([good], **known)) == []

    # not a list
    assert errors_only(validate_ops([_player_op("Beh Valid", {"behaviors": {"a": 1}})], **known))
    # entry with no actions
    assert errors_only(validate_ops([_player_op("Beh Valid", {"behaviors": [{"trigger": "on_tick"}]})], **known))
    # action with no type
    assert errors_only(validate_ops([_player_op("Beh Valid", {"behaviors": [{"actions": [{"text": "x"}]}]})], **known))


def test_validator_rejects_dead_behaviour_vocabulary():
    """task-739: a behaviour authored in the node/item trigger vocabulary, or with
    keys the engine never reads, must be refused — it would stage but never fire."""
    app = create_app({"TESTING": True})
    _make_character(app, "Beh Vocab")
    known = {"nodes": app.world.graph}

    def errs(behaviours):
        return bool(errors_only(validate_ops(
            [_player_op("Beh Vocab", {"behaviors": behaviours})], **known)))

    # node/item triggers the behaviour runner never receives
    assert errs([{"trigger": "on_take", "actions": [{"type": "message", "text": "x"}]}])
    assert errs([{"trigger": "on_night", "actions": [{"type": "message", "text": "x"}]}])
    # adjust_vital with the wrong keys (vital/delta instead of stat/amount)
    assert errs([{"trigger": "on_tick",
                  "actions": [{"type": "adjust_vital", "vital": "Thirst", "delta": 5}]}])
    # vital_below with no stat — silently defaults to HP
    assert errs([{"trigger": "on_tick",
                  "actions": [{"type": "message", "text": "x"}],
                  "conditions": [{"type": "vital_below", "value": 40}]}])
    # spawn_character with template instead of character_id
    assert errs([{"trigger": "on_tick",
                  "actions": [{"type": "spawn_character", "template": "worg"}]}])
    # a typo'd action type
    assert errs([{"trigger": "on_tick", "actions": [{"type": "explode"}]}])

    # the corrected shape is valid
    ok = [
        {"trigger": "on_item_taken",
         "conditions": [{"type": "target_has_tag", "value": ["meat"]}],
         "actions": [
             {"type": "message", "text": "snarls"},
             {"type": "damage", "amount": 8, "target": "player"},
             {"type": "add_tag", "tag": "hostile"},
         ]},
        {"trigger": "on_tick",
         "conditions": [{"type": "vital_below", "stat": "Thirst", "value": 40, "operator": "lt"}],
         "actions": [
             {"type": "go", "area": "Raven River"},
             {"type": "adjust_vital", "stat": "Thirst", "amount": 50},
         ]},
    ]
    assert errors_only(validate_ops(
        [_player_op("Beh Vocab", {"behaviors": ok})], **known)) == []


def test_update_player_rejects_an_unknown_character():
    app = create_app({"TESTING": True})
    res = _apply(app, {"character": "Nobody Here", "patch": {"emotion": {"name": "joy", "delta": 1}}})
    assert "error" in res, res


def test_validator_accepts_a_good_player_op_and_flags_bad_ones():
    app = create_app({"TESTING": True})
    _make_character(app, "Valid Probe")
    known = {"nodes": app.world.graph}

    good = [_player_op("Valid Probe", {"emotion": {"name": "afraid", "delta": 2}})]
    assert errors_only(validate_ops(good, **known)) == [], "a well-formed op is valid"

    # unknown character
    assert errors_only(validate_ops([_player_op("Ghost", {"emotion": {"name": "afraid"}})], **known))
    # unknown patch key
    assert errors_only(validate_ops([_player_op("Valid Probe", {"nonsense": 1})], **known))
    # memory with no text
    assert errors_only(validate_ops([_player_op("Valid Probe", {"memories": [{"importance": 3}]})], **known))
    # relationship with no target
    assert errors_only(validate_ops([_player_op("Valid Probe", {"relationship": {"closeness": 2}})], **known))
    # non-numeric closeness
    assert errors_only(validate_ops([_player_op("Valid Probe", {"relationship": {"target": "Belne", "closeness": "a lot"}})], **known))
    # unknown emotion dimension (silently ignored by spike -> a no-op)
    assert errors_only(validate_ops([_player_op("Valid Probe", {"emotion": {"name": "not_a_dim"}})], **known))
    # empty patch
    assert errors_only(validate_ops([_player_op("Valid Probe", {})], **known))


def test_update_player_sets_schedule():
    app = create_app({"TESTING": True})
    player = _make_character(app, "Sched Probe")

    res = _apply(app, {"character": "Sched Probe",
                       "patch": {"schedule": [
                           {"start": "07:00", "activity": "work", "area": "Workshop", "fallback": "wait"},
                           {"start": "18:00", "activity": "sleep", "area": "Bedroom", "fallback": "rest"},
                       ]}})
    assert res.get("applied", {}).get("schedule") == 2, res
    assert len(player.schedule) == 2
    assert player.schedule[0]["start"] == 420  # 07:00 in minutes
    assert player.schedule[0]["activity"] == "work"
    assert player.schedule[0]["area"] == "Workshop"
    assert player.schedule[1]["start"] == 1080  # 18:00 in minutes
    assert player.schedule[1]["activity"] == "sleep"


def test_update_player_sets_goals():
    app = create_app({"TESTING": True})
    player = _make_character(app, "Goal Probe")

    res = _apply(app, {"character": "Goal Probe",
                       "patch": {"goals": [
                           {"what": "Become chief", "status": "active",
                            "motivation": "I want respect", "intention": "Power"},
                           {"what": "Find the key", "status": "proposed"},
                       ]}})
    assert res.get("applied", {}).get("goals") == 2, res
    assert len(player.goals) == 2
    chief = player.goals[0]
    assert chief["id"] == "become_chief"
    assert chief["what"] == "Become chief"
    assert chief["status"] == "active"
    assert chief["motivation"] == "I want respect"
    assert chief["intention"] == "Power"
    find_key = player.goals[1]
    assert find_key["id"] == "find_the_key"
    assert find_key["what"] == "Find the key"
    assert find_key["status"] == "proposed"


def test_update_player_sets_obligations():
    app = create_app({"TESTING": True})
    player = _make_character(app, "Oblig Probe")

    res = _apply(app, {"character": "Oblig Probe",
                       "patch": {"obligations": [
                           {"charge": "Guard the gate", "from": "Chief", "due": 1000,
                            "status": "offered", "reward": "a coin"},
                           {"charge": "Deliver the letter", "status": "accepted"},
                       ]}})
    assert res.get("applied", {}).get("obligations") == 2, res
    assert len(player.obligations) == 2
    gate = player.obligations[0]
    assert gate["id"] == "guard_the_gate"
    assert gate["charge"] == "Guard the gate"
    assert gate["from"] == "Chief"
    assert gate["due"] == 1000
    assert gate["status"] == "offered"
    assert gate["reward"] == "a coin"
    letter = player.obligations[1]
    assert letter["id"] == "deliver_the_letter"
    assert letter["charge"] == "Deliver the letter"
    assert letter["status"] == "accepted"


def test_validator_schedule_rejects_bad_steps():
    app = create_app({"TESTING": True})
    _make_character(app, "Sched Valid")
    known = {"nodes": app.world.graph}

    # valid schedule
    good = [_player_op("Sched Valid", {"schedule": [
        {"start": "07:00", "activity": "work", "area": "Workshop"},
    ]})]
    assert errors_only(validate_ops(good, **known)) == []

    # no start time -> flagged as error by validator
    bad_start = [_player_op("Sched Valid", {"schedule": [
        {"activity": "work"},  # no start
    ]})]
    assert errors_only(validate_ops(bad_start, **known))

    # unknown activity -> normalized to wait, still valid
    bad_act = [_player_op("Sched Valid", {"schedule": [
        {"start": "07:00", "activity": "dance"},
    ]})]
    assert errors_only(validate_ops(bad_act, **known)) == []

    # start out of range -> error
    bad_range = [_player_op("Sched Valid", {"schedule": [
        {"start": "25:00", "activity": "work"},
    ]})]
    assert errors_only(validate_ops(bad_range, **known))


def test_validator_goals_rejects_bad_entries():
    app = create_app({"TESTING": True})
    _make_character(app, "Goal Valid")
    known = {"nodes": app.world.graph}

    # valid goals
    good = [_player_op("Goal Valid", {"goals": [
        {"what": "Become chief", "status": "active", "motivation": "Power", "intention": "Respect"},
    ]})]
    assert errors_only(validate_ops(good, **known)) == []

    # missing what -> flagged as error by validator
    no_what = [_player_op("Goal Valid", {"goals": [
        {"status": "active"},
    ]})]
    assert errors_only(validate_ops(no_what, **known))

    # unknown status -> flagged as error by validator
    bad_status = [_player_op("Goal Valid", {"goals": [
        {"what": "Test", "status": "not_a_status"},
    ]})]
    assert errors_only(validate_ops(bad_status, **known))


def test_validator_obligations_rejects_bad_entries():
    app = create_app({"TESTING": True})
    _make_character(app, "Oblig Valid")
    known = {"nodes": app.world.graph}

    # valid obligations
    good = [_player_op("Oblig Valid", {"obligations": [
        {"charge": "Guard the gate", "from": "Chief", "due": 1000},
    ]})]
    assert errors_only(validate_ops(good, **known)) == []

    # missing charge -> flagged as error by validator
    no_charge = [_player_op("Oblig Valid", {"obligations": [
        {"status": "offered"},
    ]})]
    assert errors_only(validate_ops(no_charge, **known))

    # unknown status -> flagged as error by validator
    bad_status = [_player_op("Oblig Valid", {"obligations": [
        {"charge": "Test", "status": "not_a_status"},
    ]})]
    assert errors_only(validate_ops(bad_status, **known))


def test_update_player_rejects_derived_mosiac_fields():
    app = create_app({"TESTING": True})
    player = _make_character(app, "Derived Probe")

    # MOSIAC scores are derived projections, not authored state
    res = _apply(app, {"character": "Derived Probe",
                       "patch": {"mosiac": {"M": "hostile"}}})
    assert "error" in res or res.get("applied", {}).get("mosiac") is None, res


def test_update_player_rejects_derived_goal_progress():
    app = create_app({"TESTING": True})
    player = _make_character(app, "Derived Goal Probe")

    # goal progress is derived, not authored
    res = _apply(app, {"character": "Derived Goal Probe",
                       "patch": {"goal_log": [{"goal_id": "x", "status": "reached"}]}})
    assert "error" in res or res.get("applied", {}).get("goal_log") is None, res
