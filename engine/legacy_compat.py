"""Legacy compatibility properties for VirtualWorld.

Provides the ``areas``, ``current_area``, and ``player`` properties
that older code (routes, app glue, scripts) expects to find directly
on the engine.  These are thin wrappers over the graph + subsystems.
"""

from typing import Any, Dict, Optional

from area import Area


class LegacyCompat:
    """Builds legacy Area objects and player references on the fly.

    Parameters
    ----------
    graph:
        WorldGraph instance.
    player_manager:
        Must provide ``players``, ``active_player``,
        ``get_active_player_obj()``, and ``current_area``.
    area_description:
        Must provide ``get_current_area_id()`` and
        ``build_exits_for_area(area_name)``.
    """

    def __init__(self, graph, player_manager, area_description):
        self.graph = graph
        self.player_manager = player_manager
        self.area_description = area_description

    # ────────────────────────────── areas ─────────────────────────────

    @property
    def areas(self) -> Dict[str, Area]:
        """Build a dict of Area objects from graph nodes.

        This recreates the dict every time it is accessed — do not
        rely on object identity.
        """
        result = {}
        for node in self.graph.nodes.values():
            if node.type == "area":
                area = Area(
                    name=node.name,
                    description=node.properties.get("description", ""),
                    items=[],  # populated elsewhere if needed
                    exits={},  # populated from graph connections
                    environment=node.properties.get("environment", {}),
                )
                result[node.name] = area
        return result

    # ────────────────────────── current_area ──────────────────────────

    @property
    def current_area(self) -> Optional[Area]:
        """Return the active player's current area as a legacy Area object."""
        area_id = self.area_description.get_current_area_id()
        if not area_id:
            return None
        node = self.graph.get_node(area_id)
        if not node:
            return None
        return Area(
            name=node.name,
            description=node.properties.get("description", ""),
            items=[],
            exits=self.area_description.build_exits_for_area(node.name),
            environment=node.properties.get("environment", {}),
        )

    # ────────────────────────────── player ────────────────────────────

    @property
    def player(self):
        """Return the active Player object, or None."""
        return self.player_manager.get_active_player_obj()
