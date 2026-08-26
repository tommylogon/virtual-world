import time
from typing import Optional

from graph import EDGE_IN, Node, Edge


class GhostSystem:
    """Manages ghost mode behavior — what dead characters can and cannot do,
    and spawning body items upon death."""

    def __init__(self, graph, skills, logging_events):
        self.graph = graph
        self.skills = skills
        self.logging_events = logging_events

    def spawn_body_item(self, player_name: str, cause_of_death: str = "unknown causes"):
        """Create a body item in the player's current area upon death."""
        # self.skills is duck-typed VirtualWorld
        player = self.skills.players.get(player_name) if hasattr(self.skills, 'players') else None
        if not player:
            return

        area_name = player.current_area
        if not area_name:
            return

        body_item_id = f"body_{player_name}"

        body_description = f"The lifeless body of {player_name}. Death came from {cause_of_death}."

        cause_lower = cause_of_death.lower()
        if "exhaustion" in cause_lower or "energy" in cause_lower:
            body_description += f" {player_name}'s face is drawn and pale, eyes sunken from utter exhaustion."
        elif "hunger" in cause_lower or "starve" in cause_lower:
            body_description += f" {player_name}'s body is emaciated, ribs visible through the skin."
        elif "thirst" in cause_lower or "dehydrat" in cause_lower:
            body_description += f" {player_name}'s skin is dry and cracked, lips parched."
        elif "environ" in cause_lower or "temperature" in cause_lower or "cold" in cause_lower or "heat" in cause_lower:
            body_description += f" {player_name}'s body shows the ravages of the harsh environment."
        elif "toxic" in cause_lower or "poison" in cause_lower:
            body_description += f" A faint discoloration marks {player_name}'s skin."
        elif "damage" in cause_lower or "hp" in cause_lower or "attack" in cause_lower:
            body_description += f" Wounds are visible on {player_name}'s body."
        else:
            body_description += f" {player_name}'s body lies still, claimed by {cause_of_death}."

        existing = self.graph.get_node(body_item_id)
        if existing:
            existing.properties["description"] = body_description
            existing.updated = time.time()
            return

        body_node = Node(
            id=body_item_id,
            type="item",
            name=f"{player_name}'s Body",
            properties={
                "description": body_description,
                "actions": ["examine"],
                "weight": 50.0,
                "is_body": True,
                "character_name": player_name
            }
        )
        self.graph.add_node(body_node)

        area_node_id = f"area_{area_name.lower().replace(' ', '_')}"
        self.graph.add_edge(Edge(source=body_item_id, target=area_node_id, type=EDGE_IN))

        self.logging_events.add_log_entry(f"[System] {player_name}'s body lies in the {area_name}.")

    def check_ghost_action(self, player_manager, action_type: str, target_name: str = None) -> Optional[str]:
        """Check if a dead character can perform an action in ghost mode.
        Returns an error message string if blocked, or None if allowed.
        Physical interactions require a Wisdom/Perception check DC 15."""
        # player_manager is duck-typed VirtualWorld
        player = player_manager.players.get(player_manager.active_player)
        if not player or player.state != "dead":
            return None

        if not player_manager.ghost_mode:
            return "Your body lies still. You can do nothing."

        ghost_free_actions = ["look", "inventory", "stats", "status", "examine", "fumble"]
        if action_type in ghost_free_actions:
            return None

        if action_type == "manifest":
            return None

        if action_type in ("go", "move"):
            return None

        physical_actions = ["take", "drop", "use", "open", "close", "speak", "say", "rest", "sleep", "eat", "drink"]
        if action_type in physical_actions:
            if action_type in ("speak", "say"):
                success, total, msg = player_manager.skill_check("Perception", 15)
                if not success:
                    return "Your voice echoes in the spirit realm, but the living cannot hear you."
                return None
            elif action_type in ("take", "drop"):
                success, total, msg = player_manager.skill_check("Perception", 15)
                if not success:
                    return "Your ghostly hands pass right through it. You cannot grasp physical objects."
                return None
            elif action_type in ("open", "close"):
                success, total, msg = player_manager.skill_check("Perception", 15)
                if not success:
                    return f"You try to {action_type} the {target_name or 'door'}, but your hands pass through. You lack the physical presence."
                return None
            elif action_type in ("use",):
                success, total, msg = player_manager.skill_check("Perception", 15)
                if not success:
                    return "You cannot interact with physical objects in your ghostly state."
                return None
            elif action_type in ("rest", "sleep", "eat", "drink"):
                if action_type in ("rest", "sleep"):
                    return "You are already beyond rest. The dead do not sleep."
                else:
                    return "You cannot eat or drink in your ghostly state. You have no physical body."

        return None
