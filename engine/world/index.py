"""Global scope index — the small resident map over a chunked world (task-583).

A scope (chunk) can be unloaded from the live graph; the index is what stays.
It records, without holding the nodes themselves:

- scope ids and their parent links;
- area ownership (area id → scope id), including areas in unloaded scopes;
- character and unique-item **location** (id-keyed, never a display name);
- boundary/gateway ways and the remote ``target_area_id`` / ``target_scope_id``
  they name;
- scheduled/due work (delayed events) so a due event aimed at an unloaded node
  is not dropped.

It is derived from the graph when the whole world is loaded (``reindex``) and
from its own persisted form when it is not (``from_dict``). A loader callback
lets :meth:`ensure_scope_loaded` materialise a scope on demand, which is what
makes a gateway a real crossing rather than a dead UI shortcut.
"""

from __future__ import annotations

import logging
from typing import Callable, Dict, Iterable, List, Optional

from graph import EDGE_IN

logger = logging.getLogger(__name__)

#: Property names a gateway may use for its remote end, most specific first.
_TARGET_AREA_KEYS = ("target_area_id", "area_to_id")
_TARGET_SCOPE_KEYS = ("target_scope_id", "child_scope_id")
_SOURCE_AREA_KEYS = ("area_from_id",)

#: Spatial edge types that place a character or item in an area.
_LOCATION_EDGES = frozenset({EDGE_IN, "in"})


def _first(props: dict, keys: Iterable[str]) -> Optional[str]:
    for key in keys:
        value = (props or {}).get(key)
        if value:
            return str(value)
    return None


def _node_scope(node) -> Optional[str]:
    props = getattr(node, "properties", None) or {}
    owner = props.get("world_scope_id")
    if owner:
        return str(owner)
    generated = props.get("generated") or {}
    if generated.get("scope_id"):
        return str(generated["scope_id"])
    return None


class GlobalScopeIndex:
    """Resident index for scope ownership, location, gateways and due work."""

    def __init__(self):
        self._scope_parent: Dict[str, Optional[str]] = {}
        self._area_owner: Dict[str, str] = {}
        self._character_location: Dict[str, str] = {}
        self._item_location: Dict[str, str] = {}
        self._gateways: Dict[str, dict] = {}
        self._scheduled: List[dict] = []
        self._loader: Optional[Callable[[str], Optional[dict]]] = None

    # ── construction ───────────────────────────────────────────────────

    def register_loader(self, loader: Callable[[str], Optional[dict]]):
        """Register ``loader(scope_id) -> {nodes, edges} | None``.

        The loader is how a gateway materialises its destination scope. It may
        return ``None`` when the scope cannot be loaded (no store configured),
        which callers treat as "the destination is not reachable".
        """
        self._loader = loader

    def reindex(self, graph, manifest: Optional[dict] = None) -> "GlobalScopeIndex":
        """Rebuild the index from a (fully loaded) graph and its manifest.

        Clears first: the graph is the authority when it is whole, so a stale
        persisted entry must not outlive a node that has moved.
        """
        self._scope_parent = {}
        self._area_owner = {}
        self._character_location = {}
        self._item_location = {}
        self._gateways = {}
        self._populate_from_graph(graph, manifest)
        return self

    def augment_from_graph(self, graph, manifest: Optional[dict] = None) -> "GlobalScopeIndex":
        """Overlay what the loaded graph says without discarding the rest.

        A save may carry ownership/location/gateway entries for scopes whose
        nodes are **not** loaded; reindexing from the graph would drop them.
        This refreshes the loaded half only.
        """
        self._populate_from_graph(graph, manifest)
        return self

    def _populate_from_graph(self, graph, manifest: Optional[dict] = None):
        for scope_id, record in (manifest or {}).items():
            self._scope_parent[str(scope_id)] = (record or {}).get("parent_id")

        for node in graph.nodes.values():
            node_type = getattr(node, "type", "")
            props = getattr(node, "properties", {}) or {}
            owner = _node_scope(node)
            if node_type == "area" and owner:
                self._area_owner[node.id] = owner
            elif node_type == "way":
                target_area = _first(props, _TARGET_AREA_KEYS)
                target_scope = _first(props, _TARGET_SCOPE_KEYS)
                if target_area or target_scope:
                    self._gateways[node.id] = {
                        "source_area_id": _first(props, _SOURCE_AREA_KEYS),
                        "target_area_id": target_area,
                        "target_scope_id": target_scope,
                        "world_scope_id": owner,
                    }

        for edge in graph.edges:
            if edge.type not in _LOCATION_EDGES:
                continue
            target = graph.get_node(edge.target)
            source = graph.get_node(edge.source)
            if target is None or source is None or getattr(target, "type", "") != "area":
                continue
            if getattr(source, "type", "") in ("character", "player"):
                self._character_location[edge.source] = edge.target
            elif getattr(source, "type", "") == "item":
                self._item_location[edge.source] = edge.target

    # ── scopes and area ownership ──────────────────────────────────────

    def set_scope_parent(self, scope_id: str, parent_id: Optional[str]):
        self._scope_parent[str(scope_id)] = parent_id

    def scope_parent(self, scope_id: str):
        return self._scope_parent.get(str(scope_id))

    def own_area(self, area_id: str, scope_id: str):
        self._area_owner[str(area_id)] = str(scope_id)

    def release_area(self, area_id: str):
        self._area_owner.pop(str(area_id), None)

    def scope_for_area(self, area_id: str) -> Optional[str]:
        return self._area_owner.get(str(area_id))

    def areas_in_scope(self, scope_id: str) -> List[str]:
        scope_id = str(scope_id)
        return sorted(a for a, s in self._area_owner.items() if s == scope_id)

    # ── location (id-keyed, the authoritative record) ───────────────────

    def set_character_location(self, character_id: str, area_id: str):
        if area_id:
            self._character_location[str(character_id)] = str(area_id)
        else:
            self._character_location.pop(str(character_id), None)

    def character_location(self, character_id: str) -> Optional[str]:
        return self._character_location.get(str(character_id))

    def set_item_location(self, item_id: str, area_id: str):
        if area_id:
            self._item_location[str(item_id)] = str(area_id)
        else:
            self._item_location.pop(str(item_id), None)

    def item_location(self, item_id: str) -> Optional[str]:
        return self._item_location.get(str(item_id))

    # ── gateways ────────────────────────────────────────────────────────

    def add_gateway(self, way_id: str, *, target_area_id: Optional[str],
                    target_scope_id: Optional[str] = None,
                    source_area_id: Optional[str] = None,
                    world_scope_id: Optional[str] = None):
        self._gateways[str(way_id)] = {
            "source_area_id": source_area_id,
            "target_area_id": target_area_id,
            "target_scope_id": target_scope_id,
            "world_scope_id": world_scope_id,
        }

    def gateway(self, way_id: str) -> Optional[dict]:
        return self._gateways.get(str(way_id))

    def gateways(self) -> Dict[str, dict]:
        return dict(self._gateways)

    # ── scheduled / due work ────────────────────────────────────────────

    def schedule(self, event: dict):
        self._scheduled.append(dict(event))

    def scheduled(self) -> List[dict]:
        return [dict(e) for e in self._scheduled]

    def due_events(self, tick: int) -> List[dict]:
        tick = int(tick)
        due = [dict(e) for e in self._scheduled
               if int(e.get("fire_tick", 0) or 0) <= tick]
        self._scheduled = [e for e in self._scheduled
                           if int(e.get("fire_tick", 0) or 0) > tick]
        return due

    # ── load-before-you-move ────────────────────────────────────────────

    def ensure_scope_loaded(self, scope_id: str, graph) -> bool:
        """Materialise *scope_id* into *graph* if it is not already loaded.

        Returns True when the scope's nodes are present afterwards. With no
        loader registered an unloaded scope stays unloaded and the caller must
        refuse the move rather than crash on a missing node.
        """
        scope_id = str(scope_id or "")
        if not scope_id:
            return False
        if graph.is_scope_loaded(scope_id):
            return True
        if self._loader is None:
            return False
        payload = self._loader(scope_id)
        if not payload:
            return False
        result = graph.merge_scope(scope_id, payload)
        logger.info("loaded scope %s on demand (%d node(s))",
                    scope_id, len(result.get("added", [])))
        return graph.is_scope_loaded(scope_id)

    def ensure_destination_loaded(self, graph, way_id: str) -> Optional[str]:
        """The remote area a gateway leads to, loading its scope first.

        Returns the ``target_area_id`` when the way is a loadable gateway and
        its destination is available, else None (a non-gateway way, or a scope
        with no loader). The caller then resolves the node normally.
        """
        record = self.gateway(way_id)
        if not record:
            return None
        target_scope = record.get("target_scope_id")
        if target_scope and not self.ensure_scope_loaded(target_scope, graph):
            # A gateway whose remote scope cannot be materialised (no loader)
            # is not crossable: the caller must refuse rather than deref a node
            # that is not there.
            return None
        return record.get("target_area_id")

    # ── persistence ─────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "scope_parent": dict(self._scope_parent),
            "area_owner": dict(self._area_owner),
            "character_location": dict(self._character_location),
            "item_location": dict(self._item_location),
            "gateways": {k: dict(v) for k, v in self._gateways.items()},
            "scheduled": [dict(e) for e in self._scheduled],
        }

    @classmethod
    def from_dict(cls, data) -> "GlobalScopeIndex":
        index = cls()
        if not isinstance(data, dict):
            return index
        index._scope_parent = dict(data.get("scope_parent") or {})
        index._area_owner = {str(k): str(v)
                             for k, v in (data.get("area_owner") or {}).items()}
        index._character_location = {str(k): str(v)
                                     for k, v in (data.get("character_location") or {}).items()}
        index._item_location = {str(k): str(v)
                                for k, v in (data.get("item_location") or {}).items()}
        index._gateways = {str(k): dict(v)
                           for k, v in (data.get("gateways") or {}).items()}
        index._scheduled = [dict(e) for e in (data.get("scheduled") or [])]
        return index
