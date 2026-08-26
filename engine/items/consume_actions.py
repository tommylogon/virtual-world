"""Consume verbs (eat / drink) for ItemActions.

Moved verbatim from engine/item_actions.py as part of the task-314
verb-family split. Methods hang off the ItemActions context (graph,
matching, trigger_system, ghost_system, world) via the mixin.
"""


def _is_valid_for(node, trigger_type: str) -> bool:
    """Same acceptance rule as _consume_item's validity gate, so bare
    eat/drink auto-pick only grabs items that would pass anyway."""
    actions = node.properties.get("actions", [])
    if isinstance(actions, str):
        actions = [a.strip() for a in actions.split(",")]
    tags = [str(t).lower() for t in node.properties.get("tags", [])]
    if trigger_type == "on_eat":
        return "eat" in actions or "food" in tags
    if trigger_type == "on_drink":
        return "drink" in actions or "drink" in tags
    return False


def _pick_consumable(graph, player_manager, trigger_type: str):
    """First reachable item valid for this consume verb — carried items
    come first via reachable_items' ordering; deterministic pick."""
    from engine.item_reach import reachable_items
    for node in reachable_items(graph, player_manager):
        if _is_valid_for(node, trigger_type):
            return node
    return None


class ConsumeActionsMixin:
    """eat / drink / shared consume pipeline."""

    def eat_item(self, player_manager, item_name: str) -> str:
        return self._consume_item(player_manager, item_name, "on_eat", "eat")

    def drink_item(self, player_manager, item_name: str) -> str:
        return self._consume_item(player_manager, item_name, "on_drink", "drink")

    def _consume_item(self, player_manager, item_name: str, trigger_type: str, action_verb: str) -> str:
        ghost_block = self.ghost_system.check_ghost_action(player_manager, action_verb, item_name)
        if ghost_block:
            raise ValueError(ghost_block)

        if not str(item_name or "").strip():
            # Bare eat/drink (task-335): auto-pick the first consumable in
            # reach — carried items first, then the area subtree. A blank
            # name must NOT fall through to find_item_node: its containment
            # match ('' in anything) would grab the first carried object,
            # edible or not.
            item_node = _pick_consumable(self.graph, player_manager, trigger_type)
            if item_node is None:
                raise ValueError(f"You have nothing to {action_verb}.")
            item_name = item_node.name
        else:
            item_node = player_manager.find_item_node(item_name)
            if not item_node:
                # Not carried — food/drink anywhere reachable counts (room,
                # surfaces, open containers, equipped backpack contents).
                from engine.item_reach import find_reachable
                item_node = find_reachable(self.graph, self.matching, player_manager, item_name)
            if not item_node:
                raise ValueError(f"You don't have '{item_name}'.")
        if player_manager.player.state in ["sleeping", "unconscious", "bound"]:
            raise ValueError(f"You can't {action_verb} items while {player_manager.player.state}.")
        if player_manager.player.state == "dead" and not player_manager.ghost_mode:
            raise ValueError("Your body lies still. You can do nothing.")

        item_actions = item_node.properties.get("actions", [])
        if isinstance(item_actions, str):
            item_actions = [a.strip() for a in item_actions.split(",")]
        item_tags = [t.lower() for t in item_node.properties.get("tags", [])]

        is_valid = False
        if trigger_type == "on_eat":
            is_valid = "eat" in item_actions or "food" in item_tags
        elif trigger_type == "on_drink":
            is_valid = "drink" in item_actions or "drink" in item_tags

        if not is_valid:
            available = self.trigger_system._get_available_actions(item_node)
            raise ValueError(self.trigger_system._contextual_failure(action_verb, item_node.name, available))

        result = f"You {action_verb} the {item_name}."

        if hasattr(player_manager.player, 'exhaustion_count') and player_manager.player.exhaustion_count > 0:
            player_manager.player.exhaustion_count = 0

        trigger_outputs = self._exec_triggers(item_node, trigger_type)
        if trigger_outputs:
            result += "\n" + "\n".join(trigger_outputs)
            if not self.graph.get_node(item_node.id):
                return result

        skill_check_config = item_node.properties.get("skill_check", {})
        if skill_check_config and skill_check_config.get("skill"):
            skill_name = skill_check_config["skill"]
            dc = skill_check_config.get("dc", 10)
            success, total, message = player_manager.skill_check(skill_name, dc)
            result += " " + message
            if not success:
                result += f" You fail to {action_verb} the {item_name} properly."
                return result

        p_check = player_manager.players.get(player_manager.active_player)
        if not (p_check and p_check.state == "dead"):
            item_cost = item_node.properties.get("action_costs", {}).get(action_verb, {})
            player_manager.apply_action(action_verb, item_cost, player=player_manager.player)

        area_name = player_manager.current_area.name if player_manager.current_area else None
        past_verb = "ate" if action_verb == "eat" else "drank"
        player_manager.record_turn_event(player_manager.active_player, action_verb, f"{past_verb} the {item_name}", area_name=area_name)
        return result
