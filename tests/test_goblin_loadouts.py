"""task-519: the six Kraktooth goblins load with their gear equipped.

Content, not instrumentation: the goblins' starting loadouts are authored in
`data/library/characters/` as library-id references and library-id equipped
entries. Importing them must materialize the gear with its template stats, link
every piece to the character once, and resolve equipment to node-id strings
(the carried + equipped invariant, task-450).
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app
from player import Player

GOBLINS = ["Zikka", "Mikka", "Gribba", "Rikka", "Vekka", "Krikka"]


@pytest.fixture(scope="module")
def loaded():
    app = create_app({"TESTING": True})
    client = app.test_client()
    players = {}
    for name in GOBLINS:
        resp = client.post(f"/api/library/import/character/{name}",
                           json={"active": False})
        assert resp.status_code == 200, (name, resp.get_data(as_text=True))
        players[name] = app.world.player_manager.players[name]
    return app, players


def _carried(app, name):
    node_id = Player.node_id_for(name)
    out = []
    for edge in app.world.graph.get_edges_for_target(node_id, "carrying"):
        node = app.world.graph.get_node(edge.source)
        if node:
            out.append(node)
    return out


@pytest.mark.parametrize("name", GOBLINS)
def test_goblin_loads_with_no_duplicate_or_orphan_items(loaded, name):
    app, _ = loaded
    carried = _carried(app, name)
    ids = [n.id for n in carried]
    assert ids, f"{name} loaded with nothing"
    assert len(ids) == len(set(ids)), f"{name} has duplicate carried nodes"
    for node in carried:
        assert node.properties.get("library_id"), f"{name}: {node.id} is orphaned (no library_id)"


@pytest.mark.parametrize("name", GOBLINS)
def test_goblin_equipment_resolves_to_carried_node_ids(loaded, name):
    app, players = loaded
    player = players[name]
    carried_ids = {n.id for n in _carried(app, name)}
    assert player.equipped, f"{name} has no equipped slots"
    for slot, stack in player.equipped.items():
        assert isinstance(stack, list), f"{name}.{slot} is not a list"
        for entry in stack:
            assert isinstance(entry, str), f"{name}.{slot} holds a non-string: {entry!r}"
            if entry.startswith("__"):
                continue
            assert entry in carried_ids, f"{name}.{slot} points at uncarried {entry}"


def test_goblin_gear_keeps_template_stats(loaded):
    """A materialized weapon carries its damage/damage_type, not a bare name."""
    app, _ = loaded
    cleaver = next(n for n in _carried(app, "Zikka")
                   if n.properties.get("library_id") == "zikka_cleaver")
    assert cleaver.properties["damage"] == 6
    assert cleaver.properties["damage_type"] == "slashing"
    assert cleaver.properties["equip_slots"] == ["hand_right"]

    plate = next(n for n in _carried(app, "Zikka")
                 if n.properties.get("library_id") == "zikka_shoulder_plate")
    assert plate.properties["defense"] == 2
