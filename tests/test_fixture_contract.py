"""Contract for ``tests/fixtures/world.json`` (task-586).

The fixture is the world every ``create_app({"TESTING": True})`` boots. It is a
declaration, not an accident: the rows below are the content ~139 call sites
depend on, and the negative rows are the things that must NOT be there (a
``Living Area`` that collides with the 404 literals, an autonomous NPC that
defeats isolation).

The last test is the whole point: a full turn must not move the cast. If it
does, the fixture is not inert and the order-dependent failures bug-55 recorded
will keep being minted.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app import create_app  # noqa: E402
from conftest import new_world, solo  # noqa: E402
from vital_rates import BASELINE_DECAY, BLADDER_FILL  # noqa: E402

CANONICAL_DECAY = {**BASELINE_DECAY, "Bladder": BLADDER_FILL}

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "world.json"
REQUIRED_AREAS = {"Blizzard Forest Clearing", "Kitchen", "Study", "Cellar"}
REQUIRED_ITEMS = {"item_bread", "item_Create Flame", "item_water_pitcher"}


def _payload():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def _nodes(payload):
    return payload["graph"]["nodes"]


def _areas(nodes=None):
    if nodes is None:
        nodes = _nodes(_payload())
    return {k: v for k, v in nodes.items() if v.get("type") == "area"}


def _adjacency(payload):
    nodes = _nodes(payload)
    adj = defaultdict(set)
    for edge in payload["graph"]["edges"]:
        if edge.get("type") != "connection":
            continue
        source, target = edge.get("source"), edge.get("target")
        if source in nodes and target in nodes:
            adj[source].add(target)
            adj[target].add(source)
    return adj


def _area_graph(payload):
    """Areas are adjacent when a way node joins them."""
    nodes = _nodes(payload)
    areas = _areas(nodes)
    adj = _adjacency(payload)
    out = defaultdict(set)
    for way_id, node in nodes.items():
        if node.get("type") != "way":
            continue
        touched = [n for n in adj[way_id] if n in areas]
        for area in touched:
            out[area] |= set(touched) - {area}
    return out


# ── boot wiring ────────────────────────────────────────────────────────────


def test_testing_boots_the_fixture_not_the_shipped_template():
    app = create_app({"TESTING": True})
    assert app.config["TESTING_TEMPLATE"] == str(FIXTURE)
    # Read-only: no scenario source, so commit cannot write the fixture.
    assert app.world._scenario_source is None
    # And the fixture's inertness is visible on the live cast.
    assert app.world.player_manager.players["rat"].autonomy is False


def test_save_payload_carries_players_and_areas():
    """The savegame shape (to_dict), not the scenario shape (to_scenario_dict,
    which deliberately strips areas)."""
    world = new_world()
    payload = world.to_dict()
    assert payload.get("players"), "to_dict() must carry players"
    assert payload.get("areas"), "to_dict() must carry areas"


# ── the declared content ───────────────────────────────────────────────────


def test_required_areas_exist():
    names = {v["name"] for v in _areas().values()}
    assert REQUIRED_AREAS <= names


def test_area_ids_are_canonical_and_unique():
    keys = list(_areas())
    assert all(k.startswith("area_") for k in keys)
    assert len(keys) == len(set(keys))


def test_characters():
    payload = _payload()
    players = payload["players"]
    assert list(players)[0] == "Kaelen Voss", "Kaelen must be first in the registry"
    assert players["Kaelen Voss"].get("traits") == {}
    assert "Lyrie" in players
    rat = players["rat"]
    assert rat.get("simple_npc") is True
    assert len(rat.get("behaviors") or []) >= 8
    assert rat.get("npc_behavior") == "stationary"


def test_required_items_exist():
    assert REQUIRED_ITEMS <= set(_nodes(_payload()))


def test_shape_minimums():
    nodes = _nodes(_payload())
    assert len(_areas(nodes)) >= 2
    assert sum(1 for n in nodes.values() if n.get("type") == "item") >= 1
    assert sum(1 for n in nodes.values() if n.get("type") == "character") >= 1


def test_every_way_is_wired_to_exactly_two_areas():
    payload = _payload()
    nodes = _nodes(payload)
    areas = set(_areas(nodes))
    adj = _adjacency(payload)
    offenders = []
    for way_id, node in nodes.items():
        if node.get("type") != "way":
            continue
        touched = {n for n in adj[way_id] if n in areas}
        if len(touched) != 2:
            offenders.append((way_id, len(touched)))
    assert not offenders, (
        "test_way_connect_repair walks every way node, so each must join exactly "
        f"two areas: {offenders[:8]}"
    )


def test_clearing_has_exits_and_a_two_way_route():
    payload = _payload()
    areas = _areas()
    clearing = next(k for k, v in areas.items() if v["name"] == "Blizzard Forest Clearing")
    adjacency = _area_graph(payload)

    one_hop = set(adjacency[clearing])
    assert one_hop, "the clearing must have at least one exit"

    two_hop = set()
    for area in one_hop:
        two_hop |= adjacency[area]
    assert two_hop - ({clearing} | one_hop), "expected some area two ways away"


def test_clock_pins():
    payload = _payload()
    assert payload["time_per_tick_minutes"] == 5
    assert payload["clock_start_hour"] == 8
    assert payload["game_time"] == "08:00:00"


def test_no_decay_rate_overrides():
    baseline = CANONICAL_DECAY
    for name, player in _payload()["players"].items():
        rates = player.get("decay_rates") or {}
        non_baseline = {k: v for k, v in rates.items() if baseline.get(k) != v}
        assert not non_baseline, f"{name} overrides baseline decay: {non_baseline}"


# ── the negative rows ──────────────────────────────────────────────────────


def test_no_living_area():
    """`Living Area` is the app.py fallback name and the 404 literal in
    test_graph_move/test_library_build; adding it breaks those as a 'routing bug'."""
    assert "Living Area" not in {v["name"] for v in _areas().values()}


def test_no_autonomous_npc():
    for name, player in _payload()["players"].items():
        assert player.get("autonomy") is False, f"{name} is autonomous"


def test_a_testing_boot_cannot_write_the_fixture():
    """`_scenario_source` is unset under TESTING, so a stray commit has no
    target; the fixture bytes must be identical afterwards."""
    app = create_app({"TESTING": True})
    client = app.test_client()
    before = FIXTURE.read_bytes()
    client.post("/api/scenario/commit", json={})
    assert FIXTURE.read_bytes() == before, "a TESTING commit wrote the fixture"


def test_the_cast_does_not_move_on_a_full_turn():
    """The bug-55 regression at the fixture level: a full turn (NPC behaviour and
    the background simulation both on) must leave the isolated character alone."""
    world = new_world()
    solo(world, "Kaelen Voss")
    for _ in range(5):
        world.tick_turn()

    players = world.player_manager.players
    kaelen = players["Kaelen Voss"]
    assert kaelen.current_area == "Blizzard Forest Clearing", (
        f"the measured character moved to {kaelen.current_area!r}"
    )
    present = [p.name for p in players.values()
               if p is not kaelen and p.current_area == kaelen.current_area]
    assert present == [], f"company wandered back into the isolated area: {present}"
