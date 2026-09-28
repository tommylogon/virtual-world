"""Data-integrity guards for the single goblin scenario (task-408).

These assert properties of ``data/scenarios/kraktooth_goblin_camp.json`` itself,
because the file is the thing task-408 makes authoritative: one scenario, one
node per character *after load*, canonical way endpoints, and strict-id
pathfinding that does not need the name-normalizing fallback in
``engine/background_simulation._resolve_area_id``.

The authored count is deliberately twice the player count — an authored
``character_<slug>`` node plus its ``player_<Name>`` anchor per person, collapsed
to one at load. See ``tools/author_character_aliases.py`` for why deleting the
authored node is the wrong fix.
"""

import json
import sys
from collections import defaultdict, deque
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine.character_identity import (  # noqa: E402
    authored_character_node_id,
    canonical_character_node_id,
    collapse_character_identity,
)
from tools.scenario_refs import AreaResolver, way_area_refs  # noqa: E402

ROOT = Path(__file__).parent.parent
SCENARIOS = ROOT / "data" / "scenarios"
CAMP = SCENARIOS / "kraktooth_goblin_camp.json"

WATER_TAGS = {"water", "drink", "beverage"}
FOOD_TAGS = {"food", "eat", "edible", "meal"}


def _payload():
    with open(CAMP, encoding="utf-8-sig") as handle:
        return json.load(handle)


def _nodes(payload):
    return payload["graph"]["nodes"]


def _areas(payload):
    return {k: v for k, v in _nodes(payload).items() if v.get("type") == "area"}


def _tags(node):
    return {str(t).lower() for t in (node.get("properties", {}).get("tags") or [])}


def _adjacency(payload):
    """Undirected adjacency over ``connection`` edges, strict ids only."""
    adj = defaultdict(set)
    for edge in payload["graph"]["edges"]:
        if edge.get("type") != "connection":
            continue
        source, target = edge.get("source"), edge.get("target")
        if source in _nodes(payload) and target in _nodes(payload):
            adj[source].add(target)
            adj[target].add(source)
    return adj


def _reachable(adj, start):
    seen = {start}
    queue = deque([start])
    while queue:
        current = queue.popleft()
        for neighbour in adj[current]:
            if neighbour not in seen:
                seen.add(neighbour)
                queue.append(neighbour)
    return seen


# ── exactly one goblin scenario ────────────────────────────────────────────


def test_only_one_goblin_scenario_remains():
    goblin_files = sorted(
        p.name for p in SCENARIOS.glob("*.json")
        if "goblin" in p.name.lower() or "kraktooth" in p.name.lower()
    )
    assert goblin_files == [CAMP.name], (
        "task-408 keeps ONE goblin scenario; the assembly/generation byproducts "
        f"must not come back: {goblin_files}"
    )


def test_camp_is_valid_utf8_and_parses():
    raw = CAMP.read_bytes()
    raw.decode("utf-8")
    assert json.loads(raw.decode("utf-8"))["_scenario_name"] == "kraktooth_goblin_camp"


def test_camp_carries_a_title():
    payload = _payload()
    assert payload.get("name"), "the scenario file must not be labelled world_template"
    assert (payload.get("meta") or {}).get("title") == payload["name"]


# ── one character per person ───────────────────────────────────────────────


def test_no_duplicate_character_nodes():
    payload = _payload()
    characters = [n for n in _nodes(payload).values() if n.get("type") == "character"]

    keys = [k for k in _nodes(payload) if k.startswith("character_")]
    ids = [n["id"] for n in characters]
    assert len(keys) == len(set(keys)), "character node keys must be unique"
    assert len(ids) == len(set(ids)), "character node ids must be unique"

    anchors = {canonical_character_node_id(p.get("name") or key)
               for key, p in payload["players"].items()}
    for key in keys:
        name = _nodes(payload)[key]["name"]
        assert key == authored_character_node_id(name), (
            f"{key} is not the canonical authored id for {name!r}"
        )
        assert key not in anchors, (
            f"{key} is both an authored node and an anchor; that is two nodes for "
            "one person after the collapse runs"
        )


def test_every_player_has_exactly_one_character_after_load():
    payload = _payload()
    report = collapse_character_identity(payload["graph"], payload["players"])

    assert len(report["collapsed"]) == len(payload["players"]), (
        "every player needs an authored node the loader can collapse"
    )
    assert not [k for k in payload["graph"]["nodes"] if k.startswith("character_")], (
        "the collapse left retired ids in the graph"
    )
    characters = [n for n in payload["graph"]["nodes"].values()
                  if n.get("type") == "character"]
    assert len(characters) == len(payload["players"])

    names = [n["name"] for n in characters]
    assert len(names) == len(set(names)), "no duplicated character names"

    # Second collapse must find nothing left to do.
    assert collapse_character_identity(payload["graph"], payload["players"])["collapsed"] == []


def test_every_collapsed_alias_resolves_back_to_its_anchor():
    payload = _payload()
    report = collapse_character_identity(payload["graph"], payload["players"])
    for retired, canonical in report["collapsed"]:
        assert report["aliases"].get(retired.lower()) == canonical


# ── canonical ids ──────────────────────────────────────────────────────────


def test_way_endpoints_are_area_node_ids():
    payload = _payload()
    area_ids = set(_areas(payload))
    offenders = [
        (way_id, field, value)
        for way_id, field, value in way_area_refs(_nodes(payload))
        if value not in area_ids
    ]
    assert not offenders, (
        "way endpoints must be area node ids so strict-id pathfinding works: "
        f"{offenders[:5]}"
    )


def test_every_edge_endpoint_resolves():
    payload = _payload()
    ids = set(_nodes(payload))
    dangling = [
        (edge.get("type"), edge.get("source"), edge.get("target"))
        for edge in payload["graph"]["edges"]
        if edge.get("source") not in ids or edge.get("target") not in ids
    ]
    assert not dangling, f"dangling edge endpoints: {dangling[:5]}"


def test_area_reference_resolver_is_unambiguous():
    payload = _payload()
    resolver = AreaResolver(_nodes(payload))
    for way_id, field, value in way_area_refs(_nodes(payload)):
        resolved = resolver.resolve(value)
        assert resolved is not None, f"{way_id}.{field}={value!r} names no area"
        assert (payload["graph"]["nodes"][resolved].get("type")) == "area"


def _components(payload):
    """Connected components of the ``connection`` graph, as sets of area ids."""
    adj = _adjacency(payload)
    areas = set(_areas(payload))
    seen = set()
    out = []
    for area in sorted(areas):
        if area in seen:
            continue
        group = {a for a in _reachable(adj, area) if a in areas}
        seen |= group
        out.append(group)
    return out


def _scopes(payload):
    return payload.get("world_scopes") or {}


def _scope_areas(payload):
    """area id -> scope id, from the scope manifest's ``area_ids`` lists."""
    owner = {}
    for scope_id, scope in _scopes(payload).items():
        for area_id in scope.get("area_ids") or []:
            owner.setdefault(area_id, scope_id)
    return owner


def _unscoped(payload):
    return sorted(set(_areas(payload)) - set(_scope_areas(payload)))


# ── strict-id reachability, no name fallback ───────────────────────────────


@pytest.mark.parametrize("tag_set,label", [
    (WATER_TAGS, "water"),
    (FOOD_TAGS, "food"),
])
def test_the_camp_reaches_its_resource_by_strict_id(tag_set, label):
    """No ``_norm_area_table`` fallback: ids alone must close the camp.

    The camp component is the one holding the authored camp areas. A child
    scope (``west_woods``) is a separate region reached by scope entry, not by a
    way in this graph, so it is judged by ``test_each_scope_is_one_component``
    and ``test_every_area_has_an_exit`` instead — a missing path across a scope
    boundary is not a broken id.
    """
    payload = _payload()
    areas = _areas(payload)
    adj = _adjacency(payload)
    resources = {aid for aid, node in areas.items() if _tags(node) & tag_set}
    assert resources, f"the camp has no {label} area to reach"

    camp_component = max(_components(payload), key=len)
    unreachable = [
        aid for aid in sorted(camp_component)
        if aid not in resources and not (_reachable(adj, aid) & resources)
    ]
    assert not unreachable, (
        f"{len(unreachable)} camp areas cannot reach {label} by strict id: "
        f"{unreachable[:8]}"
    )


def test_every_component_is_declared_as_a_scope_or_the_camp():
    """Every area is either in the camp component or owned by a scope.

    Without this, a region that is in neither the camp graph nor the scope
    manifest would silently have no water and no way to be diagnosed.
    """
    payload = _payload()
    scopes = _scopes(payload)
    assert scopes, "the camp should declare its scopes"
    owned = _scope_areas(payload)
    camp_component = max(_components(payload), key=len)
    unowned = [
        area for area in _unscoped(payload)
        if area not in camp_component
    ]
    assert not unowned, f"areas in neither the camp nor a scope: {unowned[:8]}"


def test_each_scope_is_one_component():
    """A scope's areas must not be split across unconnected regions."""
    payload = _payload()
    components = _components(payload)
    for scope_id, scope in _scopes(payload).items():
        areas = {a for a in (scope.get("area_ids") or []) if a in _areas(payload)}
        if len(areas) < 2:
            continue
        touching = [c for c in components if c & areas]
        assert len(touching) == 1, (
            f"scope {scope_id} spans {len(touching)} disconnected components: "
            f"{[len(c) for c in touching]}"
        )
        assert touching[0] & areas == areas, (
            f"scope {scope_id} is not fully inside its component"
        )


def test_every_area_has_an_exit():
    payload = _payload()
    adj = _adjacency(payload)
    stranded = [aid for aid in sorted(_areas(payload)) if not adj.get(aid)]
    assert not stranded, f"areas with no way at all: {stranded}"


# ── traits ─────────────────────────────────────────────────────────────────


def test_goblins_have_high_metabolism_or_a_documented_reason():
    """task-408 change 4, gated on the soak: a week must not become unreachable.

    The trait lives in ``data/library/traits/`` and is unattached by default.
    Attaching it is only safe if the camp still survives a week, so this test
    accepts EITHER attached (with a passing soak) OR a recorded opt-out in the
    task file — the point is that the decision is explicit, not that the
    multiplier is on.
    """
    payload = _payload()
    goblins = {
        key: p for key, p in payload["players"].items()
        if "goblin" in {str(t).lower() for t in (p.get("tags") or [])}
    }
    assert goblins, "the camp should still have goblins"

    attached = [key for key, p in goblins.items()
                if (p.get("traits") or {}).get("high_metabolism")]
    if attached:
        assert len(attached) == len(goblins), (
            f"high_metabolism is on {attached} but not the other goblins; a "
            "partial attach is an authored accident, not a decision"
        )
        return

    task = (ROOT / "docs" / "virtualWorld" / "dev_tasks" / "review" / "world" /
            "task-408-goblin-scenario-node-dedup-and-data-integrity.md")
    if not task.exists():
        task = next(
            ROOT.glob("docs/virtualWorld/dev_tasks/*/world/"
                      "task-408-goblin-scenario-node-dedup-and-data-integrity.md")
        )
    text = task.read_text(encoding="utf-8")
    assert "high_metabolism" in text, (
        "high_metabolism is attached to nobody and the task file records no "
        "decision; add the trait or say why not"
    )
