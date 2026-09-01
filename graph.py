# graph.py
from dataclasses import dataclass, field
from typing import Optional, Any, Dict, List
import time
import uuid
import logging

logger = logging.getLogger(__name__)

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

    # ── Case-insensitive id helpers ────────────────────────────────────

    def _rebuild_id_index(self):
        self._id_index = {nid.lower(): nid for nid in self.nodes}

    def _resolve_id(self, node_id: str) -> Optional[str]:
        """Resolve *node_id* to the stored key, case-insensitively."""
        if node_id in self.nodes:
            return node_id
        return self._id_index.get(node_id.lower())

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

    def remove_node(self, node_id: str):
        # Remove node and all edges connected to it (case-insensitive)
        stored_id = self._resolve_id(node_id)
        if stored_id is None:
            return
        self.nodes.pop(stored_id, None)
        self._id_index.pop(stored_id.lower(), None)
        self.edges = [
            e for e in self.edges
            if e.source != stored_id and e.target != stored_id
        ]

    def add_edge(self, edge: Edge):
        # Prevent duplicates if needed (case-insensitive)
        if not any(
            e.source.lower() == edge.source.lower()
            and e.target.lower() == edge.target.lower()
            and e.type == edge.type
            for e in self.edges
        ):
            self.edges.append(edge)

    def remove_edge(self, source: str, target: str, edge_type: str):
        self.edges = [e for e in self.edges
                      if not (e.source.lower() == source.lower()
                              and e.target.lower() == target.lower()
                              and e.type == edge_type)]

    def remove_edges_for_node(self, node_id: str, edge_type: str):
        """Remove every edge of *edge_type* touching *node_id* (as source or target).

        Used to sever dangling connection edges when an item's ownership state
        changes (equip / unequip / drop).
        """
        node_lower = str(node_id).lower()
        self.edges = [
            e for e in self.edges
            if not (e.type == edge_type
                    and (e.source.lower() == node_lower or e.target.lower() == node_lower))
        ]

    def get_node(self, node_id: str) -> Optional[Node]:
        resolved = self._resolve_id(node_id)
        return self.nodes.get(resolved) if resolved else None

    def get_edges_for_source(self, source_id: str, edge_type: Optional[str] = None) -> List[Edge]:
        source_lower = source_id.lower()
        if edge_type is None:
            return [e for e in self.edges if e.source.lower() == source_lower]
        match_types = resolve_edge_types(edge_type)
        results = [e for e in self.edges if e.source.lower() == source_lower and e.type in match_types]
        if EDGE_CONTAINS in match_types or edge_type == EDGE_IN:
            results += [e for e in self.edges if e.target.lower() == source_lower and e.type == EDGE_CONTAINS]
        return results

    def get_edges_for_target(self, target_id: str, edge_type: Optional[str] = None) -> List[Edge]:
        target_lower = target_id.lower()
        if edge_type is None:
            return [e for e in self.edges if e.target.lower() == target_lower]
        match_types = resolve_edge_types(edge_type)
        results = [e for e in self.edges if e.target.lower() == target_lower and e.type in match_types]
        if EDGE_CONTAINS in match_types or edge_type == EDGE_IN:
            results += [e for e in self.edges if e.source.lower() == target_lower and e.type == EDGE_CONTAINS]
        if edge_type == EDGE_IN:
            # Spatial placement: items resting on/under/etc. a surface that is
            # itself positioned in the target (or pointed at the target itself)
            # are discovered as being present here. Anchors = the surfaces that
            # sit directly in the target (the `in` result sources).
            anchors = {target_lower} | {e.source.lower() for e in results}
            results += [e for e in self.edges if e.type in SPATIAL_EDGE_TYPES and e.target.lower() in anchors]
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
                migrated.append(Edge(source=e.source, target=e.target, type=EDGE_IN, properties=e.properties))
            else:
                migrated.append(e)
        self.edges = migrated

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

    def get_characters_by_tag(self, tag: str, area_id: Optional[str] = None) -> List[str]:
        """Return player names that have the given tag, optionally filtered by area."""
        tag = tag.lower()
        results = []
        for node in self.nodes.values():
            if node.type not in ("player", "character"):
                continue
            node_tags = node.properties.get("tags", [])
            if tag not in [t.lower() for t in node_tags]:
                continue
            if area_id:
                area_lower = area_id.lower()
                for edge in self.get_edges_for_source(node.id, EDGE_IN):
                    if edge.target.lower() == area_lower:
                        results.append(node.name)
                        break
            else:
                results.append(node.name)
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

    def load_from_dict(self, data: dict):
        self.nodes.clear()
        self.edges.clear()
        for node_id, ndata in data.get("nodes", {}).items():
            self.nodes[node_id] = Node(**ndata)
        for edata in data.get("edges", []):
            self.edges.append(Edge(**edata))
        self._rebuild_id_index()
        self.normalize_node_types()
        self.normalize_edges()
        self._normalize_edge_endpoints()

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
EDGE_REQUIRES = "requires"  # door → condition
EDGE_TRIGGERS = "triggers"  # node → logic/action

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