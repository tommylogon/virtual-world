"""task-447/619: renaming a character must move every place the name is used.

A character is referenced by the players-map key, `Player.name`, the node display
name, and relationship keys (keyed by display name). `update_node {name}` only
touched the node — this op does the coordinated rename. Pinned after a live
rename of "Jake Halloway" left the roster still showing the old name.
"""
from app import create_app
from engine.nl_editor_validation import errors_only, validate_ops


def _mk(app, name):
    from routes.graph_ops import _apply_batch_op
    _apply_batch_op(app, "create_character", {"node": {"name": name}})
    return name


def _apply(app, payload):
    from routes.graph_ops import _apply_batch_op
    return _apply_batch_op(app, "rename_character", payload)


def test_rename_moves_player_key_name_node_and_relationships():
    app = create_app({"TESTING": True})
    a = _mk(app, "Jake Halloway")
    b = _mk(app, "Belne")
    pm = app.world.player_manager

    # B has a relationship keyed by A's display name (task-619 shape).
    from routes.graph_ops import _apply_batch_op
    _apply_batch_op(app, "update_player",
                    {"character": "Belne", "patch": {"relationship": {"target": a, "closeness": 5}}})
    assert a in pm.players["Belne"].relationships, "precondition: relationship keyed by old name"

    old_node_id = pm.get_player_node_id(a)
    res = _apply(app, {"character": a, "new_name": "Cullen Rutherford"})
    assert res.get("renamed") is True, res

    assert "Cullen Rutherford" in pm.players, "players key moved"
    assert a not in pm.players, "old key gone"
    assert pm.players["Cullen Rutherford"].name == "Cullen Rutherford"
    node = app.world.graph.get_node(res["node_id"])
    assert node is not None and node.name == "Cullen Rutherford", "node display name moved"
    assert res["node_id"] == old_node_id, "node id stays stable (opaque anchor)"

    rels = pm.players["Belne"].relationships
    assert "Cullen Rutherford" in rels, "relationship key re-keyed"
    assert a not in rels, "old relationship key gone"
    assert rels["Cullen Rutherford"].get("name") == "Cullen Rutherford"


def test_rename_updates_active_player():
    app = create_app({"TESTING": True})
    a = _mk(app, "Zed Prime")
    app.world.player_manager.active_player = a
    _apply(app, {"character": a, "new_name": "Zed Second"})
    assert app.world.player_manager.active_player == "Zed Second"


def test_validator_checks_rename_character():
    app = create_app({"TESTING": True})
    _mk(app, "Alpha One")
    _mk(app, "Beta Two")
    known = {"nodes": app.world.graph}

    good = {"type": "rename_character", "payload": {"character": "Alpha One", "new_name": "Gamma"}}
    assert errors_only(validate_ops([good], **known)) == []

    unknown = {"type": "rename_character", "payload": {"character": "Nobody", "new_name": "X"}}
    assert errors_only(validate_ops([unknown], **known))

    blank = {"type": "rename_character", "payload": {"character": "Alpha One", "new_name": "  "}}
    assert errors_only(validate_ops([blank], **known))

    # Display names may repeat, so a name collision is NOT a validation error;
    # the registry key uniqueness is enforced at apply time.
    collide = {"type": "rename_character", "payload": {"character": "Alpha One", "new_name": "Beta Two"}}
    assert errors_only(validate_ops([collide], **known)) == []


def test_validator_resolves_a_registry_key_that_differs_from_the_node_name():
    # After a rename the players key ("Jake Halloway") no longer matches the node
    # name ("Cullen Rutherford"); a target named by key must still validate.
    app = create_app({"TESTING": True})
    _mk(app, "Jake Halloway")
    known = {"nodes": app.world.graph, "player_keys": ["Jake Halloway"]}
    op = {"type": "rename_character", "payload": {"character": "Jake Halloway", "new_name": "Cullen Rutherford"}}
    assert errors_only(validate_ops([op], **known)) == []
