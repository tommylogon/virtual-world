"""Deterministic structure-generation contract (task-398).

A generation recipe never writes a parallel world format. It returns a
:class:`GenerationPatch` — plain graph nodes/edges in the existing conventions
(``area`` nodes, ``way`` nodes with connection edges, normal item nodes) plus
provenance and a report — and :func:`apply_patch` commits it to a graph and
scope manifest exactly once.

Once-only is the safety property: applying flips the target scope from
``unmade`` to ``materialized``, and a second apply is rejected unless the caller
passes ``allow_regenerate=True``. That is what guarantees a re-run cannot
duplicate nodes or erase a manual edit made after the first generation.

Provenance (task-398): every generated node carries::

    {"generated": {"scope_id": ..., "recipe_id": ..., "seed": ...,
                   "generated_at_tick": ...}}

so a node can be told apart from hand-authored data, and a future regenerate
flow can decide what it owns without guessing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from graph import Edge, Node

UNMADE = "unmade"
MATERIALIZED = "materialized"


@dataclass
class GenerationReport:
    """What a recipe produced, for the preview and the editor's apply step."""

    scope_id: str
    recipe_id: str
    seed: str
    node_count: int = 0
    edge_count: int = 0
    area_ids: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)
    #: Requested tag → how many candidates the library could offer. A value of
    #: 0 means "asked for this and found nothing" — surfaced, never silently
    #: substituted (task-398).
    unresolved_tags: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "scope_id": self.scope_id,
            "recipe_id": self.recipe_id,
            "seed": self.seed,
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "area_ids": list(self.area_ids),
            "notes": list(self.notes),
            "unresolved_tags": dict(self.unresolved_tags),
        }


@dataclass
class GenerationPatch:
    """A staged graph edit plus where it belongs and why it happened."""

    nodes: List[Node] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)
    #: area node id → world scope id it belongs to (task-397/439 addressing).
    area_scope_assignments: Dict[str, str] = field(default_factory=dict)
    #: Scope-record fields to merge on apply (e.g. ``area_ids``, ``state``).
    generated_manifest_updates: Dict[str, Any] = field(default_factory=dict)
    report: Optional[GenerationReport] = None


def provenance(scope_id: str, recipe_id: str, seed: str,
               tick: int = 0) -> dict:
    """The ``properties`` fragment every generated node must carry."""
    return {
        "generated": {
            "scope_id": str(scope_id),
            "recipe_id": str(recipe_id),
            "seed": str(seed),
            "generated_at_tick": int(tick),
        }
    }


def is_generated(node: Node) -> bool:
    """True when a node was produced by a generator (not hand-authored)."""
    return bool(node is not None and (node.properties or {}).get("generated"))


def apply_patch(graph, manifest: Dict[str, dict], patch: GenerationPatch, *,
                allow_regenerate: bool = False) -> GenerationReport:
    """Commit *patch* to *graph* and the scope *manifest* (once).

    Raises ``ValueError`` when the target scope is already ``materialized`` and
    ``allow_regenerate`` is not set — the once-only guard. With
    ``allow_regenerate=True`` an incoming node whose id already exists is only
    replaced when both the existing and incoming node carry generated
    provenance; anything hand-authored is left untouched.
    """
    report = patch.report or GenerationReport(scope_id="", recipe_id="", seed="")
    scope_id = report.scope_id
    record = manifest.get(scope_id) if scope_id else None

    if record is not None:
        if record.get("state") == MATERIALIZED and not allow_regenerate:
            raise ValueError(
                f"scope {scope_id!r} is already materialized; pass "
                f"allow_regenerate=True to re-apply")
    else:
        record = {"id": scope_id, "name": scope_id, "kind": "scope",
                  "parent_id": None, "children": [], "area_ids": [],
                  "state": UNMADE}
        manifest[scope_id] = record

    for node in patch.nodes:
        existing = graph.get_node(node.id)
        if existing is not None and not (allow_regenerate and is_generated(existing)):
            raise ValueError(
                f"node id {node.id!r} already exists and is not a "
                f"regenerable generated node")

    # All collisions checked before any mutation, so a rejected apply leaves the
    # graph untouched rather than half-written.
    for node in patch.nodes:
        existing = graph.get_node(node.id)
        if existing is None:
            graph.add_node(node)
        else:
            # Reached only when allow_regenerate and both nodes are generated
            # (the check above rejected every other case). The node must be
            # re-stamped in place, not skipped: a re-run that only *adds* missing
            # nodes leaves every existing one with its old data, so a recipe
            # change (e.g. the compiler adding properties.cell/x/y) never reaches
            # the nodes it already emitted.
            graph.replace_node(node)

    for edge in patch.edges:
        graph.add_edge(edge)

    for area_id, owner in patch.area_scope_assignments.items():
        owner_rec = manifest.setdefault(owner, {
            "id": owner, "name": owner, "kind": "scope", "parent_id": None,
            "children": [], "area_ids": [], "state": UNMADE})
        area_ids = owner_rec.setdefault("area_ids", [])
        if area_id not in area_ids:
            area_ids.append(area_id)

    updates = dict(patch.generated_manifest_updates or {})
    updates.setdefault("state", MATERIALIZED)
    if patch.report is not None and patch.report.area_ids:
        merged = list(dict.fromkeys(record.get("area_ids", []) + patch.report.area_ids))
        updates.setdefault("area_ids", merged)
    record.update(updates)

    report.node_count = len(patch.nodes)
    report.edge_count = len(patch.edges)
    return report
