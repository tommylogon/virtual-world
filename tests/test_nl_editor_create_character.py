"""bug-527: the NL editor must create a character as a Player, not a bare node.

`create_character` is the batch op the editor stages for `create_node {kind:
character}`. It must register a Player (minting the canonical `player_<name>`
node the rest of the engine reads) — a bare `character_*` node is rejected as an
unregistered player. This pins both the apply path and the validator's knowledge
of the op.
"""
from app import create_app
from engine.nl_editor_validation import errors_only, validate_ops


def _op(name="Test Char", nid="player_Test_Char", props=None):
    return {
        "type": "create_character",
        "payload": {"node": {"id": nid, "type": "character", "name": name,
                             "properties": props or {}}},
    }


def test_create_character_registers_a_player_and_mints_the_canonical_node():
    app = create_app({"TESTING": True})
    res = _apply_batch_op_safe(app, "create_character", _op()["payload"])

    assert res.get("id") == "player_Test_Char", res
    assert "Test Char" in app.world.players, "a Player must be registered"

    node = app.world.graph.get_node("player_Test_Char")
    assert node is not None, "the canonical player_<name> node must exist"
    assert node.type == "character"
    # No bare character_* node is minted.
    assert app.world.graph.get_node("character_Test_Char") is None


def test_create_character_writes_authored_prose_onto_the_node():
    app = create_app({"TESTING": True})
    _apply_batch_op_safe(app, "create_character", _op(props={
        "personality": "sharp-eyed", "description": "a probe"})["payload"])

    node = app.world.graph.get_node("player_Test_Char")
    assert node.properties.get("personality") == "sharp-eyed"
    assert node.properties.get("description") == "a probe"


def test_validator_accepts_create_character_and_flags_a_duplicate():
    app = create_app({"TESTING": True})
    known = {"nodes": app.world.graph}

    assert errors_only(validate_ops([_op()], **known)) == [], "a fresh character is valid"

    _apply_batch_op_safe(app, "create_character", _op()["payload"])
    dup = errors_only(validate_ops([_op()], **known))
    assert dup, "the same player_<name> id a second time must be an error"


def _apply_batch_op_safe(app, optype, payload):
    # Imported here so the module still imports if the route moves.
    from routes.graph_ops import _apply_batch_op
    return _apply_batch_op(app, optype, payload)
