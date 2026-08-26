"""NPC behavior action execution for TriggerSystem.

Moved from engine/trigger_system.py.
"""

from typing import Any, List, Optional

from graph import EDGE_IN


class BehaviorMixin:
    """NPC behavior action execution."""

    def _execute_behavior_actions(
        self,
        char_name: str,
        actions: List[dict],
        game_state: Optional[Any] = None,
    ) -> List[str]:
        """Execute a list of action dicts for an NPC behaviour.

        Returns a list of output strings describing what happened.

        *game_state* must provide:

        * ``game_state.players`` — dict of all Player objects
        * ``game_state.active_player`` — current active player name (rw)
        * ``game_state.graph`` — the WorldGraph
        * ``game_state.broadcast_speech(speaker, text)``
        * ``game_state.time_ticks`` — current tick count
        * ``game_state._get_current_area_id()``
        * ``game_state.player`` — active Player object
        * ``game_state.current_area`` — Area object for current area
        """
        outputs = []
        if game_state is None:
            return outputs
        player = game_state.players.get(char_name)
        if player is None:
            return outputs
        old_active = game_state.active_player
        game_state.active_player = char_name
        try:
            for action in actions:
                action_type = action.get("type", "message")

                if action_type == "message":
                    text = action.get("text", "")
                    if not text.strip():
                        continue
                    outputs.append(f"[{char_name}] {text}")

                elif action_type == "speak":
                    text = action.get("text", "...")
                    game_state.broadcast_speech(char_name, text)
                    outputs.append(f'{char_name} says: "{text}"')

                elif action_type == "set_npc_state":
                    new_state = action.get("state", "idle")
                    if new_state != player.npc_state:
                        old_state = player.npc_state
                        player.npc_state = new_state
                        player.state_enter_tick = game_state.time_ticks
                        outputs.append(
                            f"[{char_name}] state: {old_state} -> {new_state}"
                        )

                elif action_type == "damage":
                    amount = int(action.get("amount", 5))
                    target = action.get("target", "player")
                    if target == "player":
                        target_player = (
                            game_state.players.get(game_state.active_player)
                            if game_state.active_player
                            else None
                        )
                        if target_player:
                            target_player.vitals["HP"] = max(
                                0,
                                target_player.vitals.get("HP", 100) - amount,
                            )
                            outputs.append(
                                f"{game_state.active_player} takes {amount} damage!"
                            )
                    elif target == "self" and player:
                        player.vitals["HP"] = max(
                            0, player.vitals.get("HP", 100) - amount
                        )
                        outputs.append(f"{char_name} takes {amount} damage!")

                elif action_type == "heal":
                    amount = int(action.get("amount", 10))
                    stat = action.get("stat", "HP")
                    target_name = action.get("target", "self")
                    target_player = (
                        game_state.players.get(target_name)
                        if target_name in game_state.players
                        else player
                    )
                    if target_player and stat in target_player.vitals:
                        target_player.vitals[stat] = min(
                            100,
                            target_player.vitals.get(stat, 100) + amount,
                        )

                elif action_type == "set_environment":
                    stat = action.get("stat", "temperature")
                    amount = int(action.get("amount", 0))
                    target_area_name = action.get("area", player.current_area)
                    target_area_node = None
                    for node in game_state.graph.nodes.values():
                        if node.type == "area" and node.name == target_area_name:
                            target_area_node = node
                            break
                    if target_area_node:
                        env = target_area_node.properties.setdefault(
                            "environment", {}
                        )
                        env[stat] = env.get(stat, 20) + amount
                        outputs.append(
                            f"The {stat} in {target_area_name} changes by {amount}."
                        )

                elif action_type == "spawn_item":
                    item_id = action.get("item_id", "")
                    if item_id and player.current_area:
                        area_id = game_state._get_current_area_id()
                        if area_id:
                            spawn_node = game_state.graph.get_node(item_id)
                            if spawn_node is None:
                                try:
                                    import os, json
                                    lib_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'library', 'items')
                                    lib_path = os.path.join(lib_dir, f"{item_id}.json")
                                    if os.path.exists(lib_path):
                                        with open(lib_path, 'r', encoding='utf-8') as f:
                                            lib_data = json.load(f)
                                except Exception:
                                    lib_data = {}

                                display_name = action.get("display_name") or action.get("name") or lib_data.get("name", item_id)
                                desc = action.get("description") or lib_data.get("description", "")
                                tags = lib_data.get("tags", [])
                                uses = lib_data.get("uses", -1)
                                weight = lib_data.get("weight", 0.1)

                                spawn_node = Node(
                                    id=item_id,
                                    type="item",
                                    name=display_name,
                                    properties={
                                        "description": desc,
                                        "tags": tags,
                                        "uses": uses,
                                        "weight": weight,
                                    },
                                )
                                game_state.graph.add_node(spawn_node)
                            for edge in game_state.graph.edges[:]:
                                if (
                                    edge.source == item_id
                                    and edge.type == EDGE_IN
                                ):
                                    game_state.graph.edges.remove(edge)
                            game_state.graph.add_edge(
                                Edge(
                                    source=item_id,
                                    target=area_id,
                                    type=EDGE_IN,
                                )
                            )

                elif action_type == "teleport":
                    target_area = action.get("area", "")
                    target_char = action.get("target", "player")
                    target_name = (
                        game_state.active_player
                        if target_char == "player"
                        else action.get("character_name", char_name)
                    )
                    target_player = game_state.players.get(target_name)
                    if target_player and target_area:
                        for node in game_state.graph.nodes.values():
                            if (
                                node.type == "area"
                                and node.name == target_area
                            ):
                                target_player.current_area = target_area
                                outputs.append(
                                    f"{target_name} vanishes and reappears elsewhere!"
                                )
                                break

                elif action_type == "go":
                    if hasattr(game_state, "npc_behaviors"):
                        msg = game_state.npc_behaviors.execute_go_action(
                            char_name, action
                        )
                        if msg:
                            outputs.append(msg)
                    else:
                        target_area = action.get("area") or action.get("room", "")
                        if target_area and player.current_area:
                            area_exists = any(
                                node.type == "area" and node.name == target_area
                                for node in game_state.graph.nodes.values()
                            )
                            if area_exists:
                                player.current_area = target_area
                                outputs.append(
                                    f"[{char_name}] moves to {target_area}."
                                )
                            else:
                                outputs.append(
                                    f"[{char_name}] cannot find area '{target_area}'."
                                )
        finally:
            game_state.active_player = old_active
        return outputs
