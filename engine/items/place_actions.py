"""Container / placement verbs for ItemActions.

Moved verbatim from engine/item_actions.py as part of the task-314
verb-family split. Methods hang off the ItemActions context (graph,
matching, trigger_system, ghost_system) via the mixin.
"""

from graph import (
    EDGE_AT,
    EDGE_BEHIND,
    EDGE_BESIDE,
    EDGE_CARRYING,
    EDGE_IN,
    EDGE_ON,
    EDGE_UNDER,
    Edge,
)


class PlaceActionsMixin:
    """put_item_in_container / place_item plus placement-edge cleanup."""

    def put_item_in_container(self, player_manager, item_name: str, container_name: str) -> str:
        player_id = player_manager._player_node_id(player_manager.active_player)

        ghost_block = self.ghost_system.check_ghost_action(player_manager, "put", item_name)
        if ghost_block:
            raise ValueError(ghost_block)

        if player_manager.player.state in ["sleeping", "unconscious", "bound"]:
            raise ValueError(f"You can't put items while {player_manager.player.state}.")
        if player_manager.player.state == "dead" and not player_manager.ghost_mode:
            raise ValueError("Your body lies still. You can do nothing.")

        item_node = player_manager.find_item_node(item_name)
        moving_uncarried = False
        if not item_node:
            # Move-without-taking: relocate something reachable where it lies.
            from engine.item_reach import find_reachable
            item_node = find_reachable(self.graph, self.matching, player_manager, item_name)
            moving_uncarried = item_node is not None
        if not item_node:
            raise ValueError(f"You aren't carrying '{item_name}'.")
        item_node_id = item_node.id

        container_node = player_manager.find_item_node(container_name)
        if not container_node:
            from engine.item_reach import find_reachable
            container_node = find_reachable(self.graph, self.matching, player_manager, container_name)
        if not container_node:
            raise ValueError(f"You don't have a '{container_name}' to put things in.")
        container_node_id = container_node.id

        # Capacity check
        item_weight = item_node.properties.get("weight", 0)
        cap_error = self._check_container_capacity(container_node_id, item_weight)
        if cap_error:
            raise ValueError(cap_error)

        container_tags = container_node.properties.get("tags", [])
        if isinstance(container_tags, str):
            container_tags = [t.strip() for t in container_tags.split(",")]
        if not any(t.lower() == "container" for t in container_tags):
            raise ValueError(f"The {container_name} isn't a container.")
        # A closed box won't take a sock IN it.
        container_state = (container_node.properties.get("current_state") or "").lower()
        if container_state in ("closed", "locked", "sealed"):
            raise ValueError(f"The {container_name} is {container_state} — open it first.")

        p = player_manager.players.get(player_manager.active_player)
        if p:
            for slot, stack in list(p.equipped.items()):
                if item_node_id in stack:
                    stack.remove(item_node_id)
                    break

        self.graph.remove_edge(item_node_id, player_id, EDGE_CARRYING)
        self._clear_placement_edges(item_node_id)
        self.graph.add_edge(Edge(source=item_node_id, target=container_node_id, type=EDGE_IN))

        trigger_outputs = self._exec_triggers(item_node, "on_drop") if item_node else []
        if container_node:
            trigger_outputs += self._exec_triggers(container_node, "on_use") if self.trigger_system else []

        p_check = player_manager.players.get(player_manager.active_player)
        if not (p_check and p_check.state == "dead"):
            player_manager.apply_action("put", player=player_manager.player)

        area_name = player_manager.current_area.name if player_manager.current_area else None
        player_manager.record_turn_event(player_manager.active_player, "put", f"put {item_name} in {container_name}", area_name=area_name)
        verb_past = "move" if moving_uncarried else "put"
        result = f"You {verb_past} the {item_name} in the {container_name}."
        if trigger_outputs:
            result += "\n" + "\n".join(trigger_outputs)
        return result

    def place_item(self, player_manager, item_name: str, target_name: str, relation: str = "on") -> str:
        """Place a carried item onto/under/beside/behind/at/inside a target in the same area.

        `relation` maps to a graph edge type: on, under, behind, beside, at, in.
        Surfaces are furniture/objects; containers accept `in` (and on/under/etc too).
        """
        relation = (relation or "on").strip().lower()
        edge_type = {
            "on": EDGE_ON,
            "under": EDGE_UNDER,
            "behind": EDGE_BEHIND,
            "beside": EDGE_BESIDE,
            "at": EDGE_AT,
            "in": EDGE_IN,
        }.get(relation, EDGE_ON)

        if player_manager.player.state in ["sleeping", "unconscious", "bound"]:
            raise ValueError(f"You can't put items while {player_manager.player.state}.")
        if player_manager.player.state == "dead" and not player_manager.ghost_mode:
            raise ValueError("Your body lies still. You can do nothing.")

        item_node = player_manager.find_item_node(item_name)
        moving_uncarried = False
        if not item_node:
            # Move-without-taking: relocate something reachable where it lies.
            from engine.item_reach import find_reachable
            item_node = find_reachable(self.graph, self.matching, player_manager, item_name)
            moving_uncarried = item_node is not None
        if not item_node:
            raise ValueError(f"You aren't carrying '{item_name}'.")
        item_node_id = item_node.id

        target_node = player_manager.find_item_node(target_name)
        if not target_node:
            from engine.item_reach import find_reachable
            target_node = find_reachable(self.graph, self.matching, player_manager, target_name)
        if not target_node:
            raise ValueError(f"You don't see a '{target_name}' here to put things on.")
        target_node_id = target_node.id

        if target_node_id == item_node_id:
            raise ValueError("You can't put something on itself.")

        if edge_type == EDGE_IN:
            container_tags = target_node.properties.get("tags", [])
            if isinstance(container_tags, str):
                container_tags = [t.strip() for t in container_tags.split(",")]
            if not any(t.lower() == "container" for t in container_tags):
                raise ValueError(f"The {target_name} isn't a container — try 'on', 'under', 'beside', 'behind', or 'at'.")
            # A closed box won't take a sock IN it — spatial relations still fine.
            target_state = (target_node.properties.get("current_state") or "").lower()
            if target_state in ("closed", "locked", "sealed"):
                raise ValueError(f"The {target_name} is {target_state} — open it first.")
            cap_error = self._check_container_capacity(target_node_id, item_node.properties.get("weight", 0))
            if cap_error:
                raise ValueError(cap_error)

        from engine.character_spatial import approach_item
        char_relation = edge_type if edge_type != EDGE_IN else EDGE_AT
        approach_item(self.graph, player_manager, target_name, target_node, relation=char_relation)

        p = player_manager.players.get(player_manager.active_player)
        if p:
            for slot, stack in list(p.equipped.items()):
                if item_node_id in stack:
                    stack.remove(item_node_id)
                    break

        self.graph.remove_edge(item_node_id, player_manager._player_node_id(player_manager.active_player), EDGE_CARRYING)
        self._clear_placement_edges(item_node_id)
        self.graph.add_edge(Edge(source=item_node_id, target=target_node_id, type=edge_type))

        trigger_outputs = self._exec_triggers(item_node, "on_drop") if item_node else []
        if target_node:
            trigger_outputs += self._exec_triggers(target_node, "on_use") if self.trigger_system else []

        p_check = player_manager.players.get(player_manager.active_player)
        if not (p_check and p_check.state == "dead"):
            player_manager.apply_action("put", player=player_manager.player)

        relation_prep = {"on": "on", "under": "under", "behind": "behind", "beside": "beside", "at": "at", "in": "in"}.get(relation, "on")
        area_name = player_manager.current_area.name if player_manager.current_area else None
        player_manager.record_turn_event(player_manager.active_player, "put", f"put {item_name} {relation_prep} {target_name}", area_name=area_name)
        verb_past = "move" if moving_uncarried else "put"
        result = f"You {verb_past} the {item_name} {relation_prep} the {target_name}."
        if trigger_outputs:
            result += "\n" + "\n".join(trigger_outputs)
        return result

    def _clear_placement_edges(self, item_node_id: str):
        """Remove every placement edge pointing FROM an item (in + spatial).

        Used by put/place so a moved item leaves no ghost placement behind
        (matters for move-without-taking, where the item was never picked
        up and take never cleared its edges)."""
        for etype in (EDGE_IN, EDGE_ON, EDGE_UNDER, EDGE_BESIDE, EDGE_BEHIND, EDGE_AT):
            for edge in list(self.graph.get_edges_for_source(item_node_id, etype)):
                self.graph.remove_edge(edge.source, edge.target, etype)
