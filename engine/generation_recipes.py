"""Scoped generation recipes (task-398) — the first one is `apartment.v1`.

A recipe is a pure function from a scope record to a :class:`GenerationPatch`:
no graph, no manifest, no Flask, no clock. That is what makes the task's
determinism claim testable — the same ``(scope record, library, recipe
version)`` must yield a byte-identical patch, and the only randomness allowed is
a ``random.Random`` seeded from the scope's own stable seed.

The one deliberate omission: **no resident.** The task says "either ``vacant`` or
one explicitly requested resident seed. Do not silently manufacture an LLM
character", so a recipe that wanted a resident would have to be *asked* for one by
id. ``apartment.v1`` takes no resident argument and therefore generates a vacant
apartment. That is the safe default, not an oversight.

Authored context (the profile text on a scope record) is treated as input data
and never interpolated into anything executable.
"""
from __future__ import annotations

import random
from typing import Callable, Dict, List, Optional

from engine.generation import GenerationPatch, GenerationReport, provenance
from engine.library_nodes import build_item_subtree, spatial_edge
from engine.population import LibraryIndex, apply_population, plan_population
from graph import EDGE_CONNECTION, Edge, Node

#: recipe id -> builder. Keyed by the version in the scope record's ``recipe``
#: field, so a future ``apartment.v2`` is a new entry rather than a flag.
RECIPES: Dict[str, Callable[..., GenerationPatch]] = {}


def recipe(recipe_id: str):
    """Register a recipe under its versioned id."""
    def wrap(fn):
        RECIPES[recipe_id] = fn
        return fn
    return wrap


def get_recipe(recipe_id: str) -> Optional[Callable[..., GenerationPatch]]:
    return RECIPES.get(recipe_id)


# ── apartment.v1 ─────────────────────────────────────────────────────────
#
# Three areas and four ways: an external door in from the parent area, and one
# internal door between the living space and the bedroom and the bathroom. Room
# archetype + domain tags are the *only* thing that decides what furniture a
# room gets — a raw tag intersection would put plausible-but-wrong things in
# rooms, which the task calls out explicitly.

_APARTMENT_ROOMS = [
    {
        "key": "living",
        "name": "Living-Kitchen",
        "archetype": "living_kitchen",
        "tags": ["residential", "kitchen", "storage", "display"],
        "description": "a main room with the kitchen along one wall and a "
                       "window over the sink.",
    },
    {
        "key": "bedroom",
        "name": "Bedroom",
        "archetype": "bedroom",
        "tags": ["residential", "bedroom", "storage", "display"],
        "description": "a bedroom with the bed under the window.",
    },
    {
        "key": "bathroom",
        "name": "Bathroom",
        "archetype": "bathroom",
        "tags": ["residential", "bathroom"],
        "description": "a small bathroom: sink, mirror, and a door that does "
                       "not close all the way.",
    },
]

#: internal connections, as (from room key, to room key, way label)
_APARTMENT_WAYS = [
    ("living", "bedroom", "bedroom_door"),
    ("living", "bathroom", "bathroom_door"),
]

#: how much each room gets. Not a flat `items_per_area`: a bathroom with six
#: loose items reads as a storeroom, and a kitchen with three reads as empty.
_ROOM_BUDGETS = {
    "living": {"furniture_max": 3, "items_per_area": 6, "loose_ratio": 0.34},
    "bedroom": {"furniture_max": 2, "items_per_area": 4, "loose_ratio": 0.25},
    "bathroom": {"furniture_max": 2, "items_per_area": 2, "loose_ratio": 0.5},
}


@recipe("apartment.v1")
def apartment_v1(scope_id: str, *, seed: str, index: LibraryIndex,
                 entry_area_id: Optional[str] = None,
                 entry_area_name: str = "",
                 tick: int = 0) -> GenerationPatch:
    """One small apartment: entry/living, bedroom, bathroom.

    `entry_area_id` is the area the apartment's front door opens off — for
    Pines 3B that is Hallway 3. It is an *argument* rather than a lookup so the
    recipe stays a pure function and the caller decides what "the hall" is.
    """
    lookup = index.entries.get
    prov = provenance(scope_id, "apartment.v1", seed, tick)

    nodes: List[Node] = []
    edges: List[Edge] = []
    area_scope: Dict[str, str] = {}
    area_ids: List[str] = []
    notes: List[str] = []
    unresolved: Dict[str, int] = {}
    missing_content: List[str] = []

    room_ids: Dict[str, str] = {}
    for room in _APARTMENT_ROOMS:
        area_id = f"area_{scope_id}_{room['key']}"
        nodes.append(Node(
            id=area_id, type="area", name=f"{scope_id} {room['name']}",
            properties={
                "description": room["description"],
                "tags": list(room["tags"]),
                "room_archetype": room["archetype"],
                "recipe": "apartment.v1",
                **prov,
            }))
        room_ids[room["key"]] = area_id
        area_ids.append(area_id)
        area_scope[area_id] = scope_id

    # ── ways: one external door in, then the internal ones ───────────
    if entry_area_id:
        front = f"way_{scope_id}_front_door"
        nodes.append(Node(
            id=front, type="way", name="Apartment Door",
            properties={
                "current_state": "closed",
                "description": f"the door to {_room_label(_APARTMENT_ROOMS[0])}.",
                "recipe": "apartment.v1",
                **prov,
            }))
        for area_id in (entry_area_id, room_ids["living"]):
            edges.append(Edge(source=area_id, target=front, type=EDGE_CONNECTION))
            edges.append(Edge(source=front, target=area_id, type=EDGE_CONNECTION))
    else:
        notes.append("no entry area given; the apartment has no front door")

    for from_key, to_key, label in _APARTMENT_WAYS:
        way_id = f"way_{scope_id}_{label}"
        nodes.append(Node(
            id=way_id, type="way", name=label.replace("_", " ").title(),
            properties={
                "current_state": "open",
                "description": f"the {_room_label(room)} door.",
                "recipe": "apartment.v1",
                **prov,
            }))
        for area_id in (room_ids[from_key], room_ids[to_key]):
            edges.append(Edge(source=area_id, target=way_id, type=EDGE_CONNECTION))
            edges.append(Edge(source=way_id, target=area_id, type=EDGE_CONNECTION))

    # ── tag-aware population, per room, from the task-9 planner ──────
    for room in _APARTMENT_ROOMS:
        area_id = room_ids[room["key"]]
        room_seed = f"{seed}:{room['key']}"
        plan = plan_population(
            room["tags"], index, random.Random(room_seed),
            **_ROOM_BUDGETS[room["key"]])

        for domain in plan.unresolved_domains:
            unresolved[domain] = len(index.candidates([domain]))
        notes.extend(f"{room['key']}: {n}" for n in plan.notes)

        def spawn(library_id: str, _area=area_id) -> str:
            node_id = f"item_{_area}_{library_id}"
            sub_nodes, sub_edges, missing = build_item_subtree(
                library_id, lookup(library_id) or {"name": library_id},
                node_id, lookup, extra=prov)
            nodes.extend(sub_nodes)
            edges.extend(sub_edges)
            missing_content.extend(missing)
            return node_id

        def relate(child: str, parent: str, relation: str) -> None:
            edges.append(spatial_edge(child, parent, relation))

        apply_population(plan, spawn, relate, area_id)

    if missing_content:
        notes.append(
            "library entries reference missing content: "
            + ", ".join(sorted(set(missing_content))))

    report = GenerationReport(
        scope_id=scope_id, recipe_id="apartment.v1", seed=seed,
        area_ids=area_ids, notes=notes, unresolved_tags=unresolved)

    return GenerationPatch(
        nodes=nodes, edges=edges,
        area_scope_assignments=area_scope,
        generated_manifest_updates={
            "state": "materialized",
            "area_ids": area_ids,
            "entry_area_id": entry_area_id or "",
        },
        report=report,
    )


def _room_label(room: dict) -> str:
    return room["name"]
