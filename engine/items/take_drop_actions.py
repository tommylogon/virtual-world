"""Take / drop verbs and placement-memory helpers for ItemActions.

Moved verbatim from engine/item_actions.py as part of the task-314
verb-family split. Methods hang off the ItemActions context (graph,
matching, trigger_system, equipment, ghost_system, world) via the mixin.
"""

from typing import Optional
import re

from graph import (
    EDGE_AT,
    EDGE_BEHIND,
    EDGE_BESIDE,
    EDGE_CARRYING,
    EDGE_CONNECTION,
    EDGE_EQUIPPED,
    EDGE_IN,
    EDGE_ON,
    EDGE_UNDER,
    Edge,
    Node,
)
from engine.items.errors import AmbiguousItemError


def _display_name(name):
    """Strip a leading article so verb phrasings don't double up.

    e.g. "You pick up the {item_name}" with item_name="the iron key" would
    become "the the iron key" — this normalises the noun first. No-op when the
    name has no leading article (the common canonical case).
    """
    return re.sub(r'^(?:the|a|an)\s+', '', str(name or '').strip())


class TakeDropActionsMixin:
    """take / drop / drop_held_items plus last-relation bookkeeping."""

    def _register_item_discovery(self, player_manager, item_name: str):
        """Grant an Entertainment novelty boost the first time a character
        discovers an item (examine/take of something not seen before).

        Mirrors the area-visit boost in movement.py: curious gets +50%,
        homebody gets nothing. Returns True if the item was newly discovered.
        """
        try:
            from engine.traits import TraitSystem
        except ImportError:
            return False
        player = player_manager.player
        if not player or "Entertainment" not in player.vitals or not item_name:
            return False
        if item_name in player.discovered_items:
            return False
        player.discovered_items.add(item_name)
        base_boost = 8
        if TraitSystem.has_effect(player, "curious"):
            base_boost = int(base_boost * 1.5)
        if TraitSystem.has_effect(player, "homebody"):
            base_boost = 0
        player.vitals["Entertainment"] = min(100, player.vitals.get("Entertainment", 50) + base_boost)
        return True

    def _stamp_last_relation(self, item_node):
        """Record the item's current spatial relation before pickup."""
        if not item_node or not item_node.id:
            return
        for etype in (EDGE_ON, EDGE_UNDER, EDGE_BEHIND, EDGE_BESIDE, EDGE_AT):
            edges = list(self.graph.get_edges_for_source(item_node.id, etype))
            if edges:
                target_node = self.graph.get_node(edges[0].target)
                item_node.properties["last_relation"] = {
                    "relation": etype,
                    "target_id": edges[0].target,
                    "target_name": target_node.name if target_node else "somewhere",
                }
                return
        edges = list(self.graph.get_edges_for_source(item_node.id, EDGE_IN))
        if edges:
            target_node = self.graph.get_node(edges[0].target)
            item_node.properties["last_relation"] = {
                "relation": EDGE_IN,
                "target_id": edges[0].target,
                "target_name": target_node.name if target_node else "somewhere",
            }

    def _clear_last_relation(self, item_node):
        """Remove last_relation when the item is equipped (now in hand)."""
        if item_node and "last_relation" in item_node.properties:
            del item_node.properties["last_relation"]

    def _restore_last_relation(self, item_node, player_manager, area_id):
        """Recreate the spatial edge from last_relation if the target still exists
        in the current area or in the player's inventory. Returns True on success."""
        last_rel = (item_node.properties or {}).get("last_relation")
        if not last_rel:
            return False
        target_id = last_rel.get("target_id")
        relation = last_rel.get("relation")
        if not target_id or not relation:
            return False
        target_node = self.graph.get_node(target_id)
        if not target_node:
            return False
        # Allow if target is the current area, or inside the current area, or in player's inventory
        if target_id != area_id:
            if not any(e.source == area_id and e.type == EDGE_IN for e in self.graph.get_edges_for_target(target_id, EDGE_IN)):
                player_id = player_manager._player_node_id(player_manager.active_player)
                if not any(e.source == player_id and e.type in (EDGE_CARRYING, EDGE_EQUIPPED)
                           for e in self.graph.get_edges_for_target(target_id, EDGE_IN)):
                    return False
        self.graph.add_edge(Edge(source=item_node.id, target=target_id, type=relation))
        del item_node.properties["last_relation"]
        return True

    @staticmethod
    def _auto_select_identical(nodes) -> Optional[Node]:
        """If every candidate is a functionally identical copy (same name,
        description, tags and state — e.g. two jumpsuits placed from the same
        library item), auto-pick the first instead of prompting the player.
        Returns None when the copies differ, so the caller keeps the
        "Which one?" ambiguity prompt."""
        if not nodes:
            return None
        signatures = {
            (
                n.name,
                n.properties.get("description", ""),
                tuple(n.properties.get("tags", []) or []),
                n.properties.get("current_state", ""),
            )
            for n in nodes
        }
        return nodes[0] if len(signatures) == 1 else None

    def take_item(self, player_manager, item_name: str, item_id: Optional[str] = None) -> str:
        ghost_block = self.ghost_system.check_ghost_action(player_manager, "take", item_name)
        if ghost_block:
            raise ValueError(ghost_block)

        if not player_manager.current_area or player_manager.player.state in ["sleeping", "unconscious", "bound"]:
            raise ValueError(f"You can't take items while {player_manager.player.state}.")
        if player_manager.player.state == "dead" and not player_manager.ghost_mode:
            raise ValueError("Your body lies still. You can do nothing.")

        if not player_manager.current_area:
            raise ValueError("You are in an empty void.")

        # Already held? take on a carried/worn item is a no-op with a clear
        # message, not a search failure the LLM spirals over (bug, taco_bell
        # 2026-08-24: miki "took" the sauce she was holding and panicked).
        player_id = player_manager._player_node_id(player_manager.active_player)
        wanted = item_name.lower().replace('_', ' ').replace('-', ' ').strip()
        if wanted:
            for held_edge_type in (EDGE_CARRYING, EDGE_EQUIPPED):
                for edge in self.graph.get_edges_for_target(player_id, held_edge_type):
                    node = self.graph.get_node(edge.source)
                    if not node or node.type != "item":
                        continue
                    held = node.name.lower().replace('_', ' ').replace('-', ' ').strip()
                    if wanted == held or wanted in held:
                        if held_edge_type == EDGE_EQUIPPED:
                            return f"You're already wearing the {_display_name(node.name)}."
                        return f"You're already carrying the {_display_name(node.name)}."

        if not player_manager.lighting.can_see_in_dark(player_manager, player_manager.active_player):
            area_id = player_manager._get_current_area_id()
            if player_manager.lighting.get_ambient_light(area_id, player_manager.current_area.environment) < 20:
                raise ValueError("It's too dark to find anything. try to turn on some lights?")

        area_id = player_manager._get_current_area_id()
        item_node = None
        item_node_id = None
        was_in_container = False
        container_name = None
        spatial_relation = None
        spatial_surface_id = None
        spatial_surface_name = None
        hand_used = None
        stashed_item = None

        if item_id:
            item_node = self.graph.get_node(item_id)
            if item_node:
                item_node_id = item_id

        if not item_node:
            candidate_id = player_manager.item_node_id(item_name)
            candidate = self.graph.get_node(candidate_id)
            if candidate and self.matching._is_item_reachable(candidate_id, area_id):
                item_node_id = candidate_id
                item_node = candidate

        if not item_node:
            matching_nodes = []
            spatial_map = {}
            for edge in self.graph.get_edges_for_target(area_id, EDGE_IN):
                node = self.graph.get_node(edge.source)
                if node and node.name == item_name:
                    matching_nodes.append(node)
                    if edge.type in (EDGE_ON, EDGE_UNDER, EDGE_BEHIND, EDGE_BESIDE, EDGE_AT):
                        surface = self.graph.get_node(edge.target)
                        spatial_map[node.id] = (edge.type, edge.target, surface.name if surface else "somewhere")

            if len(matching_nodes) == 0:
                fuzzy_name = self.matching._match_item_name(item_name)
                if fuzzy_name and fuzzy_name != item_name:
                    for edge in self.graph.get_edges_for_target(area_id, EDGE_IN):
                        node = self.graph.get_node(edge.source)
                        if node and node.name == fuzzy_name:
                            matching_nodes.append(node)
                            if edge.type in (EDGE_ON, EDGE_UNDER, EDGE_BEHIND, EDGE_BESIDE, EDGE_AT):
                                surface = self.graph.get_node(edge.target)
                                spatial_map[node.id] = (edge.type, edge.target, surface.name if surface else "somewhere")

            if len(matching_nodes) == 1:
                item_node_id = matching_nodes[0].id
                item_node = matching_nodes[0]
                if item_node_id in spatial_map:
                    spatial_relation, spatial_surface_id, spatial_surface_name = spatial_map[item_node_id]
            elif len(matching_nodes) > 1:
                auto = self._auto_select_identical(matching_nodes)
                if auto:
                    item_node_id = auto.id
                    item_node = auto
                    if item_node_id in spatial_map:
                        spatial_relation, spatial_surface_id, spatial_surface_name = spatial_map[item_node_id]
                else:
                    options = []
                    for n in matching_nodes:
                        desc = n.properties.get("description", "")[:40]
                        tags = n.properties.get("tags", [])
                        extra = f" - {desc}" if desc else ""
                        if tags:
                            extra += f" [{', '.join(tags[:3])}]"
                        options.append({"id": n.id, "name": n.name, "description": extra.strip()})
                    raise AmbiguousItemError(
                        f"There are {len(matching_nodes)} items named '{item_name}'. Which one?",
                        options
                    )

        if not item_node:
            matching_nodes = []
            spatial_map = {}
            for edge in self.graph.get_edges_for_target(area_id, EDGE_IN):
                node = self.graph.get_node(edge.source)
                if node and item_name.lower() in node.name.lower():
                    matching_nodes.append(node)
                    if edge.type in (EDGE_ON, EDGE_UNDER, EDGE_BEHIND, EDGE_BESIDE, EDGE_AT):
                        surface = self.graph.get_node(edge.target)
                        spatial_map[node.id] = (edge.type, edge.target, surface.name if surface else "somewhere")
            if len(matching_nodes) == 1:
                item_node_id = matching_nodes[0].id
                item_node = matching_nodes[0]
                if item_node_id in spatial_map:
                    spatial_relation, spatial_surface_id, spatial_surface_name = spatial_map[item_node_id]
            elif len(matching_nodes) > 1:
                auto = self._auto_select_identical(matching_nodes)
                if auto:
                    item_node_id = auto.id
                    item_node = auto
                    if item_node_id in spatial_map:
                        spatial_relation, spatial_surface_id, spatial_surface_name = spatial_map[item_node_id]
                else:
                    options = []
                    for n in matching_nodes:
                        desc = n.properties.get("description", "")[:40]
                        options.append({"id": n.id, "name": n.name, "description": desc})
                    raise AmbiguousItemError(
                        f"There are {len(matching_nodes)} items matching '{item_name}'. Which one?",
                        options
                    )

        if not item_node:
            matching_nodes = []
            for container_edge in self.graph.get_edges_for_target(area_id, EDGE_IN):
                container_node = self.graph.get_node(container_edge.source)
                if container_node and container_node.type == "item":
                    if container_node.properties.get("current_state") == "locked":
                        continue
                    for content_edge in self.graph.get_edges_for_target(container_node.id, EDGE_IN):
                        node = self.graph.get_node(content_edge.source)
                        if node and node.type == "item" and node.properties.get("current_state") != "hidden":
                            normalized_item_name = item_name.lower().replace('_', ' ').replace('-', ' ')
                            normalized_node_name = node.name.lower().replace('_', ' ').replace('-', ' ')
                            if normalized_item_name == normalized_node_name or normalized_item_name in normalized_node_name:
                                matching_nodes.append(node)
                                container_name = container_node.name
            if len(matching_nodes) == 1:
                item_node_id = matching_nodes[0].id
                item_node = matching_nodes[0]
                was_in_container = True
            elif len(matching_nodes) > 1:
                auto = self._auto_select_identical(matching_nodes)
                if auto:
                    item_node_id = auto.id
                    item_node = auto
                    was_in_container = True
                else:
                    options = [{"id": n.id, "name": n.name, "description": n.properties.get("description", "")[:40]} for n in matching_nodes]
                    raise AmbiguousItemError(
                        f"There are {len(matching_nodes)} items matching '{item_name}' inside containers. Which one?",
                        options
                    )

        if not item_node:
            matching_nodes = []
            player_id = player_manager._player_node_id(player_manager.active_player)
            for container_edge in self.graph.get_edges_for_target(player_id, EDGE_CARRYING):
                container_node = self.graph.get_node(container_edge.source)
                if container_node and container_node.type == "item":
                    if container_node.properties.get("current_state") == "locked":
                        continue
                    for content_edge in self.graph.get_edges_for_target(container_node.id, EDGE_IN):
                        node = self.graph.get_node(content_edge.source)
                        if node and node.type == "item" and node.properties.get("current_state") != "hidden":
                            normalized_item_name = item_name.lower().replace('_', ' ').replace('-', ' ')
                            normalized_node_name = node.name.lower().replace('_', ' ').replace('-', ' ')
                            if normalized_item_name == normalized_node_name or normalized_item_name in normalized_node_name:
                                matching_nodes.append(node)
                                container_name = container_node.name
            if len(matching_nodes) == 1:
                item_node_id = matching_nodes[0].id
                item_node = matching_nodes[0]
                was_in_container = True
            elif len(matching_nodes) > 1:
                auto = self._auto_select_identical(matching_nodes)
                if auto:
                    item_node_id = auto.id
                    item_node = auto
                    was_in_container = True
                else:
                    options = [{"id": n.id, "name": n.name, "description": n.properties.get("description", "")[:40]} for n in matching_nodes]
                    raise AmbiguousItemError(
                        f"There are {len(matching_nodes)} items matching '{item_name}' inside containers. Which one?",
                        options
                    )

        if not item_node:
            visible_items = []
            for e in self.graph.get_edges_for_target(area_id, EDGE_IN):
                node = self.graph.get_node(e.source)
                if node and node.type == "item":
                    visible_items.append(node.name)
            raise ValueError(
                f"You search for '{item_name}' but can't find it here. "
                f"Items you can see: {', '.join(visible_items) if visible_items else 'nothing'}. "
            )

        # Frightened (item source): won't touch the item they fear (trait/gate)
        if player_manager.player.has_condition("frightened"):
            from engine.conditions import frightened_block
            block = frightened_block(
                player_manager.player, "item",
                source_id=item_node.id, source_name=item_node.name,
            )
            if block:
                raise ValueError(block)

        item_actions = item_node.properties.get("actions", [])
        if isinstance(item_actions, str):
            item_actions = [a.strip() for a in item_actions.split(",")]
        if "take" not in item_actions:
            available = self.trigger_system._get_available_actions(item_node)
            raise ValueError(self.trigger_system._contextual_failure("take", item_node.name, available))

        skill_check_config = item_node.properties.get("skill_check", {})
        if skill_check_config and skill_check_config.get("skill"):
            skill_name = skill_check_config["skill"]
            dc = skill_check_config.get("dc", 10)
            success, total, message = player_manager.skill_check(skill_name, dc)
            if not success:
                return f"You try to take the {_display_name(item_name)}, but hesitate. {message}"

        trigger_outputs = self._exec_triggers(item_node, "on_take")

        if not self.graph.get_node(item_node_id):
            return "\n".join(trigger_outputs) if trigger_outputs else f"The {_display_name(item_name)} is gone."

        self._stamp_last_relation(item_node)

        if was_in_container:
            for ce in list(self.graph.get_edges_for_source(item_node_id, EDGE_IN)):
                self.graph.edges.remove(ce)
            for etype in (EDGE_ON, EDGE_UNDER, EDGE_BEHIND, EDGE_BESIDE, EDGE_AT):
                for ce in list(self.graph.get_edges_for_source(item_node_id, etype)):
                    self.graph.edges.remove(ce)
        else:
            if spatial_relation and spatial_surface_id:
                self.graph.remove_edge(item_node_id, spatial_surface_id, spatial_relation)
            else:
                self.graph.remove_edge(item_node_id, area_id, EDGE_IN)
            for etype in (EDGE_ON, EDGE_UNDER, EDGE_BEHIND, EDGE_BESIDE, EDGE_AT):
                for ce in list(self.graph.get_edges_for_source(item_node_id, etype)):
                    self.graph.edges.remove(ce)
        player_id = player_manager._player_node_id(player_manager.active_player)
        cap_error = self._check_player_capacity(player_manager, float(item_node.properties.get("weight", 0) or 0))
        if cap_error:
            raise ValueError(cap_error)

        equip_slots = item_node.properties.get("equip_slots", [])
        if isinstance(equip_slots, str):
            equip_slots = [s.strip() for s in equip_slots.split(",")]
        hand_slots = [s for s in equip_slots if s in ("hand_left", "hand_right")]

        if hand_slots:
            player = player_manager.players.get(player_manager.active_player)
            if player:
                free_hand = None
                for hand in ["hand_right", "hand_left"]:
                    if not player.equipped.get(hand):
                        free_hand = hand
                        break

                if free_hand:
                    self.graph.add_edge(Edge(source=item_node_id, target=player_id, type=EDGE_EQUIPPED, properties={"slot": free_hand}))
                    player.equipped.setdefault(free_hand, []).append(item_node_id)
                    self.graph.remove_edges_for_node(item_node_id, EDGE_CONNECTION)
                    hand_used = free_hand
                else:
                    for hand in ["hand_right", "hand_left"]:
                        if player.equipped.get(hand):
                            old_item_id = player.equipped[hand].pop()
                            self.graph.remove_edge(old_item_id, player_id, EDGE_EQUIPPED)
                            self.graph.add_edge(Edge(source=old_item_id, target=player_id, type=EDGE_CARRYING))
                            self.graph.remove_edges_for_node(old_item_id, EDGE_CONNECTION)
                            old_item = self.graph.get_node(old_item_id)
                            if old_item:
                                self._exec_triggers(old_item, "on_unequip")
                                stashed_item = old_item.name
                            self.graph.add_edge(Edge(source=item_node_id, target=player_id, type=EDGE_EQUIPPED, properties={"slot": hand}))
                            player.equipped.setdefault(hand, []).append(item_node_id)
                            self.graph.remove_edges_for_node(item_node_id, EDGE_CONNECTION)
                            hand_used = hand
                            break
            else:
                self.graph.add_edge(Edge(source=item_node_id, target=player_id, type=EDGE_CARRYING))
        else:
            self.graph.add_edge(Edge(source=item_node_id, target=player_id, type=EDGE_CARRYING))

        self._register_item_discovery(player_manager, item_node.name)

        p_check = player_manager.players.get(player_manager.active_player)
        if not (p_check and p_check.state == "dead"):
            player_manager.apply_action("take", item_node.properties.get("action_costs", {}).get("take", {}), player=player_manager.player)

        area_name = player_manager.current_area.name if player_manager.current_area else None
        if spatial_relation and spatial_surface_name:
            prep = {EDGE_ON: "off", EDGE_UNDER: "from under", EDGE_BEHIND: "from behind", EDGE_BESIDE: "from beside", EDGE_AT: "from near"}.get(spatial_relation, "from")
            source = f" {prep} the {spatial_surface_name}"
        elif container_name:
            source = f" from the {container_name}"
        else:
            source = ""
        hand_text = f" with your {hand_used.replace('_', ' ')}" if hand_used else ""

        if hand_slots:
            if stashed_item:
                result = f"You put your {_display_name(stashed_item)} away and take the {_display_name(item_name)}{hand_text}{source}."
            else:
                result = f"You take the {_display_name(item_name)}{hand_text}{source}."
        else:
            result = f"You pick up the {_display_name(item_name)}{hand_text}{source}."

        event_verb = "equipped" if hand_slots else "picked up"
        player_manager.record_turn_event(player_manager.active_player, "take", f"{event_verb} the {_display_name(item_name)}{source}", area_name=area_name)

        if trigger_outputs:
            result += "\n" + "\n".join(trigger_outputs)

        if player_manager.active_player:
            for pname, p in list(player_manager.players.items()):
                if p.simple_npc and p.state != "dead":
                    self.world.process_simple_npcs("on_item_taken", {"target_item": item_name})

        return result

    def drop_item(self, player_manager, item_name: str) -> str:
        ghost_block = self.ghost_system.check_ghost_action(player_manager, "drop", item_name)
        if ghost_block:
            raise ValueError(ghost_block)

        if not player_manager.current_area or player_manager.player.state in ["sleeping", "unconscious", "bound"]:
            raise ValueError(f"You can't drop items while {player_manager.player.state}.")
        if player_manager.player.state == "dead" and not player_manager.ghost_mode:
            raise ValueError("Your body lies still. You can do nothing.")

        player_id = player_manager._player_node_id(player_manager.active_player)
        item_node_id = player_manager.item_node_id(item_name)

        for edge in self.graph.get_edges_for_target(player_id, EDGE_CARRYING):
            node = self.graph.get_node(edge.source)
            if node and node.name == item_name:
                item_node_id = node.id
                break
        else:
            raise ValueError(f"You aren't carrying '{item_name}'.")

        item_node = self.graph.get_node(item_node_id)

        p = player_manager.players.get(player_manager.active_player)
        if p:
            for slot, stack in list(p.equipped.items()):
                if item_node_id in stack:
                    stack.remove(item_node_id)
                    trigger_outputs = self._exec_triggers(item_node, "on_unequip") if item_node else []
                    break

        trigger_outputs = self._exec_triggers(item_node, "on_drop") if item_node else []

        self.graph.remove_edge(item_node_id, player_id, EDGE_CARRYING)
        self.graph.remove_edges_for_node(item_node_id, EDGE_CONNECTION)
        area_id = player_manager._get_current_area_id()
        if item_node:
            restored = self._restore_last_relation(item_node, player_manager, area_id)
            if not restored:
                self.graph.add_edge(Edge(source=item_node_id, target=area_id, type=EDGE_IN))
        else:
            self.graph.add_edge(Edge(source=item_node_id, target=area_id, type=EDGE_IN))

        p_check = player_manager.players.get(player_manager.active_player)
        if not (p_check and p_check.state == "dead"):
            player_manager.apply_action("drop", player=player_manager.player)

        area_name = player_manager.current_area.name if player_manager.current_area else None
        player_manager.record_turn_event(player_manager.active_player, "drop", f"dropped the {_display_name(item_name)}", area_name=area_name)
        result = f"You drop the {_display_name(item_name)}."
        if trigger_outputs:
            result += "\n" + "\n".join(trigger_outputs)
        return result

    def drop_held_items(self, player_manager, player_name: str) -> list:
        """Drop everything a character holds in their hands into their area.

        Fired when a condition with ``drops_held_items`` applies (unconscious,
        dead) — the character lets go of what's in hand_left/hand_right.
        Returns the names of the items dropped.
        """
        player = player_manager.players.get(player_name)
        if not player or not getattr(player, "current_area", None):
            return []
        player_id = player_manager._player_node_id(player_name)
        if player_name == player_manager.active_player:
            area_id = player_manager._get_current_area_id()
        else:
            area_id = f"area_{player.current_area.lower().replace(' ', '_')}"
        dropped = []
        for slot in ("hand_left", "hand_right"):
            stack = (player.equipped or {}).get(slot) or []
            for item_id in list(stack):
                if not item_id or str(item_id).startswith("__"):
                    continue
                stack.remove(item_id)
                for edge in list(self.graph.get_edges_for_target(player_id, EDGE_EQUIPPED)):
                    if edge.source == item_id:
                        self.graph.remove_edge(edge.source, edge.target, edge.type)
                self.graph.remove_edge(item_id, player_id, EDGE_CARRYING)
                self.graph.remove_edges_for_node(item_id, EDGE_CONNECTION)
                self.graph.add_edge(Edge(source=item_id, target=area_id, type=EDGE_IN))
                node = self.graph.get_node(item_id)
                if node:
                    dropped.append(node.name)
        return dropped
