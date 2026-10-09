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
