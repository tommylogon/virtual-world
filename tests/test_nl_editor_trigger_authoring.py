"""task-739: the NL editor must validate logic_trigger logic against the engine vocab.

The editor can already mint an empty `logic_trigger` node; create_node/update_node
must reject logic the engine would silently ignore — an unknown trigger_type, an
effect type outside EFFECT_TYPES, or a malformed condition tree.
"""
from app import create_app
from engine.nl_editor_validation import errors_only, validate_ops


def _create_trigger(props=None, nid="logic_trigger_probe"):
    return {
        "type": "create_node",
        "payload": {"node": {"id": nid, "type": "logic_trigger", "name": "Probe",
                             "properties": props or {}}},
    }


def _known(app):
    return {"nodes": app.world.graph}


def test_a_well_formed_trigger_is_valid():
    app = create_app({"TESTING": True})
    op = _create_trigger({
        "trigger_type": "on_use",
        "effects": [{"type": "message", "params": {"text": "click"}}],
        "conditions": {"operator": "and", "conditions": [{"type": "has_tag", "tag": "goblin"}]},
    })
    assert errors_only(validate_ops([op], **_known(app))) == []


def test_unknown_trigger_type_is_an_error():
    app = create_app({"TESTING": True})
    op = _create_trigger({"trigger_type": "on_sneeze"})
    issues = errors_only(validate_ops([op], **_known(app)))
    assert issues and "trigger_type" in issues[0]["message"], issues


def test_unknown_effect_type_is_an_error():
    app = create_app({"TESTING": True})
    op = _create_trigger({"trigger_type": "on_use",
                          "effects": [{"type": "explode_the_world", "params": {}}]})
    issues = errors_only(validate_ops([op], **_known(app)))
    assert issues and "effect type" in issues[0]["message"], issues


def test_malformed_condition_tree_is_an_error():
    app = create_app({"TESTING": True})
    op = _create_trigger({"trigger_type": "on_use",
                          "conditions": {"operator": "xor", "conditions": [{"type": "has_tag"}]}})
    issues = errors_only(validate_ops([op], **_known(app)))
    assert issues and "operator" in issues[0]["message"], issues

    op2 = _create_trigger({"trigger_type": "on_use", "conditions": {"bogus": True}},
                          nid="logic_trigger_probe2")
    issues2 = errors_only(validate_ops([op2], **_known(app)))
    assert issues2, "a condition node with no operator and no type must be flagged"


def test_updating_a_logic_trigger_validates_its_patch():
    app = create_app({"TESTING": True})
    # materialise a trigger node first
    from routes.graph_ops import _apply_batch_op
    _apply_batch_op(app, "create_node", _create_trigger({"trigger_type": "on_use"})["payload"])

    good = {"type": "update_node",
            "payload": {"node_id": "logic_trigger_probe",
                        "patch": {"effects": [{"type": "damage", "params": {"amount": 3}}]}}}
    assert errors_only(validate_ops([good], **_known(app))) == []

    bad = {"type": "update_node",
           "payload": {"node_id": "logic_trigger_probe",
                       "patch": {"trigger_type": "on_nonsense"}}}
    assert errors_only(validate_ops([bad], **_known(app))), "bad trigger_type must be caught on update"


def test_create_trigger_writes_the_node_and_the_edge():
    app = create_app({"TESTING": True})
    from routes.graph_ops import _apply_batch_op
    owner = "item_nl_probe_marquee"
    _apply_batch_op(app, "create_node", {"node": {"id": owner, "type": "item", "name": "Marquee"}})

    res = _apply_batch_op(app, "create_trigger", {
        "owner_id": owner,
        "trigger": {"trigger_type": "on_use",
                    "effects": [{"type": "message", "params": {"text": "It glows."}}]},
    })
    tid = res.get("id")
    assert tid, res

    from graph import EDGE_TRIGGERS
    node = app.world.graph.get_node(tid)
    assert node is not None and node.type == "logic_trigger"
    assert node.properties.get("trigger_type") == "on_use"
    # mine, not any trigger the loaded world already had on that id
    edges = [e for e in app.world.graph.get_edges_for_source(owner, EDGE_TRIGGERS)
             if e.target == tid]
    assert edges, "the triggers edge is the whole point"
    # props are written to BOTH the node and the edge
    assert node.properties.get("effects") and edges[0].properties.get("effects")


def test_validator_accepts_create_trigger_and_flags_bad_owners_and_logic():
    app = create_app({"TESTING": True})
    from routes.graph_ops import _apply_batch_op
    _apply_batch_op(app, "create_node", {"node": {"id": "item_owner", "type": "item", "name": "Owner"}})
    known = _known(app)

    good = {"type": "create_trigger",
            "payload": {"owner_id": "item_owner",
                        "trigger": {"trigger_type": "on_examine",
                                    "effects": [{"type": "message", "params": {}}]}}}
    assert errors_only(validate_ops([good], **known)) == []

    missing_owner = {"type": "create_trigger",
                     "payload": {"owner_id": "nope",
                                 "trigger": {"trigger_type": "on_examine"}}}
    assert errors_only(validate_ops([missing_owner], **known))

    bad_logic = {"type": "create_trigger",
                 "payload": {"owner_id": "item_owner",
                             "trigger": {"trigger_type": "on_nonsense"}}}
    assert errors_only(validate_ops([bad_logic], **known))

    empty = {"type": "create_trigger", "payload": {"owner_id": "item_owner", "trigger": {}}}
    assert errors_only(validate_ops([empty], **known))


def test_trigger_fields_on_a_non_trigger_node_are_not_validated_as_logic():
    app = create_app({"TESTING": True})
    from routes.graph_ops import _apply_batch_op
    _apply_batch_op(app, "create_node", {"node": {"id": "item_probe", "type": "item", "name": "Probe"}})
    # An item patch carrying an unrelated `effects` key is not a trigger logic edit.
    op = {"type": "update_node",
          "payload": {"node_id": "item_probe", "patch": {"effects": [{"type": "not_a_real_effect"}]}}}
    assert errors_only(validate_ops([op], **_known(app))) == []
