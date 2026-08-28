"""Transfer verbs (give / steal) for ItemActions.

Moved verbatim from engine/item_actions.py as part of the task-314
verb-family split. Methods hang off the ItemActions context (graph,
matching, trigger_system, world) via the mixin.
"""

import random

from graph import EDGE_CARRYING, EDGE_EQUIPPED, EDGE_IN, Edge


class TransferActionsMixin:
    """give_item / steal_item — same-area character-to-character transfer."""

    def give_item(self, player_manager, item_name: str, target_name: str) -> str:
        """Hand a carried item to another character in the same area."""
        if player_manager.player.state in ["sleeping", "unconscious", "bound"]:
            raise ValueError(f"You can't give items while {player_manager.player.state}.")
        if player_manager.player.state == "dead" and not player_manager.ghost_mode:
            raise ValueError("Your body lies still. You can do nothing.")

        target = player_manager.players.get(target_name)
        if not target and self.matching is not None and hasattr(self.matching, "_match_character_name"):
            resolved, candidates = self.matching._match_character_name(target_name)
            if resolved:
                target_name = resolved
                target = player_manager.players.get(resolved)
            elif candidates:
                raise ValueError(f"You don't know exactly who that is. Do you mean: {', '.join(candidates)}?")
        if not target:
            raise ValueError(f"There's no one named '{target_name}' here.")
        if target.current_area != player_manager.current_area.name:
            raise ValueError(f"{target_name} isn't in the same area as you.")

        from engine.character_spatial import _pm_get_player_node_id, approach_character
        approach_character(self.graph, player_manager, target_name)

        item_node = player_manager.find_item_node(item_name)
        if not item_node:
            raise ValueError(f"You aren't carrying '{item_name}'.")
        item_node_id = item_node.id

        p = player_manager.players.get(player_manager.active_player)
        if p:
            for slot, stack in list(p.equipped.items()):
                if item_node_id in stack:
                    stack.remove(item_node_id)
                    break

        player_id = player_manager._player_node_id(player_manager.active_player)
        target_player_id = _pm_get_player_node_id(player_manager, target_name)
        self.graph.remove_edge(item_node_id, player_id, EDGE_CARRYING)
        for edge in list(self.graph.get_edges_for_source(item_node_id, EDGE_IN)):
            self.graph.remove_edge(edge.source, edge.target, EDGE_IN)
        self.graph.add_edge(Edge(source=item_node_id, target=target_player_id, type=EDGE_CARRYING))

        trigger_outputs = self._exec_triggers(item_node, "on_drop") if item_node else []

        area_name = player_manager.current_area.name if player_manager.current_area else None
        player_manager.record_turn_event(player_manager.active_player, "give", f"gave {item_name} to {target_name}", area_name=area_name)
        # A gift warms BOTH directions (task-349): the recipient warms toward
        # the giver, and the giver warms toward the recipient, matching how
        # speech updates both sides (task-94: closeness gate).
        tick = getattr(player_manager, "time_ticks", 0) or 0
        if hasattr(target, "update_relationship"):
            target.update_relationship(player_manager.active_player, tick, 5)
        giver = player_manager.players.get(player_manager.active_player)
        if giver and hasattr(giver, "update_relationship"):
            giver.update_relationship(target_name, tick, 5)
        result = f"You hand the {item_name} to {target_name}."
        if trigger_outputs:
            result += "\n" + "\n".join(trigger_outputs)
        return result

    def steal_item(self, player_manager, item_name: str, target_name: str) -> str:
        """Attempt to steal an item from another character in the same area.
        Sleight of Hand vs Perception contest."""
        if player_manager.player.state in ["sleeping", "unconscious", "bound"]:
            raise ValueError(f"You can't steal while {player_manager.player.state}.")
        if player_manager.player.state == "dead" and not player_manager.ghost_mode:
            raise ValueError("Your body lies still. You can do nothing.")

        target = player_manager.players.get(target_name)
        if not target and self.matching is not None and hasattr(self.matching, "_match_character_name"):
            resolved, candidates = self.matching._match_character_name(target_name)
            if resolved:
                target_name = resolved
                target = player_manager.players.get(resolved)
            elif candidates:
                raise ValueError(f"You don't know exactly who that is. Do you mean: {', '.join(candidates)}?")
        if not target:
            raise ValueError(f"There's no one named '{target_name}' here.")
        if target.current_area != player_manager.current_area.name:
            raise ValueError(f"{target_name} isn't in the same area as you.")

        from engine.character_spatial import _pm_get_player_node_id, approach_character
        approach_character(self.graph, player_manager, target_name)

        target_player_id = _pm_get_player_node_id(player_manager, target_name)

        # Find item in target's inventory
        item_node = None
        for edge_type in (EDGE_CARRYING, EDGE_EQUIPPED):
            for edge in self.graph.get_edges_for_target(target_player_id, edge_type):
                node = self.graph.get_node(edge.source)
                if node and node.type == "item":
                    normalized_item = item_name.lower().replace("_", " ").replace("-", " ")
                    normalized_node = node.name.lower().replace("_", " ").replace("-", " ")
                    if normalized_item == normalized_node or normalized_item in normalized_node:
                        item_node = node
                        break
            if item_node:
                break
        if not item_node:
            raise ValueError(f"{target_name} doesn't have a '{item_name}' to steal.")

        item_node_id = item_node.id

        # Sleight of Hand vs target's Perception
        sleight_skill = player_manager.player.skills.get("Sleight of Hand", 0)
        per_skill = target.skills.get("Perception", 0)
        sleight_roll = random.randint(1, 20) + sleight_skill
        per_roll = random.randint(1, 20) + per_skill

        player_manager.add_log_entry(
            f"[Steal] {player_manager.active_player} tries to steal {item_node.name} "
            f"from {target_name}: Sleight of Hand {sleight_roll} vs Perception {per_roll}"
        )

        if sleight_roll >= per_roll:
            # Success — move item from target to player
            for edge in list(self.graph.get_edges_for_source(item_node_id, EDGE_IN)):
                self.graph.remove_edge(edge.source, edge.target, EDGE_IN)
            self.graph.remove_edge(item_node_id, target_player_id, EDGE_CARRYING)
            self.graph.remove_edge(item_node_id, target_player_id, EDGE_EQUIPPED)
            player_id = player_manager._player_node_id(player_manager.active_player)
            self.graph.add_edge(Edge(source=item_node_id, target=player_id, type=EDGE_CARRYING))

            player_manager.add_log_entry(
                f"{player_manager.active_player} steals {item_node.name} from {target_name}."
            )
            trigger_outputs = self._exec_triggers(item_node, "on_take") if item_node else []
            result = f"You deftly slip the {item_node.name} from {target_name}."
            if trigger_outputs:
                result += "\n" + "\n".join(trigger_outputs)
            return result
        else:
            player_manager.add_log_entry(
                f"{target_name} notices {player_manager.active_player} trying to steal {item_node.name}!"
            )
            raise ValueError(
                f"You reach for the {item_node.name}, but {target_name} notices you! "
                f"(Sleight of Hand {sleight_roll} vs Perception {per_roll})"
            )
