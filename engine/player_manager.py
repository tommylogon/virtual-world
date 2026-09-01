"""Player management for the virtual world engine.

Manages player registration, active player state, location queries,
and player trait checks.
"""

from typing import Optional, Dict, List, Any
from player import Player
from area import Area
from graph import WorldGraph, Node, Edge, EDGE_IN, EDGE_CARRYING, EDGE_EQUIPPED
from engine.character_spatial import get_character_at_way, get_spatial_position_data


class PlayerManager:
    """Manages player registration, lookup, and state queries."""

    def __init__(self, graph: WorldGraph):
        self.graph = graph
        self.players: Dict[str, Player] = {}
        self.active_player: Optional[str] = None
        self.ghost_mode: bool = False

    # ── Player Node ID ──────────────────────────────────────────────────

    def get_player_node_id(self, player_name: str) -> str:
        """Build the graph node ID for a player."""
        return f"player_{player_name}".replace(' ', '_')

    # ── Registration ─────────────────────────────────────────────────────

    def add_player(self, player_obj: Player):
        """Register a player and create their graph node."""
        if not player_obj or not getattr(player_obj, 'name', None):
            raise ValueError("Invalid player object")

        self.players[player_obj.name] = player_obj
        self.active_player = player_obj.name

        if not player_obj.current_area:
            player_obj.current_area = None

        player_node_id = self.get_player_node_id(player_obj.name)
        if not self.graph.get_node(player_node_id):
            self.graph.add_node(Node(
                id=player_node_id,
                type="character",
                name=player_obj.name
            ))
        if player_obj.current_area:
            self._set_player_area(player_obj.name, player_obj.current_area)

    def set_active_player(self, name: str):
        """Set the active player by name."""
        if name not in self.players:
            raise ValueError(f"No such player: {name}")
        self.active_player = name
        player_obj = self.players[name]
        if player_obj.current_area:
            self._set_player_area(name, player_obj.current_area)
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
        """Return a player by name."""
        return self.players.get(player_name)

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

    def is_undead_ghost(self, player_name: str) -> bool:
        """task-309: an NPC character tagged ``ghost``/``undead`` is an
        invisible walker — omitted from room listings and social presence,
        immune to vital decay, and untargetable by normal attacks."""
        p = self.players.get(player_name)
        if p is None:
            return False
        tags = getattr(p, "tags", None) or []
        return "ghost" in tags or "undead" in tags

    def get_players_in_area(self, area_name: str = None, include_ghosts: bool = False) -> List[dict]:
        """Get players in a area. Excludes the active player by default.
        When include_ghosts is False, dead players in ghost mode are omitted,
        and so are invisible undead-ghost NPCs (task-309)."""
        target_area = area_name
        if not target_area:
            active = self.get_active_player_obj()
            if active and active.current_area:
                target_area = active.current_area
        if not target_area:
            return []

        players_here = []
        for player_name, player_obj in self.players.items():
            if player_name == self.active_player:
                continue
            if player_obj.current_area == target_area:
                if player_obj.state == "dead" and self.ghost_mode and not include_ghosts:
                    continue
                if not include_ghosts and self.is_undead_ghost(player_name):
                    continue
                players_here.append({
                    "name": player_name,
                    "state": player_obj.state,
                    "description": getattr(player_obj, 'description', '') or '',
                    "activity": getattr(player_obj, 'activity', None),
                    "at_way_id": get_character_at_way(self.graph, self.get_player_node_id(player_name)),
                    "spatial_position": get_spatial_position_data(
                        self.graph,
                        self.get_player_node_id(player_name),
                        self,
                        self.active_player or "",
                    ),
                })
        return players_here

    def get_all_dead_players(self) -> List[str]:
        """Return list of player names who are dead."""
        return [
            player_name for player_name, player_obj in self.players.items()
            if player_obj.state == "dead"
        ]

    def get_all_alive_players(self) -> List[str]:
        """Return list of player names who are alive."""
        return [
            player_name for player_name, player_obj in self.players.items()
            if player_obj.state != "dead"
        ]

    # ── Trait Checks ─────────────────────────────────────────────────────

    def is_slasher(self, player_name: str) -> bool:
        """Check if a player has the 'slasher' trait flag."""
        from engine.traits import TraitSystem
        player_obj = self.players.get(player_name)
        if not player_obj:
            return False
        return TraitSystem.has_effect(player_obj, "is_slasher")
