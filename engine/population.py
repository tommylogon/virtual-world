"""Tag-chain area population engine (task-9).

Selects furniture and items for an area from the library by walking a single
domain tag down the chain:

    area domain tags
      -> furniture carrying a role tag (display / container / storage)
           and at least one matching domain tag
      -> items carrying at least one matching domain tag

Matching is plain set intersection. Planning is pure and deterministic so the
same (area tags, library, seed) always yields the same plan; applying the plan
is delegated to caller-provided ``spawn`` / ``relate`` callables so this module
never depends on Flask, routes, or a live app.

Placement follows the existing spatial edge vocabulary (graph.py):
``in`` for containment, ``on``/``beside`` for surfaces, ``at`` for floors.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional

ROLE_DISPLAY = "display"
ROLE_CONTAINER = "container"
ROLE_STORAGE = "storage"
FURNITURE_TAG = "furniture"

# Furniture roles that act as placement targets for loose items.
_ROLE_TAGS = (ROLE_DISPLAY, ROLE_CONTAINER, ROLE_STORAGE)


@dataclass
class Placement:
    """One node to materialize."""

    library_id: str
    name: str
    role: str            # "furniture" | "item"
    relation: str        # in | on | beside | at
    parent_index: int = -1  # index into PopulationPlan.furniture, or -1 (area)


@dataclass
class PopulationPlan:
    area_tags: List[str] = field(default_factory=list)
    domains: List[str] = field(default_factory=list)
    furniture: List[Placement] = field(default_factory=list)
    items: List[Placement] = field(default_factory=list)
    unresolved_domains: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return not self.furniture and not self.items


def _tags_of(entry: dict) -> List[str]:
    tags = entry.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    return [str(t).lower() for t in tags]


class LibraryIndex:
    """Tag -> library-id index over item entries."""

    def __init__(self, entries: Dict[str, dict]):
        self.entries = entries
        self.by_tag: Dict[str, List[str]] = {}
        for library_id in sorted(entries):
            for tag in _tags_of(entries[library_id]):
                self.by_tag.setdefault(tag, []).append(library_id)

    @classmethod
    def from_directory(cls, path) -> "LibraryIndex":
        path = Path(path)
        entries: Dict[str, dict] = {}
        if not path.is_dir():
            return cls(entries)
        for file in sorted(path.glob("*.json")):
            try:
                entries[file.stem] = json.loads(file.read_text(encoding="utf-8-sig"))
            except Exception:
                continue
        return cls(entries)

    def tags_of(self, library_id: str) -> List[str]:
        return _tags_of(self.entries.get(library_id, {}))

    def name_of(self, library_id: str) -> str:
        return self.entries.get(library_id, {}).get("name", library_id)

    def is_furniture(self, library_id: str) -> bool:
        return FURNITURE_TAG in self.tags_of(library_id)

    def roles_of(self, library_id: str) -> List[str]:
        tags = set(self.tags_of(library_id))
        return [r for r in _ROLE_TAGS if r in tags]

    def candidates(self, domains: Iterable[str], *,
                   require_all: Iterable[str] = (),
                   exclude_tags: Iterable[str] = (),
                   furniture: Optional[bool] = None,
                   exclude_ids: Iterable[str] = ()) -> List[str]:
        domains = {str(d).lower() for d in domains}
        require_all = {str(t).lower() for t in require_all}
        exclude_tags = {str(t).lower() for t in exclude_tags}
        exclude_ids = set(exclude_ids)

        out: List[str] = []
        for library_id in self.entries:
            if library_id in exclude_ids:
                continue
            tags = set(self.tags_of(library_id))
            if not (tags & domains):
                continue
            if require_all and not require_all.issubset(tags):
                continue
            if exclude_tags and (tags & exclude_tags):
                continue
            if furniture is not None and self.is_furniture(library_id) != furniture:
                continue
            out.append(library_id)
        return sorted(out)

    def overlap(self, library_id: str, domains: Iterable[str]) -> int:
        return len(set(self.tags_of(library_id)) & {str(d).lower() for d in domains})


def _weighted_choice(index: LibraryIndex, candidates: List[str], domains, rng: random.Random):
    """Pick candidates preferring more domain overlap, with seeded tie-breaks."""
    ranked = sorted(candidates, key=lambda lid: (-index.overlap(lid, domains), lid))
    pool = [lid for lid in ranked if index.overlap(lid, domains) >= index.overlap(ranked[0], domains)]
    return rng.choice(pool)


def plan_population(area_tags: Iterable[str],
                    index: LibraryIndex,
                    rng: random.Random,
                    *,
                    furniture_max: int = 3,
                    items_per_area: int = 6,
                    loose_ratio: float = 0.4) -> PopulationPlan:
    """Plan furniture + items for an area from its domain tags.

    Deterministic for a fixed ``rng`` seed. Never substitutes unrelated items:
    when a domain has no library candidates it is reported in
    ``unresolved_domains`` instead.
    """
    plan = PopulationPlan()
    seen = set()
    domains: List[str] = []
    for tag in area_tags or []:
        t = str(tag).lower()
        if t and t not in seen:
            seen.add(t)
            domains.append(t)
    plan.area_tags = domains
    plan.domains = domains
    if not domains:
        plan.notes.append("area has no tags; cannot walk the population chain")
        return plan

    # ── 1. furniture with a placement role ────────────────────────────
    furn_candidates = index.candidates(domains, require_all=[FURNITURE_TAG], furniture=True)
    furn_with_role = [lid for lid in furn_candidates if index.roles_of(lid)]
    if not furn_with_role:
        plan.notes.append(f"no role-tagged furniture for domains {domains}")
    else:
        chosen: List[str] = []
        pool = list(furn_with_role)
        for _ in range(min(furniture_max, len(pool))):
            pick = _weighted_choice(index, pool, domains, rng)
            pool.remove(pick)
            chosen.append(pick)
        for lid in chosen:
            role = index.roles_of(lid)[0]
            relation = "on" if role == ROLE_DISPLAY else "in"
            if role == ROLE_DISPLAY and ROLE_CONTAINER not in index.roles_of(lid):
                relation = "on"
            plan.furniture.append(Placement(
                library_id=lid, name=index.name_of(lid), role="furniture", relation=relation))

    furniture_ids = [p.library_id for p in plan.furniture]

    # ── 2. items matching the domains ─────────────────────────────────
    item_candidates = index.candidates(
        domains, furniture=False,
        exclude_tags=[FURNITURE_TAG],
        exclude_ids=furniture_ids)

    if not item_candidates:
        plan.notes.append(f"no catalog items for domains {domains}")
        plan.unresolved_domains = list(domains)
        return plan

    # Container furniture takes most items; the rest lie loose in the area.
    containers = [i for i, p in enumerate(plan.furniture) if p.relation == "in"]
    surfaces = [i for i, p in enumerate(plan.furniture) if p.relation == "on"]
    loose_budget = max(1, int(round(items_per_area * loose_ratio)))
    in_budget = max(0, items_per_area - loose_budget)

    pool = list(item_candidates)
    placed: List[Placement] = []

    def take(n: int, parent_index: int, relation: str, budget: int) -> None:
        nonlocal pool
        taken = 0
        while pool and taken < n and taken < budget:
            pick = _weighted_choice(index, pool, domains, rng)
            pool.remove(pick)
            placed.append(Placement(
                library_id=pick, name=index.name_of(pick), role="item",
                relation=relation, parent_index=parent_index))
            taken += 1

    if containers:
        per = max(1, in_budget // len(containers))
        for i in containers:
            take(per, i, "in", in_budget)
    elif surfaces:
        per = max(1, in_budget // len(surfaces))
        for i in surfaces:
            take(per, i, "on", in_budget)

    # Loose items on the floor, plus anything still unplaced if there was no
    # furniture at all (fill to the loose budget, then stop).
    loose_budget_effective = loose_budget if plan.furniture else items_per_area
    take(loose_budget_effective, -1, "at", loose_budget_effective)

    plan.items = placed
    if not plan.furniture and placed:
        plan.notes.append("area had no role-tagged furniture; items placed loose")
    return plan


def apply_population(plan: PopulationPlan,
                     spawn: Callable[[str], str],
                     relate: Callable[[str, str, str], None],
                     area_node_id: str) -> Dict[int, str]:
    """Materialize ``plan`` using caller callbacks.

    ``spawn(library_id) -> node_id`` creates the node; ``relate(child, parent,
    relation)`` writes the spatial edge. Returns {furniture_index: node_id}.
    """
    furniture_nodes: Dict[int, str] = {}
    for i, placement in enumerate(plan.furniture):
        node_id = spawn(placement.library_id)
        relate(node_id, area_node_id, placement.relation)
        furniture_nodes[i] = node_id

    for placement in plan.items:
        node_id = spawn(placement.library_id)
        parent = furniture_nodes.get(placement.parent_index, area_node_id)
        relate(node_id, parent, placement.relation)

    return furniture_nodes
