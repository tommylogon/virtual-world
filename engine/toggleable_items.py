from typing import Optional

from graph import Node


class ToggleableItems:
    """Manages toggleable items — items with on/off states that flip
    the item's current_state between 'unlit' and 'lit' on the graph node.
    Lighting is calculated by scanning the graph for lit items."""

    def __init__(self, graph, location):
        self.graph = graph
        self.location = location

    def toggle_item_status(self, player_manager, item_name: str) -> str:
        """Toggle an item's current_state between 'unlit' and 'lit'.
        Items with 'toggleable' tag can be toggled on/off.
        The lighting system scans the graph for lit items."""
        from engine.item_reach import find_reachable
        item_node = find_reachable(self.graph, None, player_manager, item_name)
        if not item_node:
            raise ValueError(f"You don't have '{item_name}'.")

        player = player_manager.players.get(player_manager.active_player)
        if not player:
            raise ValueError("No active player.")

        tags = item_node.properties.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]
        if "toggleable" not in tags:
            raise ValueError(f"The {item_name} can't be toggled on or off.")

        current = item_node.properties.get("current_state", "unlit")
        new_status = "unlit" if current == "lit" else "lit"
        was_depleted = False

        if new_status == "lit":
            uses = item_node.properties.get("uses", -1)
            if uses == 0:
                raise ValueError(f"The {item_name} is depleted and can't be turned on.")
            if uses > 0:
                item_node.properties["uses"] = uses - 1
                if uses - 1 == 0:
                    was_depleted = True

        old_light = None
        light_area_id = None
        light_area_name = player_manager.current_area.name if player_manager.current_area else None
        if "light_source" in tags and player_manager.current_area and hasattr(player_manager, 'lighting'):
            for n in self.graph.nodes.values():
                if n.type == "area" and n.name == light_area_name:
                    light_area_id = n.id
                    break
            if light_area_id:
                env_node = next((n for n in self.graph.nodes.values() if n.id == light_area_id), None)
                if env_node:
                    env = env_node.properties.get("environment", {})
                    old_light = player_manager.lighting.get_ambient_light(light_area_id, env)

        item_node.properties["current_state"] = new_status
        item_node.updated = __import__('time').time()

        is_electric = any(t in tags for t in ["electric", "synthetic"])
        if new_status == "lit":
            verb = "turn on" if is_electric else "light"
        else:
            verb = "turn off" if is_electric else "extinguish"
        result = f"You {verb} the {item_name}."

        if new_status == "lit":
            trig_outputs = player_manager._execute_triggers(item_node, "on_toggle_on")
        else:
            trig_outputs = player_manager._execute_triggers(item_node, "on_toggle_off")
        if trig_outputs:
            result += "\n" + "\n".join(trig_outputs)

        if was_depleted:
            item_node.properties["current_state"] = "unlit"
            dep_outputs = player_manager._execute_triggers(item_node, "on_depleted")
            if dep_outputs:
                result += "\n" + "\n".join(dep_outputs)

        area_name = player_manager.current_area.name if player_manager.current_area else None
        env_desc = ""
        if "light_source" in tags and player_manager.current_area and hasattr(player_manager, 'lighting') and light_area_id:
            env_node = next((n for n in self.graph.nodes.values() if n.id == light_area_id), None)
            if env_node:
                env = env_node.properties.get("environment", {})
                new_light = player_manager.lighting.get_ambient_light(light_area_id, env)
                level = player_manager.lighting.light_to_level(new_light)
                env_desc = f" The area is now {level}."
                if old_light is not None and old_light != new_light:
                    old_level = player_manager.lighting.light_to_level(old_light)
                    player_manager.add_log_entry(
                        f"[System] {player_manager.active_player} used {item_name} in {env_node.name}, "
                        f"light changed from {old_level} to {level}"
                    )
        result += env_desc
        turn_msg = f"turned the {item_name} {new_status}.{env_desc}"
        player_manager.record_turn_event(player_manager.active_player, "toggle", turn_msg, area_name=area_name)
        return result
