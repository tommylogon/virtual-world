"""Camp trigger wiring + the two engine features it depends on.

Background: the camp's 11 triggers were authored in a legacy shape
(`logic_trigger -> owner`, event on the node) that the runtime never matches,
so none of them fired. `tools/fix_scenario_authoring.py` inverted them to the
modern shape (`owner -> logic_trigger`, `trigger_type` on the edge).

The discovery triggers also carry `once: true` and a `grant_memory` effect, so
these tests lock the fire-once gate and the memory effect.
"""

import json
import os

from area import Area
from graph import EDGE_TRIGGERS


SCENARIO = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..",
    "data", "scenarios", "kraktooth_goblin_camp.json",
)
EFFECT_TYPES = None  # populated in test_triggers_have_canonical_effect_types


def _load_camp():
    with open(SCENARIO, encoding="utf-8-sig") as f:
        return json.load(f)


def test_camp_triggers_are_wired_to_their_owner():
    """Every logic_trigger is the TARGET of a triggers edge, never the source."""
    data = _load_camp()
    nodes = data["graph"]["nodes"]
    edges = data["graph"]["edges"]
    logic = {nid for nid, n in nodes.items() if n.get("type") == "logic_trigger"}
    assert logic, "expected the camp to have triggers"

    incoming = {e["target"] for e in edges if e.get("type") == "triggers"}
    for trigger_id in logic:
        assert trigger_id in incoming, f"{trigger_id} has no incoming triggers edge"
        for edge in edges:
            if edge.get("type") != "triggers" or edge.get("target") != trigger_id:
                continue
            assert edge["source"] not in logic, (
                f"{trigger_id} is still sourced from a logic_trigger "
                f"({edge['source']}) — the edge was never inverted"
            )
            assert (edge.get("properties") or {}).get("trigger_type"), (
                f"{trigger_id} edge has no trigger_type"
            )


def test_camp_trigger_effects_use_known_engine_types():
    from engine.triggers.constants import EFFECT_TYPES

    data = _load_camp()
    nodes = data["graph"]["nodes"]
    unknown = []
    for node in nodes.values():
        if node.get("type") != "logic_trigger":
            continue
        for effect in (node.get("properties", {}).get("effects") or []):
            if effect.get("type") not in EFFECT_TYPES:
                unknown.append((node["id"], effect.get("type")))
    assert not unknown, f"unknown effect types: {unknown}"


def test_camp_discovery_triggers_are_once():
    data = _load_camp()
    nodes = data["graph"]["nodes"]
    once_triggers = [
        nid for nid, n in nodes.items()
        if n.get("type") == "logic_trigger" and n.get("properties", {}).get("once")
    ]
    # The four discovery triggers (examine/search/enter) must stay fire-once —
    # otherwise they repeat their message and duplicate their spawned items.
    assert len(once_triggers) == 4, once_triggers


def _make_world():
    from virtual_world_engine import VirtualWorld
    world = VirtualWorld()
    world.movement.add_area(Area("Kitchen", "A test kitchen.", []))
    world.name_matcher._set_player_area(world.active_player, "Kitchen")
    return world


def test_grant_memory_effect_adds_a_memory():
    world = _make_world()
    node, _lib = world.effects._hydrate_item("template_grant_memory", {}, always_fresh=True)
    player = world.player
    before = len(player.memories)
    outs = world.triggers._execute_triggers(node, "on_use", game_state=world)
    assert outs, "grant_memory template produced no output"
    assert len(player.memories) == before + 1
    assert "[template:grant_memory]" in player.memories[-1]["text"]


def test_once_trigger_fires_exactly_one_time():
    world = _make_world()
    node, _lib = world.effects._hydrate_item("template_grant_memory", {}, always_fresh=True)
    edges = world.graph.get_edges_for_source(node.id, EDGE_TRIGGERS)
    assert edges, "hydrated template has no trigger edge"
    trigger_node = world.graph.get_node(edges[0].target)
    trigger_node.properties["once"] = True

    first = world.triggers._execute_triggers(node, "on_use", game_state=world)
    assert first, "once-trigger did not fire the first time"
    second = world.triggers._execute_triggers(node, "on_use", game_state=world)
    assert second == [], "once-trigger fired a second time"
