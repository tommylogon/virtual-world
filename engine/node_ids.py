"""Node ID generation helpers for the virtual world engine.

Provides consistent node ID conventions for areas, ways, items,
and players across the world graph.
"""


class NodeIDHelper:
    """Static helpers for building graph node IDs following project conventions.

    All methods return a canonical node ID string.  The same conventions
    are used by every engine subsystem that needs to locate graph nodes
    by their well-known ID.
    """

    @staticmethod
    def area_node_id(name: str) -> str:
        """Build a area node ID from a human-readable area *name*.

        >>> NodeIDHelper.area_node_id("Living Area")
        'area_living_area'
        """
        safe = name.lower().replace(" ", "_")
        return f"area_{safe}"

    @staticmethod
    def way_node_id(area_name: str, direction: str) -> str:
        """Build a door node ID from a area name and a direction.

        >>> NodeIDHelper.way_node_id("Kitchen", "west")
        'way_kitchen_west'
        """
        safe = area_name.lower().replace(" ", "_")
        return f"way_{safe}_{direction.lower()}"

    @staticmethod
    def item_node_id(name: str) -> str:
        """Build an item node ID from an item name.

        >>> NodeIDHelper.item_node_id("rusty key")
        'item_rusty_key'
        """
        return f"item_{name.lower().replace(' ', '_')}"

    @staticmethod
    def player_node_id(name: str) -> str:
        """Build a player node ID from a player name.

        >>> NodeIDHelper.player_node_id("Traveler")
        'player_Traveler'
        """
        return f"player_{name}".replace(' ', '_')
