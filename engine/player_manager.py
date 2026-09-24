"""Player management for the virtual world engine.

Manages player registration, active player state, location queries,
and player trait checks.
"""

from typing import Optional, Dict, List, Any
from player import Player
from area import Area
from graph import WorldGraph, Node, Edge, EDGE_IN, EDGE_CARRYING, EDGE_EQUIPPED, EDGE_KNOWN
from engine.character_spatial import get_character_at_way, get_spatial_position_data


class PlayerManager:
    """Manages player registration, lookup, and state queries."""

    def __init__(self, graph: WorldGraph):
        self.graph = graph
        self.players: Dict[str, Player] = {}
        # task-446: id-first identity. Registry keys are unique identities; a
        # player's display name (`p.name`) is free to repeat. For a unique name
        # the key IS the name (legacy compatibility); a duplicate gets a stable
        # suffixed key derived from the player's opaque id.
        self._players_by_id: Dict[str, str] = {}
        self._players_by_node_id: Dict[str, str] = {}
        self.active_player: Optional[str] = None
        self.ghost_mode: bool = False

    def reindex(self):
        """Rebuild the id→key index and give duplicate-keyed players a unique
        anchor node id. Safe to call after a bulk ``players`` assignment (save
        load) — unique-name players are left exactly as they were."""
        self._players_by_id = {}
        self._players_by_node_id = {}
        for key, p in self.players.items():
            p.player_manager = self
            pid = getattr(p, "id", None)
            if pid:
                self._players_by_id[pid] = key
            if key != getattr(p, "name", key):
                base = Player.node_id_for(getattr(p, "name", key))
                p.node_id = f"{base}__{(pid or 'dup')[:6]}"
            self._players_by_node_id[self.get_player_node_id(key)] = key

    def key_for_node_id(self, node_id: str) -> Optional[str]:
        """Reverse of ``get_player_node_id``: the registry key owning a node.

        Grapple and other edge-driven code carries graph node ids, so it needs
        the identity back (task-449). Falls back to a case-insensitive scan, then
        None when the id is not a player anchor.
        """
        if not node_id:
            return None
        if node_id not in self._players_by_node_id:
            self.reindex()
        key = self._players_by_node_id.get(node_id)
        if key:
            return key
        lowered = str(node_id).lower()
        for nid, k in self._players_by_node_id.items():
            if nid.lower() == lowered:
                return k
        return None

    def relationship_key(self, ref) -> str:
        """The identity a relationship should be stored under (task-446).

        A Player/uid/key resolves to its registry key; a display name resolves to
        the primary holder (unique names map to themselves, so nothing churns);
        an unknown ref is returned verbatim so an off-world mention still stores.
        """
        if ref is None:
            return ""
        if isinstance(ref, Player):
            pid = getattr(ref, "id", None)
            key = self._players_by_id.get(pid) if pid else None
            if key:
                return key
            for k, p in self.players.items():
                if p is ref:
                    return k
            return getattr(ref, "name", "") or ""
        ref = str(ref)
        if not ref:
            return ""
        if ref in self.players:
            return ref
        key = self._players_by_id.get(ref)
        if key and key in self.players:
            return key
        for k, p in self.players.items():
            if getattr(p, "name", None) == ref:
                return k
        return ref

    def display_name_of(self, ref) -> str:
        """Display name for any identity ref (key, name, id or Player)."""
        if isinstance(ref, Player):
            return getattr(ref, "name", "") or ""
        p = self.players.get(ref)
        if p is None:
            key = self._players_by_id.get(str(ref))
            p = self.players.get(key) if key else None
        return getattr(p, "name", str(ref)) if p is not None else str(ref)

    # ── Player Node ID ──────────────────────────────────────────────────

    def get_player_node_id(self, player_ref) -> str:
        """Return the graph node id for a player.

        Accepts a registry key, a display name, an opaque id, or a ``Player``.
        Display names remain valid because the anchor id is derived from the
        name for a unique player (task-434); a duplicate name resolves to the
        primary candidate unless its key/id is passed.
        """
        if player_ref is None:
            return Player.node_id_for("")
        if isinstance(player_ref, Player):
            return getattr(player_ref, "node_id", None) or Player.node_id_for(player_ref.name)
        p = self.players.get(player_ref)
        if p is not None:
            return getattr(p, "node_id", None) or Player.node_id_for(p.name)
        key = self._players_by_id.get(player_ref)
        if key and key in self.players:
            p = self.players[key]
            return getattr(p, "node_id", None) or Player.node_id_for(p.name)
        return Player.node_id_for(player_ref)

    # ── Identity helpers (task-446) ──────────────────────────────────────

    def uid_of(self, player_ref) -> Optional[str]:
        """Stable opaque identity for a player given a key, name, id or object."""
        if isinstance(player_ref, Player):
            return getattr(player_ref, "id", None)
        p = self.get_player(player_ref)
        return getattr(p, "id", None) if p else None

    def get_by_id(self, uid: str) -> Optional[Player]:
        """Look a player up by their stable opaque id."""
        if not uid:
            return None
        if uid not in self._players_by_id:
            self.reindex()
        key = self._players_by_id.get(uid)
        return self.players.get(key) if key else None

    def find_by_name(self, name: str) -> List[Player]:
        """All players carrying a display name (may be more than one)."""
        if not name:
            return []
        matches = [p for p in self.players.values() if getattr(p, "name", None) == name]
        if matches:
            return matches
        p = self.players.get(name)
        return [p] if p else []

    def resolve(self, player_ref) -> Optional[Player]:
        """Resolve a name, registry key, opaque id or Player to the object."""
        if isinstance(player_ref, Player):
            return player_ref
        p = self.get_player(player_ref)
        if p is not None:
            return p
        return self.get_by_id(player_ref)

    # ── Registration ─────────────────────────────────────────────────────

    def _unique_key(self, player_obj: Player) -> str:
        """Registry key for a new player: the name when free, else a stable
        suffix from the opaque id (500 players may share a display name)."""
        name = player_obj.name
        if name not in self.players:
            return name
        uid = (getattr(player_obj, "id", "") or "dup")
        key = f"{name}__{uid[:6]}"
        n = 2
        while key in self.players:
            key = f"{name}__{uid[:6]}_{n}"
            n += 1
        return key

    def add_player(self, player_obj: Player):
        """Register a player and create their graph node."""
        if not player_obj or not getattr(player_obj, 'name', None):
            raise ValueError("Invalid player object")

        key = self._unique_key(player_obj)
        if key != player_obj.name:
            base = Player.node_id_for(player_obj.name)
            player_obj.node_id = f"{base}__{(getattr(player_obj, 'id', '') or 'dup')[:6]}"
        player_obj.player_manager = self
        self.players[key] = player_obj
        if getattr(player_obj, "id", None):
            self._players_by_id[player_obj.id] = key
        self.active_player = key

        if not player_obj.current_area:
            player_obj.current_area = None

        player_node_id = self.get_player_node_id(key)
        if not self.graph.get_node(player_node_id):
            self.graph.add_node(Node(
                id=player_node_id,
                type="character",
                name=player_obj.name
            ))
        self._players_by_node_id[player_node_id] = key
        if player_obj.current_area:
            self._set_player_area(key, player_obj.current_area)

    def set_active_player(self, name: str):
        """Set the active player by registry key, display name or id."""
        key = name if name in self.players else self._players_by_id.get(name)
        if key is None:
            p = self.get_player(name)
            if p is None:
                raise ValueError(f"No such player: {name}")
            key = next((k for k, v in self.players.items() if v is p), name)
        self.active_player = key
        player_obj = self.players[key]
        if player_obj.current_area:
            self._set_player_area(key, player_obj.current_area)
        if not hasattr(player_obj, 'recent_hearing'):
            player_obj.recent_hearing = []

    def _set_player_area(self, player_name: str, area_name: str):
        """Set the graph location edge for a player to a area."""
        player_node_id = self.get_player_node_id(player_name)
        area_id = f"area_{area_name.lower()}".replace(' ', '_')
        area_node = self.graph.get_node(area_id)
        if area_node:
            # Remove any existing location edges first so a move never leaves
            # a stale edge behind (the actual node id may differ from the
            # derived id, e.g. case, so match by source + type).
            for edge in list(self.graph.get_edges_for_source(player_node_id, EDGE_IN)):
                self.graph.remove_edge(edge.source, edge.target, edge.type)
            self.graph.add_edge(Edge(
                source=player_node_id,
                target=area_id,
                type=EDGE_IN
            ))

    # ── Accessors ────────────────────────────────────────────────────────

    def get_active_player_obj(self) -> Optional[Player]:
        """Return the active player object, or None."""
        if not self.active_player:
            return None
        return self.players.get(self.active_player)

    @property
    def player(self) -> Optional[Player]:
        return self.get_active_player_obj()

    def get_player(self, player_name: str) -> Optional[Player]:
        """Return a player by registry key, display name or opaque id.

        A display name returns the primary candidate when duplicated; use
        ``find_by_name`` for all candidates and ``resolve`` for the same
        permissive lookup.
        """
        if not player_name:
            return None
        p = self.players.get(player_name)
        if p is not None:
            return p
        key = self._players_by_id.get(player_name)
        if key and key in self.players:
            return self.players[key]
        for candidate in self.players.values():
            if getattr(candidate, "name", None) == player_name:
                return candidate
        return None

    @property
    def current_area(self) -> Optional[Area]:
        """Return the current area object for the active player."""
        player_obj = self.get_active_player_obj()
        if not player_obj or not player_obj.current_area:
            return None
        area_id = f"area_{player_obj.current_area}".replace(' ', '_')
        # get_node is case-insensitive at the graph layer — scenario ids are
        # always lowercase ("area_task_7") while player.current_area stores the
        # display name ("Task 7"), so exact-id lookup would miss.
        node = self.graph.get_node(area_id)
        if node:
            return Area(
                name=node.name,
                description=node.properties.get("description", ""),
                items=[],
                exits={},
                environment=node.properties.get("environment", {})
            )
        return None

    # ── Item Lookup ──────────────────────────────────────────────────────

    def find_item_node(self, item_name: str) -> Optional[Node]:
        """Find an item node by name, checking inventory and current area."""
        player_obj = self.get_active_player_obj()
        if not player_obj:
            return None
        player_id = self.get_player_node_id(self.active_player or "")
        area_id = None
        if self.current_area:
            area_id = f"area_{self.current_area.name.lower()}".replace(' ', '_')

        normalized_name = item_name.lower().replace('_', ' ').replace('-', ' ')

        def name_matches(node):
            if not node:
                return False
            node_normalized = node.name.lower().replace('_', ' ').replace('-', ' ')
            return normalized_name == node_normalized or normalized_name in node_normalized

        for edge_type in (EDGE_CARRYING, EDGE_EQUIPPED):
            for edge in self.graph.get_edges_for_target(player_id, edge_type):
                node = self.graph.get_node(edge.source)
                if name_matches(node):
                    return node

        for edge in self.graph.get_edges_for_target(player_id, EDGE_KNOWN):
            node = self.graph.get_node(edge.source)
            if name_matches(node):
                return node

        if area_id:
            for edge in self.graph.get_edges_for_target(area_id, EDGE_IN):
                node = self.graph.get_node(edge.source)
                if name_matches(node):
                    return node

        if area_id:
            for container_edge in self.graph.get_edges_for_target(area_id, EDGE_IN):
                container_node = self.graph.get_node(container_edge.source)
                if container_node and container_node.type == "item":
                    if container_node.properties.get("current_state") == "locked":
                        continue
                    for content_edge in self.graph.get_edges_for_target(container_node.id, EDGE_IN):
                        node = self.graph.get_node(content_edge.source)
                        if node and node.type == "item" and node.properties.get("current_state") != "hidden":
                            if name_matches(node):
                                return node

        for edge_type in (EDGE_CARRYING, EDGE_EQUIPPED):
            for container_edge in self.graph.get_edges_for_target(player_id, edge_type):
                container_node = self.graph.get_node(container_edge.source)
                if container_node and container_node.type == "item":
                    if container_node.properties.get("current_state") == "locked":
                        continue
                    for content_edge in self.graph.get_edges_for_target(container_node.id, EDGE_IN):
                        node = self.graph.get_node(content_edge.source)
                        if node:
                            if name_matches(node):
                                return node

        return None

    # ── Area Queries ─────────────────────────────────────────────────────

    def is_undead(self, player_name: str) -> bool:
        """task-309 (5e-aligned): ``undead`` tag — not alive. Skips vitals and
        physiological needs, but is fully corporeal (a zombie is *not* invisible
        and *not* untargetable)."""
        p = self.players.get(player_name)
        if p is None:
            return False
        return "undead" in (getattr(p, "tags", None) or [])

    def is_incorporeal(self, player_name: str) -> bool:
        """task-309 (5e-aligned): ``ghost`` tag — intangible. Phases through
        ways, and is unseen until it manifests. Visibility is a separate state
        (see ``is_visible``); intangibility does not by itself stop targeting."""
        p = self.players.get(player_name)
        if p is None:
            return False
        return "ghost" in (getattr(p, "tags", None) or [])

    def is_undead_ghost(self, player_name: str) -> bool:
        """task-309 compat alias: undead *or* incorporeal.

        Prefer ``is_undead`` / ``is_incorporeal`` / ``is_visible`` at call sites
        — this broad check is kept for callers that mean "spectral entity" (e.g.
        skipping vitals or social reactions)."""
        return self.is_undead(player_name) or self.is_incorporeal(player_name)

    def is_visible(self, player_name: str) -> bool:
        """Can this character be seen (listed in a room, targeted) right now?

        Mundane hiding always hides. A ``ghost`` is unseen until manifested —
        a plain `undead` (zombie) is not affected.
        """
        p = self.players.get(player_name)
        if p is None:
            return False
        if getattr(p, "hidden", False):
            return False
        if self.is_incorporeal(player_name) and not getattr(p, "manifested", False):
            return False
        return True

    def get_players_in_area(self, area_name: str = None, include_ghosts: bool = False) -> List[dict]:
        """Get players in a area. Excludes the active player by default.
        When include_ghosts is False, dead players in ghost mode are omitted,
        and so is anyone not currently visible — hidden characters and
        unmanifested ghosts (task-309)."""
        target_area = area_name
        if not target_area:
            active = self.get_active_player_obj()
            if active and active.current_area:
                target_area = active.current_area
        if not target_area:
            return []

        players_here = []
        for key, player_obj in self.players.items():
            if key == self.active_player:
                continue
            if player_obj.current_area == target_area:
                if player_obj.state == "dead" and self.ghost_mode and not include_ghosts:
                    continue
                if not include_ghosts and not self.is_visible(key):
                    continue
                players_here.append({
                    "name": getattr(player_obj, "name", key),
                    "state": player_obj.state,
                    "description": getattr(player_obj, 'description', '') or '',
                    "activity": getattr(player_obj, 'activity', None),
                    "at_way_id": get_character_at_way(self.graph, self.get_player_node_id(key)),
                    "spatial_position": get_spatial_position_data(
                        self.graph,
                        self.get_player_node_id(key),
                        self,
                        self.active_player or "",
                    ),
                })
        return players_here

    def get_all_dead_players(self) -> List[str]:
        """Return list of dead player display names."""
        return [
            getattr(player_obj, "name", key) for key, player_obj in self.players.items()
            if player_obj.state == "dead"
        ]

    def get_all_alive_players(self) -> List[str]:
        """Return list of alive player display names."""
        return [
            getattr(player_obj, "name", key) for key, player_obj in self.players.items()
            if player_obj.state != "dead"
        ]

    # ── Trait Checks ─────────────────────────────────────────────────────

    def is_slasher(self, player_name: str) -> bool:
        """Check if a player has the 'slasher' trait flag."""
        from engine.traits import TraitSystem
        player_obj = self.get_player(player_name)
        if not player_obj:
            return False
        return TraitSystem.has_effect(player_obj, "is_slasher")
