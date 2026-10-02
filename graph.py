# graph.py
from dataclasses import dataclass, field
from typing import Optional, Any, Dict, List
import time
import uuid
import logging

logger = logging.getLogger(__name__)


class ScopeOwnershipError(ValueError):
    """A scope/chunk operation would touch a node another scope owns (task-582)."""


@dataclass
class Node:
    """A generic graph node."""
    id: str
    type: str  # "area", "item", "door", "character", "logic_trigger", etc.
    name: str
    properties: Dict[str, Any] = field(default_factory=dict)
    created: float = field(default_factory=time.time)
    updated: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "properties": self.properties,
            "created": self.created,
            "updated": self.updated
        }

@dataclass
class Edge:
    """A directed relationship between two nodes."""
    source: str
    target: str
    type: str  # "location", "connection", "unlocks", "triggers", "requires", etc.
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "source": self.source,
            "target": self.target,
            "type": self.type,
            "properties": self.properties
        }

class WorldGraph:
    """Manages all nodes and edges for the virtual world."""
    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        # Lowercase id → actual id, so lookups never break on case mismatches
        # ("Task 7" derived as area_Task_7 vs node id area_task_7).
        self._id_index: Dict[str, str] = {}
        # Retired id → surviving id (task-463). When two identities for one
        # character collapse into one node, authored references still mention
        # the retired id; resolving it here keeps them from dangling.
        self._id_aliases: Dict[str, str] = {}
        # task-407: edges indexed by lowercased endpoint so lookups never scan
        # the whole edge list (and never call .lower() per edge).
        self._edges_by_source: Dict[str, List[Edge]] = {}
        self._edges_by_target: Dict[str, List[Edge]] = {}
        self._spatial_edges: List[Edge] = []
        # task-406: trigger event/type → set of source node ids, so turn/time
        # sweeps visit only nodes that actually carry that trigger.
        self._trigger_index: Dict[str, set] = {}
        # Number of edges the indexes were built from. A few effect handlers
        # mutate ``self.edges`` directly; the length check forces a lazy rebuild.
        self._indexed_edge_count = 0
        # Bumped on every mutation; derived caches (exits) key on this.
        self._revision = 0

    # ── Case-insensitive id helpers ────────────────────────────────────

    def _rebuild_id_index(self):
        self._id_index = {nid.lower(): nid for nid in self.nodes}

    def _resolve_id(self, node_id: str) -> Optional[str]:
        """Resolve *node_id* to the stored key, case-insensitively."""
        if node_id in self.nodes:
            return node_id
        if not isinstance(node_id, str):
            return None
        lowered = node_id.lower()
        resolved = self._id_index.get(lowered)
        if resolved is not None:
            return resolved
        # task-463: a retired id (e.g. "character_arix") follows its alias to
        # the surviving canonical node ("player_Arix").
        alias = self._id_aliases.get(lowered)
        if alias is None:
            return None
        if alias in self.nodes:
            return alias
        return self._id_index.get(alias.lower())

    def register_alias(self, retired_id: str, surviving_id: str):
        """Point a retired node id at its surviving node (task-463)."""
        if not retired_id or not surviving_id:
            return
        retired = str(retired_id)
        surviving = str(surviving_id)
        if retired.lower() == surviving.lower():
            return
        self._id_aliases[retired.lower()] = surviving

    def register_aliases(self, aliases: Dict[str, str]):
        """Bulk form of :meth:`register_alias` (retired-id → surviving-id)."""
        for retired, surviving in (aliases or {}).items():
            self.register_alias(retired, surviving)

    def aliases(self) -> Dict[str, str]:
        """A copy of the retired-id → surviving-id alias map."""
        return dict(self._id_aliases)

    # ── task-407: edge indexes ──────────────────────────────────────────

    def _index_edge(self, edge: Edge):
        self._edges_by_source.setdefault(str(edge.source).lower(), []).append(edge)
        self._edges_by_target.setdefault(str(edge.target).lower(), []).append(edge)
        if edge.type in SPATIAL_EDGE_TYPES:
            self._spatial_edges.append(edge)
        if edge.type == EDGE_TRIGGERS:
            tt = edge.properties.get("trigger_type")
            if tt:
                for t in (tt if isinstance(tt, (list, tuple, set)) else [tt]):
                    if t:
                        self._trigger_index.setdefault(str(t), set()).add(str(edge.source))

    def _rebuild_indexes(self):
        self._edges_by_source = {}
        self._edges_by_target = {}
        self._spatial_edges = []
        self._trigger_index = {}
        for e in self.edges:
            self._index_edge(e)
        self._indexed_edge_count = len(self.edges)
        self._revision += 1

    def _ensure_indexes(self):
        if self._indexed_edge_count != len(self.edges):
            self._rebuild_indexes()

    def get_trigger_sources(self, trigger_type: str) -> List[str]:
        """Ids of nodes owning a trigger of *trigger_type* (task-406).

        Faithful to ``_execute_triggers``: an edge qualifies only when it is a
        ``triggers`` edge carrying a non-empty ``trigger_type`` in its own
        properties (the runtime shape). Legacy shapes that never matched are
        still not matched — no behaviour change, just no wasted sweep.
        """
        self._ensure_indexes()
        return list(self._trigger_index.get(str(trigger_type), ()))

    def get_revision(self) -> int:
        return self._revision

    def add_node(self, node: Node):
        """Add a node. If node ID already exists, append a random suffix."""
        # Legacy type migration: door → way (ways are the canonical node type)
        if node.type == "door":
            node.type = "way"
        if node.id in self.nodes:
            existing = self.nodes[node.id]
            # Auto-rename items, ways, and characters (task-316: a second
            # same-named character must never silently overwrite the first —
            # areas are the only type where collision is a hard error).
            if node.type in ('item', 'door', 'logic_trigger', 'character'):
                suffix = str(uuid.uuid4())[:8]
                node.id = f"{node.id}_{suffix}"
                node.name = f"{node.name}_{suffix}"
            elif node.type == 'area':
                raise ValueError(f"Area node '{node.id}' already exists.")
        self.nodes[node.id] = node
        self._id_index[node.id.lower()] = node.id
        self._revision += 1

    def replace_node(self, node: Node):
        """Overwrite an existing node's payload in place, keeping its edges.

        A generator re-run must re-stamp a node it already emitted (e.g. the
        WorldPainter compiler adding ``properties.cell``), not leave the old
        payload behind. Edges are deliberately untouched: a remove+add would drop
        gateways emitted from the other side of a scope. Raises ``KeyError`` for a
        missing id — new nodes go through :meth:`add_node`.
        """
        stored_id = self._resolve_id(node.id)
        if stored_id is None:
            raise KeyError(node.id)
        existing = self.nodes[stored_id]
        existing.type = "way" if node.type == "door" else node.type
        existing.name = node.name
        existing.properties = dict(node.properties)
        existing.updated = time.time()
        self._revision += 1

    def remove_node(self, node_id: str):
        # Remove node and all edges connected to it (case-insensitive)
        stored_id = self._resolve_id(node_id)
        if stored_id is None:
            return
        self.nodes.pop(stored_id, None)
        self._id_index.pop(stored_id.lower(), None)
        for alias, target in list(self._id_aliases.items()):
            if target.lower() == stored_id.lower():
                self._id_aliases.pop(alias, None)
        stored_lower = stored_id.lower()
        self.edges = [
            e for e in self.edges
            if str(e.source).lower() != stored_lower
            and str(e.target).lower() != stored_lower
        ]
        self._rebuild_indexes()

    def add_edge(self, edge: Edge):
        # Prevent duplicates (case-insensitive) — only same-source edges can
        # collide, so the source index makes this O(degree) instead of O(E).
        self._ensure_indexes()
        key_s = str(edge.source).lower()
        key_t = str(edge.target).lower()
        for e in self._edges_by_source.get(key_s, ()):
            if str(e.target).lower() == key_t and e.type == edge.type:
                return
        self.edges.append(edge)
        self._index_edge(edge)
        self._indexed_edge_count = len(self.edges)
        self._revision += 1

    def _unindex_edge(self, edge: Edge):
        """Remove one edge from the derived indexes (task-407).

        Falls back to nothing for the trigger index, which is a set of sources;
        callers that touch ``triggers`` edges rebuild instead.
        """
        src = str(edge.source).lower()
        tgt = str(edge.target).lower()
        lst = self._edges_by_source.get(src)
        if lst is not None:
            self._edges_by_source[src] = [e for e in lst if e is not edge]
        lst = self._edges_by_target.get(tgt)
        if lst is not None:
            self._edges_by_target[tgt] = [e for e in lst if e is not edge]
        if edge.type in SPATIAL_EDGE_TYPES:
            self._spatial_edges = [e for e in self._spatial_edges if e is not edge]

    def remove_edge(self, source: str, target: str, edge_type: str):
        self._ensure_indexes()
        key_s = str(source).lower()
        key_t = str(target).lower()
        doomed = [
            e for e in self._edges_by_source.get(key_s, ())
            if str(e.target).lower() == key_t and e.type == edge_type
        ]
        if not doomed:
            return
        doomed_ids = {id(e) for e in doomed}
        self.edges = [e for e in self.edges if id(e) not in doomed_ids]
        if edge_type == EDGE_TRIGGERS:
            # Trigger index is a set of sources — rebuild rather than guess.
            self._rebuild_indexes()
            return
        for e in doomed:
            self._unindex_edge(e)
        self._indexed_edge_count = len(self.edges)
        self._revision += 1

    def retarget_edge(self, edge: Edge, new_type: Optional[str] = None,
                      new_target: Optional[str] = None,
                      properties: Optional[Dict] = None):
        """Move an edge to a new type/target **in place** (task-407).

        One graph operation instead of ``remove_edge`` + ``add_edge`` for a
        pure move (take / drop / equip hand swaps): the source is unchanged, so
        only the target/type indexes are touched. ``properties`` replaces the
        edge's properties when given (e.g. clearing a slot on equip→carry).
        """
        self._ensure_indexes()
        if not any(e is edge for e in self.edges):
            return
        if edge.type == EDGE_TRIGGERS or new_type == EDGE_TRIGGERS:
            if new_type is not None:
                edge.type = new_type
            if new_target is not None:
                edge.target = new_target
            if properties is not None:
                edge.properties = properties
            self._rebuild_indexes()
            return
        self._unindex_edge(edge)
        if new_type is not None:
            edge.type = new_type
        if new_target is not None:
            edge.target = new_target
        if properties is not None:
            edge.properties = properties
        self._index_edge(edge)
        self._indexed_edge_count = len(self.edges)
        self._revision += 1

    def remove_edges_for_node(self, node_id: str, edge_type: str):
        """Remove every edge of *edge_type* touching *node_id* (as source or target).

        Used to sever dangling connection edges when an item's ownership state
        changes (equip / unequip / drop).
        """
        self._ensure_indexes()
        node_lower = str(node_id).lower()
        doomed_ids = set()
        doomed = []
        for e in self._edges_by_source.get(node_lower, ()):
            if e.type == edge_type and id(e) not in doomed_ids:
                doomed_ids.add(id(e))
                doomed.append(e)
        for e in self._edges_by_target.get(node_lower, ()):
            if e.type == edge_type and id(e) not in doomed_ids:
                doomed_ids.add(id(e))
                doomed.append(e)
        if not doomed:
            return
        self.edges = [e for e in self.edges if id(e) not in doomed_ids]
        if edge_type == EDGE_TRIGGERS:
            self._rebuild_indexes()
            return
        for e in doomed:
            self._unindex_edge(e)
        self._indexed_edge_count = len(self.edges)
        self._revision += 1

    def get_node(self, node_id: str) -> Optional[Node]:
        resolved = self._resolve_id(node_id)
        return self.nodes.get(resolved) if resolved else None

    def get_edges_for_source(self, source_id: str, edge_type: Optional[str] = None) -> List[Edge]:
        self._ensure_indexes()
        source_lower = str(source_id).lower()
        candidates = self._edges_by_source.get(source_lower, [])
        if edge_type is None:
            return list(candidates)
        match_types = resolve_edge_types(edge_type)
        results = [e for e in candidates if e.type in match_types]
        if EDGE_CONTAINS in match_types or edge_type == EDGE_IN:
            results += [
                e for e in self._edges_by_target.get(source_lower, ())
                if e.type == EDGE_CONTAINS
            ]
        return results

    def get_edges_for_target(self, target_id: str, edge_type: Optional[str] = None) -> List[Edge]:
        self._ensure_indexes()
        target_lower = str(target_id).lower()
        candidates = self._edges_by_target.get(target_lower, [])
        if edge_type is None:
            return list(candidates)
        match_types = resolve_edge_types(edge_type)
        results = [e for e in candidates if e.type in match_types]
        if EDGE_CONTAINS in match_types or edge_type == EDGE_IN:
            results += [
                e for e in self._edges_by_source.get(target_lower, ())
                if e.type == EDGE_CONTAINS
            ]
        if edge_type == EDGE_IN:
            # Spatial placement: items resting on/under/etc. a surface that is
            # itself positioned in the target (or pointed at the target itself)
            # are discovered as being present here. Anchors = the surfaces that
            # sit directly in the target (the `in` result sources).
            anchors = {target_lower} | {str(e.source).lower() for e in results}
            results += [
                e for e in self._spatial_edges
                if str(e.target).lower() in anchors
            ]
        return results

    def get_edges_by_type(self, edge_type: str) -> List[Edge]:
        match_types = resolve_edge_types(edge_type)
        return [e for e in self.edges if e.type in match_types]

    def normalize_edges(self):
        """Migrate all legacy edge types to their modern equivalents in-place.
        Handles location->in/carrying split based on target node type."""
        migrated = []
        for e in self.edges:
            if e.type == EDGE_LOCATION:
                target_node = self.nodes.get(e.target)
                if target_node and target_node.type in ("player", "character"):
                    migrated.append(Edge(source=e.source, target=e.target, type=EDGE_CARRYING, properties=e.properties))
                else:
                    migrated.append(Edge(source=e.source, target=e.target, type=EDGE_IN, properties=e.properties))
            elif e.type == EDGE_CARRIED_BY:
                migrated.append(Edge(source=e.source, target=e.target, type=EDGE_CARRYING, properties=e.properties))
            elif e.type == EDGE_CONTAINS:
                # Legacy `contains` was container -> contained; canonical `in`
                # is the reverse (contained -> container). Swap the endpoints.
                migrated.append(Edge(source=e.target, target=e.source, type=EDGE_IN, properties=e.properties))
            else:
                migrated.append(e)
        self.edges = migrated
        self._rebuild_indexes()

    def to_dict(self) -> dict:
        self.normalize_node_types()
        return {
            "nodes": {node_id: n.to_dict() for node_id, n in self.nodes.items()},
            "edges": [e.to_dict() for e in self.edges]
        }

    def normalize_node_types(self):
        """Migrate legacy node types to their canonical form (door → way)."""
        for node in self.nodes.values():
            if node.type == "door":
                node.type = "way"

    def normalize_area_floors(self):
        """Repair areas/ways whose ``floor`` holds a ground *material* instead of a storey.

        The WorldPainter compiler's ``grid.v1`` recipe wrote the biome's ground
        material ("dirt", "stone", ...) onto ``properties.floor`` of both the
        areas and the ways it minted, so saves compiled by it carry a string
        where a **storey index** belongs: 0 is the ground plane, 1 one up, -1 one
        down, and it is unbounded (three stacked rooms, a lake bottom, an
        80-storey tower, -900 in a hole to hell). The material moves to
        ``properties.surface``, where it belongs, and the storey falls back to
        ground (0), which is what an unpainted cell means anyway.

        Same save-repair pattern as ``normalize_node_types``: the recipe is
        fixed in ``engine/world_compile.py``, and this keeps an existing save
        loadable and readable instead of showing "Floor dirt" in the picker until
        the scope is regenerated. Only area/way nodes are touched — an item or
        trigger that happens to carry a string ``floor`` is none of this
        migration's business.
        """
        for node in self.nodes.values():
            if node.type not in ("area", "way"):
                continue
            floor = (node.properties or {}).get("floor")
            if isinstance(floor, str) and floor.strip() != "":
                surface = str(floor).strip()
                if not node.properties.get("surface"):
                    node.properties["surface"] = surface
                node.properties["floor"] = 0

    def get_items_by_tag(self, tag: str, area_id: Optional[str] = None) -> List[Node]:
        """Return all item nodes that have the given tag, optionally filtered by area."""
        tag = tag.lower()
        results = []
        for node in self.nodes.values():
            if node.type != "item":
                continue
            node_tags = node.properties.get("tags", [])
            if tag not in [t.lower() for t in node_tags]:
                continue
            if area_id:
                area_lower = area_id.lower()
                for edge in self.get_edges_for_source(node.id, EDGE_IN):
                    if edge.target.lower() == area_lower:
                        results.append(node)
                        break
            else:
                results.append(node)
        return results


    def get_tagged_items_in_area(self, area_id: str, exclude_tags: Optional[List[str]] = None) -> Dict[str, List[Node]]:
        """Return all items in a area grouped by tag. Optionally exclude certain tags."""
        exclude = [t.lower() for t in (exclude_tags or [])]
        tagged: Dict[str, List[Node]] = {}
        for edge in self.get_edges_for_target(area_id, EDGE_IN):
            node = self.nodes.get(edge.source)
            if node and node.type == "item":
                for item_tag in node.properties.get("tags", []):
                    item_tag_lower = item_tag.lower()
                    if item_tag_lower in exclude:
                        continue
                    if item_tag_lower not in tagged:
                        tagged[item_tag_lower] = []
                    tagged[item_tag_lower].append(node)
        return tagged

    def get_items_by_tag_and_status(self, tag: str, status: str, area_id: Optional[str] = None) -> List[Node]:
        """Return items matching both tag and current status (e.g., all 'flammable' items with status 'lit')."""
        items = self.get_items_by_tag(tag, area_id)
        status_lower = status.lower()
        return [item for item in items if str(item.properties.get("current_state", "")).lower() == status_lower]

    def clear(self):
        """Remove all nodes and edges."""
        self.nodes.clear()
        self.edges.clear()
        self._id_index.clear()
        self._id_aliases.clear()
        self._edges_by_source.clear()
        self._edges_by_target.clear()
        self._spatial_edges.clear()
        self._trigger_index.clear()
        self._indexed_edge_count = 0
        self._revision += 1

    def load_from_dict(self, data: dict):
        self.nodes.clear()
        self.edges.clear()
        self._id_aliases.clear()
        for node_id, ndata in data.get("nodes", {}).items():
            self.nodes[node_id] = Node(**ndata)
        for edata in data.get("edges", []):
            self.edges.append(Edge(**edata))
        self._rebuild_id_index()
        self.normalize_node_types()
        self.normalize_area_floors()
        self.normalize_edges()
        self._normalize_edge_endpoints()
        self.normalize_in_edge_directions()
        self.normalize_item_hold_state()
        self._rebuild_indexes()

    # ── task-582: scope/chunk load, unload and merge ───────────────────
    #
    # ``load_from_dict`` clears the whole graph, so it cannot materialise one
    # scope into a live world. These operations do: a scope is added to or
    # removed from the graph without touching any node another scope owns.
    # Ownership is the node's ``properties.world_scope_id`` (areas, hand-placed
    # things) or its ``properties.generated.scope_id`` (compiled/generated
    # nodes); a node with neither is scope-less (characters, library items) and
    # is addressed through its edges rather than removed by a scope unload.

    @staticmethod
    def _declared_scope(node) -> Optional[str]:
        """The scope a node claims ownership by, or None (task-582)."""
        props = getattr(node, "properties", None) or {}
        owner = props.get("world_scope_id")
        if owner:
            return str(owner)
        generated = props.get("generated") or {}
        if generated.get("scope_id"):
            return str(generated["scope_id"])
        return None

    @staticmethod
    def _declared_scope_dict(ndata: dict) -> Optional[str]:
        props = (ndata or {}).get("properties") or {}
        owner = props.get("world_scope_id")
        if owner:
            return str(owner)
        generated = props.get("generated") or {}
        if generated.get("scope_id"):
            return str(generated["scope_id"])
        return None

    def scope_owners(self) -> Dict[str, List[str]]:
        """scope id → sorted node ids it owns (task-582/583)."""
        owners: Dict[str, List[str]] = {}
        for node_id, node in self.nodes.items():
            scope = self._declared_scope(node)
            if scope:
                owners.setdefault(scope, []).append(node_id)
        return {scope: sorted(ids) for scope, ids in owners.items()}

    def nodes_owned_by(self, scope_id: str) -> List[str]:
        """Node ids owned by *scope_id* (task-582)."""
        scope_id = str(scope_id)
        return sorted(nid for nid, node in self.nodes.items()
                      if self._declared_scope(node) == scope_id)

    def is_scope_loaded(self, scope_id: str) -> bool:
        """True when at least one node owned by *scope_id* is in the graph.

        A scope whose nodes are all unloaded is *not* materialised; `load_from_dict`
        and `clear` make every scope unloaded. This is the graph-local view;
        task-583's global index is authoritative across a save.
        """
        return bool(self.nodes_owned_by(scope_id))

    def merge_scope(self, scope_id: str, data: dict, *,
                    replace: bool = False) -> dict:
        """Materialise one scope's nodes/edges into the live graph (task-582).

        ``data`` is a ``{"nodes": {id: node_dict}, "edges": [...]}`` slice.
        Ownership is checked **before any mutation**, so a rejected merge leaves
        the graph exactly as it was:

        - every incoming node that declares an owner must declare *this* scope;
        - an id already present in the graph is refused unless it is owned by
          this scope and ``replace`` is set (re-stamp, never steal another
          scope's node).

        Returns ``{"scope_id", "added", "replaced", "skipped"}``.
        """
        scope_id = str(scope_id or "")
        if not scope_id:
            raise ScopeOwnershipError("merge_scope requires a scope id")
        incoming_nodes = (data or {}).get("nodes", {}) or {}
        incoming_edges = (data or {}).get("edges", []) or []

        for node_id, ndata in incoming_nodes.items():
            declared = self._declared_scope_dict(ndata)
            if declared is not None and declared != scope_id:
                raise ScopeOwnershipError(
                    f"node {node_id!r} declares scope {declared!r}, not {scope_id!r}")
            existing = self.get_node(node_id)
            if existing is None:
                continue
            existing_scope = self._declared_scope(existing)
            if existing_scope == scope_id and replace:
                continue
            raise ScopeOwnershipError(
                f"node {node_id!r} is already loaded "
                f"(owner {existing_scope or 'none'}); "
                f"{'pass replace=True' if existing_scope == scope_id else 'it belongs to another scope'}")

        added: List[str] = []
        replaced: List[str] = []
        for node_id, ndata in incoming_nodes.items():
            existing = self.get_node(node_id)
            if existing is None:
                node = Node(**ndata)
                self.add_node(node)
                added.append(node.id)
            else:
                self.replace_node(Node(**ndata))
                replaced.append(existing.id)
        for edata in incoming_edges:
            self.add_edge(Edge(**edata))
        return {"scope_id": scope_id, "added": sorted(added),
                "replaced": sorted(replaced),
                "skipped": sorted(set(incoming_nodes) - set(added) - set(replaced))}

    def unload_scope(self, scope_id: str) -> dict:
        """Remove every node *scope_id* owns, and the edges touching them.

        Nodes owned by another scope, and scope-less nodes (characters, library
        items), are never removed. An edge with one endpoint in the unloaded
        scope is dropped with it — the cross-scope policy for carried/equipped
        items and delayed events is task-584's, not silently decided here.
        Returns ``{"scope_id", "removed", "edges_removed"}``.
        """
        scope_id = str(scope_id or "")
        if not scope_id:
            raise ScopeOwnershipError("unload_scope requires a scope id")
        doomed = set(self.nodes_owned_by(scope_id))
        if not doomed:
            return {"scope_id": scope_id, "removed": [], "edges_removed": 0}
        doomed_lower = {nid.lower() for nid in doomed}
        # task-584: a trigger node has no independent life — it is owned by
        # whatever triggers it. Remember which triggers this scope's nodes
        # referenced, so one left with no referrer is cleaned up rather than
        # dangling on a removed node.
        orphan_candidates = {
            e.target for e in self.edges
            if e.type == EDGE_TRIGGERS and str(e.source).lower() in doomed_lower
        }
        for node_id in doomed:
            self.nodes.pop(node_id, None)
            self._id_index.pop(str(node_id).lower(), None)
        for alias, target in list(self._id_aliases.items()):
            if target.lower() in doomed_lower:
                self._id_aliases.pop(alias, None)
        before = len(self.edges)
        self.edges = [
            e for e in self.edges
            if str(e.source).lower() not in doomed_lower
            and str(e.target).lower() not in doomed_lower
        ]
        self._rebuild_indexes()
        edges_after_filter = len(self.edges)
        orphans = [tid for tid in orphan_candidates
                   if self.get_node(tid) is not None
                   and not self.get_edges_for_target(tid)]
        for trigger_id in orphans:
            self.remove_node(trigger_id)
        return {"scope_id": scope_id, "removed": sorted(doomed),
                "edges_removed": before - edges_after_filter,
                "orphaned_triggers": sorted(orphans)}

    def slice_scope(self, scope_id: str) -> dict:
        """A ``merge_scope`` payload for exactly the nodes *scope_id* owns.

        Self-contained: only edges whose **both** endpoints are owned by the
        scope are included, so a slice can be reloaded without dragging in a
        neighbour. A gateway into a child scope is owned by the parent and is
        therefore part of the parent's slice; the child side lives in the global
        index (task-583).
        """
        included = set(self.nodes_owned_by(scope_id))
        nodes = {nid: self.nodes[nid].to_dict() for nid in sorted(included)}
        edges = [e.to_dict() for e in self.edges
                 if e.source in included and e.target in included]
        return {"scope_id": str(scope_id), "nodes": nodes, "edges": edges}

    # ── task-581: one authoritative location record per entity ──────────
    #
    # A character or unique item's location is the `in` edge to an area. The
    # display-name `Player.current_area` is a resolution layer over this, not a
    # second record; these are the id-keyed read/write sides.

    def area_of(self, entity_id: str) -> Optional[str]:
        """The id of the area *entity_id* occupies, from its `in` edge.

        Returns None when the entity has no location edge, or when its target
        is not a loaded area — an area in an evicted scope is still recorded by
        id in the global index (task-583/584), not here.
        """
        node = self.get_node(entity_id)
        if node is None:
            return None
        for edge in self.get_edges_for_source(node.id, EDGE_IN):
            target = self.get_node(edge.target)
            if target is not None and getattr(target, "type", "") == "area":
                return target.id
        return None

    def set_area_of(self, entity_id: str, area_id: str) -> Optional[str]:
        """Point *entity_id*'s location at *area_id*, replacing any existing
        location edge so exactly one authoritative record remains."""
        node = self.get_node(entity_id)
        if node is None:
            return None
        target = self.get_node(area_id)
        if target is None or getattr(target, "type", "") != "area":
            raise ValueError(f"{area_id!r} is not a loaded area")
        for edge in list(self.get_edges_for_source(node.id, EDGE_IN)):
            self.remove_edge(edge.source, edge.target, edge.type)
        self.add_edge(Edge(source=node.id, target=target.id, type=EDGE_IN))
        return target.id

    def normalize_in_edge_directions(self):
        """Swap container -> contained ``in`` edges into contained -> container.

        Canonical ``in`` points *from* the contained item *to* its container
        (see ``EDGE_IN``). An item that sits directly in a room (``in``) or on a
        character (``carrying``/``equipped``) is 'placed'; its contents are
        reached through it and are not placed themselves. So an item -> item
        ``in`` edge whose source is placed and whose target is not is stored
        backwards and must be reversed.

        This repairs saves written while ``contains`` was relabelled to ``in``
        without swapping endpoints (bug-44) — those contents were invisible to
        take/examine/search. :meth:`normalize_edges` reverses legacy ``contains``
        edges directly; this catches the already-relabelled ones.
        """
        placed = set()
        for e in self.edges:
            if e.type not in (EDGE_IN, EDGE_CARRYING, EDGE_EQUIPPED):
                continue
            target = self.get_node(e.target)
            if target is not None and target.type in ("area", "player", "character"):
                placed.add(str(e.source).lower())

        swapped = 0
        for e in self.edges:
            if e.type != EDGE_IN:
                continue
            source = self.get_node(e.source)
            target = self.get_node(e.target)
            if source is None or target is None:
                continue
            if source.type != "item" or target.type != "item":
                continue
            if str(e.source).lower() in placed and str(e.target).lower() not in placed:
                e.source, e.target = e.target, e.source
                swapped += 1
        if swapped:
            logger.info("Reversed %d container edge(s) to contained->container", swapped)
        return swapped

    def normalize_item_hold_state(self) -> int:
        """An item holds at most one of carrying/equipped to a character (task-450).

        bug-25: an item carrying BOTH edges reads as "already carrying" on
        ``take`` and "already wearing" on ``equip`` -- two true statements that
        contradict one another and send an LLM into a spiral. The engine's own
        equip/transfer paths converge on one edge; this is the load-time boundary
        that repairs saves and scenarios written by older paths that added
        ``carrying`` without removing ``equipped``.

        Equipped wins: worn is the more specific state, and demoting it would make
        a worn item silently leave the body. Returns the number of edges removed.
        """
        equipped_to = {}
        for e in self.edges:
            if e.type == EDGE_EQUIPPED:
                equipped_to.setdefault(str(e.source).lower(), set()).add(
                    str(e.target).lower())
        if not equipped_to:
            return 0
        removed = 0
        kept = []
        for e in self.edges:
            if (e.type == EDGE_CARRYING
                    and str(e.target).lower() in equipped_to.get(str(e.source).lower(), ())):
                node = self.get_node(e.source)
                if node is not None and node.type == "item":
                    removed += 1
                    continue
            kept.append(e)
        if removed:
            self.edges = kept
            self._rebuild_indexes()
            logger.warning(
                "Removed %d item carrying edge(s) duplicating an equipped edge "
                "(task-450: an item can't be both carried and worn by one character)",
                removed,
            )
        return removed

    def _normalize_edge_endpoints(self):
        """Remap edge source/target ids to the canonical stored node ids.

        Edges created before the lowercase-id convention (or that survived a
        node rename) can reference ids whose case differs from the actual
        node key — e.g. an edge pointing at ``area_Task_18_-_Room_4`` while
        the node is stored as ``area_task_18_-_room_4``. Lookups are
        case-insensitive so the game still works, but raw serialization and
        editor edge parsing see phantom endpoints. Rewrite each endpoint to
        the resolved key so saves stay clean.
        """
        rewritten = 0
        for e in self.edges:
            src = self._resolve_id(e.source)
            tgt = self._resolve_id(e.target)
            if src is None or tgt is None:
                continue
            if e.source != src:
                e.source = src
                rewritten += 1
            if e.target != tgt:
                e.target = tgt
                rewritten += 1
        if rewritten:
            logger.info(f"Normalized {rewritten} edge endpoint(s) to canonical node ids")

# ── New spatial edge types ──
EDGE_IN = "in"              # item/character → room/container (was: location, contains-reversed)
EDGE_ON = "on"              # item → surface
EDGE_UNDER = "under"        # item → furniture/object (hidden beneath)
EDGE_BEHIND = "behind"      # item → furniture/object (obscured)
EDGE_BESIDE = "beside"      # item → furniture/object (next to)
EDGE_AT = "at"              # item → area/object (loosely positioned near)
EDGE_CARRYING = "carrying"  # item → character (in inventory; was: carried_by, location-to-player)
EDGE_EQUIPPED = "equipped"  # item → character (worn/held, slot in edge props)
EDGE_GRAPPLED = "grappled"  # character → character (grappler holds target)
EDGE_CONNECTION = "connection"  # area ↔ area (via door/way nodes)
EDGE_UNLOCKS = "unlocks"    # item → door
EDGE_TRIGGERS = "triggers"  # node → logic/action
EDGE_KNOWN = "known"        # ability/spell/power item → character

# Spatial placement types — items positioned relative to a surface/area rather
# than inside it. Treated as present-in-area for room-level discovery.
SPATIAL_EDGE_TYPES = {EDGE_ON, EDGE_UNDER, EDGE_BEHIND, EDGE_BESIDE, EDGE_AT}

# ── Legacy constants (kept for migration compat) ──
EDGE_LOCATION = "location"     # → in or carrying depending on target
EDGE_CONTAINS = "contains"     # → in (direction reversed)
EDGE_CARRIED_BY = "carried_by" # → carrying

# ── Migration maps ──
LEGACY_EDGE_MAP = {
    EDGE_IN: {EDGE_LOCATION, EDGE_CONTAINS},
    EDGE_CARRYING: {EDGE_CARRIED_BY, EDGE_LOCATION},
}

OLD_TO_NEW_EDGE = {
    EDGE_LOCATION: EDGE_IN,
    EDGE_CONTAINS: EDGE_IN,
    EDGE_CARRIED_BY: EDGE_CARRYING,
}


def normalize_edge_type(edge_type: str) -> str:
    return OLD_TO_NEW_EDGE.get(edge_type, edge_type)


def resolve_edge_types(query_type) -> set:
    # Accept a single type or an iterable of types (e.g. (EDGE_CARRYING,
    # EDGE_EQUIPPED)) — flatten so callers can match several at once.
    if isinstance(query_type, (tuple, list)):
        types: set = set()
        for part in query_type:
            types |= resolve_edge_types(part)
        return types
    types = {query_type}
    if query_type in LEGACY_EDGE_MAP:
        types |= LEGACY_EDGE_MAP[query_type]
    new_type = OLD_TO_NEW_EDGE.get(query_type)
    if new_type:
        types.add(new_type)
    return types